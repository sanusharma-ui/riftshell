"""Opt-in local ConPTY smoke test; no network, installs or project writes."""
import os
import queue
import tempfile
import time
import unittest
import sys
import traceback
from pathlib import Path

from core.native_terminal import NativeTerminal, native_dependency_error, output_excerpt


@unittest.skipUnless(os.environ.get("RIFT_TEST_LIVE_TERMINAL") == "1", "opt-in local PowerShell test")
class LiveTerminalTests(unittest.TestCase):
    def test_persistent_state_pipeline_directory_and_interrupt(self):
        dependency_error = native_dependency_error()
        if dependency_error:
            self.skipTest(dependency_error)
        import ctypes
        ctypes.windll.kernel32.SetConsoleCtrlHandler(None, False)
        # pywinpty 2.x may release its final ConPTY directory handle slightly
        # after the transport thread reports stopped; ignore only that temp
        # cleanup race, never a transport assertion.
        with tempfile.TemporaryDirectory(prefix="rift terminal ", ignore_cleanup_errors=True) as directory:
            terminal = NativeTerminal(Path(directory))
            import pyte

            class Screen(pyte.Screen):
                def write_process_input(self, data):
                    terminal.write(data)

            stream = pyte.Stream(Screen(100, 24))
            terminal.start()

            def prompt_after(sequence):
                deadline = time.monotonic() + 25
                output = []
                while time.monotonic() < deadline:
                    try:
                        kind, payload = terminal.events.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if kind == "output":
                        output.append(payload)
                        stream.feed(payload)
                    elif kind == "error":
                        self.fail(payload)
                    elif kind == "exit":
                        self.fail("PowerShell exited before returning a prompt")
                    elif kind == "prompt" and payload["sequence"] > sequence:
                        return payload, output_excerpt("".join(output))
                frame = sys._current_frames().get(terminal._thread.ident)
                stack = "".join(traceback.format_stack(frame)) if frame else "worker stopped"
                self.fail("PowerShell prompt timed out; worker: " + stack + "; captured output: " + repr(output_excerpt("".join(output))[-1500:]))

            try:
                state, _ = prompt_after(0)
                self.assertEqual(Path(state["cwd"]), Path(directory))
                terminal.write("$riftSmokeValue = 37\r")
                state, _ = prompt_after(state["sequence"])
                terminal.write("Write-Output ($riftSmokeValue + 5) | ForEach-Object { 'VALUE=' + $_ }\r")
                state, output = prompt_after(state["sequence"])
                self.assertEqual(state["exit_code"], 0)
                self.assertIn("VALUE=42", output)
                terminal.write("Set-Location ..\r")
                state, _ = prompt_after(state["sequence"])
                self.assertEqual(Path(state["cwd"]), Path(directory).parent)
                terminal.write("Start-Sleep -Seconds 60\r")
                time.sleep(0.5)
                terminal.write("\x03")
                state, _ = prompt_after(state["sequence"])
                terminal.write("Write-Output 'AFTER_INTERRUPT'\r")
                _, output = prompt_after(state["sequence"])
                self.assertIn("AFTER_INTERRUPT", output)
            finally:
                terminal.close()
                deadline = time.monotonic() + 15
                while not terminal.stopped and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue(terminal.stopped, "Terminal cleanup timed out")
