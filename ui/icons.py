"""Small, consistent outline icons for desktop presentation (no asset dependency)."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def icon(name: str, size: int = 24, color: str | None = None) -> QIcon:
    paths = {
        "terminal": '<path d="m4 6 6 6-6 6m9 0h7"/>',
        "plus": '<path d="M12 5v14M5 12h14"/>',
        "search": '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
        "history": '<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6m3-3v5l3 2"/>',
        "commands": '<path d="m8 5-6 7 6 7m8-14 6 7-6 7m-3-16-2 18"/>',
        "settings": '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="15" cy="17" r="3"/>',
        "extensions": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
        "orbit": (
            '<defs><radialGradient id="planet" cx="28%" cy="22%" r="80%">'
            '<stop offset="0" stop-color="#e1eaf6"/><stop offset=".4" stop-color="#8da5c2"/>'
            '<stop offset=".78" stop-color="#3b506b"/><stop offset="1" stop-color="#182330"/>'
            '</radialGradient></defs>'
            '<ellipse cx="12" cy="12" rx="11" ry="4" transform="rotate(-28 12 12)" '
            'stroke="#61758e" stroke-width="1"/>'
            '<circle cx="12" cy="12" r="7.5" fill="url(#planet)" stroke="#9baec4" stroke-width=".5"/>'
            '<path d="M2.3 16.9c3.2 1.5 15.8-4.8 19.4-9.8" stroke="#c0ccdc" stroke-width="1.2"/>'
        ),
        "copy": '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
        "clear": '<path d="M4 7h16M9 7V3h6v4M6 7l1 14h10l1-14M10 11v6m4-6v6"/>',
        "send": '<path d="m3 3 18 9-18 9 4-9-4-9Zm4 9h14"/>',
        "chevron-down": '<path d="m6 9 6 6 6-6"/>',
        "chevron-right": '<path d="m9 18 6-6-6-6"/>',
        "check": '<path d="M20 6 9 17l-5-5"/>',
        "error": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/>',
        "play": '<polygon points="5 3 19 12 5 21 5 3"/>',
        "rerun": '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>',
        "spinner": '<path d="M21 12a9 9 0 1 1-6.219-8.56"/>',
        "collapse": '<path d="m4 14 8-8 8 8"/>',
        "file": '<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>',
        "folder": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
        "sidebar": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/>',
        "cancel": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6m0-6 6 6"/>',
        "sparkles": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
        "external": '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6m4-3h6v6m-11 5L21 3"/>',
    }
    stroke_color = color or "#9baec4"
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
           'viewBox="0 0 24 24" fill="none" stroke="' + stroke_color + '" stroke-width="1.6" '
           'stroke-linecap="round" stroke-linejoin="round">' + paths.get(name, paths["terminal"]) + '</svg>')
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)
