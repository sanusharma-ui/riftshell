from __future__ import annotations

from dataclasses import dataclass


FONT_UI = '"Sora", "Inter", "Segoe UI", sans-serif'
FONT_MONO = '"IBM Plex Mono", "Fira Code", Consolas, monospace'
TEXT_PRIMARY = "#EBFFFFFF"
TEXT_SECONDARY = "#ADFFFFFF"
TEXT_PLACEHOLDER = "#73FFFFFF"


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
        return TEXT_SECONDARY

    @property
    def accent_alt(self) -> str:
        return self.accent_alt_override or self.secondary or self.accent

    @property
    def output(self) -> str:
        return TEXT_PRIMARY

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
        display_name="Rift Horizon",
        aliases=(
            "default", "rift-horizon", "horizon", "violet", "dark+",
            "dark-plus", "vscode", "vs-code", "vs-code-dark-plus",
        ),
        bg="#0A0710",
        panel="#130D1E",
        panelBorder="rgba(192, 132, 252, 0.16)",
        text="#F4F0FA",
        textMuted="#9A8FB2",
        accent="#8B5CF6",
        accentGlow="rgba(139, 92, 246, 0.22)",
        success="#10B981",
        danger="#F43F5E",
        terminalBg="#08050D",
        inputBg="#140E21",
        buttonBg="#1D152E",
        buttonText="#F4F0FA",
        secondary="#C084FC",
        selection_override="#381E5E",
    ),
    "github-dark": Theme(
        key="github-dark",
        display_name="GitHub Carbon",
        aliases=("github", "github-dark", "gh-dark"),
        bg="#0B0E14",
        panel="#121721",
        panelBorder="#252C38",
        text="#E6EDF3",
        textMuted="#848D97",
        accent="#58A6FF",
        accentGlow="rgba(88, 166, 255, 0.16)",
        success="#3FB950",
        danger="#F85149",
        terminalBg="#070A0E",
        inputBg="#181F2C",
        buttonBg="#1E2636",
        buttonText="#E6EDF3",
        secondary="#79C0FF",
        selection_override="#1B3B6B",
    ),
    "midnight-aurora": Theme(
        key="midnight-aurora",
        display_name="Midnight Aurora",
        aliases=("midnight aurora", "aurora", "midnight"),
        bg="#04060D",
        panel="#07111F",
        panelBorder="rgba(20, 90, 140, 0.34)",
        text="#E6F7FF",
        textMuted="#8CA8B8",
        accent="#14B8A6",
        accentGlow="rgba(0, 150, 140, 0.24)",
        success="#34D399",
        danger="#FB7185",
        terminalBg="#03070A",
        inputBg="#0A1725",
        buttonBg="#0D2230",
        buttonText="#E6F7FF",
        secondary="#38BDF8",
        selection_override="#124A5A",
    ),
    "ember-grove": Theme(
        key="ember-grove",
        display_name="Ember Grove (Default)",
        aliases=("ember grove", "ember", "grove"),
        bg="#0A080B",
        panel="#080D0D",
        panelBorder="rgba(80, 35, 45, 0.34)",
        text="#F1F5F2",
        textMuted="#9BAEA6",
        accent="#14B88A",
        accentGlow="rgba(20, 110, 85, 0.24)",
        success="#34D399",
        danger="#F87171",
        terminalBg="#050A09",
        inputBg="#101817",
        buttonBg="#17231F",
        buttonText="#F1F5F2",
        secondary="#D97766",
        selection_override="#24483E",
    ),
}

