"""Literal, bounded terminal transcript rendering on the Qt event loop."""
from collections import deque

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit


class TerminalOutput(QTextEdit):
    CHUNK_SIZE = 4096

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.document().setMaximumBlockCount(5000)
        self._pending = deque()
        self._output_timer = QTimer(self)
        self._output_timer.setInterval(8)
        self._output_timer.timeout.connect(self._drain_output)

    def append_output(self, text, color, label="", accent=None):
        # Keep the original string once; slice only the next visible batch.
        self._pending.append([text, 0, color, label, accent or color])
        if not self._output_timer.isActive():
            self._drain_output()
            if self._pending:
                self._output_timer.start()

    def _drain_output(self):
        if not self._pending:
            self._output_timer.stop()
            return
        text, offset, color, label, accent = self._pending[0]
        bar = self.verticalScrollBar()
        at_bottom, position = bar.value() == bar.maximum(), bar.value()
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if offset == 0:
            if not self.document().isEmpty():
                cursor.insertBlock()
            if label:
                prefix = QTextCharFormat(fmt)
                prefix.setForeground(QColor(accent))
                prefix.setFontWeight(QFont.DemiBold)
                cursor.insertText(label + " ", prefix)
        cursor.insertText(text[offset:offset + self.CHUNK_SIZE], fmt)
        offset += self.CHUNK_SIZE
        if offset >= len(text):
            self._pending.popleft()
        else:
            self._pending[0][1] = offset
        bar.setValue(bar.maximum() if at_bottom else position)
        if not self._pending:
            self._output_timer.stop()

    def clear(self):
        self._pending.clear()
        self._output_timer.stop()
        super().clear()
