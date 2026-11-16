from ui.themes import DEFAULT_THEME_KEY, build_stylesheet, get_theme

STYLE = build_stylesheet(get_theme(DEFAULT_THEME_KEY))

BOOT_BANNER = r"""
<pre style="
color:#C084FC;
font-family:'Cascadia Code', 'JetBrains Mono', 'Fira Code', Consolas, monospace;
font-size:10pt;
line-height:132%;
">
╭──────────────────────────────────────────────────────────────────────────────╮
│  ◈  R I F T S H E L L   //   A I - N A T I V E   W I N D O W S   S H E L L   │
├──────────────────────────────────────────────────────────────────────────────┤
│  CORE ENGINE   :  HYBRID PTY + BUILT-IN COMMAND RUNTIME                      │
│  AI COPILOT    :  ORBIT AGENT  (WORKSPACE-AWARE PLANNING &amp; DIFF REVIEW)      │
│  SHORTCUTS     :  [Ctrl+K] Command Palette   ·   [Ctrl+Shift+T] New Session  │
╰──────────────────────────────────────────────────────────────────────────────╯
  › Type "help" to browse built-in commands or ask Orbit AI in the right panel.
</pre>
"""