DEFAULT_THEME_KEY = "ember-grove"

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
    is_rift_horizon = theme.key == "vscode-dark-plus"

    ui_font = FONT_UI
    mono_font = FONT_MONO

    panel_fill = theme.panel if theme.panel != "transparent" else "rgba(13, 19, 30, 0.40)"
    input_fill = theme.inputBg if theme.inputBg != "transparent" else "rgba(22, 31, 46, 0.30)"
    button_fill = theme.buttonBg if theme.buttonBg != "transparent" else "rgba(30, 41, 59, 0.35)"
    terminal_fill = theme.terminalBg if theme.terminalBg != "transparent" else "rgba(8, 11, 17, 0.35)"

    if is_rift_horizon:
        window_bg_css = (
            "background: qlineargradient(x1: 0.0, y1: 1.0, x2: 1.0, y2: 0.0, "
            "stop: 0.0 #240D2B, stop: 0.38 #0B0813, stop: 0.72 #0D1322, stop: 1.0 #162636);"
        )
        title_bar_bg = "background: transparent; border-bottom: none;"
        rail_bg_css = "background-color: rgba(20, 14, 32, 0.35);"
        primary_btn_bg = (
            "qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, "
            "stop: 0 #6D28D9, stop: 0.5 #7C3AED, stop: 1 #9333EA)"
        )
        primary_btn_hover = (
            "qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, "
            "stop: 0 #7C3AED, stop: 0.5 #8B5CF6, stop: 1 #A855F7)"
        )
        primary_btn_fg = "#FFFFFF"
        dock_bg_css = "background: transparent;"
    else:
        window_bg_css = f"background-color: {theme.bg};"
        title_bar_bg = "background: transparent; border-bottom: none;"
        rail_bg_css = f"background-color: rgba(19, 19, 28, 0.35);"
        primary_btn_bg = theme.accent
        primary_btn_hover = theme.accent_alt
        primary_btn_fg = "#06090F"
        dock_bg_css = "background: transparent;"

    tab_selected_css = f"""
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: {theme.bg};
    color: {TEXT_SECONDARY};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 7px 16px;
    margin-right: 4px;
    margin-top: 4px;
    font-size: 12px;
    font-weight: 600;
}}
QTabBar::tab:hover {{
    background: {input_fill};
    color: {TEXT_PRIMARY};
}}
QTabBar::tab:selected {{
    background: {panel_fill};
    color: {TEXT_PRIMARY};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-top: 2px solid {theme.accent};
    border-bottom: 1px solid {panel_fill};
    font-weight: 700;
}}
"""

    buttons_css = f"""
QPushButton {{
    background-color: {button_fill};
    color: {TEXT_PRIMARY};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 10px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12.5px;
    min-width: 0;
}}

QPushButton:hover {{
    background-color: {input_fill};
    border-color: {theme.accent};
    color: {TEXT_PRIMARY};
}}

QPushButton:pressed {{
    background-color: {theme.accentGlow};
    border-color: {theme.accent};
}}

QPushButton:disabled {{
    background-color: rgba(255, 255, 255, 0.02);
    color: {TEXT_PLACEHOLDER};
    border-color: rgba(255, 255, 255, 0.02);
}}

QPushButton#primaryButton {{
    background: {primary_btn_bg};
    color: {primary_btn_fg};
    border: 1px solid rgba(192, 132, 252, 0.45);
    border-radius: 12px;
    padding: 9px 20px;
    font-weight: 700;
    font-size: 13px;
}}

QPushButton#primaryButton:hover {{
    background: {primary_btn_hover};
    border-color: {theme.accent_alt};
    color: {primary_btn_fg};
}}

QPushButton#primaryButton:pressed {{
    background: {primary_btn_bg};
}}

QPushButton#primaryButton:disabled {{
    background: {button_fill};
    color: {theme.textMuted};
    border-color: {theme.panelBorder};
}}

QPushButton#railPrimaryBtn {{
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 rgba(139, 92, 246, 0.42), stop: 1 rgba(192, 132, 252, 0.24));
    color: {theme.text};
    border: 1px solid rgba(192, 132, 252, 0.45);
    border-radius: 13px;
    padding: 0px;
}}

QPushButton#railPrimaryBtn:hover {{
    background: {theme.accent};
    border-color: {theme.accent_alt};
}}

QPushButton#railIconBtn {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 11px;
    padding: 0px;
}}

QPushButton#railIconBtn:hover {{
    background-color: {theme.accentGlow};
    border-color: rgba(255, 255, 255, 0.04);
}}

QToolButton#railCardBtn {{
    background-color: transparent;
    color: {theme.text};
    border: 1px solid transparent;
    border-radius: 12px;
    padding: 6px 2px;
    font-size: 11.5px;
    font-weight: 600;
}}

QToolButton#railCardBtn:hover {{
    background-color: {theme.accentGlow};
    border-color: rgba(255, 255, 255, 0.04);
    color: #FFFFFF;
}}

QPushButton#railToggleBtn {{
    background-color: rgba(255, 255, 255, 0.03);
    color: {theme.text};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 12px;
    padding: 0px;
    font-size: 18px;
    font-weight: 700;
}}

QPushButton#railToggleBtn:hover {{
    background-color: {theme.accentGlow};
    border-color: {theme.accent};
    color: #FFFFFF;
}}

QPushButton#inlinePaletteBtn {{
    background-color: transparent;
    color: {theme.textMuted};
    border: none;
    border-radius: 8px;
    padding: 4px 10px;
    font-family: {mono_font};
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#inlinePaletteBtn:hover {{
    background-color: rgba(255, 255, 255, 0.05);
    color: {theme.text};
}}

QPushButton#approveButton {{
    background-color: rgba(16, 185, 129, 0.14);
    color: {theme.success};
    border: 1px solid {theme.success};
    border-radius: 10px;
    padding: 7px 12px;
    font-weight: 700;
    font-size: 12px;
}}

QPushButton#approveButton:hover {{
    background-color: {theme.success};
    border-color: {theme.success};
    color: #05080D;
}}

QPushButton#approveButton:disabled {{
    background-color: transparent;
    color: {theme.textMuted};
    border-color: {theme.panelBorder};
}}

QPushButton#dismissButton {{
    background-color: {button_fill};
    color: {theme.textMuted};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 10px;
    padding: 7px 12px;
    font-weight: 600;
    font-size: 12px;
}}

QPushButton#dismissButton:hover {{
    border-color: {theme.textMuted};
    color: {theme.text};
}}

QPushButton#dismissButton:disabled {{
    background-color: transparent;
    color: {theme.textMuted};
    border-color: rgba(255, 255, 255, 0.02);
}}

QPushButton#stopButton {{
    background-color: rgba(26, 18, 40, 0.50);
    color: {theme.text};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 12px;
    padding: 9px 18px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#stopButton:hover:enabled {{
    background-color: {theme.danger};
    border-color: {theme.danger};
    color: #FFFFFF;
}}

QPushButton#stopButton:disabled {{
    background-color: rgba(24, 16, 36, 0.35);
    color: {theme.text};
    border-color: rgba(255, 255, 255, 0.02);
}}
"""

    return f"""
QMainWindow {{
    {window_bg_css}
    border: 1px solid {theme.panelBorder};
    border-radius: 16px;
}}

QWidget#windowContainer {{
    background: transparent;
}}

QWidget#customTitleBar {{
    {title_bar_bg}
    min-height: 46px;
    max-height: 46px;
}}

QLabel#titleBrand {{
    color: {theme.text};
    font-size: 13.5px;
    font-weight: 700;
    font-family: {ui_font};
    letter-spacing: 0.3px;
    padding-left: 2px;
}}

QLabel#titleBadge {{
    background-color: rgba(255, 255, 255, 0.03);
    color: {theme.textMuted};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 10.5px;
    font-family: {mono_font};
    font-weight: 600;
}}

QLabel#titleCenterPill {{
    background-color: rgba(18, 13, 30, 0.40);
    color: {theme.textMuted};
    border: 1px solid rgba(255, 255, 255, 0.03);
    border-radius: 14px;
    padding: 4px 20px;
    font-size: 11.5px;
    font-family: {mono_font};
    font-weight: 600;
    letter-spacing: 0.8px;
}}

QPushButton#titleMinBtn, QPushButton#titleMaxBtn, QPushButton#titleCloseBtn {{
    background-color: transparent;
    color: {theme.textMuted};
    border: none;
    border-radius: 8px;
    padding: 0px;
    font-size: 14px;
    font-weight: 500;
    font-family: {ui_font};
    min-width: 44px;
    max-width: 44px;
    min-height: 36px;
    max-height: 36px;
}}

QPushButton#titleMinBtn:hover, QPushButton#titleMaxBtn:hover {{
    background-color: {input_fill};
    color: {theme.text};
}}

QPushButton#titleCloseBtn:hover {{
    background-color: #E11D48;
    color: #FFFFFF;
}}

QPushButton#titleCloseBtn:pressed {{
    background-color: #BE123C;
    color: #FFFFFF;
}}

QWidget {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    font-family: {ui_font};
    font-size: 13px;
}}

QLabel {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    font-size: 12.5px;
    font-family: {ui_font};
    min-width: 0;
}}

QLabel#brand {{
    color: {theme.text};
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.3px;
}}

QLabel#heroTitle {{
    color: {TEXT_PRIMARY};
    font-size: 28px;
    font-weight: 600;
    font-family: {mono_font};
    letter-spacing: 3px;
}}

QLabel#heroSubtitle {{
    color: {TEXT_SECONDARY};
    font-size: 13.5px;
    font-weight: 500;
    font-family: {mono_font};
    letter-spacing: 0.5px;
}}

QLabel#eyebrow, QLabel#sectionTitle {{
    color: {theme.textMuted};
    font-size: 10.5px;
    font-weight: 700;
    font-family: {mono_font};
    letter-spacing: 0.8px;
}}

QLabel#sessionPath {{
    color: {TEXT_SECONDARY};
    font-size: 11.5px;
    font-family: {mono_font};
    min-width: 0;
}}

QLabel#promptBadge {{
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 rgba(139, 92, 246, 0.36), stop: 1 rgba(192, 132, 252, 0.20));
    color: {theme.accent_alt};
    border: 1px solid rgba(192, 132, 252, 0.40);
    border-radius: 12px;
    padding: 7px 11px;
    font-size: 14px;
    font-family: {mono_font};
    font-weight: 700;
}}

QLabel#statusPill {{
    background-color: transparent;
    color: {theme.accent_alt};
    border: none;
    padding: 2px 8px;
    font-size: 11px;
    font-family: {mono_font};
    font-weight: 700;
    letter-spacing: 0.8px;
}}

QLabel#orbitStatusBanner {{
    background-color: {input_fill};
    color: {theme.textMuted};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-left: 3px solid {theme.accent};
    border-radius: 10px;
    padding: 7px 10px;
    font-size: 12px;
}}

QFrame#infoCard, QFrame#shortcutCard, QFrame#extensionCard, QFrame#modeBar, QFrame#orbitComposer {{
    background-color: {input_fill};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 12px;
}}

QFrame#commandInputShell {{
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 0.03);
    border-radius: 16px;
}}

QFrame#commandDock {{
    {dock_bg_css}
    border: 1px solid rgba(255, 255, 255, 0.02);
    border-radius: 24px;
}}

QTextEdit {{
    background-color: {panel_fill};
    color: {theme.text};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    selection-background-color: {theme.selection};
    selection-color: {theme.text};
    min-width: 0;
}}

QLineEdit {{
    background-color: {input_fill};
    color: {theme.text};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {theme.selection};
    selection-color: {theme.text};
    min-width: 0;
}}

QLineEdit:hover {{
    border-color: rgba(255, 255, 255, 0.08);
}}

QLineEdit:focus {{
    border: 1px solid {theme.accent};
    background-color: {input_fill};
}}

QListWidget {{
    background-color: {input_fill};
    color: {theme.text};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 12px;
    padding: 5px;
    outline: none;
    font-size: 12.5px;
    min-width: 0;
}}

QListWidget::item {{
    padding: 7px 10px;
    border-radius: 8px;
    margin: 1px 0px;
    border: 1px solid transparent;
}}

QListWidget::item:hover {{
    background-color: {button_fill};
    color: {theme.text};
}}

QListWidget::item:selected {{
    background-color: {theme.accentGlow};
    color: {theme.text};
    border: 1px solid {theme.accent};
    font-weight: 600;
}}

{tab_selected_css}

QAbstractItemView#commandSuggestions {{
    background-color: {panel_fill};
    color: {theme.text};
    border: 1px solid {theme.accent};
    border-radius: 12px;
    padding: 4px;
    outline: none;
    selection-background-color: {theme.selection};
    selection-color: {theme.text};
    font-family: {mono_font};
    font-size: 13px;
}}

QAbstractItemView#commandSuggestions::item {{
    padding: 7px 12px;
    min-height: 22px;
    border-radius: 6px;
    border: none;
}}

QAbstractItemView#commandSuggestions::item:hover {{
    background-color: {input_fill};
}}

{buttons_css}

QPushButton#navButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
    text-align: left;
    padding: 8px 11px;
    color: {theme.textMuted};
    font-size: 12.5px;
    font-weight: 600;
}}

QPushButton#navButton:hover {{
    background-color: {input_fill};
    border-color: rgba(255, 255, 255, 0.04);
    color: {theme.text};
}}

QPushButton#navButton:checked, QPushButton#navButton:pressed {{
    background-color: {theme.accentGlow};
    border-color: {theme.accent};
    color: {theme.accent};
    font-weight: 700;
}}

QPushButton#wrapToggle {{
    background-color: {input_fill};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 11px;
    font-family: {mono_font};
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
    background-color: transparent;
    color: {theme.textMuted};
    border-top: 1px solid rgba(255, 255, 255, 0.02);
    font-size: 11.5px;
    font-family: {mono_font};
    padding: 3px 14px;
}}

QStatusBar::item {{
    border: none;
}}

QFrame#leftRail, QFrame#rightRail {{
    {rail_bg_css}
    border: 1px solid rgba(255, 255, 255, 0.03);
    border-radius: 20px;
}}

QFrame#sidebar, QFrame#inspector {{
    {rail_bg_css}
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 18px;
}}

QFrame#terminalHeader {{
    border-radius: 14px;
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 0.02);
}}

QFrame#terminalHeader QPushButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    color: {theme.textMuted};
    padding: 4px 10px;
    font-size: 11.5px;
    font-weight: 600;
}}

QFrame#terminalHeader QPushButton:hover {{
    background-color: {button_fill};
    border-color: rgba(255, 255, 255, 0.05);
    color: {theme.text};
}}

QLineEdit#commandInput {{
    background-color: transparent;
    color: {theme.text};
    border: none;
    padding: 7px 12px;
    font-family: {mono_font};
    font-size: 13.5px;
    min-height: 22px;
    min-width: 0;
}}

QLineEdit#commandInput:focus {{
    border: none;
    background-color: transparent;
}}

QTextEdit#terminalOutput {{
    background-color: transparent;
    color: {theme.text};
    border: 1px solid rgba(255, 255, 255, 0.02);
    border-radius: 16px;
    padding: 12px 14px;
    font-family: {mono_font};
    font-size: 13.5px;
    min-width: 0;
}}

QLineEdit#orbitInput {{
    background-color: {theme.bg};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 10px;
    padding: 9px 12px;
    font-family: {ui_font};
    font-size: 13px;
    min-height: 22px;
    min-width: 0;
}}

QLineEdit#orbitInput:focus {{
    border-color: {theme.accent};
}}

QTextEdit#orbitConversation {{
    background-color: transparent;
    color: {theme.text};
    border: 1px solid rgba(255, 255, 255, 0.02);
    border-radius: 14px;
    padding: 12px;
    font-family: {ui_font};
    font-size: 13px;
    min-width: 0;
}}

QTabWidget#workspaceTabs::pane {{
    border: none;
    background: transparent;
    margin-top: 0px;
}}

QTabWidget::pane {{
    border: 1px solid rgba(255, 255, 255, 0.03);
    border-radius: 12px;
    background-color: transparent;
    margin-top: -1px;
}}

QTabBar::close-button {{
    subcontrol-position: right;
    margin: 2px;
    border-radius: 4px;
    padding: 2px;
}}

QTabBar::close-button:hover {{
    background-color: rgba(244, 63, 94, 0.25);
}}

QSplitter::handle {{
    background-color: transparent;
}}

QSplitter::handle:hover {{
    background-color: {theme.accent};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px 1px;
}}

QScrollBar::handle:vertical {{
    background: {theme.panelBorder};
    border-radius: 4px;
    min-height: 28px;
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
    margin: 1px 2px;
}}

QScrollBar::handle:horizontal {{
    background: {theme.panelBorder};
    border-radius: 4px;
    min-width: 28px;
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
    background-color: {input_fill};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 10px;
    padding: 6px 12px;
    font-size: 12.5px;
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
    background-color: {panel_fill};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 10px;
    selection-background-color: {theme.selection};
    selection-color: {theme.text};
    padding: 4px;
    outline: none;
}}

QSpinBox {{
    background-color: {input_fill};
    color: {theme.text};
    border: 1px solid {theme.panelBorder};
    border-radius: 10px;
    padding: 6px 10px;
    font-size: 12.5px;
    min-height: 20px;
}}

QSpinBox:focus {{
    border-color: {theme.accent};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 18px;
    background-color: {button_fill};
    border: 1px solid {theme.panelBorder};
    border-radius: 4px;
    margin: 1px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {theme.accentGlow};
}}

QCheckBox {{
    color: {theme.text};
    spacing: 8px;
    font-size: 12.5px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {theme.panelBorder};
    border-radius: 5px;
    background-color: {input_fill};
}}

QCheckBox::indicator:hover {{
    border-color: {theme.accent};
}}

QCheckBox::indicator:checked {{
    background-color: {theme.accent};
    border-color: {theme.accent};
}}

QDialog {{
    {window_bg_css}
    border: 1px solid {theme.panelBorder};
    border-radius: 14px;
}}

QLabel#titleBrand, QLabel#brand, QLabel#heroTitle, QLabel#titleCenterPill,
QTextEdit#terminalOutput, QTextEdit#orbitConversation, QLineEdit#commandInput,
QLineEdit#orbitInput {{
    color: {TEXT_PRIMARY};
}}

QLabel#titleBadge, QLabel#heroSubtitle, QLabel#eyebrow, QLabel#sectionTitle,
QLabel#sessionPath, QStatusBar, QTabBar::tab {{
    color: {TEXT_SECONDARY};
}}

QWidget:disabled, QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled,
QSpinBox:disabled, QCheckBox:disabled, QLabel:disabled {{
    color: {TEXT_PLACEHOLDER};
}}

QToolTip {{
    background-color: {panel_fill};
    color: {TEXT_PRIMARY};
    border: 1px solid {theme.panelBorder};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}}
"""
