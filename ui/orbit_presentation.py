"""Display-only formatting for Orbit; source messages and actions stay untouched."""
import re
from html import escape

from PySide6.QtGui import QFont, QTextDocument


def display_markdown(text: str) -> str:
    protected = r"(```[\s\S]*?```|~~~[\s\S]*?~~~|`+[^`\n]+`+)"
    # Protect commands before repairing prose so an approval preview always
    # displays the exact command, including literal escape sequences.
    parts = re.split(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)", text)
    for index in range(0, len(parts), 2):
        parts[index] = re.sub(
            r"(?m)^(Running in the active terminal:|Proposed command:)\n([^\n]+)",
            lambda match: match[1] + "\n\n```\n" + match[2] + "\n```",
            parts[index],
        )
    text = "".join(parts)
    # Repair escaped paragraph/list separators, never globally unescape paths or
    # code (D:\new, regexes, JSON and Python string literals must remain literal).
    parts = re.split(protected, text)
    structured = bool(re.search(r"(?<!\\)\\n(?:\\n|[ \t]*(?:[-*+] |\d+[.)] |#{1,6} ))", "".join(parts[::2])))
    for index in range(0, len(parts), 2):
        value = parts[index]
        value = re.sub(r"(?<!\\)\\r\\n(?=\\r\\n|\s*[-*#]|$)", "\n", value)
        value = re.sub(r"(?<!\\)(?:\\n){2,}", "\n\n", value)
        if structured:
            value = re.sub(r"(?<!\\)\\n(?=[ \t]*(?:[-*+] |\d+[.)] |#{1,6} )|$)", "\n", value)
        parts[index] = value
    return "".join(parts)


def message_html(label: str, text: str, theme) -> str:
    document = QTextDocument()
    document.setDefaultFont(QFont("Segoe UI", 10))
    if label == "You":
        # User input remains literal, including Markdown syntax and backslashes.
        document.setPlainText(text)
    else:
        document.setMarkdown(display_markdown(text))
    # A paragraph boundary carries meaning in short execution notifications.
    # Preserve those soft line breaks too; code/list formatting stays with Qt.
    if label != "You" and text.startswith("Completed:"):
        document.setPlainText(text)
    markup = document.toHtml().split("<body", 1)[1].split(">", 1)[1].rsplit("</body>", 1)[0]
    markup = markup.replace('<pre style="', f'<pre style="background-color:{theme.surface_alt};')
    foreground = "#d8dfe8"  # Readable prose even with neon terminal palettes.
    orbit_cyan = getattr(theme, "orbit_accent", "#38bdf8")

    if label == "You":
        role = "YOU"
        role_color = "#93c5fd"
        background = theme.surface
        border_style = f"border: 1px solid {theme.border}; border-radius: 8px;"
        extra_card = ""
    else:
        role = escape(label.upper())
        role_color = orbit_cyan
        background = theme.surface_alt
        border_style = (
            f"border-left: 3px solid {orbit_cyan}; border-top: 1px solid {theme.border}; "
            f"border-right: 1px solid {theme.border}; border-bottom: 1px solid {theme.border}; "
            f"border-radius: 8px;"
        )
        extra_card = ""
        if text.startswith("Completed:"):
            cmd = text.split("\n", 1)[0].replace("Completed:", "").strip()
            extra_card = (
                f'<p style="margin-top: 8px; font-size: 8.5pt;">'
                f'<a href="terminal://jump/{escape(cmd)}" style="color: {orbit_cyan}; text-decoration: none;">'
                f'<b>&#8594; View in terminal</b></a></p>'
            )

    return (
        f'<table width="100%" cellspacing="0" cellpadding="10" bgcolor="{background}" style="{border_style}">'
        f'<tr><td style="color:{foreground};">'
        f'<p style="font-family:Segoe UI;font-size:8pt;color:{role_color};font-weight:bold;margin-bottom:8px;">'
        f'{role}</p>{markup}{extra_card}</td></tr></table>'
        '<p style="font-size:4pt;margin:0;"><br /></p>'
    )


def terminal_reply(text: str) -> str:
    """Readable mirror of an AI message; native and built-in output bypass this."""
    if text.startswith("Completed:"):
        return text
    document = QTextDocument()
    document.setMarkdown(display_markdown(text))
    # toPlainText omits list markers; retain their hierarchy in the terminal.
    lines = []
    block = document.begin()
    while block.isValid():
        value = block.text()
        if block.textList():
            listing = block.textList()
            marker = listing.itemText(block) if listing.itemText(block)[:1].isdigit() else "-"
            value = "  " * max(0, listing.format().indent() - 1) + marker + " " + value
        lines.append(value)
        block = block.next()
    return "\n".join(lines)
