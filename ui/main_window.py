import random
import re
from html import escape

from PySide6.QtCore import Qt, QStringListModel, QThread, Signal, QTimer, QEvent
from PySide6.QtGui import QFont, QTextCursor, QColor
from PySide6.QtWidgets import (
    QCompleter,
    QGraphicsColorizeEffect,
    QGraphicsDropShadowEffect,
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
from ui.styles import STYLE, BOOT_BANNER


class CommandInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = []
        self.history_index = -1
        self.command_names = []

    def set_history(self, history):
        self.history = history[:]
        self.history_index = len(self.history)

    def set_completion_items(self, items):
        self.command_names = [item.lower() for item in items]

    def _complete_current_command(self) -> bool:
        text = self.text()
        if not text.strip():
            return False

        parts = text.split(maxsplit=1)
        prefix = parts[0]
        rest = f" {parts[1]}" if len(parts) > 1 else ""

        matches = [cmd for cmd in self.command_names if cmd.startswith(prefix.lower())]
        if not matches:
            return False

        self.setText(matches[0] + rest)
        self.setCursorPosition(len(matches[0]))
        return True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            if self._complete_current_command():
                return

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


# ======= NAYA BACKGROUND WORKER CLASS =======
class CommandWorker(QThread):
    # Jab command khatam ho jayegi toh ye signal result wapas bhejega
    result_ready = Signal(object)

    def __init__(self, shell, cmd_text, parent=None):
        super().__init__(parent)
        self.shell = shell
        self.cmd_text = cmd_text

    def run(self):
        # Ye background thread me execute hoga, UI block nahi karega!
        result = self.shell.execute_line(self.cmd_text)
        self.result_ready.emit(result)
# ==============================================


# ======= NAYA SCANLINE OVERLAY (boot ke time console ke upar chalta hai) =======
class ScanlineOverlay(QWidget):
    """Translucent scanning beam that sweeps down over a widget during boot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._pos = 0.0
        self._speed = 0.025
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    def start(self):
        self._pos = -0.15
        self.show()
        self.raise_()
        self._timer.start(16)

    def stop(self):
        self._timer.stop()
        self.hide()

    def _advance(self):
        self._pos += self._speed
        if self._pos > 1.15:
            self._pos = -0.15
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QLinearGradient, QPen

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # faint persistent scanline texture
        painter.setPen(QPen(QColor(0, 255, 156, 10)))
        for y in range(0, h, 3):
            painter.drawLine(0, y, w, y)

        # the sweeping beam
        beam_y = int(self._pos * h)
        gradient = QLinearGradient(0, beam_y - 40, 0, beam_y + 40)
        gradient.setColorAt(0.0, QColor(0, 255, 156, 0))
        gradient.setColorAt(0.5, QColor(0, 255, 156, 70))
        gradient.setColorAt(1.0, QColor(0, 255, 156, 0))
        painter.fillRect(0, beam_y - 40, w, 80, gradient)

        painter.setPen(QPen(QColor(0, 255, 156, 160), 1))
        painter.drawLine(0, beam_y, w, beam_y)

        painter.end()
# ==============================================


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.shell = Shell()

        self.setWindowTitle("RiftShell // Neon Mode")
        self.resize(1180, 760)
        self.setStyleSheet(STYLE)

        central = QWidget()
        self.setCentralWidget(central)

        self.title_label = QLabel("RiftShell")
        self.title_label.setFont(QFont("Consolas", 18, QFont.Bold))
        self.title_label.setStyleSheet("color: #00ff9c; letter-spacing: 1px;")

        title_glow = QGraphicsDropShadowEffect(self)
        title_glow.setBlurRadius(24)
        title_glow.setOffset(0, 0)
        title_glow.setColor(Qt.green)
        self.title_label.setGraphicsEffect(title_glow)

        self.tagline = QLabel("dark neon shell • tab completion enabled • custom commands")
        self.tagline.setFont(QFont("Consolas", 10))
        self.tagline.setStyleSheet("color: #7dd3fc;")

        self.path_label = QLabel(self.shell.prompt())
        self.path_label.setFont(QFont("Consolas", 10))
        self.path_label.setStyleSheet("color: #94a3b8;")

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 11))

        self._apply_console_glow()

        # scanline overlay sits on top of the console, only visible during boot
        self.scanline = ScanlineOverlay(self.console)
        self.scanline.setGeometry(self.console.rect())
        self.scanline.hide()
        self.console.installEventFilter(self)

        self.suggest_label = QLabel("Suggestions")
        self.suggest_label.setFont(QFont("Consolas", 10))
        self.suggest_label.setStyleSheet("color: #7dd3fc;")

        self.suggestions = QListWidget()
        self.suggestions.setMaximumHeight(150)

        self.input = CommandInput()
        self.input.setPlaceholderText("Type command here...  (Tab to complete)")
        self.input.setFont(QFont("Consolas", 12))

        self.run_btn = QPushButton("Run")
        self.clear_btn = QPushButton("Clear")

        bottom = QHBoxLayout()
        bottom.addWidget(self.input, stretch=1)
        bottom.addWidget(self.run_btn)
        bottom.addWidget(self.clear_btn)

        layout = QVBoxLayout(central)
        layout.addWidget(self.title_label)
        layout.addWidget(self.tagline)
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
        self.input.set_completion_items(self.command_names)

        self.completer_model = QStringListModel(self.command_names, self)
        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchStartsWith)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.input.setCompleter(self.completer)

        self.input.set_history(self.shell.ctx.history)
        self.update_suggestions("")
        self.update_status()

        # boot ab yahin se shuru hota hai — cinematic sequence
        self._start_boot_sequence()

    def _apply_console_glow(self):
        # Naya drop shadow banate hain kyunki glitch effect purane ko replace/delete kar deta hai
        console_glow = QGraphicsDropShadowEffect(self)
        console_glow.setBlurRadius(30)
        console_glow.setOffset(0, 0)
        console_glow.setColor(Qt.black)
        self.console.setGraphicsEffect(console_glow)

    def eventFilter(self, obj, event):
        if obj is self.console and event.type() == QEvent.Resize:
            self.scanline.setGeometry(self.console.rect())
        return super().eventFilter(obj, event)

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
        self.append_html(text, "#7dffb2")

    def append_error(self, text: str):
        self.append_html(text, "#ff7b7b")

    def clear_console(self):
        self.console.clear()
        self.append_system("Console cleared.")
        self.update_status()

    def update_suggestions(self, text: str):
        raw = text.strip()
        query = raw.split()[0].lower() if raw else ""
        self.suggestions.clear()

        if not query:
            self.suggestions.hide()
            self.suggest_label.hide()
            return

        matches = []
        for cmd in self.shell.registry.list_commands():
            names = [cmd.name] + list(getattr(cmd, "aliases", []))
            if any(name.lower().startswith(query) or query in name.lower() for name in names):
                alias_text = f" | {', '.join(cmd.aliases)}" if cmd.aliases else ""
                item_text = f"{cmd.name}{alias_text} — {cmd.description}"
                matches.append((cmd.name, item_text))

        for name, item_text in matches[:12]:
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, name)
            self.suggestions.addItem(item)

        visible = bool(matches)
        self.suggestions.setVisible(visible)
        self.suggest_label.setVisible(visible)

        filtered = [name for name in self.command_names if name.startswith(query) or query in name]
        self.completer_model.setStringList(filtered[:50])

    def apply_suggestion(self, item):
        command_name = item.data(Qt.UserRole)
        if command_name:
            rest = self.input.text().split(maxsplit=1)
            suffix = f" {rest[1]}" if len(rest) > 1 else ""
            self.input.setText(command_name + suffix)
            self.input.setCursorPosition(len(command_name))
            self.input.setFocus()

    # ======= NAYA CINEMATIC BOOT SEQUENCE =======
    def _start_boot_sequence(self):
        self.input.setEnabled(False)
        self.run_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.input.setPlaceholderText("Booting...")

        self.scanline.start()

        self._boot_queue = self._boot_banner_lines()
        self._boot_timer = QTimer(self)
        self._boot_timer.timeout.connect(self._reveal_next_banner_line)
        self._boot_timer.start(16)

    def _boot_banner_lines(self):
        inner = re.sub(r"</?pre[^>]*>", "", BOOT_BANNER)
        lines = inner.split("\n")
        # trim the blank first/last lines that come from the triple-quoted string
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    def _reveal_next_banner_line(self):
        if not self._boot_queue:
            self._boot_timer.stop()
            self._start_boot_messages()
            return
        line = self._boot_queue.pop(0)
        self.console.moveCursor(QTextCursor.End)
        safe = escape(line) if line.strip() else "&nbsp;"
        self.console.append(
            f'<div style="color:#00ff9c; white-space:pre; font-family:Consolas;">{safe}</div>'
        )
        self.console.moveCursor(QTextCursor.End)

    def _start_boot_messages(self):
        n = len(self.shell.registry.all_names())
        self._msg_queue = [
            "Initializing kernel modules...",
            "Mounting virtual filesystem...",
            f"Loading command registry [{n} commands]...",
            "Calibrating neon core...",
            "Handshaking with AI subsystem...",
            "Tab completion armed.",
            "Neon mode online.",
        ]
        self._type_next_message()

    def _type_next_message(self):
        if not self._msg_queue:
            self._run_glitch_transition()
            return
        message = self._msg_queue.pop(0)
        color = "#00ff9c" if message == "Neon mode online." else "#cbd5e1"
        self._typewriter_line(message, color, self._type_next_message)

    def _typewriter_line(self, text, color, on_done, char_delay=14):
        fmt = self.console.currentCharFormat()
        fmt.setForeground(QColor(color))

        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertBlock()
        cursor.setCharFormat(fmt)
        self.console.setTextCursor(cursor)

        state = {"index": 0}
        timer = QTimer(self)

        def step():
            if state["index"] >= len(text):
                timer.stop()
                timer.deleteLater()
                on_done()
                return
            cursor = self.console.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(text[state["index"]], fmt)
            self.console.setTextCursor(cursor)
            self.console.moveCursor(QTextCursor.End)
            state["index"] += 1

        timer.timeout.connect(step)
        timer.start(char_delay)
        self._active_typewriter_timer = timer  # reference zinda rakhne ke liye

    def _run_glitch_transition(self):
        self.scanline.stop()

        self._glitch_effect = QGraphicsColorizeEffect(self.console)
        self._glitch_effect.setStrength(0.0)
        self.console.setGraphicsEffect(self._glitch_effect)

        # color, strength frames — flicker fast then settle back to normal
        self._glitch_frames = [
            ("#ff2b6d", 0.85),
            ("#00e5ff", 0.75),
            ("#00ff9c", 0.0),
            ("#ff2b6d", 0.6),
            ("#00e5ff", 0.5),
            ("#00ff9c", 0.0),
            ("#ffffff", 0.35),
            ("#00ff9c", 0.0),
        ]
        self._glitch_timer = QTimer(self)
        self._glitch_timer.timeout.connect(self._glitch_step)
        self._glitch_timer.start(45)

    def _glitch_step(self):
        if not self._glitch_frames:
            self._glitch_timer.stop()
            self._apply_console_glow()  # restore the normal drop shadow
            self._end_boot_sequence()
            return
        color, strength = self._glitch_frames.pop(0)
        self._glitch_effect.setColor(QColor(color))
        self._glitch_effect.setStrength(strength)

    def _end_boot_sequence(self):
        self.append_system("Type help to see commands.")
        self.append_system("Tab completion is active.")

        self.input.setEnabled(True)
        self.run_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.input.setPlaceholderText("Type command here...  (Tab to complete)")
        self.input.setFocus()
    # ===============================================

    # ======= MULTI-THREADED RUN_COMMAND =======
    def run_command(self):
        cmd = self.input.text().strip()
        if not cmd:
            return

        self.append_user(f"{self.shell.prompt()}{cmd}")

        # UI ko disable karo jab tak background command chal rahi ho
        self.input.setEnabled(False)
        self.run_btn.setEnabled(False)
        self.input.setPlaceholderText("Running command, please wait...")

        # Worker thread start karo
        self.worker = CommandWorker(self.shell, cmd)
        self.worker.result_ready.connect(self.on_command_finished)
        self.worker.start()

    def on_command_finished(self, result):
        # Jab result aa jaye, tab usko console par print karo
        if result.output:
            if result.success:
                self.append_output(result.output)
            else:
                self.append_error(result.output)

        # Agar `exit` command chali thi toh application close karo
        if hasattr(result, 'exit_shell') and result.exit_shell:
            self.close()

        # UI wapas enable aur reset karo
        self.input.set_history(self.shell.ctx.history)
        self.input.clear()
        self.update_status()

        self.input.setEnabled(True)
        self.run_btn.setEnabled(True)
        self.input.setPlaceholderText("Type command here...  (Tab to complete)")
        self.input.setFocus()
    # ===============================================