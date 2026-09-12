"""Pure protocol and mocked session regressions. Never launches a shell."""
import base64
import json
import queue
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.native_terminal import PromptDecoder, output_excerpt, powershell_startup
from ai.safety import SafetyPolicy


TOKEN = "a" * 32


def marker(sequence=1, exit_code=0, cwd="C:\\Work", filesystem=True):
    state = dict(sequence=sequence, exit_code=exit_code, cwd=cwd, filesystem=filesystem)
    encoded = base64.b64encode(json.dumps(state).encode()).decode()
    return f"\x1b]0;rift;{TOKEN};{encoded}\x07", state


class PromptProtocolTests(unittest.TestCase):
    def test_marker_can_split_at_every_byte_boundary(self):
        packet, state = marker(cwd="C:\\Work\\नया folder")
        for split in range(len(packet) + 1):
            decoder = PromptDecoder(TOKEN)
            events = decoder.feed("before" + packet[:split]) + decoder.feed(packet[split:] + "after")
            self.assertEqual([value for kind, value in events if kind == "prompt"], [state])
            self.assertEqual("".join(value for kind, value in events if kind == "output"), "beforeafter")

    def test_nonmatching_and_invalid_markers_cannot_complete_command(self):
        packet, _ = marker()
        for raw in (packet.replace(TOKEN, "b" * 32), f"\x1b]0;rift;{TOKEN};invalid!\x07"):
            events = PromptDecoder(TOKEN).feed(raw)
            self.assertFalse(any(kind == "prompt" for kind, _ in events))
            self.assertEqual("".join(value for kind, value in events), raw)

    def test_title_variant_and_string_terminator(self):
        packet, state = marker()
        packet = packet.replace("]0;", "]2;").replace("\x07", "\x1b\\")
        self.assertEqual(PromptDecoder(TOKEN).feed(packet), [("prompt", state)])

    def test_order_between_output_and_multiple_prompts_is_preserved(self):
        first, _ = marker(1)
        second, _ = marker(2, 7)
        events = PromptDecoder(TOKEN).feed(first + "failure" + second)
        self.assertEqual([kind for kind, _ in events], ["prompt", "output", "prompt"])
        self.assertEqual(events[-1][1]["exit_code"], 7)

    def test_startup_is_encoded_and_rejects_script_injection(self):
        script = base64.b64decode(powershell_startup(TOKEN)).decode("utf-16-le")
        self.assertIn("function global:prompt", script)
        self.assertIn(TOKEN, script)
        with self.assertRaises(ValueError):
            powershell_startup("'; Remove-Item X; '")

    def test_observations_remove_terminal_controls_and_are_bounded(self):
        text = "\x1b[31mfailed\x1b[0m\r\n\x1b]0;title\x07done"
        self.assertEqual(output_excerpt(text), "failed\ndone")
        self.assertEqual(len(output_excerpt("x" * 20000)), 16000)


class PowerShellSafetyTests(unittest.TestCase):
    def test_native_syntax_cannot_hide_mutations_behind_read_only_prefix(self):
        policy = SafetyPolicy()
        for raw in (
            'run git status $(Remove-Item data.txt)',
            'run whoami; Remove-Item data.txt',
            'run python --version\nRemove-Item data.txt',
            'run whoami > data.txt',
            'run git status `\n; Remove-Item data.txt',
            'npm install axios',
        ):
            with self.subTest(raw=raw):
                self.assertTrue(policy.check_powershell_command(raw).requires_approval)


class MockSignal:
    def connect(self, callback):
        self.callback = callback


class FakeTransport:
    def __init__(self, cwd):
        self.events = queue.Queue()
        self.writes = []
        self.shell_name = "PowerShell"
        self.stopped = False

    def start(self):
        pass

    def write(self, text):
        self.writes.append(text)

    def resize(self, *args):
        pass

    def close(self):
        self.stopped = True


class NativeSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["rift-tests", "-platform", "offscreen"])

    def setUp(self):
        from ui.native_session import NativeSession
        self.shell = SimpleNamespace(ctx=SimpleNamespace(cwd=Path("C:/Work"), last_output=""))
        self.terminal = SimpleNamespace(input_ready=MockSignal(), size_changed=MockSignal(), input_enabled=False, feed=lambda text: None)
        with patch("ui.native_session.NativeTerminal", FakeTransport):
            self.session = NativeSession(self.shell, self.terminal)
        self.session.timer.stop()
        self.results = []
        self.session.completed.connect(lambda command, result: self.results.append((command, result)))
        self.prompt(1)

    def tearDown(self):
        self.session.close()
        self.session.deleteLater()

    def prompt(self, sequence, exit_code=0, cwd="C:/Work", filesystem=True):
        self.session.transport.events.put(("prompt", dict(sequence=sequence, exit_code=exit_code, cwd=cwd, filesystem=filesystem)))
        self.session._drain()

    def test_live_output_is_not_completion_and_exit_code_is_observed(self):
        self.assertTrue(self.session.submit("npm install axios"))
        self.session.transport.events.put(("output", "downloading..."))
        self.session._drain()
        self.assertTrue(self.session.busy)
        self.assertEqual(self.results, [])
        self.prompt(2, 1)
        self.assertFalse(self.session.busy)
        self.assertFalse(self.results[0][1].success)
        self.assertIn("downloading", self.results[0][1].output)

    def test_duplicate_prompt_cannot_complete_a_later_command(self):
        self.session.submit("python")
        self.prompt(1)
        self.assertTrue(self.session.busy)
        self.assertEqual(self.results, [])

    def test_native_navigation_updates_legacy_workspace(self):
        self.session.submit("cd C:/Other")
        self.prompt(2, cwd="C:/Other")
        self.assertEqual(self.shell.ctx.cwd, Path("C:/Other"))

    def test_legacy_navigation_is_synced_before_native_command(self):
        self.shell.ctx.cwd = Path("C:/Other")
        self.session.submit("npm install axios")
        self.assertIn("Set-Location -LiteralPath", self.session.transport.writes[-1])
        self.assertFalse(self.terminal.input_enabled)
        self.prompt(2, cwd="C:/Other")
        self.assertEqual(self.session.transport.writes[-1], "npm install axios\r")
        self.assertEqual(self.results, [])
        self.prompt(3, cwd="C:/Other")
        self.assertTrue(self.results[0][1].success)

    def test_failed_directory_sync_does_not_run_requested_command(self):
        self.shell.ctx.cwd = Path("C:/Missing")
        self.session.submit("npm install axios")
        self.prompt(2, 1)
        self.assertFalse(any(text == "npm install axios\r" for text in self.session.transport.writes))
        self.assertFalse(self.results[0][1].success)

    def test_ctrl_c_never_becomes_successful_server_completion(self):
        self.session.submit("uvicorn backend.main:app --reload")
        self.session._write_input("\x03")
        self.prompt(2)
        self.assertFalse(self.results[0][1].success)

    def test_shell_exit_finishes_inflight_action_as_unconfirmed_failure(self):
        self.session.submit("python")
        self.session.transport.events.put(("exit", None))
        self.session._drain()
        self.assertFalse(self.results[0][1].success)
        self.assertFalse(self.session.submit("another command"))

    def test_nonfilesystem_location_does_not_become_a_fake_path(self):
        self.session.submit("cd HKCU:/")
        self.prompt(2, cwd="HKCU:/", filesystem=False)
        self.assertFalse(self.session.context_available)
        self.assertEqual(self.shell.ctx.cwd, Path("C:/Work"))


class OrbitNativeRoutingTests(unittest.TestCase):
    def test_native_pipeline_is_validated_only_for_native_desktop_context(self):
        from ai.actions import AgentAction
        from ai.llm import AgentPlanner
        planner = object.__new__(AgentPlanner)
        planner.command_names = ["run", "files", "where"]
        planner.native_context_provider = None
        action = AgentAction(action="shell", command="run git status | Select-Object -First 1")
        self.assertEqual(planner._validate_action(action).action, "respond")
        planner.native_context_provider = lambda: "PowerShell"
        self.assertIs(planner._validate_action(action), action)
        self.assertTrue(SafetyPolicy().check_action("shell", action.command).requires_approval)

    def test_native_capability_does_not_turn_conversation_into_commands(self):
        from ai.actions import AgentAction
        from ai.llm import AgentPlanner
        planner = object.__new__(AgentPlanner)
        planner.command_names = ["run", "files", "where"]
        planner.native_context_provider = lambda: "PowerShell"
        action = AgentAction(action="shell", command="tell me about the moon")
        self.assertEqual(planner._validate_action(action).action, "respond")
        reply = AgentAction(action="respond", message="I can help explain that.")
        self.assertIs(planner._validate_action(reply), reply)


class TerminalSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["rift-tests", "-platform", "offscreen"])

    def test_missing_native_dependencies_preserves_legacy_session(self):
        from core.shell import Shell
        from ui.main_window import TerminalSession
        preferences = dict(font_family="Consolas", font_size=11, theme="vscode-dark-plus", confirm_risky=True)
        with patch("ui.main_window.native_dependency_error", return_value="Install requirements.txt"):
            session = TerminalSession(Shell(), "Test", preferences)
        try:
            self.assertIsNone(session.native)
            self.assertEqual(session.mode.currentData(), "legacy")
            self.assertIs(session.input.completer(), session.legacy_completer)
            self.assertIn("Install requirements.txt", session.console.toPlainText())
        finally:
            session.deleteLater()

    def test_carriage_return_updates_existing_progress_line(self):
        from ui.terminal_widget import TerminalWidget
        terminal = TerminalWidget()
        try:
            terminal.feed("download 10%\rdownload 90%")
            self.assertTrue(terminal.toPlainText().startswith("download 90%"))
            self.assertNotIn("10%", terminal.toPlainText())
        finally:
            terminal.deleteLater()

    def test_alternate_screen_restores_main_screen_and_scrollback(self):
        from ui.terminal_widget import TerminalWidget
        terminal = TerminalWidget()
        try:
            terminal.feed("original\x1b[?1049hinteractive app\x1b[?1049l")
            self.assertTrue(terminal.toPlainText().startswith("original"))
            self.assertNotIn("interactive app", terminal.toPlainText())
        finally:
            terminal.deleteLater()


if __name__ == "__main__":
    unittest.main()
