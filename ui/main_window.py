from __future__ import annotations

import ctypes
import math
import re
import sys
from dataclasses import replace
from time import perf_counter
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import (
    QEasingCurve, QEvent, QParallelAnimationGroup, QPoint, QPointF, QPropertyAnimation,
    QRect, QRectF, QSettings, QSize, QStringListModel, Qt, QThread, QTimer, Signal,
)
from PySide6.QtGui import (
    QBrush, QColor, QFont, QIcon, QKeySequence, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient, QShortcut, QTextCursor, QTextOption,
)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QCompleter, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QSplitter, QStackedWidget, QTabWidget, QTextEdit,
    QToolButton, QVBoxLayout, QWidget,
)

from core.shell import Shell
from core.base import CommandResult
from core.native_terminal import native_dependency_error
from ai.agent_run import AgentRun
from ai.config import AIConfig
from ai.desktop_settings import (
    load_desktop_config, load_mode_preferences, remove_api_key, remove_telegram_token,
    save_api_key, save_telegram_token, saved_key_exists, saved_telegram_token_exists,
)
from ai.telegram_control import TelegramControlService
from ai.code_writer import WriteResult, apply_file_writes, preview_file_writes
from ai.safety import SafetyPolicy
from ai.provider_runtime import PROVIDER_RUNTIME
from ui.themes import build_stylesheet, get_theme, list_themes
from ui.terminal_output import TerminalOutput
from version import __version__
from update_ui import UpdateController


