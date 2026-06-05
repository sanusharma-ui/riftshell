from html import escape

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
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
        self.resize(1180, 760)
        self.setStyleSheet(STYLE)

        central = QWidget()
        self.setCentralWidget(central)

        self.title_label = QLabel("SanuShell")
        self.title_label.setFont(QFont("Consolas", 12))

        self.path_label = QLabel(self.shell.prompt())
        self.path_label.setFont(QFont("Consolas", 10))

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 11))

        self.suggest_label = QLabel("Suggestions")
        self.suggest_label.setFont(QFont("Consolas", 10))

        self.suggestions = QListWidget()
        self.suggestions.setMaximumHeight(140)

        self.input = CommandInput()
        self.input.setPlaceholderText("Type command here...")

        self.run_btn = QPushButton("Run")
        self.clear_btn = QPushButton("Clear")

        bottom = QHBoxLayout()
        bottom.addWidget(self.input, stretch=1)
        bottom.addWidget(self.run_btn)
        bottom.addWidget(self.clear_btn)

        layout = QVBoxLayout(central)
        layout.addWidget(self.title_label)
        layout.addWidget(self.path_label)
        layout.addWidget(self.console, stretch=1)
        layout.addWidget(self.suggest_label)
        layout.addWidget(self.suggestions)
        layout.addLayout(bottom)

        self.run_btn.clicked.connect(self.run_command)
        self.input.returnPressed.connect(self.run_command)
        self.clear_btn.clicked.connect(self.clear_console)
        self.input.textChanged.connect(self.update_suggestions)
        self.suggestions.itemDoubleClicked.connect(self.apply_suggestion)

        self.command_names = self.shell.registry.all_names()
        self.completer_model = QStringListModel(self.command_names, self)
        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.input.setCompleter(self.completer)

        self.input.set_history(self.shell.ctx.history)
        self.update_suggestions("")
        self.update_status()

        self.append_system("Welcome to SanuShell")
        self.append_system("Type help to see commands.")

        self.input.setFocus()

    def update_status(self):
        self.statusBar().showMessage(
            f"cwd: {self.shell.ctx.cwd} | commands: {len(self.shell.registry.all_names())} | history: {len(self.shell.ctx.history)}"
        )
        self.path_label.setText(self.shell.prompt())

    def append_html(self, text: str, color: str):
        safe = escape(text).replace("\n", "<br>")
        self.console.moveCursor(QTextCursor.End)
        self.console.append(f'<div style="color:{color}; white-space:pre-wrap;">{safe}</div>')
        self.console.moveCursor(QTextCursor.End)

    def append_user(self, text: str):
        self.append_html(text, "#7dd3fc")

    def append_system(self, text: str):
        self.append_html(text, "#cbd5e1")

    def append_output(self, text: str):
        self.append_html(text, "#9dffb0")

    def append_error(self, text: str):
        self.append_html(text, "#ff7b7b")

    def clear_console(self):
        self.console.clear()
        self.append_system("Console cleared.")

    def update_suggestions(self, text: str):
        query = text.strip().lower()
        self.suggestions.clear()

        if not query:
            self.suggestions.hide()
            self.suggest_label.hide()
            return

        matches = []
        for cmd in self.shell.registry.list_commands():
            haystack = " ".join([cmd.name] + list(getattr(cmd, "aliases", []))).lower()
            if query in haystack:
                alias_text = f" | {', '.join(cmd.aliases)}" if cmd.aliases else ""
                item_text = f"{cmd.name}{alias_text} — {cmd.description}"
                matches.append((cmd.name, item_text))

        for name, item_text in matches[:12]:
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, name)
            self.suggestions.addItem(item)

        self.suggestions.setVisible(bool(matches))
        self.suggest_label.setVisible(bool(matches))

        filtered = [name for name in self.command_names if query in name.lower()]
        if not filtered:
            filtered = [name for name in self.command_names if query in name.lower() or query in name]
        self.completer_model.setStringList(filtered[:50])

    def apply_suggestion(self, item):
        command_name = item.data(Qt.UserRole)
        if command_name:
            self.input.setText(command_name)
            self.input.setFocus()
            self.input.setCursorPosition(len(command_name))

    def run_command(self):
        cmd = self.input.text().strip()
        if not cmd:
            return

        self.append_user(f"{self.shell.prompt()}{cmd}")
        result = self.shell.execute_line(cmd)

        if result.output:
            if result.success:
                self.append_output(result.output)
            else:
                self.append_error(result.output)

        self.shell.ctx.history.append(cmd) if False else None
        self.input.set_history(self.shell.ctx.history)
        self.input.clear()
        self.update_status()
        self.input.setFocus()