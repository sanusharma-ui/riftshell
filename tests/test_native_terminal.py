"""Pure protocol and mocked session regressions. Never launches a shell."""
import base64
import json
import queue
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.native_terminal import NativeTerminal, PromptDecoder, output_excerpt, powershell_startup
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


class NativeTransportTests(unittest.TestCase):
    def test_blocked_output_read_does_not_block_input_or_close(self):
        reading = threading.Event()
        release = threading.Event()
        written = threading.Event()

        class Pty:
            alive = True
            pid = 123

            def spawn(self, *args, **kwargs):
                pass

            def read(self, *args, **kwargs):
                reading.set()
                release.wait(3)
                if not self.alive:
                    raise EOFError
                return ""

            def write(self, text):
                if text == "\x03":
                    written.set()

            def isalive(self):
                return self.alive

        process = Pty()

        def terminate(*args, **kwargs):
            process.alive = False
            release.set()

        with patch.dict("sys.modules", {"winpty": SimpleNamespace(PTY=lambda *args, **kwargs: process)}), \
                patch("core.native_terminal.shutil.which", return_value="powershell.exe"), \
                patch("core.native_terminal.subprocess.CREATE_NO_WINDOW", 0, create=True), \
                patch("core.native_terminal.subprocess.run", side_effect=terminate):
            terminal = NativeTerminal(Path.cwd())
            terminal.start()
            try:
                self.assertTrue(reading.wait(2))
                terminal.write("\x03")
                self.assertTrue(written.wait(1), "Ctrl+C waited for an idle output read")
            finally:
                terminal.close()
                terminal._thread.join(3)
                release.set()
            self.assertTrue(terminal.stopped)


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

    def test_large_output_yields_without_losing_output_or_completing_early(self):
        chunks = []
        self.terminal.feed = chunks.append
        self.session.submit("large-output")
        self.session.transport.events.put(("output", "x" * 40000))
        self.session.transport.events.put(("prompt", dict(sequence=2, exit_code=0, cwd="C:/Work", filesystem=True)))
        self.session._drain()
        self.assertLessEqual(sum(map(len, chunks)), 8192)
        self.assertTrue(self.session.busy)
        for _ in range(100):
            self.session._drain()
            if self.results:
                break
        self.assertEqual("".join(chunks), "x" * 40000)
        self.assertTrue(self.results[0][1].success)

    def test_pending_application_output_precedes_native_output(self):
        chunks = []
        self.terminal.feed = chunks.append
        self.terminal.output_pending = True
        self.session.transport.events.put(("output", "native"))
        self.session._drain()
        self.assertEqual(chunks, [])
        self.terminal.output_pending = False
        self.session._drain()
        self.assertEqual(chunks, ["native"])


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

    def test_cursor_only_blinks_during_focused_interactive_input(self):
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit
        from ui.terminal_widget import TerminalWidget
        host = QWidget()
        layout = QVBoxLayout(host)
        terminal, entry = TerminalWidget(), QLineEdit()
        layout.addWidget(terminal)
        layout.addWidget(entry)
        old_flash_time = self.app.cursorFlashTime()
        try:
            self.app.setCursorFlashTime(1000)
            host.show()
            host.activateWindow()
            terminal.setFocus()
            self.app.processEvents()
            self.assertFalse(terminal._cursor_timer.isActive())
            terminal.input_enabled = True
            self.assertTrue(terminal._cursor_timer.isActive())
            entry.setFocus()
            self.app.processEvents()
            self.assertFalse(terminal._cursor_timer.isActive())
            terminal.setFocus()
            self.app.processEvents()
            terminal.input_enabled = False
            self.assertFalse(terminal._cursor_timer.isActive())
        finally:
            self.app.setCursorFlashTime(old_flash_time)
            host.close()
            host.deleteLater()

    def test_completion_returns_focus_without_stealing_it_from_other_panels(self):
        from core.shell import Shell
        from ui.main_window import TerminalSession
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit
        preferences = dict(font_family="Consolas", font_size=11, theme="vscode-dark-plus", confirm_risky=False)
        host = QWidget()
        layout = QVBoxLayout(host)
        with patch("ui.main_window.native_dependency_error", return_value=""), patch("ui.native_session.NativeTerminal", FakeTransport):
            session = TerminalSession(Shell(), "Test", preferences)
        other = QLineEdit()
        layout.addWidget(session)
        layout.addWidget(other)
        try:
            host.show()
            host.activateWindow()
            self.app.processEvents()
            session.native._prompt(dict(sequence=1, exit_code=0, cwd=str(session.shell.ctx.cwd), filesystem=True))
            self.assertNotIn("PowerShell", session.input.placeholderText())
            for sequence, keep_elsewhere in ((2, False), (3, True)):
                session.input.setText("python --version")
                self.assertTrue(session.run_command())
                if keep_elsewhere:
                    other.setFocus()
                self.app.processEvents()
                session.native._prompt(dict(sequence=sequence, exit_code=0, cwd=str(session.shell.ctx.cwd), filesystem=True))
                self.app.processEvents()
                self.assertTrue(session.input.isEnabled())
                self.assertTrue((other if keep_elsewhere else session.input).hasFocus())
        finally:
            session.shutdown()
            host.close()
            host.deleteLater()

    def test_missing_native_dependencies_preserves_legacy_session(self):
        from core.shell import Shell
        from ui.main_window import TerminalSession
        preferences = dict(font_family="Consolas", font_size=11, theme="vscode-dark-plus", confirm_risky=True)
        with patch("ui.main_window.native_dependency_error", return_value="Install requirements.txt"):
            session = TerminalSession(Shell(), "Test", preferences)
        try:
            self.assertIsNone(session.native)
            self.assertFalse(hasattr(session, "mode"))
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

    def test_unified_routing_preserves_builtins_plugins_and_powershell_syntax(self):
        from core.shell import Shell
        from core.base import CommandResult
        from ui.main_window import TerminalSession
        from PySide6.QtCore import QEventLoop, QTimer
        preferences = dict(font_family="Consolas", font_size=11, theme="vscode-dark-plus", confirm_risky=False)
        with patch("ui.main_window.native_dependency_error", return_value=""), patch("ui.native_session.NativeTerminal", FakeTransport):
            session = TerminalSession(Shell(), "Test", preferences)
        try:
            session.native_console.screen.resize(lines=24, columns=100)
            session.native._prompt(dict(sequence=1, exit_code=0, cwd=str(session.shell.ctx.cwd), filesystem=True))
            self.assertFalse(hasattr(session, "mode"))
            for command in ("files", "read README.md", "files | filter .py", "where; now", "theme", "cd .."):
                self.assertFalse(session._uses_native(command), command)
            for command in ("python --version", "npm --version", "Get-ChildItem | Select-Object -First 2", "$x = 42", "& 'python' --version", "run git status"):
                self.assertTrue(session._uses_native(command), command)
            session.shell.ctx.aliases["listing"] = "files"
            self.assertFalse(session._uses_native("listing"))
            session.shell.registry.register(SimpleNamespace(name="customplugin", aliases=[], execute=lambda ctx, args: CommandResult("plugin result")))
            self.assertFalse(session._uses_native("customplugin"))
            self.assertFalse(session._uses_native("files", from_orbit=True))
            self.assertTrue(session._uses_native("run git status", from_orbit=True))
            session.input.setText("customplugin")
            self.assertTrue(session.run_command())
            loop = QEventLoop()
            session.worker.finished.connect(loop.quit)
            QTimer.singleShot(3000, loop.quit)
            loop.exec()
            self.assertFalse(session.worker.isRunning())
            while session.native_console.output_pending:
                session.native_console._drain_messages()
            self.assertIn("plugin result", session.native_console.toPlainText())
            self.assertIs(session.console_stack.currentWidget(), session.native_console)
            session.input.setText("Get-ChildItem | Select-Object -First 2")
            self.assertTrue(session.run_command())
            self.assertEqual(session.native.transport.writes[-1], "Get-ChildItem | Select-Object -First 2\r")
            self.assertIs(session.console_stack.currentWidget(), session.native_console)
        finally:
            session.shutdown()
            session.deleteLater()

    def test_large_builtin_output_is_incremental_and_clear_discards_pending_text(self):
        from ui.terminal_widget import TerminalWidget
        terminal = TerminalWidget()
        try:
            terminal.append_message("line\n" * 20000)
            self.assertTrue(terminal.output_pending)
            terminal._drain_messages()
            self.assertTrue(terminal.output_pending)
            self.assertIn("line", terminal.toPlainText())
            terminal.clear()
            self.assertFalse(terminal.output_pending)
            self.assertEqual(terminal.toPlainText(), "")
        finally:
            terminal.deleteLater()

    def test_event_loop_stays_responsive_while_output_is_rendering(self):
        from PySide6.QtCore import QEventLoop, QTimer
        from ui.terminal_widget import TerminalWidget
        terminal = TerminalWidget()
        terminal.resize(900, 500)
        terminal._resize_screen()
        loop = QEventLoop()
        ticks = []
        heartbeat = QTimer()
        heartbeat.setInterval(1)

        def tick():
            ticks.append(terminal.output_pending)
            if not terminal.output_pending:
                loop.quit()

        heartbeat.timeout.connect(tick)
        try:
            terminal.append_message("output line\n" * 3000, "#ff0000")
            heartbeat.start()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
            self.assertFalse(terminal.output_pending)
            self.assertGreater(sum(ticks), 2)
            # Exercise actual painting, including grouped colors and text styles.
            terminal.feed("\x1b[1;4;32mstyled\x1b[0m Unicode: \u4e2d\r\n")
            self.assertFalse(terminal.grab().isNull())
        finally:
            heartbeat.stop()
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
