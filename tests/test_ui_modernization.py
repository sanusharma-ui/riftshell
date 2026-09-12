import os
import re
import unittest
from ui.themes import THEMES, build_stylesheet, get_theme


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
