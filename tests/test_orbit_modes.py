import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ai.actions import AgentAction
from ai.config import AIConfig
from ai.desktop_settings import load_desktop_config
from ai.llm import MemoryManager
from ai.modes import OrbitMode, decode_modes, default_modes, encode_modes, estimated_tokens, modes_from_env
from ai.provider_runtime import ProviderRuntime
from ai.workspace_reader import inspect_workspace_paths
from test_ai_providers import FakeHTTPResponse, make_config, make_planner
from test_desktop_settings import FakeSettings
from test_workspace_agent import SequencedGemini


class ModeConfigurationTests(unittest.TestCase):
    def test_custom_names_and_budgets_round_trip_without_name_based_behaviour(self):
        custom = replace(OrbitMode(), name="My shell", output_tokens=512, max_files=2)
        self.assertEqual(decode_modes(encode_modes((custom,))), (custom,))
        planner = make_planner(make_config(orbit_mode=custom))
        prompt = planner._build_prompt("Explain this project")
        self.assertIn("Selected Orbit mode: My shell", prompt)
        self.assertIn("512 tokens for the ENTIRE JSON", prompt)
        self.assertIn("at most 2 files", prompt)

    def test_invalid_profiles_are_rejected(self):
        for data in [[], [{"max_steps": 0}], [{"output_tokens": True}],
                     [{"name": ""}], [{"name": "A"}, {"name": "a"}],
                     [{"compact_prompt": "false"}], [{"unsupported": 1}]]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode_modes(json.dumps(data))

    def test_env_file_selects_a_custom_profile(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            path = Path(folder) / "modes.json"
            mode = replace(OrbitMode(), name="Local", output_tokens=1234)
            path.write_text(encode_modes((mode,)), encoding="utf-8")
            with patch.dict(os.environ, {"AI_MODES_FILE": str(path), "AI_MODE": "local"}):
                self.assertEqual(modes_from_env(), ((mode,), mode))

    def test_desktop_mode_applies_without_a_saved_provider_or_credential_access(self):
        base = AIConfig.from_env()
        custom = replace(OrbitMode(), name="Small", output_tokens=400)
        values = {"ai/mode": "Small", "ai/modes": encode_modes((custom,))}
        with patch("ai.desktop_settings.AIConfig.from_env", return_value=base), patch(
            "ai.desktop_settings.QSettings", return_value=FakeSettings(values)
        ), patch("ai.desktop_settings.credential_store", side_effect=AssertionError("key access")):
            loaded = load_desktop_config()
        self.assertEqual(loaded.orbit_mode, custom)
        self.assertEqual(loaded.ai_provider, base.ai_provider)

    def test_worker_pins_the_mode_chosen_when_the_task_started(self):
        from ai.agent_run import AgentRun
        from ui.main_window import OrbitWorker
        chosen = replace(OrbitMode(), name="Selected", max_steps=2, output_tokens=333)
        task = AgentRun("Explain this project", mode=chosen)
        planner = Mock()
        planner.mode = chosen
        planner.plan.return_value = AgentAction("respond", "A project.")
        shell = Mock()
        with patch("ui.main_window.load_desktop_config", return_value=AIConfig.from_env()), patch(
            "ai.llm.AgentPlanner", return_value=planner
        ) as factory:
            OrbitWorker(shell, task.objective, task=task).run()
        self.assertEqual(factory.call_args.kwargs["config"].orbit_mode, chosen)
        self.assertEqual(task.max_steps, 2)


class ModeBudgetTests(unittest.TestCase):
    def planner(self, mode=None, **kwargs):
        planner = make_planner(make_config(orbit_mode=mode or OrbitMode(), **kwargs))
        planner.provider_runtime = ProviderRuntime()
        return planner

    def test_balanced_and_high_have_explicit_shell_behaviour_and_limits(self):
        balanced, high = default_modes()
        short = self.planner(balanced)._build_prompt("Explain this project")
        detailed = self.planner(high)._build_prompt("Explain this project")
        self.assertIn("compact, useful answer first", short)
        self.assertIn("relevant file relationships and tradeoffs", detailed)
        for mode, prompt in [(balanced, short), (high, detailed)]:
            self.assertIn("never switch modes yourself", prompt)
            self.assertIn("user-directed AI shell", prompt)
            self.assertIn(f"Hard output ceiling: {mode.output_tokens}", prompt)
            self.assertLessEqual(estimated_tokens(prompt), mode.prompt_tokens)
        self.assertLess(len(short), len(detailed))

    def test_large_context_history_and_observations_fit_and_keep_user_intent(self):
        planner = self.planner()
        planner.memory.load = lambda: [
            {"role": role, "content": f"turn-{i}: " + "old context " * 1000}
            for i in range(12) for role in ("user", "assistant")
        ]
        workspace = "\n".join(f"### File: {name}\n" + "details " * 10000
                              for name in ("README.md", "package.json", "main.py"))
        prompt = planner._build_prompt("Explain this project; do not edit files.",
                                       workspace_context=workspace, task_context="evidence " * 15000)
        self.assertLessEqual(estimated_tokens(prompt), planner.mode.prompt_tokens)
        self.assertTrue(prompt.endswith("Explain this project; do not edit files."))
        self.assertNotIn("turn-0:", prompt)
        for name in ("README.md", "package.json", "main.py"):
            self.assertIn(f"### File: {name}", prompt)
        self.assertIn("UNTRUSTED DATA", prompt)

    def test_history_turn_limit_does_not_delete_saved_history(self):
        memory = MemoryManager("unused", 12, True)
        rows = [{"role": role, "content": f"turn-{i}"}
                for i in range(8) for role in ("user", "assistant")]
        memory.load = lambda: rows
        self.assertNotIn("turn-4", memory.format_for_prompt(3))
        self.assertIn("turn-5", memory.format_for_prompt(3))
        self.assertIn("turn-7", memory.format_for_prompt(3))
        self.assertEqual(memory.format_for_prompt(0), "No previous memory.")
        self.assertEqual(len(rows), 16)

    def test_overlong_user_request_is_not_silently_cropped_or_sent(self):
        planner = self.planner(groq_api_key="test", ai_provider="groq")
        planner._call_provider = Mock()
        action = planner.plan("Please explain " + "very detailed request " * 4000)
        self.assertEqual(action.action, "respond")
        self.assertIn("prompt budget", action.message)
        planner._call_provider.assert_not_called()

    def test_project_overview_inspects_three_files_and_sends_one_bounded_request(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            root = Path(folder)
            for name in ("README.md", "package.json", "main.py", "other.py", "notes.txt"):
                (root / name).write_text(name + "\n" + "long file content " * 3000, encoding="utf-8")
            planner = self.planner(workspace_root=root, gemini_api_key="test", ai_provider="gemini")
            model = SequencedGemini({"action": "respond", "message": "A compact project overview."})
            planner._gemini = model
            action = planner.plan("Explain this project")
            self.assertEqual(action.message, "A compact project overview.")
            self.assertEqual(len(model.prompts), 1)
            self.assertEqual(len(planner._inspected_files), 3)
            self.assertLessEqual(estimated_tokens(model.prompts[0]), 4500)
            for name in ("README.md", "package.json", "main.py"):
                self.assertIn(f"### File: {name}", model.prompts[0])

    def test_file_and_planning_budgets_span_related_inspections(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            root = Path(folder)
            for name in ("a.py", "b.py", "c.py"):
                (root / name).write_text("print('hello')", encoding="utf-8")
            mode = replace(OrbitMode(), max_files=2, max_steps=2, inspection_passes=4)
            planner = self.planner(mode, workspace_root=root, gemini_api_key="test", ai_provider="gemini")
            planner._gemini = SequencedGemini(
                {"action": "inspect", "paths": ["b.py"]},
                {"action": "inspect", "paths": ["c.py"]},
            )
            action = planner.plan("Explain a.py")
            self.assertEqual(action.action, "respond")
            self.assertIn("inspection budget", action.message)
            self.assertEqual(len(planner._inspected_files), 2)
            self.assertEqual(len(planner._gemini.prompts), 2)
            planner._call_provider = Mock()
            self.assertIsNone(planner._request_model_action("one more")[0])
            planner._call_provider.assert_not_called()

    def test_partial_file_is_not_offered_as_a_complete_replacement(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            root = Path(folder)
            content = "print('keep this')\n" * 1000
            (root / "main.py").write_text(content, encoding="utf-8")
            planner = self.planner(workspace_root=root, gemini_api_key="test", ai_provider="gemini")
            planner._call_provider = Mock()
            action = planner.plan("Fix main.py")
            self.assertEqual(action.action, "respond")
            self.assertIn("partial file content", action.message)
            self.assertEqual((root / "main.py").read_text(encoding="utf-8"), content)
            planner._call_provider.assert_not_called()

    def test_inspector_caps_each_file(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            root = Path(folder)
            for name in ("a.txt", "b.txt", "c.txt"):
                (root / name).write_text("x" * 5000, encoding="utf-8")
            result = inspect_workspace_paths(["a.txt", "b.txt", "c.txt"], workspace_root=root,
                current_dir=root, allow_outside_workspace=False, max_files=2, max_file_chars=256)
            self.assertEqual(len(result.files), 2)
            self.assertEqual(len(result.truncated_files), 2)
            self.assertLess(len(result.content), 1000)

    def test_gemini_generation_cap_and_truncation(self):
        planner = self.planner(gemini_api_key="test", ai_provider="gemini")
        model = Mock()
        model.generate_content.return_value = SimpleNamespace(candidates=[SimpleNamespace(finish_reason=2)])
        planner._gemini = model
        action, errors, _ = planner._request_model_action("test")
        self.assertIsNone(action)
        self.assertIn("output limit", errors[0])
        self.assertEqual(model.generate_content.call_args.kwargs["generation_config"]["max_output_tokens"], 768)
        model.generate_content.assert_called_once()

    def test_groq_length_stop_does_not_execute_or_fallback(self):
        planner = self.planner(groq_api_key="test", gemini_api_key="test")
        create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(
            finish_reason="length", message=SimpleNamespace(content='{"action":"shell","command":"files"}'))]))
        planner._groq = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        planner._gemini = Mock()
        action = planner.plan("Please check the project dependencies")
        self.assertEqual(action.action, "respond")
        self.assertIn("output limit", action.message)
        self.assertNotIn("unavailable", action.message)
        self.assertEqual(create.call_args.kwargs["extra_body"]["max_completion_tokens"], 768)
        planner._gemini.generate_content.assert_not_called()

    def test_ollama_generation_cap_and_truncation(self):
        planner = self.planner(ai_provider="ollama", ollama_model="local")
        response = FakeHTTPResponse()
        response.body = json.dumps({"response": '{"action":', "done_reason": "length"}).encode()
        with patch("ai.llm.urllib.request.urlopen", return_value=response) as call:
            action = planner.plan("Explain dependency injection")
        self.assertEqual(action.action, "respond")
        self.assertIn("output limit", action.message)
        payload = json.loads(call.call_args.args[0].data)
        self.assertEqual(payload["options"]["num_predict"], 768)


class ModeEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_edit_duplicate_save_and_reload_custom_budget(self):
        from ui.orbit_modes import OrbitModesDialog
        settings = Mock()
        with patch("ui.orbit_modes.load_mode_preferences", return_value=(default_modes(), OrbitMode())), patch(
            "ui.orbit_modes.QSettings", return_value=settings
        ):
            dialog = OrbitModesDialog()
            dialog.fields["output_tokens"].setValue(900)
            dialog.selector.setCurrentIndex(1)
            dialog.selector.setCurrentIndex(0)
            self.assertEqual(dialog.fields["output_tokens"].value(), 900)
            dialog._duplicate()
            dialog.name.setText("Personal")
            dialog.fields["prompt_tokens"].setValue(6000)
            dialog._save()
            writes = dict(call.args for call in settings.setValue.call_args_list)
            saved = decode_modes(writes["ai/modes"])
            self.assertEqual(writes["ai/mode"], "Personal")
            self.assertEqual(saved[-1].prompt_tokens, 6000)
            self.assertEqual(saved[-1].output_tokens, 900)
            dialog.close()
