from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    key: str
    display_name: str
    aliases: tuple[str, ...]
    bg: str
    panel: str
    panelBorder: str
    text: str
    textMuted: str
    accent: str
    accentGlow: str
    success: str
    danger: str
    terminalBg: str
    inputBg: str
    buttonBg: str
    buttonText: str
    secondary: str = ""
    accent_alt_override: str = ""
    selection_override: str = ""

    @property
    def background(self) -> str:
        return self.bg

    @property
    def surface(self) -> str:
        return self.panel

    @property
    def surface_alt(self) -> str:
        return self.inputBg if self.inputBg != "transparent" else "rgba(255, 255, 255, 0.05)"

    @property
    def border(self) -> str:
        return self.panelBorder

    @property
    def muted(self) -> str:
        return self.textMuted

    @property
    def accent_alt(self) -> str:
        return self.accent_alt_override or self.secondary or self.accent

    @property
    def output(self) -> str:
        return self.text

    @property
    def error(self) -> str:
        return self.danger

    @property
    def selection(self) -> str:
        return self.selection_override or self.accentGlow

    @property
    def button(self) -> str:
        return self.buttonBg

    @property
    def button_hover(self) -> str:
        return self.accentGlow

    @property
    def button_pressed(self) -> str:
        return self.panel if self.panel != "transparent" else "rgba(255, 255, 255, 0.08)"

    @property
    def console_glow(self) -> str:
        return self.accentGlow

    @property
    def css_variables(self) -> dict[str, str]:
        return {
            "--bg": self.bg,
            "--panel": self.panel,
            "--panel-border": self.panelBorder,
            "--text": self.text,
            "--text-muted": self.textMuted,
            "--accent": self.accent,
            "--accent-glow": self.accentGlow,
            "--success": self.success,
            "--danger": self.danger,
            "--terminal-bg": self.terminalBg,
            "--input-bg": self.inputBg,
            "--button-bg": self.buttonBg,
            "--button-text": self.buttonText,
            "--selection": self.selection,
        }


