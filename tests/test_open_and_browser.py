from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from commands.custom_commands import OpenCommand, NoteCommand, BrowserCommand
from core.context import ShellContext
from ai.actions import AgentAction
from ai.safety import SafetyPolicy
from utils.browser import BrowserError


class TestOpenCommand(unittest.TestCase):
    def setUp(self):
        self.cmd = OpenCommand()
        self.ctx = ShellContext(cwd=Path.cwd())

    def test_open_requires_args(self):
        res = self.cmd.execute(self.ctx, [])
        self.assertFalse(res.success)
        self.assertIn("Usage: open", res.output)

    @patch("commands.custom_commands.os.startfile")
    def test_open_existing_file(self, mock_startfile):
        test_file = Path("test_sample.txt")
        test_file.write_text("hello", encoding="utf-8")
        try:
            res = self.cmd.execute(self.ctx, ["test_sample.txt"])
            self.assertTrue(res.success)
            self.assertIn("Opened:", res.output)
            mock_startfile.assert_called_once()
        finally:
            if test_file.exists():
                test_file.unlink()

    @patch("commands.custom_commands.webbrowser.open")
    def test_open_web_shortcut(self, mock_web_open):
        res = self.cmd.execute(self.ctx, ["youtube"])
        self.assertTrue(res.success)
        self.assertIn("Opened Youtube", res.output)
        mock_web_open.assert_called_once_with("https://www.youtube.com")

    @patch("commands.custom_commands.webbrowser.open")
    def test_open_url(self, mock_web_open):
        res = self.cmd.execute(self.ctx, ["https://example.com"])
        self.assertTrue(res.success)
        self.assertIn("Opened URL: https://example.com", res.output)
        mock_web_open.assert_called_once_with("https://example.com")

    @patch("commands.custom_commands.os.startfile")
    def test_open_system_app(self, mock_startfile):
        res = self.cmd.execute(self.ctx, ["notepad"])
        self.assertTrue(res.success)
        self.assertIn("Opened Notepad", res.output)
        mock_startfile.assert_called_once_with("notepad.exe")

    def test_open_nonexistent_returns_clear_message(self):
        res = self.cmd.execute(self.ctx, ["definitely_nonexistent_program_xyz_12345"])
        self.assertFalse(res.success)
        self.assertIn("Not found:", res.output)


class TestNoteCommand(unittest.TestCase):
    def setUp(self):
        self.cmd = NoteCommand()
        self.ctx = ShellContext(cwd=Path.cwd())

    def test_note_requires_text(self):
        res = self.cmd.execute(self.ctx, [])
        self.assertFalse(res.success)
        self.assertIn("Usage: note", res.output)

    @patch("commands.custom_commands.subprocess.Popen")
    def test_note_creation(self, mock_popen):
        res = self.cmd.execute(self.ctx, ["Meeting", "with", "team", "at", "3pm"])
        self.assertTrue(res.success)
        self.assertIn("Note saved and opened in Notepad:", res.output)
        mock_popen.assert_called_once()


class TestBrowserCommand(unittest.TestCase):
    def setUp(self):
        self.cmd = BrowserCommand()
        self.ctx = ShellContext(cwd=Path.cwd())

    def test_browser_requires_args(self):
        res = self.cmd.execute(self.ctx, [])
        self.assertFalse(res.success)
        self.assertIn("Usage: browser", res.output)

    @patch("utils.browser.get_browser_controller")
    def test_browser_open(self, mock_get_ctrl):
        mock_ctrl = MagicMock()
        mock_ctrl.open_url.return_value = "Opened Example"
        mock_get_ctrl.return_value = mock_ctrl

        res = self.cmd.execute(self.ctx, ["open", "https://example.com"])
        self.assertTrue(res.success)
        self.assertEqual(res.output, "Opened Example")
        mock_ctrl.open_url.assert_called_once_with("https://example.com")

    @patch("utils.browser.get_browser_controller")
    def test_browser_search(self, mock_get_ctrl):
        mock_ctrl = MagicMock()
        mock_ctrl.search.return_value = "Searching Google for 'python tutorials'"
        mock_get_ctrl.return_value = mock_ctrl

        res = self.cmd.execute(self.ctx, ["search", "python", "tutorials"])
        self.assertTrue(res.success)
        mock_ctrl.search.assert_called_once_with("python tutorials", engine="Google")

    @patch("utils.browser.get_browser_controller")
    def test_browser_control(self, mock_get_ctrl):
        mock_ctrl = MagicMock()
        mock_ctrl.control.return_value = "Page reloaded."
        mock_get_ctrl.return_value = mock_ctrl

        res = self.cmd.execute(self.ctx, ["control", "refresh"])
        self.assertTrue(res.success)
        mock_ctrl.control.assert_called_once_with("refresh")

    @patch("utils.browser.get_browser_controller")
    def test_browser_error_handled(self, mock_get_ctrl):
        mock_ctrl = MagicMock()
        mock_ctrl.open_url.side_effect = BrowserError("Network disconnected")
        mock_get_ctrl.return_value = mock_ctrl

        res = self.cmd.execute(self.ctx, ["open", "bad_url"])
        self.assertFalse(res.success)
        self.assertIn("Browser: Network disconnected", res.output)


class TestSafetyPolicyBrowser(unittest.TestCase):
    def setUp(self):
        self.safety = SafetyPolicy()

    def test_safe_browser_action(self):
        decision = self.safety.check_action("browser", "open https://example.com")
        self.assertFalse(decision.requires_approval)

    def test_sensitive_browser_fill_requires_approval(self):
        decision = self.safety.check_action("browser", "fill e1 my_secret_password")
        self.assertTrue(decision.requires_approval)
        self.assertIn("sensitive credentials", decision.reason.lower())
