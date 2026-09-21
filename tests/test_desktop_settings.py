import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from ai.config import AIConfig
from ai.desktop_settings import load_desktop_config


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


if __name__ == "__main__":
    unittest.main()
