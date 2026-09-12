from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    key: str
    display_name: str
    aliases: tuple[str, ...]
    background: str
    surface: str
    surface_alt: str
    border: str
    text: str
    muted: str
    accent: str
    accent_alt: str
    output: str
    error: str
    selection: str
    button: str
    button_hover: str
    button_pressed: str
    console_glow: str


THEMES: dict[str, Theme] = {
    "vscode-dark-plus": Theme(
        key="vscode-dark-plus",
        display_name="VS Code Dark+ (Default)",
        aliases=("default", "dark+", "dark-plus", "vscode", "vs-code", "vs-code-dark-plus"),
        background="#101218",
        surface="#181c25",
        surface_alt="#222837",
        border="#30384a",
        text="#e7ecf5",
        muted="#9aa7bc",
        accent="#8baaff",
        accent_alt="#b8a4ff",
        output="#bdc9dc",
        error="#f48771",
        selection="#264f78",
        button="#2d2d30",
        button_hover="#38383c",
        button_pressed="#222225",
        console_glow="#000000",
    ),
    "tokyo-night": Theme(
        key="tokyo-night",
        display_name="Tokyo Night",
        aliases=("tokyo", "tokyonight", "tokyo-night"),
        background="#16161e",
        surface="#1a1b26",
        surface_alt="#24283b",
        border="#2f354d",
        text="#c0caf5",
        muted="#7aa2f7",
        accent="#7aa2f7",
        accent_alt="#7dcfff",
        output="#9ece6a",
        error="#f7768e",
        selection="#33467c",
        button="#24283b",
        button_hover="#2f354d",
        button_pressed="#1a1c2a",
        console_glow="#000000",
    ),
    "nord": Theme(
        key="nord",
        display_name="Nord",
        aliases=("nord",),
        background="#242933",
        surface="#2e3440",
        surface_alt="#3b4252",
        border="#434c5e",
        text="#eceff4",
        muted="#98a4ba",
        accent="#88c0d0",
        accent_alt="#8fbcbb",
        output="#a3be8c",
        error="#bf616a",
        selection="#434c5e",
        button="#3b4252",
        button_hover="#4c566a",
        button_pressed="#2e3440",
        console_glow="#1f242d",
    ),
    "dracula": Theme(
        key="dracula",
        display_name="Dracula",
        aliases=("dracula",),
        background="#1e1f29",
        surface="#282a36",
        surface_alt="#343746",
        border="#44475a",
        text="#f8f8f2",
        muted="#a5a8be",
        accent="#bd93f9",
        accent_alt="#8be9fd",
        output="#50fa7b",
        error="#ff5555",
        selection="#44475a",
        button="#343746",
        button_hover="#44475a",
        button_pressed="#282a36",
        console_glow="#191a21",
    ),
    "github-dark": Theme(
        key="github-dark",
        display_name="GitHub Dark",
        aliases=("github", "github-dark", "gh-dark"),
        background="#0a0c10",
        surface="#161b22",
        surface_alt="#21262d",
        border="#30363d",
        text="#e6edf3",
        muted="#8b949e",
        accent="#58a6ff",
        accent_alt="#79c0ff",
        output="#7ee787",
        error="#ff7b72",
        selection="#1f6feb",
        button="#21262d",
        button_hover="#30363d",
        button_pressed="#161b22",
        console_glow="#000000",
    ),
    "catppuccin-mocha": Theme(
        key="catppuccin-mocha",
        display_name="Catppuccin Mocha",
        aliases=("catppuccin", "mocha"),
        background="#181825",
        surface="#1e1e2e",
        surface_alt="#313244",
        border="#45475a",
        text="#cdd6f4",
        muted="#9399b2",
        accent="#cba6f7",
        accent_alt="#89dceb",
        output="#a6e3a1",
        error="#f38ba8",
        selection="#45475a",
        button="#313244",
        button_hover="#45475a",
        button_pressed="#1e1e2e",
        console_glow="#000000",
    ),
    "one-dark-pro": Theme(
        key="one-dark-pro",
        display_name="One Dark Pro",
        aliases=("one-dark", "onedark", "atom"),
        background="#1e2227",
        surface="#282c34",
        surface_alt="#353b45",
        border="#3e4451",
        text="#abb2bf",
        muted="#7f848e",
        accent="#61afef",
        accent_alt="#56b6c2",
        output="#98c379",
        error="#e06c75",
        selection="#3e4451",
        button="#353b45",
        button_hover="#3e4451",
        button_pressed="#282c34",
        console_glow="#000000",
    ),
    "cyberpunk-neon": Theme(
        key="cyberpunk-neon",
        display_name="Cyberpunk Neon",
        aliases=("cyberpunk", "cyber", "neon"),
        background="#0d0e15",
        surface="#131520",
        surface_alt="#1d2030",
        border="#2b2d42",
        text="#00ff9f",
        muted="#7a82ab",
        accent="#00f0ff",
        accent_alt="#ff007f",
        output="#00ff9f",
        error="#ff3366",
        selection="#3d1e4e",
        button="#1d2030",
        button_hover="#2b2d42",
        button_pressed="#131520",
        console_glow="#00f0ff",
    ),
}

