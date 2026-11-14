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
        self.assertIn("violet", default_theme.aliases)
        self.assertEqual(default_theme.accent.lower(), "#8b5cf6")

        ghost = get_theme("ghost")
        self.assertEqual(ghost.key, "ghost")
        self.assertEqual(ghost.panel, "transparent")
        self.assertEqual(ghost.terminalBg, "transparent")
        self.assertEqual(ghost.buttonBg, "transparent")

        cyber = get_theme("cyber-cyan")
        self.assertEqual(cyber.key, "cyber-cyan")
        self.assertEqual(cyber.bg.lower(), "#070b10")
        self.assertEqual(cyber.panel.lower(), "#0c131b")
        self.assertEqual(cyber.accent.lower(), "#3de0f5")
        self.assertEqual(cyber.secondary.lower(), "#14b8a6")

        obsidian = get_theme("obsidian-aura")
        self.assertEqual(obsidian.key, "obsidian-aura")
        self.assertEqual(obsidian.bg.lower(), "#0a090f")
        self.assertEqual(obsidian.panel.lower(), "#121018")
        self.assertEqual(obsidian.text.lower(), "#f4f0fa")
        self.assertEqual(obsidian.accent.lower(), "#e9defa")
        self.assertEqual(obsidian.secondary.lower(), "#fbfcdb")
        self.assertEqual(get_theme("obsidian").key, "obsidian-aura")
        self.assertEqual(get_theme("aura").key, "obsidian-aura")

        with self.assertRaises(KeyError):
            get_theme("unknown-theme")

    def test_central_theme_object_attributes_and_css_vars(self):
        required_attrs = (
            "bg", "panel", "panelBorder", "text", "textMuted",
            "accent", "accentGlow", "success", "danger",
            "terminalBg", "inputBg", "buttonBg", "buttonText",
        )
        for key, theme in THEMES.items():
            for attr in required_attrs:
                self.assertTrue(hasattr(theme, attr), f"Theme {key} missing {attr}")
                self.assertIsInstance(getattr(theme, attr), str)
            css_vars = theme.css_variables
            self.assertIsInstance(css_vars, dict)
            self.assertIn("--bg", css_vars)
            self.assertIn("--accent", css_vars)

    def test_stylesheet_styles_all_components(self):
        for key, theme in THEMES.items():
            sheet = build_stylesheet(theme)
            self.assertIn("QPushButton#approveButton", sheet)
            self.assertIn("QPushButton#dismissButton", sheet)
            self.assertIn("QPushButton#stopButton", sheet)
            self.assertIn("QPushButton#primaryButton", sheet)
            self.assertIn("QTabBar::tab", sheet)
            self.assertIn("QScrollBar:vertical", sheet)
            self.assertIn("QStatusBar", sheet)
            self.assertIn("QAbstractItemView#commandSuggestions", sheet)
            self.assertIn("QLineEdit#commandInput", sheet)
            self.assertIn("QLineEdit#orbitInput", sheet)
            self.assertIn("QTextEdit#orbitConversation", sheet)
            self.assertIn("QTextEdit#terminalOutput", sheet)
            self.assertIn("QWidget#customTitleBar", sheet)
            self.assertIn("QPushButton#titleCloseBtn", sheet)
            self.assertIn("QLabel#titleBrand", sheet)
            self.assertIn("QLabel#titleBadge", sheet)
            self.assertIn("QLabel#titleCenterPill", sheet)
            self.assertNotIn(":root", sheet)

    def test_no_qss_parse_warnings(self):
        from PySide6.QtCore import qInstallMessageHandler
        from PySide6.QtWidgets import QApplication, QListView, QMainWindow

        errors = []
        def handler(mode, ctx, msg):
            if "QFontDatabase" not in msg:
                errors.append(msg)

        qInstallMessageHandler(handler)
        _ = QApplication.instance() or QApplication(["output-tests", "-platform", "offscreen"])

        for key, theme in THEMES.items():
            sheet = build_stylesheet(theme)
            errors.clear()
            lv = QListView()
            lv.setObjectName("commandSuggestions")
            lv.setStyleSheet(sheet)
            self.assertEqual(errors, [], f"Theme {key} produced QSS errors on QListView: {errors}")

            errors.clear()
            mw = QMainWindow()
            mw.setStyleSheet(sheet)
            self.assertEqual(errors, [], f"Theme {key} produced QSS errors on QMainWindow: {errors}")

    def test_terminal_output_word_wrap(self):
        from PySide6.QtWidgets import QApplication, QTextEdit
        from ui.terminal_output import TerminalOutput

        _ = QApplication.instance() or QApplication(["output-tests", "-platform", "offscreen"])
        term = TerminalOutput()
        self.assertEqual(term.lineWrapMode(), QTextEdit.WidgetWidth)
        term.set_wrap_mode(False)
        self.assertEqual(term.lineWrapMode(), QTextEdit.NoWrap)
        term.set_wrap_mode(True)
        self.assertEqual(term.lineWrapMode(), QTextEdit.WidgetWidth)

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

    def test_dialog_flip_animation(self):
        from PySide6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout
        from ui.main_window import animate_dialog_flip_open

        _ = QApplication.instance() or QApplication(["output-tests", "-platform", "offscreen"])
        dlg = QDialog()
        dlg.resize(460, 520)
        dlg.setMinimumWidth(440)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Settings Animation Test"))

        animate_dialog_flip_open(dlg, duration_ms=40)
        self.assertTrue(hasattr(dlg, "_flip_anim"))
        anim = dlg._flip_anim
        self.assertIsNotNone(anim)
        dlg.close()

    def test_custom_title_bar(self):
        from PySide6.QtWidgets import QApplication, QMainWindow
        from ui.main_window import CustomTitleBar

        _ = QApplication.instance() or QApplication(["output-tests", "-platform", "offscreen"])
        mw = QMainWindow()
        tb = CustomTitleBar(mw)

        self.assertEqual(tb.brand_label.text(), "RiftShell")
        self.assertTrue(tb.version_badge.text().startswith("v"))
        self.assertIn("DEVELOPER WORKSPACE", tb.center_pill.text())
        tb.set_workspace_text("DEVELOPER WORKSPACE  —  riftshell")
        self.assertEqual(tb.center_pill.text(), "DEVELOPER WORKSPACE  —  riftshell")

        self.assertEqual(tb.min_btn.text(), "—")
        self.assertEqual(tb.max_btn.text(), "□")
        self.assertEqual(tb.close_btn.text(), "×")
        self.assertEqual(tb.height(), 40)
        self.assertEqual(tb.min_btn.size(), tb.max_btn.size())
        self.assertEqual(tb.max_btn.size(), tb.close_btn.size())
        self.assertEqual(tb.min_btn.width(), 48)
        tb.update_max_icon(True)
        self.assertEqual(tb.max_btn.text(), "⧉")
        tb.update_max_icon(False)
        self.assertEqual(tb.max_btn.text(), "□")
