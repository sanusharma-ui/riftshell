from html import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.shell import Shell
from ui.styles import STYLE


class CommandInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = []
        self.history_index = -1

    def set_history(self, history):
        self.history = history[:]
        self.history_index = len(self.history)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            if self.history:
                self.history_index = max(0, self.history_index - 1)
                self.setText(self.history[self.history_index])
                self.setCursorPosition(len(self.text()))
            return

        if event.key() == Qt.Key_Down:
            if self.history:
                self.history_index = min(len(self.history), self.history_index + 1)
                if self.history_index >= len(self.history):
                    self.clear()
                else:
                    self.setText(self.history[self.history_index])
                    self.setCursorPosition(len(self.text()))
            return

        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.shell = Shell()

        self.setWindowTitle("SanuShell")
        self.resize(1100, 700)
        self.setStyleSheet(STYLE)

        central = QWidget()
        self.setCentralWidget(central)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 11))

        self.path_label = QLabel(self.shell.prompt())
        self.path_label.setFont(QFont("Consolas", 10))

        self.input = CommandInput()
        self.input.setPlaceholderText("Type command here...")

        self.run_btn = QPushButton("Run")
        self.clear_btn = QPushButton("Clear")

        bottom = QHBoxLayout()
        bottom.addWidget(self.input, stretch=1)
        bottom.addWidget(self.run_btn)
        bottom.addWidget(self.clear_btn)

        layout = QVBoxLayout(central)
        layout.addWidget(self.path_label)
        layout.addWidget(self.console, stretch=1)
        layout.addLayout(bottom)

        self.run_btn.clicked.connect(self.run_command)
        self.input.returnPressed.connect(self.run_command)
        self.clear_btn.clicked.connect(self.console.clear)

        self.input.setFocus()

        self.append_system("Welcome to SanuShell")
        self.append_system("Type help to see commands.")

    def append_line(self, text: str, color: str = "#9dffb0"):
        safe = escape(text).replace("\n", "<br>")
        self.console.moveCursor(QTextCursor.End)
        self.console.append(f'<span style="color:{color}; white-space:pre-wrap;">{safe}</span>')
        self.console.moveCursor(QTextCursor.End)

    def append_prompt(self, text: str):
        safe = escape(text).replace("\n", "<br>")
        self.console.moveCursor(QTextCursor.End)
        self.console.append(f'<span style="color:#7dd3fc; white-space:pre-wrap;">{safe}</span>')
        self.console.moveCursor(QTextCursor.End)

    def append_system(self, text: str):
        self.append_line(text, "#cbd5e1")

    def append_error(self, text: str):
        self.append_line(text, "#ff7b7b")

    def run_command(self):
        cmd = self.input.text().strip()
        if not cmd:
            return

        self.append_prompt(f"{self.shell.prompt()}{cmd}")

        result = self.shell.execute_line(cmd)

        if result.output:
            if result.success:
                self.append_line(result.output, "#9dffb0")
            else:
                self.append_error(result.output)

        self.path_label.setText(self.shell.prompt())
        self.input.set_history(self.shell.ctx.history)
        self.input.clear()
        self.input.setFocus()