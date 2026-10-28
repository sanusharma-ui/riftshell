import os
import re
import unittest
from unittest.mock import patch
from ui.themes import THEMES, build_stylesheet, get_theme


class WorkspacePresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(["ui-tests", "-platform", "offscreen"])

    def setUp(self):
        from ui.main_window import OrbitPanel
        with patch.object(OrbitPanel, "_reload_modes"):
            self.panel = OrbitPanel(lambda: None)

    def tearDown(self):
        self.panel.deleteLater()
        self.app.processEvents()

    def test_suggestion_only_fills_composer_and_respects_disabled_input(self):
        from PySide6.QtWidgets import QPushButton
        chip = self.panel.welcome.findChildren(QPushButton)[0]
        with patch.object(self.panel, "create_plan") as submit:
            chip.click()
            self.assertEqual(self.panel.input.text(), "Explain the structure of this workspace")
            self.assertEqual(self.panel.messages, [])
            submit.assert_not_called()
            self.panel.input.setEnabled(False)
            self.panel._fill_prompt("must not replace the pending input")
            self.assertEqual(self.panel.input.text(), "Explain the structure of this workspace")

    def test_action_review_follows_existing_button_states(self):
        self.assertTrue(self.panel.action_review.isHidden())
        for button in (self.panel.approve_button, self.panel.reject_button, self.panel.stop_button):
            button.setEnabled(True)
            self.assertFalse(self.panel.action_review.isHidden())
            button.setEnabled(False)
            self.assertTrue(self.panel.action_review.isHidden())

    def test_chat_preserves_literal_input_markdown_and_welcome_reset(self):
        self.panel._append("You", "<b>literal</b> **input**")
        self.panel._append("Orbit", "## Result\n\n**Formatted** reply with `code`.")
        self.assertIs(self.panel.chat_stack.currentWidget(), self.panel.conversation)
        plain = self.panel.conversation.toPlainText()
        self.assertIn("<b>literal</b> **input**", plain)
        self.assertIn("Formatted reply with code.", plain)
        self.assertEqual(plain.count("Formatted reply"), 1)
        self.panel.messages.clear()
        self.panel._render_conversation()
        self.assertIs(self.panel.chat_stack.currentWidget(), self.panel.welcome)

    def test_escaped_directory_list_renders_as_list_without_changing_source(self):
        raw = r"**Contents of `D:\test`:**\n\n- Directories:\n  - anime_api\n  - coffee_shop\n  - node_notes\n- Files:\n  - archive.zip (21,113,481 B)\n"
        self.panel._append("Orbit", raw)
        self.assertEqual(self.panel.messages[-1], ("Orbit", raw))
        plain = self.panel.conversation.toPlainText()
        self.assertNotIn(r"\n", plain)
        self.assertIn("anime_api\ncoffee_shop\nnode_notes", plain)
        self.assertIn(r"D:\test", plain)
        block = self.panel.conversation.document().begin()
        list_items = []
        while block.isValid():
            if block.textList():
                list_items.append(block.text())
            block = block.next()
        self.assertIn("coffee_shop", list_items)

    def test_display_normalization_preserves_windows_paths_code_and_regex(self):
        from ui.orbit_presentation import display_markdown
        source = 'Paths D:\\new D:\\node D:\\n\n\n`r"\\n"`\n\n```python\nprint("\\n- literal")\n```'
        self.assertEqual(display_markdown(source), source)

    def test_execution_command_and_completion_keep_line_boundaries(self):
        self.panel._append("Orbit", "Running in the active terminal:\ngoto D:\\test")
        self.panel._append("Orbit", "Completed: goto D:\\test\nThe command output is now available in the active terminal.")
        plain = self.panel.conversation.toPlainText()
        self.assertIn("Running in the active terminal:\ngoto D:\\test", plain)
        self.assertIn("Completed: goto D:\\test\nThe command output", plain)

    def test_terminal_mirror_is_formatted_without_altering_published_response(self):
        from ui.orbit_presentation import terminal_reply
        raw = r"**Contents**\n\n- Directories:\n  - coffee_shop\n  - node_notes\n"
        self.assertIn("- Directories:\n  - coffee_shop\n  - node_notes", terminal_reply(raw))
        with patch.object(self.panel, "_publish_output") as publish:
            self.panel._append("Orbit", raw)
            publish.assert_called_once_with("Orbit", raw)

    def test_proposed_command_escape_sequences_remain_literal_in_both_views(self):
        from ui.orbit_presentation import terminal_reply
        for command in [r'''run python -c "print('\n- literal')"''', 'run Write-Output "`nvalue`n"']:
            response = "Proposed command:\n" + command + "\n\nApproval is required."
            self.panel._append("Orbit", response)
            self.assertIn(command, self.panel.conversation.toPlainText())
            self.assertIn(command, terminal_reply(response))


class UIModernizationTests(unittest.TestCase):
    def test_all_themes_build_stylesheets(self):
        self.assertGreaterEqual(len(THEMES), 8)
        for key, theme in THEMES.items():
            sheet = build_stylesheet(theme)
            self.assertIsInstance(sheet, str)
            self.assertGreater(len(sheet), 1000)
            self.assertIn(theme.background, sheet)
            self.assertIn(theme.accent, sheet)

    def test_theme_lookup_and_aliases(self):
        tokyo = get_theme("tokyonight")
        self.assertEqual(tokyo.key, "tokyo-night")
        default_theme = get_theme(None)
        self.assertEqual(default_theme.key, "vscode-dark-plus")
        with self.assertRaises(KeyError):
            get_theme("unknown-theme")

    def test_emoji_policy_in_ui_code(self):
        """Only the folder emoji (U+1F4C1) is allowed in UI files as requested."""
        emoji_pattern = re.compile(r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]")
        allowed_codepoints = {0x1F4C1}  # folder emoji

        ui_dir = os.path.join(os.path.dirname(__file__), "..", "ui")
        violations = []
        for root, _, files in os.walk(ui_dir):
            for filename in files:
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        for char in line:
                            if emoji_pattern.match(char):
                                if ord(char) not in allowed_codepoints:
                                    violations.append(
                                        f"{filename}:{line_num}: Disallowed character U+{ord(char):04X} ({char!r})"
                                    )
        self.assertEqual(violations, [], "Disallowed emojis found in UI code:\n" + "\n".join(violations))