DEFAULT_THEME_KEY = "vscode-dark-plus"

_ALIAS_TO_KEY = {
    alias.lower(): key
    for key, theme in THEMES.items()
    for alias in (theme.key, theme.display_name, *theme.aliases)
}


def normalize_theme_name(name: str) -> str:
    return "-".join(name.strip().lower().replace("+", " plus").split())


def get_theme(name: str | None = None) -> Theme:
    if not name:
        return THEMES[DEFAULT_THEME_KEY]

    raw = name.strip().strip('"\'')
    candidates = [
        raw.lower(),
        normalize_theme_name(raw),
        normalize_theme_name(raw).replace("-plus", "+"),
    ]
    for candidate in candidates:
        if candidate in THEMES:
            return THEMES[candidate]
        if candidate in _ALIAS_TO_KEY:
            return THEMES[_ALIAS_TO_KEY[candidate]]
    raise KeyError(name)


def list_themes() -> list[Theme]:
    return list(THEMES.values())


def build_stylesheet(theme: Theme) -> str:
    return f"""
QMainWindow {{
    background-color: {theme.background};
}}

QWidget {{
    background-color: {theme.background};
    color: {theme.text};
    font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 10pt;
}}

QLabel {{
    background-color: transparent;
    color: {theme.muted};
    font-size: 9.5pt;
    font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
}}

QTextEdit {{
    background-color: {theme.surface};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 9px;
    padding: 10px 12px;
    font-family: "Cascadia Code", "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 10.5pt;
    line-height: 140%;
    selection-background-color: {theme.selection};
    selection-color: {theme.text};
}}

QLineEdit {{
    background-color: {theme.surface};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 8px;
    padding: 8px 12px;
    font-family: "Cascadia Code", "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 10.5pt;
    selection-background-color: {theme.selection};
    selection-color: {theme.text};
}}

QLineEdit:focus {{
    border: 1px solid {theme.accent};
    background-color: {theme.surface_alt};
}}

QListWidget {{
    background-color: {theme.surface};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 8px;
    padding: 6px;
    outline: none;
}}

QListWidget::item {{
    padding: 8px 10px;
    border-radius: 6px;
    margin: 1px 0px;
    border: 1px solid transparent;
}}

QListWidget::item:hover {{
    background-color: {theme.surface_alt};
    color: {theme.text};
}}

QListWidget::item:selected {{
    background-color: {theme.surface_alt};
    color: {theme.accent_alt};
    border: 1px solid {theme.border};
    font-weight: 600;
}}

QPushButton {{
    background-color: {theme.button};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 7px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 9.5pt;
}}

QPushButton:hover {{
    background-color: {theme.button_hover};
    border-color: {theme.accent};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: {theme.button_pressed};
}}

QPushButton:disabled {{
    background-color: {theme.surface};
    color: {theme.muted};
    border-color: {theme.border};
}}

QStatusBar {{
    background-color: {theme.surface};
    color: {theme.muted};
    border-top: 1px solid {theme.border};
    font-size: 8.5pt;
    padding: 3px 10px;
}}

QFrame#sidebar, QFrame#inspector, QFrame#terminalHeader {{
    background-color: {theme.surface};
    border: 1px solid {theme.border};
    border-radius: 10px;
}}

QFrame#sidebar {{
    border-radius: 0;
    border-top: 0;
    border-bottom: 0;
    border-left: 0;
    border-right: 1px solid {theme.border};
}}

QFrame#sidebar QLabel, QFrame#inspector QLabel, QFrame#terminalHeader QLabel {{
    background-color: transparent;
}}

QFrame#terminalHeader {{
    border-radius: 12px;
}}

QLineEdit#commandInput {{
    background-color: {theme.surface};
    border-radius: 12px;
    padding: 13px 16px;
    min-height: 24px;
}}

QLineEdit#commandInput:focus {{
    border-color: {theme.accent};
    background-color: {theme.surface_alt};
}}

QTextEdit#orbitConversation {{
    background-color: {theme.background};
    border: none;
    border-radius: 12px;
    padding: 14px;
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 10.5pt;
}}

QTextEdit#terminalOutput {{
    background-color: {theme.background};
    border: none;
}}

QFrame#terminalHeader QPushButton {{
    background-color: transparent;
    border-color: transparent;
    color: {theme.muted};
    padding: 5px 9px;
}}

QFrame#terminalHeader QPushButton:hover {{
    background-color: {theme.surface_alt};
    color: {theme.text};
}}

QPushButton:focus {{
    border-color: {theme.accent};
}}

QLabel#brand {{
    color: {theme.accent_alt};
    font-size: 16pt;
    font-weight: 800;
    letter-spacing: -0.3px;
}}

QLabel#eyebrow {{
    color: {theme.muted};
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 1.2px;
}}

QLabel#sectionTitle {{
    color: {theme.accent};
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1px;
}}

QLabel#sessionPath {{
    color: {theme.muted};
    font-size: 8.5pt;
    font-family: "Cascadia Code", "JetBrains Mono", "Consolas", monospace;
}}

QLabel#statusPill {{
    background-color: {theme.surface_alt};
    color: {theme.accent_alt};
    border: 1px solid {theme.border};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 0.8px;
}}

QPushButton#primaryButton {{
    background-color: {theme.accent};
    color: {theme.background};
    border: 1px solid {theme.accent};
    border-radius: 7px;
    padding: 7px 16px;
    font-weight: 700;
}}

QPushButton#primaryButton:hover {{
    background-color: {theme.accent_alt};
    border-color: {theme.accent_alt};
    color: {theme.background};
}}

QPushButton#primaryButton:pressed {{
    background-color: {theme.accent};
}}

QPushButton#primaryButton:disabled {{
    background-color: {theme.surface_alt};
    color: {theme.muted};
    border-color: {theme.border};
}}

QPushButton#navButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    text-align: left;
    padding: 8px 10px;
    color: {theme.muted};
    font-size: 9.5pt;
    font-weight: 500;
}}

QPushButton#navButton:hover {{
    background-color: {theme.surface_alt};
    border-color: {theme.border};
    color: {theme.text};
}}

QPushButton#navButton:checked, QPushButton#navButton:pressed {{
    background-color: {theme.surface_alt};
    border-color: {theme.accent};
    color: {theme.accent_alt};
    font-weight: 600;
}}

QTabWidget::pane {{
    border: 1px solid {theme.border};
    border-radius: 8px;
    background-color: {theme.surface};
    margin-top: -1px;
}}

QTabBar::tab {{
    background: {theme.background};
    color: {theme.muted};
    border: 1px solid {theme.border};
    border-bottom: none;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    padding: 8px 14px;
    margin-right: 3px;
    font-size: 9.5pt;
    font-weight: 500;
}}

QTabBar::tab:hover {{
    background: {theme.surface_alt};
    color: {theme.text};
}}

QTabBar::tab:selected {{
    background: {theme.surface};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-bottom: 2px solid {theme.accent};
    font-weight: 600;
}}

QTabBar::close-button {{
    subcontrol-position: right;
    margin: 2px;
    border-radius: 4px;
    padding: 2px;
}}

QTabBar::close-button:hover {{
    background-color: rgba(255, 100, 100, 0.25);
}}

QSplitter::handle {{
    background-color: {theme.background};
}}

QSplitter::handle:hover {{
    background-color: {theme.accent};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {theme.border};
    border-radius: 4px;
    min-height: 28px;
}}

QScrollBar::handle:vertical:hover {{
    background: {theme.muted};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
    border: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {theme.border};
    border-radius: 4px;
    min-width: 28px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {theme.muted};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
    border: none;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

QComboBox {{
    background-color: {theme.surface};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 9.5pt;
    min-height: 20px;
}}

QComboBox:hover {{
    border-color: {theme.accent};
}}

QComboBox:focus {{
    border: 1px solid {theme.accent};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}}

QComboBox QAbstractItemView {{
    background-color: {theme.surface};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 7px;
    selection-background-color: {theme.surface_alt};
    selection-color: {theme.accent_alt};
    padding: 4px;
    outline: none;
}}

QSpinBox {{
    background-color: {theme.surface};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 9.5pt;
    min-height: 20px;
}}

QSpinBox:focus {{
    border-color: {theme.accent};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
    background-color: {theme.button};
    border: 1px solid {theme.border};
    border-radius: 3px;
    margin: 1px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {theme.button_hover};
}}

QCheckBox {{
    color: {theme.text};
    spacing: 8px;
    font-size: 9.5pt;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {theme.border};
    border-radius: 4px;
    background-color: {theme.surface};
}}

QCheckBox::indicator:hover {{
    border-color: {theme.accent};
}}

QCheckBox::indicator:checked {{
    background-color: {theme.accent};
    border-color: {theme.accent};
}}

QDialog {{
    background-color: {theme.background};
}}

QToolTip {{
    background-color: {theme.surface_alt};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 9pt;
}}
"""
