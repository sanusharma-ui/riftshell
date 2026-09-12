"""Qt terminal surface: VT parsing, scrollback and interactive keyboard input."""
from __future__ import annotations

import copy
import re
from collections import deque
from itertools import groupby
from time import perf_counter

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QKeySequence
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QMessageBox


class TerminalWidget(QAbstractScrollArea):
    input_ready = Signal(str)
    size_changed = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        import pyte

        owner = self

        class Screen(pyte.HistoryScreen):
            def __init__(self):
                self.alternate = None
                super().__init__(100, 24, history=5000)

            def write_process_input(self, data):
                owner.input_ready.emit(data)

            def set_mode(self, *modes, **kwargs):
                if kwargs.get("private") and any(mode in {47, 1047, 1049} for mode in modes):
                    if self.alternate is None:
                        self.alternate = (copy.deepcopy(self.buffer), copy.copy(self.cursor), self.history)
                        self.buffer.clear()
                        self.cursor_position()
                        self.history = self.history._replace(top=copy.copy(self.history.top), bottom=copy.copy(self.history.bottom))
                        self.history.top.clear()
                        self.history.bottom.clear()
                super().set_mode(*modes, **kwargs)

            def reset_mode(self, *modes, **kwargs):
                if kwargs.get("private") and any(mode in {47, 1047, 1049} for mode in modes):
                    if self.alternate is not None:
                        self.buffer, self.cursor, self.history = self.alternate
                        self.alternate = None
                        self.cursor.x = min(self.cursor.x, self.columns - 1)
                        self.cursor.y = min(self.cursor.y, self.lines - 1)
                super().reset_mode(*modes, **kwargs)

        self.screen = Screen()
        self.stream = pyte.Stream(self.screen)
        self.input_enabled = False
        self.foreground = QColor("#d4d4d4")
        self.background = QColor("#1e1e1e")
        self._selection_start = None
        self._selection_end = None
        self._messages = deque()
        self._message_timer = QTimer(self)
        self._message_timer.timeout.connect(self._drain_messages)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.verticalScrollBar().valueChanged.connect(lambda _: self.viewport().update())
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._resize_screen)
        self.setFont(QFont("Consolas", 11))

    def set_colors(self, foreground: str, background: str):
        self.foreground, self.background = QColor(foreground), QColor(background)
        self.viewport().update()

    def feed(self, text: str):
        bar = self.verticalScrollBar()
        at_bottom = bar.value() == bar.maximum()
        self.stream.feed(text)
        self.screen.dirty.clear()
        bar.setRange(0, len(self.screen.history.top))
        bar.setPageStep(self.screen.lines)
        if at_bottom:
            bar.setValue(bar.maximum())
        self.viewport().update()

    def append_message(self, text: str, color: str | None = None):
        # Application messages are text, never terminal instructions.
        text = "\r\n" + re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text).replace("\n", "\r\n") + "\r\n"
        if color:
            tint = QColor(color)
            if tint.isValid():
                text = f"\x1b[0;38;2;{tint.red()};{tint.green()};{tint.blue()}m" + text + "\x1b[0m"
        self._messages.extend(text[i:i + 2048] for i in range(0, len(text), 2048))
        if not self._message_timer.isActive():
            self._message_timer.start(16)

    @property
    def output_pending(self):
        return bool(self._messages)

    def _drain_messages(self):
        deadline = perf_counter() + 0.006
        for _ in range(4):
            if not self._messages or perf_counter() >= deadline:
                break
            self.feed(self._messages.popleft())
        if not self._messages:
            self._message_timer.stop()

    def clear(self):
        self._messages.clear()
        self._message_timer.stop()
        self.screen.reset()
        self._selection_start = self._selection_end = None
        self.verticalScrollBar().setRange(0, 0)
        self.viewport().update()

    def _all_lines(self):
        return list(self.screen.history.top) + [self.screen.buffer[y] for y in range(self.screen.lines)]

    def toPlainText(self):
        return "\n".join("".join(line[x].data for x in range(self.screen.columns)).rstrip() for line in self._all_lines()).rstrip()

    def _metrics(self):
        metrics = QFontMetrics(self.font())
        return max(1, metrics.horizontalAdvance("M")), max(1, metrics.height()), metrics.ascent()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(60)

    def _resize_screen(self):
        width, height, _ = self._metrics()
        rows = max(2, self.viewport().height() // height)
        columns = max(10, self.viewport().width() // width)
        if (rows, columns) != (self.screen.lines, self.screen.columns):
            self.screen.resize(lines=rows, columns=columns)
            self.size_changed.emit(rows, columns)
        self.viewport().update()

    def _color(self, value, default):
        palette = {
            "black": "#1e1e1e", "red": "#cd3131", "green": "#0dbc79", "brown": "#e5e510",
            "blue": "#2472c8", "magenta": "#bc3fbc", "cyan": "#11a8cd", "white": "#e5e5e5",
            "brightblack": "#666666", "brightred": "#f14c4c", "brightgreen": "#23d18b",
            "brightbrown": "#f5f543", "brightblue": "#3b8eea", "brightmagenta": "#d670d6",
            "brightcyan": "#29b8db", "brightwhite": "#ffffff",
        }
        if value == "default":
            return default
        color = QColor(palette.get(value, "#" + value))
        return color if color.isValid() else default

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.fillRect(self.viewport().rect(), self.background)
        width, height, ascent = self._metrics()
        lines = self._all_lines()
        offset = self.verticalScrollBar().value()
        selected = sorted((self._selection_start, self._selection_end)) if self._selection_start is not None and self._selection_end is not None else None
        colors = {}
        fonts = {}
        def color(value, background=False):
            key = (value, background)
            if key not in colors:
                colors[key] = self._color(value, self.background if background else self.foreground)
            return colors[key]

        for y, line in enumerate(lines[offset:offset + self.screen.lines]):
            cells = [line[x] for x in range(self.screen.columns)]
            def background_key(x):
                cell = cells[x]
                highlighted = bool(selected and selected[0] <= (y + offset, x) <= selected[1])
                return (cell.fg if cell.reverse else cell.bg, not cell.reverse, highlighted)

            for key, indices in groupby(range(len(cells)), background_key):
                run = list(indices)
                bg = QColor("#365780") if key[2] else color(key[0], key[1])
                if bg != self.background:
                    painter.fillRect(run[0] * width, y * height, len(run) * width, height, bg)
            # Paint glyphs after backgrounds so a wide Unicode glyph is not
            # erased by the background of its following continuation cell.
            def foreground_key(x):
                cell = cells[x]
                # Non-ASCII glyphs keep their explicit terminal-cell positions.
                return (cell.bg if cell.reverse else cell.fg, cell.reverse,
                        cell.bold, cell.italics, cell.underscore, cell.strikethrough,
                        x if len(cell.data) != 1 or not cell.data.isascii() else None)

            for key, indices in groupby(range(len(cells)), foreground_key):
                run = list(indices)
                style = key[2:6]
                if style not in fonts:
                    font = QFont(self.font())
                    font.setBold(style[0])
                    font.setItalic(style[1])
                    font.setUnderline(style[2])
                    font.setStrikeOut(style[3])
                    fonts[style] = font
                painter.setFont(fonts[style])
                painter.setPen(color(key[0], key[1]))
                text = "".join(cells[x].data for x in run)
                if text.strip() or style[2] or style[3]:
                    painter.drawText(run[0] * width, y * height + ascent, text)
        cursor = self.screen.cursor
        if not cursor.hidden and offset == self.verticalScrollBar().maximum():
            painter.setPen(self.foreground)
            painter.drawRect(min(cursor.x, self.screen.columns - 1) * width, cursor.y * height, width - 1, height - 1)

    def _point(self, event):
        width, height, _ = self._metrics()
        return (max(0, min(self.screen.lines - 1, int(event.position().y()) // height)) + self.verticalScrollBar().value(),
                max(0, min(self.screen.columns - 1, int(event.position().x()) // width)))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setFocus()
            self._selection_start = self._selection_end = self._point(event)
            self.viewport().update()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._selection_end = self._point(event)
            self.viewport().update()

    def copy_selection(self):
        if self._selection_start is None or self._selection_end is None:
            return False
        start, end = sorted((self._selection_start, self._selection_end))
        if start == end:
            return False
        parts = []
        for row, line in enumerate(self._all_lines()):
            if start[0] <= row <= end[0]:
                left = start[1] if row == start[0] else 0
                right = end[1] + 1 if row == end[0] else self.screen.columns
                parts.append("".join(line[x].data for x in range(left, right)).rstrip())
        QApplication.clipboard().setText("\n".join(parts))
        return True

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy) and self.copy_selection():
            return
        if not self.input_enabled:
            super().keyPressEvent(event)
            return
        if event.matches(QKeySequence.Paste):
            text = QApplication.clipboard().text()
            if ("\n" in text or "\r" in text) and QMessageBox.question(
                self, "Paste multiple lines", "This paste contains line breaks and may submit input immediately. Paste it?"
            ) != QMessageBox.Yes:
                return
            text = text.replace("\r\n", "\n").replace("\n", "\r")
            if (2004 << 5) in self.screen.mode:
                text = "\x1b[200~" + text + "\x1b[201~"
            self.input_ready.emit(text)
            return
        mapping = {
            Qt.Key_Return: "\r", Qt.Key_Enter: "\r", Qt.Key_Backspace: "\x7f", Qt.Key_Tab: "\t",
            Qt.Key_Backtab: "\x1b[Z", Qt.Key_Escape: "\x1b", Qt.Key_Up: "\x1b[A",
            Qt.Key_Down: "\x1b[B", Qt.Key_Right: "\x1b[C", Qt.Key_Left: "\x1b[D",
            Qt.Key_Home: "\x1b[H", Qt.Key_End: "\x1b[F", Qt.Key_Insert: "\x1b[2~",
            Qt.Key_Delete: "\x1b[3~", Qt.Key_PageUp: "\x1b[5~", Qt.Key_PageDown: "\x1b[6~",
            Qt.Key_F1: "\x1bOP", Qt.Key_F2: "\x1bOQ", Qt.Key_F3: "\x1bOR", Qt.Key_F4: "\x1bOS",
            Qt.Key_F5: "\x1b[15~", Qt.Key_F6: "\x1b[17~", Qt.Key_F7: "\x1b[18~", Qt.Key_F8: "\x1b[19~",
            Qt.Key_F9: "\x1b[20~", Qt.Key_F10: "\x1b[21~", Qt.Key_F11: "\x1b[23~", Qt.Key_F12: "\x1b[24~",
        }
        text = mapping.get(event.key(), event.text())
        ctrl, alt = bool(event.modifiers() & Qt.ControlModifier), bool(event.modifiers() & Qt.AltModifier)
        if ctrl and not alt and Qt.Key_A <= event.key() <= Qt.Key_Z:
            text = chr(event.key() - Qt.Key_A + 1)
        elif alt and not ctrl:
            text = "\x1b" + text
        if (1 << 5) in self.screen.mode and text in {"\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D", "\x1b[H", "\x1b[F"}:
            text = text.replace("[", "O", 1)
        if text:
            self._selection_start = self._selection_end = None
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
            self.input_ready.emit(text)
        event.accept()

    def focusNextPrevChild(self, next_child):
        # Interactive tools need Tab/Shift+Tab rather than Qt focus traversal.
        if self.input_enabled:
            return False
        return super().focusNextPrevChild(next_child)