def _make_vector_icon(kind: str, color_hex: str = "#9D8EB5", accent_hex: str = "#C084FC", size: int = 24) -> QIcon:
    """Render crisp geometric vector icons for the collapsible rails."""
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(2.0, 2.0)

    c = QColor(color_hex)
    ac = QColor(accent_hex)
    pen = QPen(c, 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if kind == "terminal":
        pen_ac = QPen(ac, 2.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen_ac)
        path = QPainterPath()
        path.moveTo(6, 7)
        path.lineTo(11.5, 12)
        path.lineTo(6, 17)
        p.drawPath(path)
        p.drawLine(QPointF(13.0, 17.0), QPointF(18.5, 17.0))
    elif kind == "grid":
        r = 1.5
        p.drawRoundedRect(QRectF(4.5, 4.5, 6.2, 6.2), r, r)
        p.drawRoundedRect(QRectF(13.3, 4.5, 6.2, 6.2), r, r)
        p.drawRoundedRect(QRectF(4.5, 13.3, 6.2, 6.2), r, r)
        p.drawRoundedRect(QRectF(13.3, 13.3, 6.2, 6.2), r, r)
    elif kind == "clock":
        p.drawEllipse(QRectF(4.2, 4.2, 15.6, 15.6))
        p.drawLine(QPointF(12.0, 7.5), QPointF(12.0, 12.2))
        p.drawLine(QPointF(12.0, 12.2), QPointF(15.2, 14.2))
    elif kind == "explorer":
        poly = QPolygonF([
            QPointF(19.5, 4.5),
            QPointF(4.2, 11.2),
            QPointF(10.8, 13.2),
            QPointF(12.8, 19.8),
        ])
        p.drawPolygon(poly)
        p.drawLine(QPointF(19.5, 4.5), QPointF(10.8, 13.2))
    elif kind == "settings":
        p.drawEllipse(QRectF(8.8, 8.8, 6.4, 6.4))
        for i in range(8):
            angle = i * (math.pi / 4.0)
            x1 = 12.0 + math.cos(angle) * 5.2
            y1 = 12.0 + math.sin(angle) * 5.2
            x2 = 12.0 + math.cos(angle) * 8.2
            y2 = 12.0 + math.sin(angle) * 8.2
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        p.drawEllipse(QRectF(6.2, 6.2, 11.6, 11.6))
    elif kind == "updates":
        p.drawEllipse(QRectF(5.2, 5.2, 13.6, 13.6))
        p.drawLine(QPointF(12.0, 3.2), QPointF(12.0, 6.2))
        p.drawLine(QPointF(12.0, 17.8), QPointF(12.0, 20.8))
        p.drawLine(QPointF(3.2, 12.0), QPointF(6.2, 12.0))
        p.drawLine(QPointF(17.8, 12.0), QPointF(20.8, 12.0))
    elif kind == "cube":
        top = QPolygonF([QPointF(12, 4.2), QPointF(19.2, 8.2), QPointF(12, 12.2), QPointF(4.8, 8.2)])
        p.drawPolygon(top)
        path = QPainterPath()
        path.moveTo(4.8, 8.2)
        path.lineTo(4.8, 16.0)
        path.lineTo(12.0, 20.0)
        path.lineTo(19.2, 16.0)
        path.lineTo(19.2, 8.2)
        p.drawPath(path)
        p.drawLine(QPointF(12.0, 12.2), QPointF(12.0, 20.0))
    elif kind == "orbit":
        pen_ac = QPen(ac, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen_ac)
        p.drawEllipse(QRectF(7.0, 7.0, 10.0, 10.0))
        p.save()
        p.translate(12.0, 12.0)
        p.rotate(-26.0)
        p.drawEllipse(QRectF(-9.8, -3.6, 19.6, 7.2))
        p.restore()
    elif kind == "modes":
        for dy in (-3.8, 0.0, 3.8):
            poly = QPolygonF([
                QPointF(12.0, 6.5 + dy),
                QPointF(19.0, 10.0 + dy),
                QPointF(12.0, 13.5 + dy),
                QPointF(5.0, 10.0 + dy),
            ])
            p.drawPolygon(poly)

    p.end()
    return QIcon(pix)


class HeroLogoWidget(QWidget):
    """Paints the glowing purple-magenta `>_` centerpiece emblem on the initial Hero screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(110, 78)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        window = self.window()
        theme = getattr(window, "theme", None)
        accent = QColor(theme.accent if theme else "#A855F7")
        secondary = QColor(theme.accent_alt if theme else "#D946EF")

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Ambient radial glow behind `>_`
        glow = QRadialGradient(QPointF(self.width() * 0.5, self.height() * 0.52), 46.0)
        c_center = QColor(accent)
        c_center.setAlpha(65)
        c_zero = QColor(accent)
        c_zero.setAlpha(0)
        glow.setColorAt(0.0, c_center)
        glow.setColorAt(1.0, c_zero)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QRectF(8, 2, 94, 74))

        grad = QLinearGradient(QPointF(24, 16), QPointF(88, 62))
        grad.setColorAt(0.0, secondary)
        grad.setColorAt(1.0, accent)

        pen = QPen(QBrush(grad), 6.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        chevron = QPainterPath()
        chevron.moveTo(30.0, 20.0)
        chevron.lineTo(50.0, 39.0)
        chevron.lineTo(30.0, 58.0)
        p.drawPath(chevron)

        p.drawLine(QPointF(58.0, 58.0), QPointF(82.0, 58.0))
        p.end()


def pending_action_reply(text: str) -> str | None:
    """Classify an explicit reply to a proposal waiting for approval."""
    normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    if not normalized:
        return None

    rejection = re.search(
        r"\b(?:cancel|deny|dismiss|reject|don t|do not|mat karo|mat likho|nahi|nahin)\b",
        normalized,
    )
    if rejection or normalized in {"no", "nope", "cancel it"}:
        return "reject"

    if normalized in {
        "approve", "approved", "yes", "yep", "ok", "okay", "haan", "han",
        "proceed", "go ahead", "kar do", "karo", "likh do", "save it",
    }:
        return "approve"

    has_affirmation = bool(
        re.match(r"^(?:yes|yep|ok|okay|haan|han|sure|please)\b", normalized)
    )
    has_apply_instruction = bool(
        re.search(
            r"\b(?:apply|approve|proceed|save|push|write|go ahead|kar do|karo|likh do|daal do)\b",
            normalized,
        )
    )
    if has_affirmation and has_apply_instruction:
        return "approve"
    if re.search(
        r"\b(?:apply (?:it|this|the changes?)|write (?:it|this code)|save (?:it|this)|"
        r"changes? apply karo|code likh do)\b",
        normalized,
    ):
        return "approve"
    return None


def fuzzy_score(query: str, text: str) -> int | None:
    """Small subsequence matcher: lower score means a more relevant result."""
    query, text = query.lower().strip(), text.lower()
    if not query:
        return 0
    if query in text:
        return text.index(query)
    position = -1
    gaps = 0
    for char in query:
        next_position = text.find(char, position + 1)
        if next_position < 0:
            return None
        if position >= 0:
            gaps += next_position - position - 1
        position = next_position
    return 50 + gaps


def animate_dialog_flip_open(dialog: QDialog, parent: QWidget | None = None, duration_ms: int = 200) -> None:
    """Animate a dialog opening with a smooth modern Windows 11 scale & fade transition."""
    dialog.ensurePolished()
    target_w = dialog.width()
    target_h = dialog.height()
    if parent and parent.isVisible():
        center = parent.mapToGlobal(parent.rect().center())
    else:
        screen = QApplication.primaryScreen()
        center = screen.geometry().center() if screen else QPoint(500, 400)

    target_x = max(20, center.x() - target_w // 2)
    target_y = max(20, center.y() - target_h // 2)
    target_rect = QRect(target_x, target_y, target_w, target_h)

    start_w = max(120, int(target_w * 0.92))
    start_h = max(90, int(target_h * 0.92))
    start_x = center.x() - start_w // 2
    start_y = center.y() - start_h // 2 + 8
    start_rect = QRect(start_x, start_y, start_w, start_h)

    orig_min_w = dialog.minimumWidth()
    orig_min_h = dialog.minimumHeight()
    dialog.setMinimumSize(0, 0)
    dialog.setGeometry(start_rect)
    dialog.setWindowOpacity(0.0)

    group = QParallelAnimationGroup(dialog)
    geo_anim = QPropertyAnimation(dialog, b"geometry", group)
    geo_anim.setDuration(duration_ms)
    geo_anim.setStartValue(start_rect)
    geo_anim.setEndValue(target_rect)
    geo_anim.setEasingCurve(QEasingCurve.OutCubic)

    op_anim = QPropertyAnimation(dialog, b"windowOpacity", group)
    op_anim.setDuration(max(90, int(duration_ms * 0.85)))
    op_anim.setStartValue(0.0)
    op_anim.setEndValue(1.0)
    op_anim.setEasingCurve(QEasingCurve.OutCubic)

    group.addAnimation(geo_anim)
    group.addAnimation(op_anim)

    def _on_flip_finished():
        dialog.setMinimumSize(orig_min_w, orig_min_h)
        dialog.setGeometry(target_rect)
        dialog.setWindowOpacity(1.0)

    group.finished.connect(_on_flip_finished)
    dialog._flip_anim = group
    dialog.show()
    group.start()


class CustomTitleBar(QWidget):
    def __init__(self, parent: MainWindow):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("customTitleBar")
        self.setFixedHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("titleIcon")
        self.icon_label.setFixedSize(18, 18)
        self.icon_label.setScaledContents(True)
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.icon_label.setPixmap(QPixmap(str(icon_path)))
        else:
            self.icon_label.setText("◈")
            self.icon_label.setAlignment(Qt.AlignCenter)
            self.icon_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #C084FC;")
        layout.addWidget(self.icon_label)

        self.brand_label = QLabel("RiftShell")
        self.brand_label.setObjectName("titleBrand")
        layout.addWidget(self.brand_label)

        self.version_badge = QLabel(f"v{__version__}")
        self.version_badge.setObjectName("titleBadge")
        layout.addWidget(self.version_badge)

        layout.addStretch(1)

        self.center_pill = QLabel("◈   WORKSPACE   //   riftshell", self)
        self.center_pill.setObjectName("titleCenterPill")
        self.center_pill.setAlignment(Qt.AlignCenter)
        self.center_pill.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.center_pill.show()

        self.setCursor(Qt.ArrowCursor)
        self.min_btn = QPushButton("—")
        self.min_btn.setObjectName("titleMinBtn")
        self.min_btn.setToolTip("Minimize")
        self.min_btn.setFixedSize(46, 42)
        self.min_btn.setCursor(Qt.ArrowCursor)

        self.max_btn = QPushButton("□")
        self.max_btn.setObjectName("titleMaxBtn")
        self.max_btn.setToolTip("Maximize / Restore")
        self.max_btn.setFixedSize(46, 42)
        self.max_btn.setCursor(Qt.ArrowCursor)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("titleCloseBtn")
        self.close_btn.setToolTip("Close")
        self.close_btn.setFixedSize(46, 42)
        self.close_btn.setCursor(Qt.ArrowCursor)

        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

        self.min_btn.clicked.connect(self.parent_window.showMinimized)
        self.max_btn.clicked.connect(self._toggle_maximize)
        self.close_btn.clicked.connect(self.parent_window.close)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_center_pill()

    def _position_center_pill(self):
        self.center_pill.adjustSize()
        label_width = min(max(220, self.center_pill.sizeHint().width() + 28), max(220, self.width() - 360))
        label_height = 26
        self.center_pill.setGeometry(
            max(0, (self.width() - label_width) // 2),
            (self.height() - label_height) // 2,
            label_width,
            label_height,
        )

    def _toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.max_btn.setText("□")
        else:
            self.parent_window.showMaximized()
            self.max_btn.setText("⧉")

    def update_max_icon(self, is_maximized: bool):
        self.max_btn.setText("⧉" if is_maximized else "□")

    def set_workspace_text(self, text: str):
        self.center_pill.setText(text)
        self._position_center_pill()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_maximize()
            event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            wh = self.parent_window.windowHandle()
            if wh and hasattr(wh, "startSystemMove"):
                wh.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)


class CommandInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history: list[str] = []
        self.history_index = 0
        self.command_names: list[str] = []

    def set_history(self, history: list[str]):
        self.history = history[:]
        self.history_index = len(self.history)

    def set_completion_items(self, items: list[str]):
        self.command_names = sorted({item.lower() for item in items})

    def _complete_current_command(self) -> bool:
        text = self.text()
        if not text.strip():
            return False
        parts = text.split(maxsplit=1)
        prefix = parts[0]
        rest = f" {parts[1]}" if len(parts) > 1 else ""
        matches = [name for name in self.command_names if name.startswith(prefix.lower())]
        if not matches:
            return False
        self.setText(matches[0] + rest)
        self.setCursorPosition(len(matches[0]))
        return True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab and self._complete_current_command():
            return
        if event.key() == Qt.Key_Up and self.history:
            self.history_index = max(0, self.history_index - 1)
            self.setText(self.history[self.history_index])
            self.setCursorPosition(len(self.text()))
            return
        if event.key() == Qt.Key_Down and self.history:
            self.history_index = min(len(self.history), self.history_index + 1)
            self.setText("" if self.history_index == len(self.history) else self.history[self.history_index])
            self.setCursorPosition(len(self.text()))
            return
        super().keyPressEvent(event)


class CommandWorker(QThread):
    result_ready = Signal(object)

    def __init__(self, shell: Shell, command: str, parent=None):
        super().__init__(parent)
        self.shell = shell
        self.command = command

    def run(self):
        self.shell.clear_cancel()
        if self.isInterruptionRequested():
            self.result_ready.emit(CommandResult(output="Command cancelled before execution.", success=False))
            return
        started = perf_counter()
        try:
            result = self.shell.execute_line(self.command)
        except Exception as exc:
            result = CommandResult(output=f"Command failed: {exc}", success=False)
        PROVIDER_RUNTIME.record("execution", elapsed_seconds=perf_counter() - started, success=result.success)
        self.result_ready.emit(result)


class OrbitWorker(QThread):
    planned = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, shell: Shell, prompt: str, parent=None, task=None, execute: bool = False, planner=None):
        super().__init__(parent)
        self.shell = shell
        self.prompt = prompt
        self.task = task
        self.execute = execute
        self.planner = planner

    def run(self):
        started = perf_counter()
        try:
            from ai.llm import AgentPlanner

            planner = self.planner or (self.task.planner if self.task else None)
            if planner is None:
                config = self.task.planner.config if self.task and self.task.planner else load_desktop_config()
                if self.task and self.task.mode and not self.task.planner:
                    config = replace(config, orbit_mode=self.task.mode)
                planner = AgentPlanner(
                    config=config,
                    command_names=self.shell.registry.all_names(),
                    command_catalog=self.shell.registry.catalog_entries(),
                    command_metadata=self.shell.registry.list_metadata(),
                    current_dir_provider=lambda: self.shell.ctx.cwd,
                    last_output_provider=lambda: self.shell.ctx.last_output,
                    cancelled=lambda task=self.task: bool(task and task.stopped),
                    native_context_provider=getattr(self.shell, "native_context_provider", None),
                )
            if self.task:
                if not self.task.planner:
                    self.task.max_steps = planner.mode.max_steps
                self.task.planner = planner
            planner.progress = self.progress.emit
            action = (planner.continue_task(self.prompt, self.task.observations)
                      if self.task and self.task.observations else planner.plan(self.prompt, execute=self.execute))
            self.planned.emit(action)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            PROVIDER_RUNTIME.record("planning", elapsed_seconds=perf_counter() - started,
                                    continuation=bool(self.task and self.task.observations))


class FileWriteWorker(QThread):
    result_ready = Signal(object)

    def __init__(
        self,
        files,
        workspace_root,
        allow_outside_workspace,
        current_dir,
        expected_snapshots=None,
        parent=None,
    ):
        super().__init__(parent)
        self.files = files
        self.workspace_root = workspace_root
        self.allow_outside_workspace = allow_outside_workspace
        self.current_dir = current_dir
        self.expected_snapshots = expected_snapshots

    def run(self):
        try:
            result = apply_file_writes(
                self.files,
                self.workspace_root,
                self.allow_outside_workspace,
                self.current_dir,
                self.expected_snapshots,
            )
        except Exception as exc:
            result = WriteResult(output=f"File update failed: {exc}", success=False)
        self.result_ready.emit(result)


class PreviewWorker(QThread):
    result_ready = Signal(object, object, str)  # (preview, action, message)

    def __init__(self, action, config, current_dir, message, parent=None):
        super().__init__(parent)
        self.action = action
        self.config = config
        self.current_dir = current_dir
        self.message = message

    def run(self):
        try:
            preview = preview_file_writes(
                self.action.files,
                self.config.workspace_root,
                self.config.allow_outside_workspace,
                self.current_dir,
            )
        except Exception as exc:
            from ai.code_writer import WriteResult
            preview = WriteResult(output=f"Preview failed: {exc}", success=False)
        self.result_ready.emit(preview, self.action, self.message)


class CommandPalette(QDialog):
    command_chosen = Signal(str)
    action_chosen = Signal(str)

    def __init__(self, shell: Shell, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setMinimumSize(680, 480)
        header_row = QHBoxLayout()
        heading = QLabel("⌘  COMMAND PALETTE")
        heading.setObjectName("eyebrow")
        hint = QLabel("ENTER to execute  ·  ESC to dismiss")
        hint.setObjectName("sessionPath")
        header_row.addWidget(heading)
        header_row.addStretch()
        header_row.addWidget(hint)

        self.query = QLineEdit()
        self.query.setPlaceholderText("Type a command name, workspace action, or plugin keyword…")
        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addLayout(header_row)
        layout.addWidget(self.query)
        layout.addWidget(self.list, 1)
        self._entries: list[tuple[str, str, str]] = [
            ("action", "New terminal session", "Create a workspace session"),
            ("action", "Open settings", "Theme, font and safety preferences"),
            ("action", "Toggle Orbit", "Show or hide the smart assistant panel"),
            ("action", "Show plugins", "Inspect loaded plugin status"),
            ("action", "Check for updates", "Check for a newer RiftShell release"),
        ]
        self._entries.extend(("command", meta.name, f"{meta.usage} — {meta.description}") for meta in shell.registry.list_metadata())
        self.query.textChanged.connect(self._refresh)
        self.query.returnPressed.connect(self._choose_current)
        self.list.itemActivated.connect(lambda _: self._choose_current())
        self._refresh("")
        self.query.setFocus()

    def _refresh(self, query: str):
        ranked = []
        for kind, name, detail in self._entries:
            score = fuzzy_score(query, f"{name} {detail}")
            if score is not None:
                ranked.append((score, kind, name, detail))
        self.list.clear()
        for _, kind, name, detail in sorted(ranked, key=lambda item: (item[0], item[2]))[:70]:
            badge = "◈ ACTION" if kind == "action" else "❯ CMD"
            item = QListWidgetItem(f"{badge}   {name}\n        {detail}")
            item.setData(Qt.UserRole, (kind, name))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _choose_current(self):
        item = self.list.currentItem()
        if item is None:
            return
        kind, name = item.data(Qt.UserRole)
        (self.command_chosen if kind == "command" else self.action_chosen).emit(name)
        self.accept()


class PreferencesDialog(QDialog):
    preferences_saved = Signal(dict)

    def __init__(self, preferences: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workspace Settings")
        self.setMinimumWidth(520)
        title = QLabel("⚙  WORKSPACE & AI ENGINE SETTINGS")
        title.setObjectName("eyebrow")
        self.theme = QComboBox()
        for item in list_themes():
            self.theme.addItem(item.display_name, item.key)
        self.theme.setCurrentIndex(max(0, self.theme.findData(preferences["theme"])))
        self.font = QComboBox()
        self.font.addItems(["JetBrains Mono", "Cascadia Code", "Consolas", "Fira Code"])
        self.font.setCurrentText(preferences["font_family"])
        self.font_size = QSpinBox()
        self.font_size.setRange(9, 20)
        self.font_size.setValue(preferences["font_size"])
        self.confirm = QCheckBox("Confirm commands that can change files or run native tools")
        self.confirm.setChecked(preferences["confirm_risky"])
        self.restore = QCheckBox("Restore recent command history on launch")
        self.restore.setChecked(preferences["restore_history"])
        self.provider = QComboBox()
        for label, value in (
            ("Auto (configured order)", "auto"), ("Groq", "groq"),
            ("Gemini", "gemini"), ("Ollama (Local / Colab)", "ollama"),
        ):
            self.provider.addItem(label, value)
        self.provider.setCurrentIndex(max(0, self.provider.findData(preferences.get("ai_provider", "auto"))))

        initial_ollama_url = preferences.get("ollama_base_url", "http://127.0.0.1:11434")
        saved_source = preferences.get("ollama_source", "")
        if not saved_source:
            saved_source = "colab" if "ngrok" in initial_ollama_url.lower() else "local"

        self.groq_key = QLineEdit()
        self.groq_key.setEchoMode(QLineEdit.Password)
        self.groq_key.setPlaceholderText("Leave blank to keep saved key")
        self.groq_remove = QCheckBox("Remove saved Groq key")
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.Password)
        self.gemini_key.setPlaceholderText("Leave blank to keep saved key")
        self.gemini_remove = QCheckBox("Remove saved Gemini key")
        self.groq_model = QLineEdit(preferences["groq_model"])

        saved_colab_url = preferences.get("ollama_colab_url", initial_ollama_url if saved_source == "colab" else "")

        self.ollama_source = QComboBox()
        self.ollama_source.addItem("Local (localhost)", "local")
        self.ollama_source.addItem("Google Colab (ngrok tunnel)", "colab")
        self.ollama_source.setCurrentIndex(max(0, self.ollama_source.findData(saved_source)))

        self.colab_link_label = QLabel("Colab ngrok link")
        self.colab_url = QLineEdit(saved_colab_url)
        self.colab_url.setPlaceholderText("Paste your Google Colab ngrok link (e.g. https://xxxx.ngrok-free.app)")
        self._dummy_local_url = QLineEdit("http://127.0.0.1:11434")

        is_colab = saved_source == "colab"
        self.colab_link_label.setVisible(is_colab)
        self.colab_url.setVisible(is_colab)

        self.ollama_source.currentIndexChanged.connect(self._on_ollama_source_changed)

        self.ollama_model = QLineEdit(preferences["ollama_model"])
        self.ollama_model.setPlaceholderText("Model installed in Ollama (e.g. deepseek-r1:8b)")
        self.workspace_root = QLineEdit(preferences["workspace_root"])
        browse_workspace = QPushButton("Browse…")
        browse_workspace.clicked.connect(self._browse_workspace)
        workspace_row = QHBoxLayout()
        workspace_row.setSpacing(8)
        workspace_row.addWidget(self.workspace_root, 1)
        workspace_row.addWidget(browse_workspace)
        self.allow_outside_workspace = QCheckBox("Allow Orbit file inspection and writes outside this folder")
        self.allow_outside_workspace.setChecked(preferences["allow_outside_workspace"])
        self.telegram_enabled = QCheckBox("Enable Telegram control when RiftShell starts")
        self.telegram_enabled.setChecked(preferences.get("telegram_enabled", False))
        self.telegram_token = QLineEdit()
        self.telegram_token_saved = bool(preferences.get("telegram_token_saved", False))
        self.telegram_token.setEchoMode(QLineEdit.Password)
        self.telegram_token.setPlaceholderText(
            "Leave blank to keep the saved bot token"
            if self.telegram_token_saved
            else "Paste the token from @BotFather"
        )
        self.telegram_remove = QCheckBox("Remove saved Telegram bot token")
        self.telegram_ids = QLineEdit(preferences.get("telegram_allowed_user_ids", ""))
        self.telegram_ids.setPlaceholderText("Your Telegram user ID(s), comma-separated")
        self.telegram_unlisted = QCheckBox("Allow any Telegram user (not recommended)")
        self.telegram_unlisted.setChecked(preferences.get("telegram_allow_unlisted_users", False))

        form = QFormLayout()
        form.setContentsMargins(8, 8, 8, 8)
        form.setSpacing(10)
        form.addRow("Color theme", self.theme)
        form.addRow("Terminal font", self.font)
        form.addRow("Font size", self.font_size)
        form.addRow("Safety policy", self.confirm)
        form.addRow("Session history", self.restore)
        form.addRow("AI provider", self.provider)
        form.addRow("Groq API key", self.groq_key)
        form.addRow("", self.groq_remove)
        form.addRow("Groq model", self.groq_model)
        form.addRow("Gemini API key", self.gemini_key)
        form.addRow("", self.gemini_remove)
        form.addRow("Ollama runtime", self.ollama_source)
        form.addRow(self.colab_link_label, self.colab_url)
        form.addRow("Ollama model", self.ollama_model)
        form.addRow("Orbit workspace", workspace_row)
        form.addRow("File boundary", self.allow_outside_workspace)

        controls = QWidget()
        controls_form = QFormLayout(controls)
        controls_form.setContentsMargins(8, 8, 8, 8)
        controls_form.setSpacing(10)
        guide_card = QFrame()
        guide_card.setObjectName("infoCard")
        guide_layout = QVBoxLayout(guide_card)
        guide_layout.setContentsMargins(12, 10, 12, 10)
        guide = QLabel(
            "1. Open Telegram and message @BotFather.\n"
            "2. Use /newbot and paste the bot token below.\n"
            "3. Send /start to your bot, then find your numeric user ID.\n"
            "4. Save settings. Only approved IDs can control this PC."
        )
        guide.setWordWrap(True)
        guide_layout.addWidget(guide)
        controls_form.addRow("Setup guide", guide_card)
        controls_form.addRow("Status", self.telegram_enabled)
        controls_form.addRow("Bot token", self.telegram_token)
        controls_form.addRow("Allowed user IDs", self.telegram_ids)
        controls_form.addRow("", self.telegram_unlisted)
        controls_form.addRow("", self.telegram_remove)

        general_scroll_content = QWidget()
        general_scroll_content.setLayout(form)
        general_scroll = QScrollArea()
        general_scroll.setWidgetResizable(True)
        general_scroll.setFrameShape(QFrame.NoFrame)
        general_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        general_scroll.setWidget(general_scroll_content)

        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setFrameShape(QFrame.NoFrame)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        controls_scroll.setWidget(controls)
        tabs = QTabWidget()
        tabs.addTab(general_scroll, "General & AI Engine")
        tabs.addTab(controls_scroll, "Telegram Remote Control")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        if save_btn := buttons.button(QDialogButtonBox.Save):
            save_btn.setObjectName("primaryButton")
            save_btn.setText("Save Changes")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(tabs, 1)
        layout.addWidget(buttons)

        screen = QApplication.primaryScreen()
        screen_h = screen.availableGeometry().height() if screen else 760
        self.resize(540, min(580, int(screen_h * 0.82)))

    @property
    def ollama_url(self):
        if self.ollama_source.currentData() == "colab":
            return self.colab_url
        return self._dummy_local_url

    def _browse_workspace(self):
        selected = QFileDialog.getExistingDirectory(self, "Choose Orbit workspace", self.workspace_root.text())
        if selected:
            self.workspace_root.setText(selected)

    def _on_ollama_source_changed(self):
        is_colab = self.ollama_source.currentData() == "colab"
        self.colab_link_label.setVisible(is_colab)
        self.colab_url.setVisible(is_colab)
        if is_colab:
            self.colab_url.setFocus()

    def _save(self):
        workspace_text = self.workspace_root.text().strip()
        workspace = Path(workspace_text).expanduser() if workspace_text else None
        if workspace is None or not workspace.is_dir():
            QMessageBox.warning(self, "Orbit workspace", "Choose an existing folder for Orbit's workspace.")
            return
        workspace = workspace.resolve(strict=True)

        provider = self.provider.currentData()
        ollama_source = self.ollama_source.currentData()
        telegram_token = self.telegram_token.text().strip()
        telegram_ids = self.telegram_ids.text().strip()
        parsed_ids = []
        for raw_id in telegram_ids.replace(";", ",").split(","):
            if raw_id.strip():
                try:
                    parsed_ids.append(str(int(raw_id.strip())))
                except ValueError:
                    QMessageBox.warning(self, "Telegram user IDs", "Use numeric Telegram user IDs separated by commas.")
                    self.telegram_ids.setFocus()
                    return
        if self.telegram_enabled.isChecked() and not (telegram_token or self.telegram_token_saved):
            QMessageBox.warning(self, "Telegram token required", "Enter a Telegram bot token before enabling Telegram control.")
            self.telegram_token.setFocus()
            return
        if self.telegram_enabled.isChecked() and not parsed_ids and not self.telegram_unlisted.isChecked():
            QMessageBox.warning(self, "Telegram user ID required", "Add at least one allowed Telegram user ID, or explicitly enable unlisted users.")
            self.telegram_ids.setFocus()
            return

        if ollama_source == "colab":
            url = self.colab_url.text().strip().rstrip("/")
            if url and not (url.startswith("http://") or url.startswith("https://")):
                url = f"https://{url}"
            if url.startswith("http://") and "ngrok" in url.lower():
                url = "https://" + url[len("http://"):]
            if url.endswith("/api/generate"):
                url = url[:-len("/api/generate")].rstrip("/")
            self.colab_url.setText(url)
        else:
            url = "http://127.0.0.1:11434"

        if provider == "ollama":
            if ollama_source == "colab":
                if not url:
                    QMessageBox.warning(self, "Google Colab", "Enter your Google Colab ngrok URL (e.g. https://xxxx.ngrok-free.app).")
                    self.colab_url.setFocus()
                    return
                parsed = urlparse(url)
                if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                    QMessageBox.warning(self, "Google Colab", "Use a valid HTTP or HTTPS address such as https://xxxx.ngrok-free.app.")
                    self.colab_url.setFocus()
                    return
            if not self.ollama_model.text().strip():
                QMessageBox.warning(self, "Local model", "Enter the model name installed in Ollama.")
                self.ollama_model.setFocus()
                return

        try:
            for name, field, remove in (
                ("groq", self.groq_key, self.groq_remove),
                ("gemini", self.gemini_key, self.gemini_remove),
            ):
                if remove.isChecked():
                    remove_api_key(name)
                elif field.text().strip():
                    save_api_key(name, field.text().strip())
            if self.telegram_remove.isChecked():
                remove_telegram_token()
            elif telegram_token:
                save_telegram_token(telegram_token)
            env_config = AIConfig.from_env()
            env_key = env_config.groq_api_key if provider == "groq" else env_config.gemini_api_key
            if provider in {"groq", "gemini"} and not (saved_key_exists(provider) or env_key):
                QMessageBox.warning(self, "API key required", f"Enter a {provider.title()} API key.")
                return
        except Exception as exc:
            QMessageBox.warning(self, "Credential storage", f"Could not save the API key: {exc}")
            return

        self.preferences_saved.emit({
            "theme": self.theme.currentData(), "font_family": self.font.currentText(),
            "font_size": self.font_size.value(), "confirm_risky": self.confirm.isChecked(),
            "restore_history": self.restore.isChecked(),
            "ai_provider": provider, "groq_model": self.groq_model.text().strip(),
            "ollama_source": ollama_source,
            "ollama_base_url": url,
            "ollama_colab_url": self.colab_url.text().strip(),
            "ollama_model": self.ollama_model.text().strip(),
            "workspace_root": str(workspace),
            "allow_outside_workspace": self.allow_outside_workspace.isChecked(),
            "telegram_enabled": self.telegram_enabled.isChecked(),
            "telegram_allowed_user_ids": ",".join(parsed_ids),
            "telegram_allow_unlisted_users": self.telegram_unlisted.isChecked(),
        })
        self.accept()


def _paint_hud_brackets(widget: QWidget):
    """Paint subtle, refined sci-fi telemetry corner accents on HUD surfaces."""
    window = widget.window()
    theme = getattr(window, "theme", None)
    accent_hex = theme.accent if theme else "#A855F7"
    color = QColor(accent_hex)
    is_tactical = bool(theme and theme.key in {"cyber-cyan", "ghost", "cyberpunk-neon"})
    color.setAlpha(135 if is_tactical else 55)

    painter = QPainter(widget)
    painter.setRenderHint(QPainter.Antialiasing, False)
    pen = QPen(color, 1.2)
    painter.setPen(pen)
    r = widget.rect()
    s = 7
    # Top-left
    painter.drawLine(r.left() + 1, r.top() + 1, r.left() + 1 + s, r.top() + 1)
    painter.drawLine(r.left() + 1, r.top() + 1, r.left() + 1, r.top() + 1 + s)
    # Top-right
    painter.drawLine(r.right() - 1, r.top() + 1, r.right() - 1 - s, r.top() + 1)
    painter.drawLine(r.right() - 1, r.top() + 1, r.right() - 1, r.top() + 1 + s)
    # Bottom-left
    painter.drawLine(r.left() + 1, r.bottom() - 1, r.left() + 1 + s, r.bottom() - 1)
    painter.drawLine(r.left() + 1, r.bottom() - 1, r.left() + 1, r.bottom() - 1 - s)
    # Bottom-right
    painter.drawLine(r.right() - 1, r.bottom() - 1, r.right() - 1 - s, r.bottom() - 1)
    painter.drawLine(r.right() - 1, r.bottom() - 1, r.right() - 1, r.bottom() - 1 - s)
    painter.end()


class HUDFrame(QFrame):
    def paintEvent(self, event):
        super().paintEvent(event)
        _paint_hud_brackets(self)


class TerminalSession(QWidget):
    session_changed = Signal()
    history_added = Signal(str)
    close_requested = Signal(object)
    command_completed = Signal(str, object)

    def __init__(self, shell: Shell, title: str, preferences: dict, parent=None):
        super().__init__(parent)
        self.shell, self.title, self.preferences = shell, title, preferences
        self.safety = SafetyPolicy()
        self.worker: CommandWorker | None = None
        self.native = None
        self._active_native = False
        self.active_command = ""
        self._is_hero_mode = True

        self.name_label = QLabel(title)
        self.name_label.setFont(QFont("Cascadia Code", 10, QFont.Bold))
        self.path_label = QLabel(f"{shell.ctx.cwd}")
        self.path_label.setObjectName("sessionPath")
        self.state_label = QLabel("READY")
        self.state_label.setObjectName("statusPill")

        self.clear_button = QPushButton("Clear")
        self.copy_button = QPushButton("Copy")
        self.copy_button.setToolTip("Copy selected text, or all output")
        self.wrap_button = QPushButton("Wrap")
        self.wrap_button.setObjectName("wrapToggle")
        self.wrap_button.setCheckable(True)
        self.wrap_button.setChecked(True)
        self.wrap_button.setToolTip("Toggle line wrap (default On)")
        self.wrap_button.toggled.connect(self._toggle_wrap)

        self.header = HUDFrame()
        self.header.setObjectName("terminalHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(14, 8, 14, 8)
        header_layout.setSpacing(10)
        session_icon = QLabel(">_")
        session_icon.setObjectName("promptBadge")
        header_layout.addWidget(session_icon)
        header_layout.addWidget(self.name_label)
        header_layout.addWidget(self.path_label, 1)
        header_layout.addWidget(self.clear_button)
        header_layout.addWidget(self.copy_button)
        header_layout.addWidget(self.wrap_button)
        header_layout.addWidget(self.state_label)

        self.console = TerminalOutput()
        self.console.setReadOnly(True)
        self.console.setObjectName("terminalOutput")
        self.console.document().setMaximumBlockCount(5000)
        self.console.setLineWrapMode(QTextEdit.WidgetWidth)
        self.console.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.console.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.console_stack = QStackedWidget()
        self.console_stack.addWidget(self.console)

        self.input = CommandInput()
        self.input.setObjectName("commandInput")
        self.input.setPlaceholderText("Enter command (help, files, git, python...)")
        self.input.set_history(shell.ctx.history)
        names = shell.registry.all_names()
        self.input.set_completion_items(names)
        completer = QCompleter(QStringListModel(names, self), self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setMaxVisibleItems(8)
        completer.popup().setObjectName("commandSuggestions")
        completer.popup().setUniformItemSizes(True)
        self.legacy_completer = completer
        self.input.setCompleter(completer)

        self.palette_inline_btn = QPushButton("Ctrl+K  ⌄")
        self.palette_inline_btn.setObjectName("inlinePaletteBtn")
        self.palette_inline_btn.setToolTip("Open Command Palette (Ctrl+K)")
        self.palette_inline_btn.setCursor(Qt.PointingHandCursor)
        self.palette_inline_btn.clicked.connect(self._open_window_palette)

        input_shell = QFrame()
        input_shell.setObjectName("commandInputShell")
        input_shell_layout = QHBoxLayout(input_shell)
        input_shell_layout.setContentsMargins(4, 2, 6, 2)
        input_shell_layout.setSpacing(4)
        input_shell_layout.addWidget(self.input, 1)
        input_shell_layout.addWidget(self.palette_inline_btn)

        self.run_button = QPushButton("Run  ↵")
        self.run_button.setObjectName("primaryButton")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("stopButton")
        self.cancel_button.setEnabled(False)

        self.command_dock = HUDFrame()
        self.command_dock.setObjectName("commandDock")
        self.command_dock.setMinimumWidth(520)
        self.command_dock.setMaximumWidth(680)
        dock_layout = QHBoxLayout(self.command_dock)
        dock_layout.setContentsMargins(10, 8, 10, 8)
        dock_layout.setSpacing(10)
        prompt_glyph = QLabel(">_")
        prompt_glyph.setObjectName("promptBadge")
        dock_layout.addWidget(prompt_glyph)
        dock_layout.addWidget(input_shell, 1)
        dock_layout.addWidget(self.run_button)
        dock_layout.addWidget(self.cancel_button)

        # Centered Hero Landing Container (shown until the first command is fired)
        self.hero_container = QWidget()
        hero_v = QVBoxLayout(self.hero_container)
        hero_v.setContentsMargins(24, 24, 24, 36)
        hero_v.setSpacing(8)
        hero_v.addStretch(11)

        logo_row = QHBoxLayout()
        logo_row.addStretch(1)
        self.hero_logo = HeroLogoWidget(self.hero_container)
        logo_row.addWidget(self.hero_logo)
        logo_row.addStretch(1)
        hero_v.addLayout(logo_row)

        self.hero_title = QLabel("RiftShell")
        self.hero_title.setObjectName("heroTitle")
        self.hero_title.setAlignment(Qt.AlignCenter)
        hero_v.addWidget(self.hero_title)

        self.hero_subtitle = QLabel("Your AI-Native Windows Shell")
        self.hero_subtitle.setObjectName("heroSubtitle")
        self.hero_subtitle.setAlignment(Qt.AlignCenter)
        hero_v.addWidget(self.hero_subtitle)

        hero_v.addSpacing(22)

        self.hero_dock_row = QHBoxLayout()
        self.hero_dock_row.addStretch(1)
        self.hero_dock_row.addWidget(self.command_dock, 1)
        self.hero_dock_row.addStretch(1)
        hero_v.addLayout(self.hero_dock_row)
        hero_v.addStretch(13)

        # Bottom Dock Holder (populated when the first command settles the input bar to bottom)
        self.bottom_dock_holder = QWidget()
        self.bottom_dock_layout = QVBoxLayout(self.bottom_dock_holder)
        self.bottom_dock_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_dock_layout.setSpacing(0)

        self.header.setVisible(False)
        self.console_stack.setVisible(False)
        self.bottom_dock_holder.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self.hero_container, 1)
        layout.addWidget(self.header)
        layout.addWidget(self.console_stack, 1)
        layout.addWidget(self.bottom_dock_holder)

        self.run_button.clicked.connect(self.run_command)
        self.input.returnPressed.connect(self.run_command)
        self.cancel_button.clicked.connect(self.request_cancel)
        self.clear_button.clicked.connect(self.clear_console)
        self.copy_button.clicked.connect(self.copy_output)
        self.apply_preferences(preferences)
        self.append_system("Workspace terminal ready. Type help to explore available commands.")
        dependency_error = native_dependency_error()
        if not dependency_error:
            from ui.terminal_widget import TerminalWidget
            from ui.native_session import NativeSession

            self.native_console = TerminalWidget(self)
            self.console_stack.addWidget(self.native_console)
            self.native = NativeSession(shell, self.native_console, self)
            self.shell.native_context_provider = self.native.context_summary
            self.native.changed.connect(self._native_changed)
            self.native.completed.connect(self._native_completed)
            self.native.failed.connect(self._native_failed)
            self.console_stack.setCurrentWidget(self.native_console)
            self.append_system("RiftShell ready. Built-ins and PowerShell commands share this terminal.")
        else:
            self.append_error(dependency_error)
        self.input.setPlaceholderText("Enter command (help, files, git, python...)")
        self._set_running(self.is_busy)
        self.apply_preferences(preferences)

    def _open_window_palette(self):
        win = self.window()
        if hasattr(win, "open_palette"):
            win.open_palette()

    def _settle_to_bottom(self):
        """Move the command input dock from the centered Hero screen to the bottom of the terminal."""
        if not self._is_hero_mode:
            return
        self._is_hero_mode = False
        self.hero_container.setVisible(False)
        self.hero_dock_row.removeWidget(self.command_dock)
        self.command_dock.setMinimumWidth(0)
        self.command_dock.setMaximumWidth(16777215)
        self.bottom_dock_layout.addWidget(self.command_dock)
        self.header.setVisible(True)
        self.console_stack.setVisible(True)
        self.bottom_dock_holder.setVisible(True)
        if self.native:
            self.native_console._resize_screen()

    @property
    def is_busy(self) -> bool:
        return bool(self.worker is not None and self.worker.isRunning() or self.native and self.native.busy)

    def _uses_native(self, command, from_orbit=False):
        if not self.native:
            return False
        name = command.split(maxsplit=1)[0].lower()
        if name in {"run", "exec", "native"}:
            return True
        if from_orbit:
            return False  # Orbit's catalog actions retain their reviewed semantics.
        parts = self.shell.parser.parse_line(command)
        return not parts or any(
            self.shell.registry.get(self.shell._prepare_command(parsed).name) is None
            for part in parts for parsed in part.pipeline.commands
        )

    def _native_changed(self):
        if self.native.context_available:
            self.path_label.setText(f"{self.shell.ctx.cwd}")
        else:
            self.path_label.setText(f"{self.native.location} (non-filesystem)")
        self._set_running(self.is_busy)
        if self.native.exited:
            self.state_label.setText("EXITED")
        elif not self.native.ready:
            self.state_label.setText("STARTING")
        if self.native.ready and not self.native.busy:
            self.console_stack.setCurrentWidget(self.console)

    def _native_failed(self, message):
        self.append_error(message)
        self.state_label.setText("ERROR")
        if not self._active_native:
            self.console_stack.setCurrentWidget(self.console)

    def _native_completed(self, command, result):
        self._active_native = False
        output = self.native_console.finish_capture()
        if output:
            (self.append_output if result.success else self.append_error)(output)
        elif result.output:
            (self.append_output if result.success else self.append_error)(result.output)
        self.console_stack.setCurrentWidget(self.console)
        self._on_finished(result, display_output=False)
        self._native_changed()

    def shutdown(self) -> bool:
        if not self.native:
            return True
        self.native.close()
        return self.native.transport.stopped

    def set_title(self, title: str):
        self.title = title
        self.name_label.setText(title)
        self.session_changed.emit()

    def _toggle_wrap(self, checked: bool):
        self.console.set_wrap_mode(checked)

    def apply_preferences(self, preferences: dict):
        self.preferences = preferences
        font = QFont(preferences["font_family"], preferences["font_size"])
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        family = font.family().replace(chr(34), "").replace(";", "")
        font_css = f'font-family: "{family}"; font-size: {font.pointSize()}pt;'
        for widget in (self.console, self.input, self.legacy_completer.popup()):
            widget.setStyleSheet(font_css)
        self.legacy_completer.popup().setStyleSheet(
            build_stylesheet(self._theme())
            + f"QAbstractItemView#commandSuggestions {{{font_css}}}"
        )
        self.legacy_completer.popup().setFont(font)
        self.console.setFont(font)
        self.input.setFont(font)
        self.name_label.setFont(QFont("Cascadia Code", 10, QFont.Bold))
        if self.native:
            self.native_console.setStyleSheet(font_css)
            self.native_console.setFont(font)
            theme = self._theme()
            self.native_console.set_colors(theme.text, theme.terminalBg, theme.selection, theme.accent)
            self.native_console._resize_screen()

    def _theme(self):
        return get_theme(self.preferences["theme"])

    def append_html(self, text: str, color: str, label: str = ""):
        self.console.append_output(text, color, label, self._theme().accent)

    def append_system(self, text: str):
        self.append_html(text, self._theme().muted, "•")

    def append_output(self, text: str):
        self.append_html(text, self._theme().output)

    def append_error(self, text: str):
        self.append_html(text, self._theme().error, "!")

    def append_external_command(self, command: str, result):
        """Display a command executed by a remote control channel."""
        self._settle_to_bottom()
        self.append_html(f"{self.shell.prompt()}{command}", self._theme().accent_alt, "$")
        if result.output:
            (self.append_output if result.success else self.append_error)(result.output)
        self.shell.ctx.history.append(command)
        self.input.set_history(self.shell.ctx.history)
        self.path_label.setText(f"{self.shell.ctx.cwd}")
        self.session_changed.emit()

    def clear_console(self):
        self.console.clear()
        if self.native:
            self.native_console.clear()
            self.native.transport.write("\x0c")
        self.append_system("Console cleared.")

    def copy_output(self):
        widget = self.console_stack.currentWidget()
        if isinstance(widget, QTextEdit) and widget.textCursor().hasSelection():
            widget.copy()
            self.state_label.setText("COPIED")
            return
        if hasattr(widget, "copy_selection") and widget.copy_selection():
            self.state_label.setText("COPIED")
            return
        QApplication.clipboard().setText(widget.toPlainText())
        self.state_label.setText("COPIED")

    def _approval_decision(self, command: str):
        if not self.preferences["confirm_risky"]:
            return None
        decision = self.safety.check_shell_command(command)
        return decision if decision.requires_approval else None

    def run_command(self, approval_granted: bool = False, from_orbit: bool = False):
        command = self.input.text().strip()
        if not command or self.is_busy:
            return False
        use_native = self._uses_native(command, from_orbit)
        if command.lower() in {"clear", "cls"} and not use_native:
            self._settle_to_bottom()
            self.clear_console()
            self.input.clear()
            self.input.setFocus()
            return True
        decision = None if approval_granted else (
            self.safety.check_powershell_command(command) if use_native and self.preferences["confirm_risky"]
            else self._approval_decision(command)
        )
        if decision and not decision.requires_approval:
            decision = None
        if decision:
            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Warning)
            dialog.setWindowTitle("Confirm command")
            dialog.setText(decision.reason)
            dialog.setInformativeText(f"Command:\n{command}")
            dialog.setStandardButtons(QMessageBox.Cancel | QMessageBox.Yes)
            dialog.setDefaultButton(QMessageBox.Cancel)
            if dialog.exec() != QMessageBox.Yes:
                self.append_system("Command cancelled before execution.")
                return False
        self._settle_to_bottom()
        if use_native:
            self.console_stack.setCurrentWidget(self.native_console)
            self.native_console._resize_screen()
            self.native_console.start_capture()
            if not self.native.submit(command):
                self.native_console.finish_capture()
                self.console_stack.setCurrentWidget(self.console)
                self.append_error("PowerShell is unavailable. Open a new tab to restart it.")
                return False
            self.append_html(f"{self.shell.prompt()}{command}", self._theme().accent_alt, "$")
            self.active_command = command
            self._active_native = True
            self.shell.ctx.history.append(command)
            self.input.clear()
            self.console_stack.setCurrentWidget(self.native_console)
            self.native_console.setFocus()
            self._set_running(True)
            return True
        self.append_html(f"{self.shell.prompt()}{command}", self._theme().accent_alt, "$")
        self.active_command = command
        self._set_running(True)
        self.worker = CommandWorker(self.shell, command, self)
        self.worker.result_ready.connect(self._on_finished)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()
        return True

    def request_cancel(self):
        if self.native and self.native.busy:
            self.native.cancel()
            self.state_label.setText("STOPPING")
            return
        if self.worker:
            self.worker.requestInterruption()
            self.shell.request_cancel()
            self.cancel_button.setEnabled(False)
            self.append_system("Stop requested. Native processes stop immediately; other commands finish their current safe step.")

    def _worker_finished(self):
        self._set_running(False)

    def _on_finished(self, result, display_output=True):
        if display_output and result.output:
            (self.append_output if result.success else self.append_error)(result.output)
        if result.actions.get("theme"):
            self.window().apply_theme(str(result.actions["theme"]))
        if result.actions.get("update"):
            if hasattr(self.window(), "update_controller"):
                self.window().update_controller.check(silent=False)
        self.path_label.setText(f"{self.shell.ctx.cwd}")
        self.input.set_history(self.shell.ctx.history)
        if self.shell.ctx.history:
            self.history_added.emit(self.shell.ctx.history[-1])
        self.input.clear()
        self.session_changed.emit()
        self.command_completed.emit(self.active_command, result)
        self.active_command = ""
        if result.exit_shell:
            self.close_requested.emit(self)

    def _set_running(self, running: bool):
        was_running = not self.input.isEnabled()
        focus = QApplication.focusWidget()
        self.input.setEnabled(not running)
        self.run_button.setEnabled(not running)
        self.clear_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self.state_label.setText("RUNNING" if running else "READY")
        if was_running and not running and focus is not None and self.isAncestorOf(focus):
            self.input.setFocus(Qt.OtherFocusReason)
        self.session_changed.emit()

    def can_close(self) -> bool:
        if self.native and self.native.busy:
            if QMessageBox.question(
                self, "Close terminal", "Close this terminal and terminate its shell and running processes?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            ) != QMessageBox.Yes:
                return False
            self.native.close()
            return True
        if not self.is_busy:
            return True
        QMessageBox.warning(self, "Command still running", "Request stop, then wait for the command to finish before closing this session.")
        return False


class OrbitPanel(QFrame):
    action_requested = Signal(object, bool, object)
    output_ready = Signal(object, str)
    collapse_requested = Signal()

    def __init__(self, session_provider, parent=None):
        super().__init__(parent)
        self.setObjectName("inspector")
        self.session_provider = session_provider
        self.safety = SafetyPolicy()
        self.planner = None
        self.worker: OrbitWorker | None = None
        self.pending_action = None
        self.pending_snapshots = None
        self.task = None
        self.task_session = None
        self.task_cwd = None
        self.executing = False
        self.continue_timer = QTimer(self)
        self.continue_timer.setSingleShot(True)
        self.continue_timer.timeout.connect(self._continue_task)

        heading = QLabel("◈  ORBIT AI COPILOT")
        heading.setObjectName("sectionTitle")
        hf = heading.font()
        hf.setLetterSpacing(QFont.PercentageSpacing, 108)
        heading.setFont(hf)

        self.thinking_indicator = QLabel("IDLE")
        self.thinking_indicator.setObjectName("statusPill")
        self.thinking_timer = QTimer(self)
        self.thinking_timer.timeout.connect(self._advance_thinking_indicator)
        self.thinking_frame = 0

        self.collapse_btn = QPushButton("»")
        self.collapse_btn.setObjectName("railToggleBtn")
        self.collapse_btn.setFixedSize(30, 26)
        self.collapse_btn.setToolTip("Collapse Orbit Panel")
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.clicked.connect(self.collapse_requested.emit)

        self.stream_timer = QTimer(self)
        self.stream_timer.timeout.connect(self._stream_next_chunk)
        self.stream_text = ""
        self.stream_index = 0
        self.stream_message_index: int | None = None
        self.stream_done = None
        self._preview_worker = None
        self.messages: list[tuple[str, str]] = []
        self._last_rendered_count = 0

        self.status = QLabel("Ask anything or request a workspace action.")
        self.status.setObjectName("orbitStatusBanner")
        self.status.setWordWrap(True)

        self.conversation = QTextEdit()
        self.conversation.setObjectName("orbitConversation")
        self.conversation.setReadOnly(True)
        self.conversation.setMinimumHeight(200)
        self.conversation.setLineWrapMode(QTextEdit.WidgetWidth)
        self.conversation.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.conversation.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.conversation.document().setDocumentMargin(8)
        self.conversation.document().setDefaultStyleSheet("""
            body, p, div, span {
                white-space: pre-wrap;
                overflow-wrap: anywhere;
                word-break: break-word;
                line-height: 145%;
                min-width: 0;
            }
            pre, code {
                white-space: pre-wrap;
                overflow-wrap: anywhere;
                word-break: break-all;
                font-family: "Cascadia Code", "JetBrains Mono", monospace;
                font-size: 12.5px;
                line-height: 142%;
            }
            a {
                color: #C084FC;
                overflow-wrap: anywhere;
                word-break: break-all;
            }
        """)

        self.input = QLineEdit()
        self.input.setObjectName("orbitInput")
        self.input.setPlaceholderText("Ask Orbit to inspect files, run commands, or write code…")
        self.plan_button = QPushButton("Ask Orbit  ↵")
        self.plan_button.setObjectName("primaryButton")
        self.approve_button = QPushButton("✓  Approve")
        self.approve_button.setObjectName("approveButton")
        self.approve_button.setEnabled(False)
        self.reject_button = QPushButton("✕  Dismiss")
        self.reject_button.setObjectName("dismissButton")
        self.reject_button.setEnabled(False)
        self.stop_button = QPushButton("■  Stop")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        actions.addWidget(self.approve_button)
        actions.addWidget(self.reject_button)
        actions.addWidget(self.stop_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(heading)
        header.addStretch()
        header.addWidget(self.thinking_indicator)
        header.addWidget(self.collapse_btn)
        layout.addLayout(header)

        mode_card = QFrame()
        mode_card.setObjectName("modeBar")
        mode_row = QHBoxLayout(mode_card)
        mode_row.setContentsMargins(10, 6, 10, 6)
        mode_row.setSpacing(8)
        self.mode_selector = QComboBox()
        self.mode_selector.setToolTip("Choose the budget for your next Orbit task")
        self.mode_selector.currentIndexChanged.connect(self._select_mode)
        mode_button = QPushButton("Modes…")
        mode_button.clicked.connect(self._edit_modes)
        mode_lbl = QLabel("MODE")
        mode_lbl.setObjectName("eyebrow")
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.mode_selector, 1)
        mode_row.addWidget(mode_button)
        layout.addWidget(mode_card)

        self._reload_modes()
        layout.addWidget(self.status)
        layout.addWidget(self.conversation, 1)

        composer = QFrame()
        composer.setObjectName("orbitComposer")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(10, 10, 10, 10)
        composer_layout.setSpacing(8)
        composer_layout.addWidget(self.input)
        composer_layout.addWidget(self.plan_button)
        composer_layout.addLayout(actions)
        layout.addWidget(composer)

        self.plan_button.clicked.connect(self.create_plan)
        self.input.returnPressed.connect(self.create_plan)
        self.approve_button.clicked.connect(self.approve)
        self.reject_button.clicked.connect(self.dismiss)
        self.stop_button.clicked.connect(self.stop_task)

    def paintEvent(self, event):
        super().paintEvent(event)
        _paint_hud_brackets(self)

    def _reload_modes(self):
        self.mode_selector.blockSignals(True)
        self.mode_selector.clear()
        try:
            modes, selected = load_mode_preferences()
            for mode in modes:
                self.mode_selector.addItem(mode.name, mode.name)
                self.mode_selector.setItemData(self.mode_selector.count() - 1,
                    f"~{mode.prompt_tokens} prompt tokens; {mode.output_tokens} output tokens; "
                    f"{mode.max_files} files; {mode.max_steps} planning decisions", Qt.ToolTipRole)
            self.mode_selector.setCurrentIndex(self.mode_selector.findData(selected.name))
        except ValueError as exc:
            self.status.setText(str(exc))
        finally:
            self.mode_selector.blockSignals(False)

    def _select_mode(self, index):
        if index >= 0:
            settings = QSettings("RiftShell", "RiftShell")
            settings.setValue("ai/mode", self.mode_selector.itemData(index))
            settings.sync()

    def _edit_modes(self):
        from ui.orbit_modes import OrbitModesDialog
        try:
            dialog = OrbitModesDialog(self)
            animate_dialog_flip_open(dialog, self.window() if self.window() else self)
            if dialog.exec() == QDialog.Accepted:
                self._reload_modes()
        except ValueError as exc:
            QMessageBox.warning(self, "Orbit modes", str(exc))

    def _set_thinking(self, thinking: bool):
        if thinking:
            self.thinking_frame = 0
            self.thinking_indicator.setText("THINKING  |")
            self.thinking_timer.start(110)
            self.input.setEnabled(False)
            self.plan_button.setEnabled(False)
            return
        self.thinking_timer.stop()
        self.thinking_indicator.setText("IDLE")
        available = (not self.executing and not self.continue_timer.isActive()
                     and self._preview_worker is None)
        becoming_available = available and not self.input.isEnabled()
        self.input.setEnabled(available)
        self.plan_button.setEnabled(available)
        if becoming_available:
            PROVIDER_RUNTIME.record("input_ready")

    def _advance_thinking_indicator(self):
        frames = ("|", "/", "-", "\\")
        self.thinking_indicator.setText(f"THINKING  {frames[self.thinking_frame % len(frames)]}")
        self.thinking_frame += 1

    def _ensure_planner(self, session):
        if self.planner is None:
            from ai.llm import AgentPlanner
            try:
                modes, mode = load_mode_preferences()
            except Exception:
                mode = None
            config = load_desktop_config()
            if mode:
                config = replace(config, orbit_mode=mode)
            self.planner = AgentPlanner(
                config=config,
                command_names=session.shell.registry.all_names(),
                command_catalog=session.shell.registry.catalog_entries(),
                command_metadata=session.shell.registry.list_metadata(),
                current_dir_provider=lambda: session.shell.ctx.cwd,
                last_output_provider=lambda: session.shell.ctx.last_output,
                cancelled=lambda: bool(self.task and self.task.stopped),
                native_context_provider=getattr(session.shell, "native_context_provider", None),
            )
        else:
            try:
                modes, mode = load_mode_preferences()
                if mode:
                    self.planner.mode = mode
            except Exception:
                pass
        return self.planner

    def create_plan(self):
        prompt, session = self.input.text().strip(), self.session_provider()
        if not prompt or session is None or self.executing or self.continue_timer.isActive() or self._preview_worker is not None or self.worker and self.worker.isRunning():
            return

        if self.pending_action:
            decision = pending_action_reply(prompt)
            if decision == "approve":
                self._append("You", prompt)
                self.input.clear()
                self.approve()
                return
            if decision == "reject":
                self._append("You", prompt)
                self.input.clear()
                self.dismiss()
                self._append("Orbit", "The proposed action was dismissed. Nothing was changed.")
                return

        planner = self._ensure_planner(session)
        objective = planner.confirm_pending(prompt)
        is_execute = objective is not None
        task_objective = objective if is_execute else prompt

        try:
            _, mode = load_mode_preferences()
        except ValueError as exc:
            self._append("Orbit", str(exc))
            return
        self._append("You", prompt)
        self.input.clear()
        self.dismiss()
        self.task = AgentRun(task_objective, max_steps=mode.max_steps, mode=mode, planner=planner)
        self.task_session = session
        self.task_cwd = session.shell.ctx.cwd
        self.stop_button.setEnabled(True)
        self._start_planning(execute=is_execute)

    def _start_planning(self, execute: bool = False):
        self.status.setText("Thinking with conversation and workspace context…")
        self.approve_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        self._set_thinking(True)
        self.worker = OrbitWorker(
            self.task_session.shell,
            self.task.objective,
            self,
            task=self.task,
            execute=execute,
            planner=self.planner,
        )
        self.worker.planned.connect(self._show_plan)
        self.worker.failed.connect(self._show_failure)
        self.worker.progress.connect(self._show_provider_progress)
        worker = self.worker
        worker.finished.connect(lambda: self._planning_finished(worker))
        self.worker.start()

    def _show_provider_progress(self, message):
        if self.sender() is self.worker and self.task and not self.task.stopped:
            self.status.setText(message)

    def _planning_finished(self, worker):
        if self.worker is worker:
            self.worker = None
            self._set_thinking(False)
        worker.deleteLater()

    def _show_plan(self, action):
        if self.sender() is not None and getattr(self.sender(), "task", None) is not self.task:
            return
        if not self.task or self.task.stopped:
            return
        if self.task_session.shell.ctx.cwd != self.task_cwd:
            self.stop_task()
            self._append("Orbit", "The task directory changed while I was planning. Start a fresh request in the intended directory.")
            return
        action = self.task.accept(action)
        self.pending_action = None
        self.pending_snapshots = None
        self.approve_button.setText("✓  Approve & run")
        self.approve_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        message = action.message or (
            "I prepared the following RiftShell command for your review."
            if action.action == "shell"
            else "Here is the result of my workspace analysis."
        )
        step_prefix = f"Step {self.task.steps}: " if self.task and (self.task.steps > 1 or getattr(action, "continue_after_result", False)) else ""
        if action.action == "shell" and action.command:
            decision = self.safety.check_action(action.action, action.command)
            if decision.requires_approval:
                self.pending_action = action
                self._stream("Orbit", f"{step_prefix}{message}\n\nProposed command:\n{action.command}\n\nApproval is required because {decision.reason}")
                self.status.setText("Review the proposed command before approving it.")
                self.approve_button.setEnabled(True)
                self.reject_button.setEnabled(True)
            else:
                self._stream("Orbit", f"{step_prefix}{message}\n\nRunning in the active terminal:\n{action.command}")
                self.status.setText("Executing in the active terminal. Output will appear there shortly.")
                self.executing = True
                self.action_requested.emit(action, False, None)
        elif action.action == "code_write":
            session = self.task_session
            if session is None:
                self._stream("Orbit", "The active workspace session is no longer available.")
                self.status.setText("Open a workspace session and try again.")
                return
            config = self.task.planner.config if self.task and self.task.planner else load_desktop_config()
            self.status.setText("Generating file preview…")
            self._preview_worker = PreviewWorker(
                action, config, session.shell.ctx.cwd, message, self
            )
            self._preview_worker.result_ready.connect(self._show_preview_result)
            preview_worker = self._preview_worker
            preview_worker.finished.connect(lambda: self._preview_finished(preview_worker))
            self._preview_worker.start()
        else:
            self.task.stop()
            self.stop_button.setEnabled(False)
            self._set_thinking(False)
            if action.action != "respond":
                message = "This action is not available in the desktop task runner. No action was executed."
            final_message = f"Task completed: {message}" if self.task and self.task.steps > 1 and not message.startswith("Task") else message
            self._stream("Orbit", final_message)
            self.status.setText("Ready for your next question or task.")

    def _preview_finished(self, worker):
        if self._preview_worker is worker:
            self._preview_worker = None
            self._set_thinking(False)
        worker.deleteLater()

    def _show_preview_result(self, preview, action, message):
        if self.sender() is not None and self.sender() is not self._preview_worker:
            return
        if not self.task or self.task.stopped:
            return
        if not preview.success:
            self.task.stop()
            self.stop_button.setEnabled(False)
            self._stream("Orbit", f"{message}\n\nI could not prepare a safe file preview:\n\n{preview.output}")
            self.status.setText("The proposed file change was blocked.")
            return
        paths = ", ".join(file.path for file in action.files)
        self.pending_action = action
        self.pending_snapshots = preview.snapshots
        self._stream(
            "Orbit",
            f"{message}\n\nFiles: {paths}\n\nReview the proposed diff:\n\n```diff\n{preview.output}\n```",
        )
        self.status.setText("Review the diff before applying these file changes.")
        self.approve_button.setText("✓  Approve changes")
        self.approve_button.setEnabled(True)
        self.reject_button.setEnabled(True)

    def _show_failure(self, error: str):
        if self.sender() is not None and getattr(self.sender(), "task", None) is not self.task:
            return
        if self.task and self.task.stopped:
            return
        if self.task:
            self.task.stop()
        self.stop_button.setEnabled(False)
        self._set_thinking(False)
        self._append("Orbit", f"Planning failed: {error}")
        self.status.setText("Could not reach the configured AI provider.")

    def _append(self, label: str, text: str):
        self._finish_stream()
        self.messages.append((label, text))
        self._render_conversation()
        self._publish_output(label, text)

    def _publish_output(self, label: str, text: str):
        if label == "Orbit" and text:
            session = self.task_session or self.session_provider()
            if session is not None:
                self.output_ready.emit(session, text)

    @staticmethod
    def _escape_user_markdown(text: str) -> str:
        """Keep user input literal while allowing Orbit replies to use Markdown."""
        for char in "\\`*_{}[]<>":
            text = text.replace(char, f"\\{char}")
        return text

    def _render_conversation(self):
        rendered = getattr(self, '_last_rendered_count', 0)
        total = len(self.messages)

        if rendered == 0 or rendered > total:
            blocks = []
            for label, text in self.messages:
                body = self._escape_user_markdown(text) if label == "You" else text
                tag = "❯ **You**" if label == "You" else "◈ **Orbit**"
                blocks.append(f"{tag}\n\n{body}")
            self.conversation.setMarkdown("\n\n---\n\n".join(blocks))
            self._last_rendered_count = total
        elif total > rendered:
            cursor = self.conversation.textCursor()
            cursor.movePosition(QTextCursor.End)
            for label, text in self.messages[rendered:]:
                body = self._escape_user_markdown(text) if label == "You" else text
                tag = "❯ **You**" if label == "You" else "◈ **Orbit**"
                cursor.insertBlock()
                cursor.insertMarkdown(f"---\n\n{tag}\n\n{body}")
            self._last_rendered_count = total
        else:
            if total > 0:
                blocks = []
                for l, t in self.messages:
                    b = self._escape_user_markdown(t) if l == "You" else t
                    tag = "❯ **You**" if l == "You" else "◈ **Orbit**"
                    blocks.append(f"{tag}\n\n{b}")
                self.conversation.setMarkdown("\n\n---\n\n".join(blocks))

        cursor = self.conversation.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.conversation.setTextCursor(cursor)
        self.conversation.ensureCursorVisible()

    def _finish_stream(self):
        if self.stream_message_index is None:
            return
        if self.stream_timer.isActive():
            self.stream_timer.stop()
        label, _ = self.messages[self.stream_message_index]
        self.messages[self.stream_message_index] = (label, self.stream_text)
        self.stream_index = len(self.stream_text)
        self.stream_message_index = None

    def _stream(self, label: str, text: str, on_done=None):
        """The provider already returned complete text: render it once, immediately."""
        started = perf_counter()
        self._finish_stream()
        self.stream_timer.stop()
        self._publish_output(label, text)
        self.stream_text = text
        self.stream_index = len(text)
        self.stream_done = None
        self.messages.append((label, text))
        self.stream_message_index = None
        self._render_conversation()
        PROVIDER_RUNTIME.record("render", elapsed_seconds=perf_counter() - started, response_chars=len(text))
        if on_done:
            on_done()

    def _stream_next_chunk(self):
        if self.stream_index >= len(self.stream_text):
            self.stream_timer.stop()
            self.stream_message_index = None
            if self.stream_done:
                self.stream_done()
            return
        chunk = self.stream_text[self.stream_index:self.stream_index + 18]
        if self.stream_message_index is not None:
            label, current = self.messages[self.stream_message_index]
            self.messages[self.stream_message_index] = (label, current + chunk)
        self._render_conversation()
        self.stream_index += len(chunk)

    def approve(self):
        if self.pending_action:
            action = self.pending_action
            snapshots = self.pending_snapshots
            if self.task_session.shell.ctx.cwd != self.task_cwd:
                self.stop_task()
                self._append("Orbit", "The task directory changed after review. Please request a fresh proposal.")
                return
            self.executing = True
            self.input.setEnabled(False)
            self.plan_button.setEnabled(False)
            self.action_requested.emit(action, True, snapshots)
            if action.action == "code_write":
                self._append("Orbit", "Approved. Applying the reviewed file changes with backups.")
                self.status.setText("Applying approved file changes.")
            else:
                self._append("Orbit", "Approved. Executing in the active terminal; the output will appear there.")
                self.status.setText("Executing approved command in the active terminal.")
        self.pending_action = None
        self.pending_snapshots = None
        self.approve_button.setText("✓  Approve & run")
        self.approve_button.setEnabled(False)
        self.reject_button.setEnabled(False)

    def dismiss(self):
        if self.task:
            self.task.stop()
        self.stop_button.setEnabled(False)
        self.pending_action = None
        self.pending_snapshots = None
        self.approve_button.setText("✓  Approve & run")
        self.approve_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        self.status.setText("Ask anything, or request a workspace action.")

    def stop_task(self):
        self.continue_timer.stop()
        self.dismiss()
        if self.executing and self.task_session and self.task_session.is_busy:
            self.task_session.request_cancel()
        self.status.setText("Stopped. An in-flight request or approved write may finish; no further step will run.")
        self.worker = None
        self._preview_worker = None
        self._set_thinking(False)

    def _continue_task(self):
        if not self.task or self.task.stopped:
            self._set_thinking(False)
            return
        if self.worker and self.worker.isRunning() or self.task_session.is_busy:
            self.continue_timer.start(50)
            return
        if self.task_session.shell.ctx.cwd != self.task_cwd:
            self.stop_task()
            self._append("Orbit", "The task directory changed before the next step. Please start a fresh request.")
            return
        self._start_planning()

    def _observe_result(self, result, continue_after_result=True):
        self.executing = False
        if self.task and self.task.observe(result):
            if not continue_after_result:
                self.task.stop()
                self.stop_button.setEnabled(False)
                self._set_thinking(False)
                return False
            self.task_cwd = self.task_session.shell.ctx.cwd
            self.status.setText(f"Step {self.task.steps}: reviewing the result…")
            self.continue_timer.start(50)
            self.input.setEnabled(False)
            self.plan_button.setEnabled(False)
            return True
        self.stop_button.setEnabled(False)
        self._set_thinking(False)
        return False

    def show_execution_result(self, command: str, result):
        continue_after_result = bool(
            self.task
            and self.task.pending
            and self.task.pending.continue_after_result
        )
        if self._observe_result(result, continue_after_result):
            return
        if result.success:
            output = str(result.output).strip()
            if command.strip().lower() == "where" and output:
                message = f"You are currently in the workspace directory `{output.splitlines()[-1]}`."
            else:
                message = f"Completed: {command}\nThe command output is now available in the active terminal."
            self._stream("Orbit", message)
            self.status.setText("Completed. Review the terminal output for the full result.")
            if self.task and self.task.planner and getattr(self.task.planner, "memory", None):
                self.task.planner.memory.add("assistant", message)
            return
        detail = result.output.strip().splitlines()[0] if result.output else "The command did not complete successfully."
        self._stream("Orbit", f"The command did not complete: {command}\n{detail}\n\nSee the terminal for full details.")
        self.status.setText("Command failed. Full diagnostics are in the terminal.")

    def show_write_result(self, result):
        self._append("Orbit", result.output)
        if self._observe_result(result):
            return
        if result.success:
            self._stream("Orbit", f"The approved file changes were applied successfully.\n\n{result.output}")
            self.status.setText("File changes applied. Backups are available for overwritten files.")
            return
        self._stream("Orbit", f"The file changes were not applied.\n\n{result.output}")
        self.status.setText("File update failed or was blocked.")


class MainWindow(QMainWindow):
    telegram_command_received = Signal(str, object)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.settings = QSettings("RiftShell", "RiftShell")
        self.preferences = self._load_preferences()
        self.telegram_service = TelegramControlService()
        self.telegram_command_received.connect(self._display_telegram_command)
        self.theme = get_theme(self.preferences["theme"])
        self.history = self._load_history() if self.preferences["restore_history"] else []
        self._orbit_execution: tuple[TerminalSession, str] | None = None
        self._orbit_write_worker: FileWriteWorker | None = None
        self._left_collapsed = True
        self._right_collapsed = True
        self.setWindowTitle(f"RiftShell v{__version__} — Developer Workspace")
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1460, 890)
        self.setMinimumSize(1080, 680)
        self.setStyleSheet(build_stylesheet(self.theme))
        self.setFont(QFont("Segoe UI Variable Text", 10))
        self.update_controller = UpdateController(self)
        self._build_workspace()
        self._install_shortcuts()
        self.new_session()
        self._refresh_workspace()
        if self.preferences.get("telegram_enabled"):
            QTimer.singleShot(0, lambda: self._configure_telegram(notify=False))
        QTimer.singleShot(3000, lambda: self.update_controller.check(silent=True))

    def _load_preferences(self) -> dict:
        try:
            ai = AIConfig.from_env()
            defaults = (ai.ai_provider, ai.groq_model, ai.ollama_base_url, ai.ollama_model,
                        str(ai.workspace_root), ai.allow_outside_workspace)
        except ValueError:
            defaults = ("auto", "llama-3.3-70b-versatile", "http://127.0.0.1:11434", "",
                        str(Path.home()), False)
        ollama_url = self.settings.value("ai/ollama_base_url", defaults[2], type=str)
        default_source = "colab" if "ngrok" in str(ollama_url).lower() else "local"
        ollama_source = self.settings.value("ai/ollama_source", default_source, type=str)
        return {
            "ai_provider": self.settings.value("ai/provider", defaults[0], type=str),
            "groq_model": self.settings.value("ai/groq_model", defaults[1], type=str),
            "ollama_source": ollama_source,
            "ollama_base_url": ollama_url,
            "ollama_colab_url": self.settings.value("ai/ollama_colab_url", ollama_url if ollama_source == "colab" else "", type=str),
            "ollama_local_url": self.settings.value("ai/ollama_local_url", ollama_url if ollama_source == "local" else "http://127.0.0.1:11434", type=str),
            "ollama_model": self.settings.value("ai/ollama_model", defaults[3], type=str),
            "workspace_root": self.settings.value("ai/workspace_root", defaults[4], type=str),
            "allow_outside_workspace": self.settings.value("ai/allow_outside_workspace", defaults[5], type=bool),
            "theme": self.settings.value("appearance/theme", "vscode-dark-plus", type=str),
            "font_family": self.settings.value("appearance/font_family", "JetBrains Mono", type=str),
            "font_size": self.settings.value("appearance/font_size", 11, type=int),
            "confirm_risky": self.settings.value("safety/confirm_risky", True, type=bool),
            "restore_history": self.settings.value("workspace/restore_history", True, type=bool),
            "telegram_enabled": self.settings.value("controls/telegram_enabled", False, type=bool),
            "telegram_allowed_user_ids": self.settings.value("controls/telegram_allowed_user_ids", "", type=str),
            "telegram_allow_unlisted_users": self.settings.value("controls/telegram_allow_unlisted_users", False, type=bool),
            "telegram_token_saved": self._telegram_token_saved(),
        }

    def _telegram_token_saved(self) -> bool:
        try:
            return saved_telegram_token_exists()
        except Exception:
            return False

    def _load_history(self) -> list[str]:
        value = self.settings.value("workspace/history", [])
        return value if isinstance(value, list) else []

    def _build_workspace(self):
        self.title_bar = CustomTitleBar(self)
        root = QSplitter(Qt.Horizontal)
        root.setHandleWidth(2)
        root.setChildrenCollapsible(False)

        self.left_panel_stack = QStackedWidget()
        self.left_rail = self._build_left_rail()
        self.sidebar_expanded = self._build_sidebar()
        self.left_panel_stack.addWidget(self.left_rail)
        self.left_panel_stack.addWidget(self.sidebar_expanded)
        root.addWidget(self.left_panel_stack)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("workspaceTabs")
        self.tabs.setTabsClosable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabBarAutoHide(True)
        self.tabs.currentChanged.connect(self._refresh_workspace)
        self.tabs.tabCloseRequested.connect(self.close_session_at)
        root.addWidget(self.tabs)

        self.right_panel_stack = QStackedWidget()
        self.right_rail = self._build_right_rail()
        self.orbit = OrbitPanel(self.current_session)
        self.orbit.setMinimumWidth(330)
        self.orbit.action_requested.connect(self._run_orbit_action)
        self.orbit.output_ready.connect(self._show_orbit_output)
        self.orbit.collapse_requested.connect(lambda: self.set_right_collapsed(True))
        self.right_panel_stack.addWidget(self.right_rail)
        self.right_panel_stack.addWidget(self.orbit)
        root.addWidget(self.right_panel_stack)

        self.root_splitter = root
        self.set_left_collapsed(True)
        self.set_right_collapsed(True)

        container = QWidget()
        container.setObjectName("windowContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.title_bar)
        container_layout.addWidget(root, 1)
        self.setCentralWidget(container)

        self.status_label = QLabel()
        self.statusBar().addWidget(self.status_label, 1)
        self.safety_label = QLabel("⛨  SAFE MODE")
        self.safety_label.setObjectName("statusPill")
        self.statusBar().addPermanentWidget(self.safety_label)
        self._refresh_rail_icons()

    def _build_left_rail(self) -> QWidget:
        rail = QFrame()
        rail.setObjectName("leftRail")
        rail.setFixedWidth(58)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(9, 14, 9, 14)
        layout.setSpacing(10)

        self.rail_new_btn = QPushButton()
        self.rail_new_btn.setObjectName("railPrimaryBtn")
        self.rail_new_btn.setFixedSize(40, 40)
        self.rail_new_btn.setIconSize(QSize(22, 22))
        self.rail_new_btn.setToolTip("New Terminal Session (Ctrl+Shift+T)")
        self.rail_new_btn.setCursor(Qt.PointingHandCursor)
        self.rail_new_btn.clicked.connect(self.new_session)
        layout.addWidget(self.rail_new_btn, 0, Qt.AlignHCenter)

        layout.addSpacing(4)

        self._left_rail_buttons: list[tuple[QPushButton, str]] = []
        rail_actions = [
            ("grid", "Command Palette (Ctrl+K)", self.open_palette),
            ("clock", "Command History", self.show_history),
            ("explorer", "Command Explorer", self.show_command_explorer),
            ("settings", "Workspace Settings (Ctrl+,)", self.open_settings),
            ("updates", "Check for Updates", lambda: self.update_controller.check(silent=False)),
            ("cube", "Manage Extensions", self.show_plugins),
        ]
        for icon_kind, tooltip, callback in rail_actions:
            btn = QPushButton()
            btn.setObjectName("railIconBtn")
            btn.setFixedSize(38, 38)
            btn.setIconSize(QSize(21, 21))
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(callback)
            layout.addWidget(btn, 0, Qt.AlignHCenter)
            self._left_rail_buttons.append((btn, icon_kind))

        layout.addStretch(1)

        self.expand_left_btn = QPushButton("»")
        self.expand_left_btn.setObjectName("railToggleBtn")
        self.expand_left_btn.setFixedSize(36, 32)
        self.expand_left_btn.setToolTip("Expand Sidebar")
        self.expand_left_btn.setCursor(Qt.PointingHandCursor)
        self.expand_left_btn.clicked.connect(lambda: self.set_left_collapsed(False))
        layout.addWidget(self.expand_left_btn, 0, Qt.AlignHCenter)
        return rail

    def _build_right_rail(self) -> QWidget:
        rail = QFrame()
        rail.setObjectName("rightRail")
        rail.setFixedWidth(64)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(7, 14, 7, 14)
        layout.setSpacing(10)

        self.rail_orbit_btn = QToolButton()
        self.rail_orbit_btn.setObjectName("railCardBtn")
        self.rail_orbit_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.rail_orbit_btn.setText("Orbit")
        self.rail_orbit_btn.setIconSize(QSize(24, 24))
        self.rail_orbit_btn.setFixedSize(50, 56)
        self.rail_orbit_btn.setToolTip("Open Orbit AI Copilot")
        self.rail_orbit_btn.setCursor(Qt.PointingHandCursor)
        self.rail_orbit_btn.clicked.connect(self._open_orbit_from_rail)
        layout.addWidget(self.rail_orbit_btn, 0, Qt.AlignHCenter)

        self.rail_modes_btn = QToolButton()
        self.rail_modes_btn.setObjectName("railCardBtn")
        self.rail_modes_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.rail_modes_btn.setText("Modes")
        self.rail_modes_btn.setIconSize(QSize(22, 22))
        self.rail_modes_btn.setFixedSize(50, 56)
        self.rail_modes_btn.setToolTip("Configure Orbit Execution Modes")
        self.rail_modes_btn.setCursor(Qt.PointingHandCursor)
        self.rail_modes_btn.clicked.connect(lambda: self.orbit._edit_modes())
        layout.addWidget(self.rail_modes_btn, 0, Qt.AlignHCenter)

        layout.addStretch(1)

        self.expand_right_btn = QPushButton("«")
        self.expand_right_btn.setObjectName("railToggleBtn")
        self.expand_right_btn.setFixedSize(36, 32)
        self.expand_right_btn.setToolTip("Expand Orbit Panel")
        self.expand_right_btn.setCursor(Qt.PointingHandCursor)
        self.expand_right_btn.clicked.connect(lambda: self.set_right_collapsed(False))
        layout.addWidget(self.expand_right_btn, 0, Qt.AlignHCenter)
        return rail

    def _refresh_rail_icons(self):
        muted = self.theme.textMuted if self.theme else "#9D8EB5"
        accent = self.theme.accent_alt if self.theme else "#C084FC"
        if hasattr(self, "rail_new_btn"):
            self.rail_new_btn.setIcon(_make_vector_icon("terminal", muted, accent, 24))
        for btn, kind in getattr(self, "_left_rail_buttons", []):
            btn.setIcon(_make_vector_icon(kind, muted, accent, 22))
        if hasattr(self, "rail_orbit_btn"):
            self.rail_orbit_btn.setIcon(_make_vector_icon("orbit", muted, accent, 24))
        if hasattr(self, "rail_modes_btn"):
            self.rail_modes_btn.setIcon(_make_vector_icon("modes", muted, accent, 22))

    def _open_orbit_from_rail(self):
        self.set_right_collapsed(False)
        self.orbit.input.setFocus()

    def set_left_collapsed(self, collapsed: bool):
        self._left_collapsed = bool(collapsed)
        if self._left_collapsed:
            self.left_panel_stack.setCurrentWidget(self.left_rail)
            self.left_panel_stack.setFixedWidth(58)
        else:
            self.left_panel_stack.setCurrentWidget(self.sidebar_expanded)
            self.left_panel_stack.setMinimumWidth(240)
            self.left_panel_stack.setMaximumWidth(310)
        self._sync_splitter_sizes()

    def set_right_collapsed(self, collapsed: bool):
        self._right_collapsed = bool(collapsed)
        if self._right_collapsed:
            self.right_panel_stack.setCurrentWidget(self.right_rail)
            self.right_panel_stack.setFixedWidth(64)
        else:
            self.right_panel_stack.setCurrentWidget(self.orbit)
            self.right_panel_stack.setMinimumWidth(330)
            self.right_panel_stack.setMaximumWidth(480)
        self._sync_splitter_sizes()

    def _sync_splitter_sizes(self):
        if not hasattr(self, "root_splitter"):
            return
        total = max(1080, self.width())
        left_w = 58 if self._left_collapsed else 255
        right_w = 64 if self._right_collapsed else 340
        center_w = max(500, total - left_w - right_w)
        self.root_splitter.setSizes([left_w, center_w, right_w])

    def _build_sidebar(self) -> QWidget:
        panel = HUDFrame()
        panel.setObjectName("sidebar")
        panel.setMinimumWidth(240)
        panel.setMaximumWidth(310)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(6)

        brand_row = QHBoxLayout()
        brand = QLabel("RiftShell")
        brand.setObjectName("brand")
        brand_row.addWidget(brand)
        brand_row.addStretch()
        collapse_top_btn = QPushButton("«")
        collapse_top_btn.setObjectName("railToggleBtn")
        collapse_top_btn.setFixedSize(30, 26)
        collapse_top_btn.setToolTip("Collapse Sidebar")
        collapse_top_btn.setCursor(Qt.PointingHandCursor)
        collapse_top_btn.clicked.connect(lambda: self.set_left_collapsed(True))
        brand_row.addWidget(collapse_top_btn)
        layout.addLayout(brand_row)

        subtitle = QLabel("AI-NATIVE WINDOWS SHELL")
        subtitle.setObjectName("eyebrow")
        sf = subtitle.font()
        sf.setLetterSpacing(QFont.PercentageSpacing, 108)
        subtitle.setFont(sf)
        layout.addWidget(subtitle)
        layout.addSpacing(10)

        self.new_button = QPushButton("+   New Terminal Session")
        self.new_button.setObjectName("primaryButton")
        self.new_button.clicked.connect(self.new_session)
        layout.addWidget(self.new_button)
        layout.addSpacing(6)

        tools_title = QLabel("WORKSPACE TOOLS")
        tools_title.setObjectName("sectionTitle")
        layout.addWidget(tools_title)

        for label, callback in [
            ("⌘   Command Palette", self.open_palette),
            ("◷   Command History", self.show_history),
            ("⊞   Command Explorer", self.show_command_explorer),
            ("⚙   Workspace Settings", self.open_settings),
            ("↻   Check for Updates", lambda: self.update_controller.check(silent=False)),
        ]:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.clicked.connect(callback)
            layout.addWidget(button)

        layout.addSpacing(10)
        sessions_title = QLabel("ACTIVE SESSIONS")
        sessions_title.setObjectName("sectionTitle")
        stf = sessions_title.font()
        stf.setLetterSpacing(QFont.PercentageSpacing, 108)
        sessions_title.setFont(stf)
        layout.addWidget(sessions_title)

        self.session_list = QListWidget()
        self.session_list.setWordWrap(True)
        self.session_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.session_list.setMaximumHeight(165)
        self.session_list.itemClicked.connect(self._activate_session_item)
        self.session_list.itemDoubleClicked.connect(self._rename_session_item)
        layout.addWidget(self.session_list)

        layout.addSpacing(8)
        plugins_title = QLabel("EXTENSIONS")
        plugins_title.setObjectName("sectionTitle")
        ptf = plugins_title.font()
        ptf.setLetterSpacing(QFont.PercentageSpacing, 108)
        plugins_title.setFont(ptf)
        layout.addWidget(plugins_title)

        ext_card = QFrame()
        ext_card.setObjectName("extensionCard")
        ext_layout = QVBoxLayout(ext_card)
        ext_layout.setContentsMargins(10, 8, 10, 8)
        ext_layout.setSpacing(6)
        self.plugin_summary = QLabel()
        self.plugin_summary.setWordWrap(True)
        ext_layout.addWidget(self.plugin_summary)
        plugins_button = QPushButton("Manage Extensions…")
        plugins_button.setObjectName("navButton")
        plugins_button.clicked.connect(self.show_plugins)
        ext_layout.addWidget(plugins_button)
        layout.addWidget(ext_card)

        layout.addStretch()

        bottom_row = QHBoxLayout()
        hint = QLabel("Ctrl+K  Palette  ·  Ctrl+Shift+T  New")
        hint.setWordWrap(True)
        hint.setObjectName("sessionPath")
        self.collapse_left_btn = QPushButton("«")
        self.collapse_left_btn.setObjectName("railToggleBtn")
        self.collapse_left_btn.setFixedSize(34, 30)
        self.collapse_left_btn.setToolTip("Collapse Sidebar")
        self.collapse_left_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_left_btn.clicked.connect(lambda: self.set_left_collapsed(True))
        bottom_row.addWidget(hint, 1)
        bottom_row.addWidget(self.collapse_left_btn)
        layout.addLayout(bottom_row)
        return panel

    def _install_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self.open_palette)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self, activated=self.new_session)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self.open_settings)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=lambda: self.current_session() and self.current_session().clear_console())
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=lambda: self.current_session() and self.current_session().copy_output())

    def new_session(self, start_dir: Path | None = None, title: str | None = None):
        default_dir = Path.cwd()
        if getattr(sys, "frozen", False):
            chosen = Path(self.preferences["workspace_root"])
            default_dir = chosen if chosen.is_dir() else Path.home()
        shell = Shell(start_dir=start_dir or default_dir)
        shell.ctx.current_theme = self.preferences["theme"]
        shell.ctx.history = self.history[-300:]
        session = TerminalSession(shell, title or f"Terminal {self.tabs.count() + 1}", self.preferences, self.tabs)
        session.history_added.connect(self.record_history)
        session.session_changed.connect(self._refresh_workspace)
        session.close_requested.connect(self.close_session)
        session.command_completed.connect(lambda command, result, source=session: self._on_terminal_command_complete(source, command, result))
        self.tabs.setCurrentIndex(self.tabs.addTab(session, session.title))
        self._refresh_workspace()
        session.input.setFocus()

    def current_session(self) -> TerminalSession | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, TerminalSession) else None

    def close_session_at(self, index: int):
        session = self.tabs.widget(index)
        if isinstance(session, TerminalSession):
            self.close_session(session)

    def close_session(self, session: TerminalSession):
        if session is self.orbit.task_session:
            if self.orbit.executing or self.orbit.worker and self.orbit.worker.isRunning():
                QMessageBox.warning(self, "Orbit task in progress", "Stop Orbit and wait for the current step before closing this session.")
                return
            self.orbit.stop_task()
        if not session.can_close():
            return
        if not session.shutdown():
            QTimer.singleShot(100, lambda: self.close_session(session))
            return
        index = self.tabs.indexOf(session)
        if index < 0:
            return
        self.tabs.removeTab(index)
        session.deleteLater()
        if self.tabs.count() == 0:
            self.new_session()
        self._refresh_workspace()

    def _refresh_workspace(self, *_):
        session = self.current_session()
        self.session_list.blockSignals(True)
        self.session_list.clear()
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            if not isinstance(tab, TerminalSession):
                continue
            status_dot = "●" if tab.is_busy else "○"
            item = QListWidgetItem(f"{status_dot}   {tab.title}")
            item.setData(Qt.UserRole, index)
            item.setToolTip(str(tab.shell.ctx.cwd))
            self.session_list.addItem(item)
            if tab is session:
                self.session_list.setCurrentItem(item)
            self.tabs.setTabText(index, tab.title)
        self.session_list.blockSignals(False)
        if session:
            if hasattr(self, "title_bar"):
                current_cwd = str(session.shell.ctx.cwd)
                folder_name = Path(current_cwd).name or current_cwd
                self.title_bar.set_workspace_text(f"◈   WORKSPACE   //   {folder_name}")
            plugins = session.shell.ctx.plugins
            loaded = len(plugins.loaded) if plugins else 0
            failed = len(plugins.failed) if plugins else 0
            self.plugin_summary.setText(f"{loaded} active  ·  {failed} attention")
            status_str = "● RUNNING" if session.is_busy else "● READY"
            self.status_label.setText(f"{status_str}   │   {session.shell.ctx.cwd}   │   {len(session.shell.registry.all_names())} commands")
        if hasattr(self, "safety_label"):
            self.safety_label.setText("⛨  SAFE MODE" if self.preferences.get("confirm_risky", True) else "⚡  FAST MODE")

    def _activate_session_item(self, item):
        self.tabs.setCurrentIndex(item.data(Qt.UserRole))

    def _rename_session_item(self, item):
        session = self.tabs.widget(item.data(Qt.UserRole))
        if not isinstance(session, TerminalSession):
            return
        value, accepted = QInputDialog.getText(self, "Rename session", "Session name", text=session.title)
        if accepted and value.strip():
            session.set_title(value.strip())

    def record_history(self, command: str):
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
        self.history = self.history[-500:]
        self.settings.setValue("workspace/history", self.history)

    def _exec_dialog_flip(self, dialog: QDialog) -> int:
        animate_dialog_flip_open(dialog, self)
        return dialog.exec()

    def open_palette(self):
        session = self.current_session()
        if not session:
            return
        palette = CommandPalette(session.shell, self)
        palette.command_chosen.connect(lambda command: self._insert_command(command))
        palette.action_chosen.connect(self._handle_palette_action)
        self._exec_dialog_flip(palette)

    def _insert_command(self, command: str):
        session = self.current_session()
        if session:
            if session.is_busy:
                return
            session.input.setText(command + " ")
            session.input.setFocus()

    def _handle_palette_action(self, action: str):
        callbacks = {
            "New terminal session": self.new_session, "Open settings": self.open_settings,
            "Toggle Orbit": self.toggle_orbit, "Show plugins": self.show_plugins,
            "Check for updates": lambda: self.update_controller.check(silent=False),
        }
        if callback := callbacks.get(action):
            callback()

    def show_history(self):
        session = self.current_session()
        dialog = QDialog(self)
        dialog.setWindowTitle("Command History")
        dialog.resize(660, 490)
        eyebrow = QLabel("◷  RECENT COMMAND HISTORY")
        eyebrow.setObjectName("eyebrow")
        search = QLineEdit()
        search.setPlaceholderText("Filter command history…")
        listing = QListWidget()
        listing.setWordWrap(True)
        listing.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        use = QPushButton("Insert Selected Command")
        use.setObjectName("primaryButton")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(eyebrow)
        layout.addWidget(search)
        layout.addWidget(listing, 1)
        layout.addWidget(use)
        def refresh(query=""):
            listing.clear()
            for entry in reversed(self.history):
                if fuzzy_score(query, entry) is not None:
                    listing.addItem(entry)
        def choose():
            if item := listing.currentItem():
                if session:
                    session.input.setText(item.text())
                    session.input.setFocus()
                dialog.accept()
        search.textChanged.connect(refresh)
        listing.itemDoubleClicked.connect(lambda _: choose())
        use.clicked.connect(choose)
        refresh()
        self._exec_dialog_flip(dialog)

    def show_command_explorer(self):
        session = self.current_session()
        if not session:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Command Explorer")
        dialog.resize(840, 580)
        eyebrow = QLabel("⊞  BUILT-IN & EXTENSION COMMAND EXPLORER")
        eyebrow.setObjectName("eyebrow")
        search = QLineEdit()
        search.setPlaceholderText("Search commands, aliases, descriptions…")
        listing = QListWidget()
        listing.setWordWrap(True)
        listing.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        details_card = QFrame()
        details_card.setObjectName("infoCard")
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(12, 10, 12, 10)
        details = QLabel("Select a command to inspect its usage and source.")
        details.setWordWrap(True)
        details_layout.addWidget(details)
        use = QPushButton("Use Selected Command")
        use.setObjectName("primaryButton")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(eyebrow)
        layout.addWidget(search)
        layout.addWidget(listing, 1)
        layout.addWidget(details_card)
        layout.addWidget(use)
        metas = session.shell.registry.list_metadata()
        def refresh(query=""):
            listing.clear()
            ranked = []
            for meta in metas:
                score = fuzzy_score(query, f"{meta.name} {' '.join(meta.aliases)} {meta.description}")
                if score is not None:
                    ranked.append((score, meta))
            for _, meta in sorted(ranked, key=lambda result: result[0]):
                item = QListWidgetItem(f"❯  {meta.name}   —   {meta.description}")
                item.setData(Qt.UserRole, meta)
                listing.addItem(item)
        def describe(item):
            if item:
                meta = item.data(Qt.UserRole)
                details.setText(f"{meta.description}\n\nUsage: {meta.usage}\nAliases: {', '.join(meta.aliases) or 'None'}\nSource: {'Plugin: ' + meta.plugin if meta.plugin else 'Built-in command'}")
        def use_command():
            if item := listing.currentItem():
                self._insert_command(item.data(Qt.UserRole).name)
                dialog.accept()
        search.textChanged.connect(refresh)
        listing.currentItemChanged.connect(lambda current, _: describe(current))
        listing.itemDoubleClicked.connect(lambda _: use_command())
        use.clicked.connect(use_command)
        refresh()
        self._exec_dialog_flip(dialog)

    def open_settings(self):
        dialog = PreferencesDialog(self.preferences, self)
        dialog.preferences_saved.connect(self.save_preferences)
        self._exec_dialog_flip(dialog)

    def save_preferences(self, preferences: dict):
        self.preferences = preferences
        for key, value in preferences.items():
            if key in {"ai_provider", "groq_model", "ollama_source", "ollama_base_url",
                       "ollama_colab_url", "ollama_local_url", "ollama_model",
                       "workspace_root", "allow_outside_workspace"}:
                setting = "provider" if key == "ai_provider" else key
                self.settings.setValue(f"ai/{setting}", value)
            elif key in {"telegram_enabled", "telegram_allowed_user_ids", "telegram_allow_unlisted_users"}:
                self.settings.setValue(f"controls/{key}", value)
            else:
                group = "appearance" if key in {"theme", "font_family", "font_size"} else "safety" if key == "confirm_risky" else "workspace"
                self.settings.setValue(f"{group}/{key}", value)
        self.settings.sync()
        self.preferences["telegram_token_saved"] = self._telegram_token_saved()
        self._configure_telegram()
        self.apply_theme(preferences["theme"])
        self.setFont(QFont("Segoe UI Variable Text", 10))
        for index in range(self.tabs.count()):
            if session := self.tabs.widget(index):
                session.apply_preferences(preferences)

    def _configure_telegram(self, notify: bool = True):
        if not self.preferences.get("telegram_enabled"):
            self.telegram_service.stop()
            return
        try:
            self.telegram_service.start(
                load_desktop_config(),
                on_error=self._telegram_error,
                on_command_completed=self._telegram_command_completed,
            )
            self.status_label.setText("Telegram control enabled")
            if notify:
                QMessageBox.information(self, "Telegram connected", "Telegram connected")
        except Exception as exc:
            self.preferences["telegram_enabled"] = False
            self.settings.setValue("controls/telegram_enabled", False)
            self.status_label.setText("Telegram control is disabled")
            QMessageBox.warning(self, "Telegram connection failed", str(exc))

    def _telegram_error(self, error: Exception):
        QTimer.singleShot(0, lambda: self.status_label.setText(f"Telegram stopped: {error}"))

    def _telegram_command_completed(self, command: str, result):
        self.telegram_command_received.emit(command, result)

    def _display_telegram_command(self, command: str, result):
        session = self.current_session()
        if session is not None:
            session.append_external_command(command, result)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            if hasattr(self, "title_bar"):
                self.title_bar.update_max_icon(self.isMaximized())

    def paintEvent(self, event):
        super().paintEvent(event)
        theme = getattr(self, "theme", None)
        if not theme:
            return
        w, h = float(self.width()), float(self.height())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        if theme.key == "vscode-dark-plus":
            # Silky obsidian + magenta-violet aurora waves matching the reference design
            base = QLinearGradient(0, 0, w, h)
            base.setColorAt(0.0, QColor("#12091E"))
            base.setColorAt(0.42, QColor("#08050D"))
            base.setColorAt(0.78, QColor("#14071D"))
            base.setColorAt(1.0, QColor("#21092A"))
            painter.fillRect(self.rect(), base)

            # Upper-right magenta-violet wave glow
            g1 = QRadialGradient(QPointF(w * 0.86, h * 0.28), max(w, h) * 0.48)
            g1.setColorAt(0.0, QColor(217, 70, 239, 68))
            g1.setColorAt(0.38, QColor(147, 51, 234, 34))
            g1.setColorAt(1.0, QColor(11, 7, 17, 0))
            painter.fillRect(self.rect(), g1)

            # Lower-left crimson-magenta wave glow
            g2 = QRadialGradient(QPointF(w * 0.16, h * 0.78), max(w, h) * 0.46)
            g2.setColorAt(0.0, QColor(236, 72, 153, 62))
            g2.setColorAt(0.42, QColor(126, 34, 206, 28))
            g2.setColorAt(1.0, QColor(11, 7, 17, 0))
            painter.fillRect(self.rect(), g2)

            # Bottom-right deep violet glow
            g3 = QRadialGradient(QPointF(w * 0.82, h * 0.92), max(w, h) * 0.36)
            g3.setColorAt(0.0, QColor(192, 38, 211, 54))
            g3.setColorAt(1.0, QColor(11, 7, 17, 0))
            painter.fillRect(self.rect(), g3)

            # Subtle diagonal aurora fold highlight
            wave = QPainterPath()
            wave.moveTo(w * 0.05, h * 0.82)
            wave.cubicTo(w * 0.32, h * 0.54, w * 0.64, h * 0.48, w * 0.96, h * 0.18)
            wave.lineTo(w, h * 0.35)
            wave.cubicTo(w * 0.68, h * 0.58, w * 0.36, h * 0.66, w * 0.08, h * 0.95)
            wave.closeSubpath()
            wave_grad = QLinearGradient(0, h * 0.85, w, h * 0.2)
            wave_grad.setColorAt(0.0, QColor(236, 72, 153, 24))
            wave_grad.setColorAt(0.5, QColor(168, 85, 247, 14))
            wave_grad.setColorAt(1.0, QColor(217, 70, 239, 30))
            painter.fillPath(wave, wave_grad)
        elif theme.key == "ghost":
            painter.setRenderHint(QPainter.Antialiasing, False)
            pen = QPen(QColor(56, 189, 248, 8), 1)
            painter.setPen(pen)
            for y in range(0, int(h), 6):
                painter.drawLine(0, y, int(w), y)
            for x in range(0, int(w), 48):
                painter.drawLine(x, 0, x, int(h))

        painter.end()

    def apply_theme(self, theme_key: str):
        try:
            self.theme = get_theme(theme_key)
        except KeyError:
            return
        self.preferences["theme"] = self.theme.key
        self.settings.setValue("appearance/theme", self.theme.key)
        self.setStyleSheet(build_stylesheet(self.theme))
        self._refresh_rail_icons()
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                dark_val = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(hwnd),
                    ctypes.c_uint32(20),  # DWMWA_USE_IMMERSIVE_DARK_MODE
                    ctypes.byref(dark_val),
                    ctypes.sizeof(dark_val),
                )
                h = self.theme.bg.lstrip("#")
                if len(h) == 6:
                    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                    color = ctypes.c_uint32((b << 16) | (g << 8) | r)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        ctypes.c_void_p(hwnd),
                        ctypes.c_uint32(35),  # DWMWA_CAPTION_COLOR
                        ctypes.byref(color),
                        ctypes.sizeof(color),
                    )
            except Exception:
                pass
        for index in range(self.tabs.count()):
            if session := self.tabs.widget(index):
                session.shell.ctx.current_theme = self.theme.key
                session.apply_preferences(self.preferences)
                if hasattr(session, "hero_logo"):
                    session.hero_logo.update()
        self._refresh_workspace()
        self.update()

    def show_plugins(self):
        session = self.current_session()
        if not session:
            return
        report = session.shell.ctx.plugins
        dialog = QDialog(self)
        dialog.setWindowTitle("Plugin Manager")
        dialog.resize(660, 440)
        title = QLabel("◈  PLUGINS & EXTENSIONS")
        title.setObjectName("eyebrow")
        text = QTextEdit()
        text.setReadOnly(True)
        lines = ["Loaded plugins"]
        lines.extend(f"• {item.name}  v{item.version}\n  {item.description}" for item in report.loaded) if report and report.loaded else lines.append("No plugins loaded.")
        lines.append("\nFailed plugins")
        lines.extend(f"• {item.name}\n  {item.error}" for item in report.failed) if report and report.failed else lines.append("None — all discovered plugins loaded correctly.")
        lines.append("\nPlugin enable/disable is determined at launch. Restart RiftShell after changing plugin files.")
        text.setPlainText("\n".join(lines))
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(text, 1)
        self._exec_dialog_flip(dialog)

    def toggle_orbit(self):
        self.set_right_collapsed(not self._right_collapsed)

    def _show_orbit_output(self, session, text):
        if self.tabs.indexOf(session) >= 0:
            session.append_html(text, session._theme().text, "Orbit")

    def _run_orbit_action(
        self, action, approval_granted: bool = False, expected_snapshots=None
    ):
        if session := self.orbit.task_session:
            if session.is_busy:
                self.orbit.executing = False
                self.orbit.stop_task()
                self.orbit._append("Orbit", "The active terminal is busy. Wait for the current command to finish, then try again.")
                self.orbit.status.setText("Waiting for the active terminal to become available.")
                return
            if session.native and not session.native.context_available:
                self.orbit.executing = False
                self.orbit.stop_task()
                self.orbit._append("Orbit", "The terminal is in a non-filesystem PowerShell location. Return to a filesystem folder before I perform workspace actions.")
                return
            if action.action == "code_write":
                if not approval_granted:
                    self.orbit.executing = False
                    self.orbit.stop_task()
                    self.orbit._append("Orbit", "File changes require review and approval before they can be applied.")
                    return
                if self._orbit_write_worker and self._orbit_write_worker.isRunning():
                    self.orbit.executing = False
                    self.orbit.stop_task()
                    self.orbit._append("Orbit", "Another file update is already in progress.")
                    return
                task = self.orbit.task
                config = task.planner.config if task and task.planner else load_desktop_config()
                self._orbit_write_worker = FileWriteWorker(
                    action.files,
                    config.workspace_root,
                    config.allow_outside_workspace,
                    session.shell.ctx.cwd,
                    expected_snapshots,
                    self,
                )
                self._orbit_write_worker.result_ready.connect(self.orbit.show_write_result)
                self._orbit_write_worker.finished.connect(self._clear_orbit_write_worker)
                self._orbit_write_worker.start()
                return
            if action.action != "shell":
                self.orbit.executing = False
                self.orbit.stop_task()
                return
            command = action.command
            self._orbit_execution = (session, command)
            session.input.setText(command)
            if not session.run_command(approval_granted=approval_granted, from_orbit=True):
                self._orbit_execution = None
                self.orbit.executing = False
                self.orbit.stop_task()
            elif command.lower().strip() in {"clear", "cls"} and not session._active_native:
                self._orbit_execution = None
                self.orbit.show_execution_result(command, WriteResult("Terminal cleared.", True))

    def _clear_orbit_write_worker(self):
        worker = self._orbit_write_worker
        self._orbit_write_worker = None
        if worker:
            worker.deleteLater()

    def _on_terminal_command_complete(self, session: TerminalSession, command: str, result):
        if self._orbit_execution != (session, command):
            return
        self._orbit_execution = None
        self.orbit.show_execution_result(command, result)

    def closeEvent(self, event):
        if any(worker.isRunning() for worker in self.orbit.findChildren(QThread)):
            QMessageBox.warning(self, "Orbit is thinking", "Stop the task and wait for the current model request to return before closing.")
            event.ignore()
            return
        self.orbit.stop_task()
        if self._orbit_write_worker and self._orbit_write_worker.isRunning():
            QMessageBox.warning(self, "File changes in progress", "Wait for Orbit to finish applying the approved file changes.")
            event.ignore()
            return
        for index in range(self.tabs.count()):
            if session := self.tabs.widget(index):
                if session.is_busy:
                    if not session.can_close():
                        event.ignore()
                        return
        stopped = True
        for index in range(self.tabs.count()):
            session = self.tabs.widget(index)
            if session and not session.shutdown():
                stopped = False
        if not stopped:
            event.ignore()
            QTimer.singleShot(100, self.close)
            return
        self.telegram_service.stop()
        self.settings.sync()
        event.accept()
