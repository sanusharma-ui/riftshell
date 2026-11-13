import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from ai.config import AIConfig
from ai.desktop_settings import load_desktop_config
from ui.main_window import PreferencesDialog


class FakeSettings:
    def __init__(self, values):
        self.values = values

    def contains(self, key):
        return key in self.values

    def value(self, key, default=None, type=None):
        return self.values.get(key, default)


class FakeStore:
    def __init__(self, keys):
        self.keys = keys

    def get_password(self, service, account):
        return self.keys.get(account)


class DesktopSettingsTests(unittest.TestCase):
    def setUp(self):
        self.base = replace(
            AIConfig.from_env(),
            ai_provider="auto",
            groq_api_key="env-groq",
            gemini_api_key="env-gemini",
            ollama_model="",
            workspace_root=Path.cwd(),
            allow_outside_workspace=False,
        )

    def test_unset_desktop_preference_preserves_environment(self):
        with patch("ai.desktop_settings.AIConfig.from_env", return_value=self.base), patch(
            "ai.desktop_settings.QSettings", return_value=FakeSettings({})
        ):
            self.assertIs(load_desktop_config(), self.base)

    def test_saved_provider_and_key_override_environment(self):
        values = {
            "ai/provider": "groq",
            "ai/groq_model": "custom-model",
            "ai/ollama_base_url": "http://localhost:11434",
            "ai/ollama_model": "qwen-test",
            "ai/workspace_root": str(Path.cwd().parent),
            "ai/allow_outside_workspace": True,
        }
        store = FakeStore({"groq_api_key": "user-groq"})
        with patch("ai.desktop_settings.AIConfig.from_env", return_value=self.base), patch(
            "ai.desktop_settings.QSettings", return_value=FakeSettings(values)
        ), patch("ai.desktop_settings.credential_store", return_value=store):
            config = load_desktop_config()
        self.assertEqual(config.ai_provider, "groq")
        self.assertEqual(config.groq_api_key, "user-groq")
        self.assertEqual(config.gemini_api_key, "env-gemini")
        self.assertEqual(config.groq_model, "custom-model")
        self.assertEqual(config.workspace_root, Path.cwd().parent.resolve())
        self.assertTrue(config.allow_outside_workspace)

    def test_local_provider_needs_no_credential_store(self):
        values = {"ai/provider": "ollama", "ai/ollama_model": "local-model"}
        with patch("ai.desktop_settings.AIConfig.from_env", return_value=self.base), patch(
            "ai.desktop_settings.QSettings", return_value=FakeSettings(values)
        ), patch("ai.desktop_settings.credential_store", side_effect=AssertionError("keyring used")):
            config = load_desktop_config()
        self.assertEqual(config.ai_provider, "ollama")
        self.assertEqual(config.ollama_model, "local-model")
        self.assertEqual(config.groq_api_key, "")
        self.assertEqual(config.gemini_api_key, "")

    def test_colab_ollama_provider_loads_remote_url(self):
        values = {
            "ai/provider": "ollama",
            "ai/ollama_source": "colab",
            "ai/ollama_base_url": "https://custom-colab.ngrok-free.app",
            "ai/ollama_model": "deepseek-r1:8b",
        }
        with patch("ai.desktop_settings.AIConfig.from_env", return_value=self.base), patch(
            "ai.desktop_settings.QSettings", return_value=FakeSettings(values)
        ):
            config = load_desktop_config()
        self.assertEqual(config.ai_provider, "ollama")
        self.assertEqual(config.ollama_base_url, "https://custom-colab.ngrok-free.app")
        self.assertEqual(config.ollama_model, "deepseek-r1:8b")


class PreferencesDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["preferences-tests", "-platform", "offscreen"])

    def test_colab_source_selection_and_saving(self):
        preferences = {
            "ai_provider": "ollama",
            "groq_model": "llama-3.3-70b-versatile",
            "ollama_source": "colab",
            "ollama_base_url": "https://colab-tunnel.ngrok-free.app",
            "ollama_model": "llama3:8b",
            "workspace_root": str(Path.cwd()),
            "allow_outside_workspace": False,
            "theme": "vscode-dark-plus",
            "font_family": "Cascadia Code",
            "font_size": 11,
            "confirm_risky": True,
            "restore_history": True,
        }
        dialog = PreferencesDialog(preferences)
        self.assertEqual(dialog.ollama_source.currentData(), "colab")
        self.assertEqual(dialog.ollama_url.text(), "https://colab-tunnel.ngrok-free.app")

        saved = []
        dialog.preferences_saved.connect(saved.append)
        with patch.object(dialog, "accept"):
            dialog._save()

        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["ollama_source"], "colab")
        self.assertEqual(saved[0]["ollama_base_url"], "https://colab-tunnel.ngrok-free.app")
        self.assertEqual(saved[0]["ollama_model"], "llama3:8b")
        dialog.deleteLater()

    def test_switching_source_updates_placeholder_and_restores_url(self):
        preferences = {
            "ai_provider": "ollama",
            "groq_model": "llama-3.3-70b-versatile",
            "ollama_source": "local",
            "ollama_base_url": "http://127.0.0.1:11434",
            "ollama_model": "qwen:7b",
            "workspace_root": str(Path.cwd()),
            "allow_outside_workspace": False,
            "theme": "vscode-dark-plus",
            "font_family": "Cascadia Code",
            "font_size": 11,
            "confirm_risky": True,
            "restore_history": True,
        }
        dialog = PreferencesDialog(preferences)
        self.assertEqual(dialog.ollama_source.currentData(), "local")

        # Switch to Colab
        colab_index = dialog.ollama_source.findData("colab")
        dialog.ollama_source.setCurrentIndex(colab_index)
        self.assertIn("ngrok", dialog.ollama_url.placeholderText())

        # Switch back to Local
        local_index = dialog.ollama_source.findData("local")
        dialog.ollama_source.setCurrentIndex(local_index)
        self.assertEqual(dialog.ollama_url.text(), "http://127.0.0.1:11434")
        dialog.deleteLater()

    def test_switching_source_toggles_colab_field_visibility(self):
        preferences = {
            "ai_provider": "ollama",
            "groq_model": "llama-3.3-70b-versatile",
            "ollama_source": "local",
            "ollama_base_url": "http://127.0.0.1:11434",
            "ollama_model": "qwen:7b",
            "workspace_root": str(Path.cwd()),
            "allow_outside_workspace": False,
            "theme": "vscode-dark-plus",
            "font_family": "Cascadia Code",
            "font_size": 11,
            "confirm_risky": True,
            "restore_history": True,
        }
        dialog = PreferencesDialog(preferences)
        self.assertTrue(dialog.colab_url.isHidden())
        self.assertTrue(dialog.colab_link_label.isHidden())

        colab_index = dialog.ollama_source.findData("colab")
        dialog.ollama_source.setCurrentIndex(colab_index)
        self.assertFalse(dialog.colab_url.isHidden())
        self.assertFalse(dialog.colab_link_label.isHidden())

        local_index = dialog.ollama_source.findData("local")
        dialog.ollama_source.setCurrentIndex(local_index)
        self.assertTrue(dialog.colab_url.isHidden())
        self.assertTrue(dialog.colab_link_label.isHidden())
        dialog.deleteLater()

    def test_colab_url_auto_prepends_https(self):
        preferences = {
            "ai_provider": "ollama",
            "groq_model": "llama-3.3-70b-versatile",
            "ollama_source": "colab",
            "ollama_base_url": "custom-tunnel.ngrok-free.app",
            "ollama_model": "mistral",
            "workspace_root": str(Path.cwd()),
            "allow_outside_workspace": False,
            "theme": "vscode-dark-plus",
            "font_family": "Cascadia Code",
            "font_size": 11,
            "confirm_risky": True,
            "restore_history": True,
        }
        dialog = PreferencesDialog(preferences)
        saved = []
        dialog.preferences_saved.connect(saved.append)
        with patch.object(dialog, "accept"):
            dialog._save()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["ollama_base_url"], "https://custom-tunnel.ngrok-free.app")
        dialog.deleteLater()

    def test_invalid_colab_url_shows_warning(self):
        preferences = {
            "ai_provider": "ollama",
            "groq_model": "llama-3.3-70b-versatile",
            "ollama_source": "colab",
            "ollama_base_url": "",
            "ollama_model": "mistral",
            "workspace_root": str(Path.cwd()),
            "allow_outside_workspace": False,
            "theme": "vscode-dark-plus",
            "font_family": "Cascadia Code",
            "font_size": 11,
            "confirm_risky": True,
            "restore_history": True,
        }
        dialog = PreferencesDialog(preferences)
        saved = []
        dialog.preferences_saved.connect(saved.append)
        with patch("ui.main_window.QMessageBox.warning") as mock_warning:
            dialog._save()
            mock_warning.assert_called_once()
        self.assertEqual(len(saved), 0)
        dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