THEMES: dict[str, Theme] = {
    "vscode-dark-plus": Theme(
        key="vscode-dark-plus",
        display_name="Default",
        aliases=("default", "violet", "dark+", "dark-plus", "vscode", "vs-code", "vs-code-dark-plus"),
        bg="#12111A",
        panel="#1A1826",
        panelBorder="#2E2A40",
        text="#EDE8F5",
        textMuted="#9A94AA",
        accent="#8B5CF6",
        accentGlow="rgba(139, 92, 246, 0.25)",
        success="#10B981",
        danger="#EF4444",
        terminalBg="#0F0E16",
        inputBg="#201D30",
        buttonBg="#28253B",
        buttonText="#EDE8F5",
        secondary="#A78BFA",
        selection_override="#3B2D54",
    ),
    "ghost": Theme(
        key="ghost",
        display_name="Ghost",
        aliases=("ghost", "sci-fi", "transparent"),
        bg="#08090C",
        panel="transparent",
        panelBorder="rgba(61, 224, 245, 0.12)",
        text="#E2E8F0",
        textMuted="#64748B",
        accent="#38BDF8",
        accentGlow="rgba(56, 189, 248, 0.20)",
        success="#34D399",
        danger="#F87171",
        terminalBg="transparent",
        inputBg="transparent",
        buttonBg="transparent",
        buttonText="#E2E8F0",
        secondary="#67E8F9",
        selection_override="rgba(56, 189, 248, 0.20)",
    ),
    "cyber-cyan": Theme(
        key="cyber-cyan",
        display_name="Cyber Cyan",
        aliases=("cyber-cyan", "cyan", "cyber"),
        bg="#070B10",
        panel="#0C131B",
        panelBorder="rgba(61, 224, 245, 0.25)",
        text="#DCE8F5",
        textMuted="#68829E",
        accent="#3DE0F5",
        accentGlow="rgba(61, 224, 245, 0.25)",
        success="#10B981",
        danger="#F43F5E",
        terminalBg="#05080D",
        inputBg="#101923",
        buttonBg="#131F2C",
        buttonText="#DCE8F5",
        secondary="#14B8A6",
        selection_override="#0D384D",
    ),
    "obsidian-aura": Theme(
        key="obsidian-aura",
        display_name="Obsidian Aura",
        aliases=("obsidian-aura", "obsidian", "aura", "eclipse", "eclipse-aura"),
        bg="#0A090F",
        panel="#121018",
        panelBorder="rgba(233, 222, 250, 0.20)",
        text="#F4F0FA",
        textMuted="#9B94AA",
        accent="#E9DEFA",
        accentGlow="rgba(233, 222, 250, 0.28)",
        success="#A7F3D0",
        danger="#FDA4AF",
        terminalBg="#07060A",
        inputBg="#171322",
        buttonBg="#1C182A",
        buttonText="#F4F0FA",
        secondary="#FBFCDB",
        selection_override="#33284D",
    ),
    "tokyo-night": Theme(
        key="tokyo-night",
        display_name="Tokyo Night",
        aliases=("tokyo", "tokyonight", "tokyo-night"),
        bg="#16161e",
        panel="#1a1b26",
        panelBorder="#2f354d",
        text="#c0caf5",
        textMuted="#7aa2f7",
        accent="#7aa2f7",
        accentGlow="rgba(122, 162, 247, 0.25)",
        success="#9ece6a",
        danger="#f7768e",
        terminalBg="#13141c",
        inputBg="#24283b",
        buttonBg="#24283b",
        buttonText="#c0caf5",
        secondary="#7dcfff",
        selection_override="#33467c",
    ),
    "nord": Theme(
        key="nord",
        display_name="Nord",
        aliases=("nord",),
        bg="#242933",
        panel="#2e3440",
        panelBorder="#434c5e",
        text="#eceff4",
        textMuted="#98a4ba",
        accent="#88c0d0",
        accentGlow="rgba(136, 192, 208, 0.25)",
        success="#a3be8c",
        danger="#bf616a",
        terminalBg="#1e222b",
        inputBg="#3b4252",
        buttonBg="#3b4252",
        buttonText="#eceff4",
        secondary="#8fbcbb",
        selection_override="#434c5e",
    ),
    "dracula": Theme(
        key="dracula",
        display_name="Dracula",
        aliases=("dracula",),
        bg="#1e1f29",
        panel="#282a36",
        panelBorder="#44475a",
        text="#f8f8f2",
        textMuted="#a5a8be",
        accent="#bd93f9",
        accentGlow="rgba(189, 147, 249, 0.25)",
        success="#50fa7b",
        danger="#ff5555",
        terminalBg="#191a21",
        inputBg="#343746",
        buttonBg="#343746",
        buttonText="#f8f8f2",
        secondary="#8be9fd",
        selection_override="#44475a",
    ),
    "github-dark": Theme(
        key="github-dark",
        display_name="GitHub Dark",
        aliases=("github", "github-dark", "gh-dark"),
        bg="#0a0c10",
        panel="#161b22",
        panelBorder="#30363d",
        text="#e6edf3",
        textMuted="#8b949e",
        accent="#58a6ff",
        accentGlow="rgba(88, 166, 255, 0.25)",
        success="#7ee787",
        danger="#ff7b72",
        terminalBg="#06080c",
        inputBg="#21262d",
        buttonBg="#21262d",
        buttonText="#e6edf3",
        secondary="#79c0ff",
        selection_override="#1f6feb",
    ),
    "catppuccin-mocha": Theme(
        key="catppuccin-mocha",
        display_name="Catppuccin Mocha",
        aliases=("catppuccin", "mocha"),
        bg="#181825",
        panel="#1e1e2e",
        panelBorder="#45475a",
        text="#cdd6f4",
        textMuted="#9399b2",
        accent="#cba6f7",
        accentGlow="rgba(203, 166, 247, 0.25)",
        success="#a6e3a1",
        danger="#f38ba8",
        terminalBg="#11111b",
        inputBg="#313244",
        buttonBg="#313244",
        buttonText="#cdd6f4",
        secondary="#89dceb",
        selection_override="#45475a",
    ),
    "one-dark-pro": Theme(
        key="one-dark-pro",
        display_name="One Dark Pro",
        aliases=("one-dark", "onedark", "atom"),
        bg="#1e2227",
        panel="#282c34",
        panelBorder="#3e4451",
        text="#abb2bf",
        textMuted="#7f848e",
        accent="#61afef",
        accentGlow="rgba(97, 175, 239, 0.25)",
        success="#98c379",
        danger="#e06c75",
        terminalBg="#181b20",
        inputBg="#353b45",
        buttonBg="#353b45",
        buttonText="#abb2bf",
        secondary="#56b6c2",
        selection_override="#3e4451",
    ),
    "cyberpunk-neon": Theme(
        key="cyberpunk-neon",
        display_name="Cyberpunk Neon",
        aliases=("cyberpunk", "cyber", "neon"),
        bg="#0d0e15",
        panel="#131520",
        panelBorder="#2b2d42",
        text="#00ff9f",
        textMuted="#7a82ab",
        accent="#00f0ff",
        accentGlow="rgba(0, 240, 255, 0.25)",
        success="#00ff9f",
        danger="#ff3366",
        terminalBg="#08090e",
        inputBg="#1d2030",
        buttonBg="#1d2030",
        buttonText="#00ff9f",
        secondary="#ff007f",
        selection_override="#3d1e4e",
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
    is_ghost = theme.key == "ghost"
    is_cyber = theme.key == "cyber-cyan"
    is_obsidian = theme.key == "obsidian-aura"

    # Tab selection indicator: Ghost uses a thin glowing underline, others use accent bottom border
    if is_ghost:
        tab_selected_css = f"""
QTabBar::tab {{
    background: transparent;
    color: {theme.textMuted};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 7px 14px;
    margin-right: 3px;
    font-size: 13px;
    font-weight: 500;
}}
QTabBar::tab:hover {{
    background: rgba(255, 255, 255, 0.04);
    color: {theme.text};
}}
QTabBar::tab:selected {{
    background: transparent;
    color: {theme.text};
    border: none;
    border-bottom: 2px solid {theme.accent};
    font-weight: 600;
}}
QListWidget::item:selected {{
    background-color: {theme.accentGlow};
    border-left: 2px solid {theme.accent};
    color: {theme.text};
    font-weight: 600;
}}
"""
    else:
        tab_selected_css = f"""
QTabBar::tab {{
    background: {theme.bg};
    color: {theme.textMuted};
    border: 1px solid {theme.panelBorder};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 14px;
    margin-right: 3px;
    font-size: 13px;
    font-weight: 500;
}}
QTabBar::tab:hover {{
    background: {theme.inputBg if theme.inputBg != "transparent" else "rgba(255, 255, 255, 0.05)"};
    color: {theme.text};
}}
QTabBar::tab:selected {{
    background: {theme.panel};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-bottom: 2px solid {theme.accent};
    font-weight: 600;
}}
QListWidget::item:selected {{
    background-color: {theme.inputBg if theme.inputBg != "transparent" else "rgba(255, 255, 255, 0.05)"};
    color: {theme.accent_alt};
    border: 1px solid {theme.panelBorder};
    font-weight: 600;
}}
"""

    if is_ghost:
        buttons_css = f"""
QPushButton {{
    background-color: transparent;
    color: {theme.text};
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 13px;
    min-width: 0;
}}

QPushButton:hover {{
    background-color: {theme.accentGlow};
    border-color: {theme.accent};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: rgba(255, 255, 255, 0.08);
}}

QPushButton:disabled {{
    background-color: transparent;
    color: {theme.textMuted};
    border-color: rgba(255, 255, 255, 0.08);
}}

QPushButton#primaryButton {{
    background-color: transparent;
    color: {theme.accent};
    border: 1px solid {theme.accent};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#primaryButton:hover {{
    background-color: {theme.accentGlow};
    border-color: {theme.accent_alt};
    color: #ffffff;
}}

QPushButton#approveButton {{
    background-color: transparent;
    color: {theme.success};
    border: 1px solid {theme.success};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#approveButton:hover {{
    background-color: rgba(52, 211, 153, 0.15);
    color: #ffffff;
}}

QPushButton#dismissButton {{
    background-color: transparent;
    color: {theme.textMuted};
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#dismissButton:hover {{
    border-color: {theme.text};
    color: {theme.text};
}}

QPushButton#stopButton {{
    background-color: transparent;
    color: {theme.danger};
    border: 1px solid {theme.danger};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#stopButton:hover {{
    background-color: rgba(248, 113, 113, 0.15);
    color: #ffffff;
}}
"""
    elif is_obsidian:
        buttons_css = f"""
QPushButton {{
    background-color: {theme.buttonBg};
    color: {theme.buttonText};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 13px;
    min-width: 0;
}}

QPushButton:hover {{
    background-color: #27213A;
    border-color: rgba(233, 222, 250, 0.55);
    color: #FFFFFF;
}}

QPushButton:pressed {{
    background-color: #14101E;
    border-color: rgba(251, 252, 219, 0.45);
}}

QPushButton:disabled {{
    background-color: {theme.panel};
    color: {theme.textMuted};
    border-color: rgba(233, 222, 250, 0.10);
}}

QPushButton#primaryButton {{
    background: qlineargradient(x1: 0.1, y1: 0.9, x2: 0.9, y2: 0.1, stop: 0 #E9DEFA, stop: 1 #FBFCDB);
    color: #0A090F;
    border: 1px solid rgba(251, 252, 219, 0.8);
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 13px;
}}

QPushButton#primaryButton:hover {{
    background: qlineargradient(x1: 0.1, y1: 0.9, x2: 0.9, y2: 0.1, stop: 0 #F3ECFE, stop: 1 #FFFFE8);
    border-color: #FFFFFF;
    color: #000000;
}}

QPushButton#primaryButton:pressed {{
    background: qlineargradient(x1: 0.1, y1: 0.9, x2: 0.9, y2: 0.1, stop: 0 #D5C5EE, stop: 1 #ECEEBF);
}}

QPushButton#approveButton {{
    background-color: {theme.success};
    color: #0A090F;
    border: 1px solid {theme.success};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 13px;
}}

QPushButton#approveButton:hover {{
    background-color: #6EE7B7;
    border-color: #6EE7B7;
    color: #050505;
}}

QPushButton#dismissButton {{
    background-color: {theme.buttonBg};
    color: {theme.textMuted};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#dismissButton:hover {{
    border-color: {theme.accent};
    color: {theme.text};
}}

QPushButton#stopButton {{
    background-color: {theme.danger};
    color: #0A090F;
    border: 1px solid {theme.danger};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 13px;
}}

QPushButton#stopButton:hover {{
    background-color: #FECDD3;
    border-color: #FECDD3;
    color: #000000;
}}
"""
    else:
        primary_fg = "#070B10" if is_cyber else "#ffffff"
        approve_fg = "#070B10" if is_cyber else "#ffffff"
        stop_fg = "#ffffff"
        buttons_css = f"""
QPushButton {{
    background-color: {theme.buttonBg};
    color: {theme.buttonText};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 13px;
    min-width: 0;
}}

QPushButton:hover {{
    background-color: {theme.inputBg if theme.inputBg != "transparent" else theme.buttonBg};
    border-color: {theme.accent};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: {theme.panel if theme.panel != "transparent" else "rgba(255, 255, 255, 0.08)"};
}}

QPushButton:disabled {{
    background-color: {theme.panel if theme.panel != "transparent" else "transparent"};
    color: {theme.textMuted};
    border-color: {theme.panelBorder};
}}

QPushButton#primaryButton {{
    background-color: {theme.accent};
    color: {primary_fg};
    border: 1px solid {theme.accent};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#primaryButton:hover {{
    background-color: {theme.accent_alt};
    border-color: {theme.accent_alt};
    color: {primary_fg};
}}

QPushButton#approveButton {{
    background-color: {theme.success};
    color: {approve_fg};
    border: 1px solid {theme.success};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#approveButton:hover {{
    background-color: {theme.success};
    border-color: {theme.accent};
    color: #ffffff;
}}

QPushButton#dismissButton {{
    background-color: {theme.buttonBg};
    color: {theme.textMuted};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#dismissButton:hover {{
    border-color: {theme.accent};
    color: {theme.text};
}}

QPushButton#stopButton {{
    background-color: {theme.danger};
    color: {stop_fg};
    border: 1px solid {theme.danger};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#stopButton:hover {{
    border-color: #ffffff;
    color: #ffffff;
}}
"""

    terminal_glow_css = ""
    cyber_label_font = '"JetBrains Mono", "Cascadia Code", monospace' if is_cyber else '"Inter", "Geist", "Segoe UI Variable Text", "Segoe UI", sans-serif'
    window_background_css = (
        "background: qlineargradient(x1: 0.1, y1: 0.85, x2: 0.9, y2: 0.15, stop: 0 #151022, stop: 0.45 #0A090F, stop: 0.75 #0C0B12, stop: 1 #181710);"
        if is_obsidian
        else f"background-color: {theme.bg};"
    )
    dialog_background_css = (
        "background: qlineargradient(x1: 0.1, y1: 0.85, x2: 0.9, y2: 0.15, stop: 0 #151022, stop: 0.45 #0A090F, stop: 1 #181710);"
        if is_obsidian
        else f"background-color: {theme.bg};"
    )
    if is_obsidian:
        title_bar_bg = (
            "background: qlineargradient(x1: 0.1, y1: 0.85, x2: 0.9, y2: 0.15, "
            "stop: 0 #151022, stop: 0.45 #0A090F, stop: 0.75 #0C0B12, stop: 1 #181710); "
            "border-bottom: 1px solid rgba(233, 222, 250, 0.18);"
        )
    elif is_ghost:
        title_bar_bg = "background: transparent; border-bottom: 1px solid rgba(61, 224, 245, 0.12);"
    elif is_cyber:
        title_bar_bg = "background-color: #0C131B; border-bottom: 1px solid rgba(61, 224, 245, 0.25);"
    else:
        title_bar_bg = f"background-color: {theme.bg}; border-bottom: 1px solid {theme.panelBorder};"

    return f"""
QMainWindow {{
    {window_background_css}
    border: 1px solid {theme.panelBorder};
}}

QWidget#customTitleBar {{
    {title_bar_bg}
    min-height: 40px;
    max-height: 40px;
}}

QLabel#titleBrand {{
    color: {theme.text};
    font-size: 13px;
    font-weight: 700;
    font-family: "Inter", "Geist", "Segoe UI Variable Text", sans-serif;
    padding-left: 2px;
}}

QLabel#titleBadge {{
    background: transparent;
    color: {theme.textMuted};
    border: none;
    padding: 0px;
    font-size: 11px;
    font-family: "JetBrains Mono", monospace;
    font-weight: 500;
}}

QLabel#titleCenterPill {{
    background: transparent;
    color: {theme.textMuted};
    border: none;
    padding: 0px;
    font-size: 12px;
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
    font-weight: 500;
}}

QPushButton#titleMinBtn, QPushButton#titleMaxBtn, QPushButton#titleCloseBtn {{
    background-color: transparent;
    color: {theme.textMuted};
    border: none;
    border-radius: 0px;
    padding: 0px;
    font-size: 16px;
    font-weight: 600;
    font-family: "Segoe UI", sans-serif;
    min-width: 48px;
    max-width: 48px;
    min-height: 40px;
    max-height: 40px;
}}

QPushButton#titleMinBtn:hover, QPushButton#titleMaxBtn:hover {{
    background-color: {theme.inputBg if theme.inputBg != "transparent" else "rgba(255, 255, 255, 0.08)"};
    color: {theme.accent};
}}

QPushButton#titleCloseBtn:hover {{
    background-color: {theme.danger};
    color: #FFFFFF;
}}

QPushButton#titleCloseBtn:pressed {{
    background-color: {theme.danger};
    color: #FFFFFF;
}}

QWidget {{
    background-color: {theme.bg};
    color: {theme.text};
    font-family: "Inter", "Geist", "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 13px;
}}

QLabel {{
    background-color: transparent;
    color: {theme.textMuted};
    font-size: 13px;
    font-family: {cyber_label_font};
    min-width: 0;
}}

QLabel#brand {{
    color: {theme.text};
    font-size: 16px;
    font-weight: 700;
}}

QLabel#eyebrow, QLabel#sectionTitle {{
    color: {theme.textMuted};
    font-size: 11px;
    font-weight: 700;
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
}}

QLabel#sessionPath {{
    color: {theme.textMuted};
    font-size: 11px;
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
    min-width: 0;
}}

QLabel#statusPill {{
    background-color: {theme.inputBg if theme.inputBg != "transparent" else "rgba(255, 255, 255, 0.05)"};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 11px;
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
    font-weight: 600;
}}

QTextEdit {{
    background-color: {theme.panel};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 13px;
    selection-background-color: {theme.selection};
    selection-color: {theme.text};
    min-width: 0;
}}

QLineEdit {{
    background-color: {theme.inputBg};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {theme.selection};
    selection-color: {theme.text};
    min-width: 0;
}}

QLineEdit:focus {{
    border: 1px solid {theme.accent};
    background-color: {theme.inputBg if theme.inputBg != "transparent" else "rgba(255, 255, 255, 0.04)"};
}}

QListWidget {{
    background-color: {theme.panel};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 6px;
    outline: none;
    font-size: 13px;
    min-width: 0;
}}

QListWidget::item {{
    padding: 7px 10px;
    border-radius: 5px;
    margin: 1px 0px;
    border: 1px solid transparent;
}}

QListWidget::item:hover {{
    background-color: {theme.inputBg if theme.inputBg != "transparent" else "rgba(255, 255, 255, 0.04)"};
    color: {theme.text};
}}

{tab_selected_css}

QAbstractItemView#commandSuggestions {{
    background-color: {theme.panel};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    padding: 4px;
    outline: none;
    selection-background-color: {theme.selection};
    selection-color: {theme.text};
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
    font-size: 13px;
}}

QAbstractItemView#commandSuggestions::item {{
    padding: 7px 12px;
    min-height: 20px;
    border: none;
}}

QAbstractItemView#commandSuggestions::item:hover {{
    background-color: {theme.inputBg if theme.inputBg != "transparent" else "rgba(255, 255, 255, 0.05)"};
}}

{buttons_css}

QPushButton#navButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    text-align: left;
    padding: 8px 10px;
    color: {theme.textMuted};
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#navButton:hover {{
    background-color: {theme.inputBg if theme.inputBg != "transparent" else "rgba(255, 255, 255, 0.05)"};
    border-color: {theme.panelBorder};
    color: {theme.text};
}}

QPushButton#navButton:checked, QPushButton#navButton:pressed {{
    background-color: {theme.inputBg if theme.inputBg != "transparent" else "rgba(255, 255, 255, 0.05)"};
    border-color: {theme.accent};
    color: {theme.accent};
    font-weight: 600;
}}

QPushButton#wrapToggle {{
    background-color: transparent;
    border: 1px solid {theme.panelBorder};
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 11px;
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
    font-weight: 600;
    color: {theme.textMuted};
}}

QPushButton#wrapToggle:hover {{
    border-color: {theme.accent};
    color: {theme.text};
}}

QPushButton#wrapToggle:checked {{
    background-color: {theme.accentGlow};
    border-color: {theme.accent};
    color: {theme.accent};
}}

QStatusBar {{
    background-color: {theme.panel};
    color: {theme.textMuted};
    border-top: 1px solid {theme.panelBorder};
    font-size: 12px;
    padding: 3px 10px;
}}

QFrame#sidebar, QFrame#inspector, QFrame#terminalHeader {{
    background-color: {theme.panel};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
}}

QFrame#sidebar {{
    border-radius: 0;
    border-top: 0;
    border-bottom: 0;
    border-left: 0;
    border-right: 1px solid {theme.panelBorder};
}}

QFrame#inspector {{
    border-radius: 0;
    border-top: 0;
    border-bottom: 0;
    border-right: 0;
    border-left: 1px solid {theme.panelBorder};
}}

QFrame#terminalHeader {{
    border-radius: 6px;
    background-color: {theme.panel};
}}

QFrame#terminalHeader QPushButton {{
    background-color: transparent;
    border-color: transparent;
    color: {theme.textMuted};
    padding: 4px 8px;
    font-size: 12px;
}}

QFrame#terminalHeader QPushButton:hover {{
    background-color: {theme.inputBg if theme.inputBg != "transparent" else "rgba(255, 255, 255, 0.06)"};
    color: {theme.text};
}}

QLineEdit#commandInput {{
    background-color: {theme.inputBg};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 9px 12px;
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
    font-size: 14px;
    min-height: 22px;
    min-width: 0;
}}

QLineEdit#commandInput:focus {{
    border-color: {theme.accent};
}}

QTextEdit#terminalOutput {{
    background-color: {theme.terminalBg};
    color: {theme.text};
    border: none;
    padding: 12px 14px;
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
    font-size: 14px;
    min-width: 0;
    {terminal_glow_css}
}}

QLineEdit#orbitInput {{
    background-color: {theme.inputBg};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 10px 14px;
    font-family: "JetBrains Mono", "Cascadia Code", monospace;
    font-size: 14px;
    min-height: 22px;
    min-width: 0;
}}

QLineEdit#orbitInput:focus {{
    border-color: {theme.accent};
}}

QTextEdit#orbitConversation {{
    background-color: {theme.terminalBg if not is_ghost else "transparent"};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 12px;
    font-family: "Inter", "Geist", "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 14px;
    min-width: 0;
}}

QTabWidget::pane {{
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    background-color: {theme.panel};
    margin-top: -1px;
}}

QTabBar::close-button {{
    subcontrol-position: right;
    margin: 2px;
    border-radius: 4px;
    padding: 2px;
}}

QTabBar::close-button:hover {{
    background-color: rgba(239, 68, 68, 0.25);
}}

QSplitter::handle {{
    background-color: {theme.bg};
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
    background: {theme.panelBorder};
    border-radius: 4px;
    min-height: 26px;
}}

QScrollBar::handle:vertical:hover {{
    background: {theme.textMuted};
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
    background: {theme.panelBorder};
    border-radius: 4px;
    min-width: 26px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {theme.textMuted};
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
    background-color: {theme.inputBg};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
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
    background-color: {theme.panel};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    selection-background-color: {theme.selection};
    selection-color: {theme.text};
    padding: 4px;
    outline: none;
}}

QSpinBox {{
    background-color: {theme.inputBg};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    min-height: 20px;
}}

QSpinBox:focus {{
    border-color: {theme.accent};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
    background-color: {theme.buttonBg};
    border: 1px solid {theme.panelBorder};
    border-radius: 3px;
    margin: 1px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {theme.accentGlow};
}}

QCheckBox {{
    color: {theme.text};
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {theme.panelBorder};
    border-radius: 4px;
    background-color: {theme.inputBg};
}}

QCheckBox::indicator:hover {{
    border-color: {theme.accent};
}}

QCheckBox::indicator:checked {{
    background-color: {theme.accent};
    border-color: {theme.accent};
}}

QDialog {{
    {dialog_background_css}
}}

QToolTip {{
    background-color: {theme.panel};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
}}
"""
