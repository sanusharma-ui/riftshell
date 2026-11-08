"""Warp-style Command Block presentation for RiftShell terminal sessions."""
from __future__ import annotations

import re
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.icons import icon
from ui.themes import get_theme


PROMPT_GLYPH = chr(0x276F)


def is_directory_listing(text: str) -> bool:
    """Detect if output text is from list_entries (<DIR> / FILE listing)."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines or len(lines) < 1:
        return False
    matched = 0
    pattern = re.compile(r"^(<DIR>|FILE)\s+", re.IGNORECASE)
    for line in lines[:10]:
        if pattern.match(line):
            matched += 1
    return matched >= 1 and (matched >= len(lines) // 2 or matched >= 2)


def parse_directory_listing(text: str) -> list[tuple[bool, str, str]]:
    """Parse list_entries output into list of (is_dir, name, size)."""
    items = []
    pattern = re.compile(r"^(<DIR>|FILE)\s+([-\d\w\s]+?)\s{2,}(.+)$", re.IGNORECASE)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            kind, size, name = match.group(1).upper(), match.group(2).strip(), match.group(3).strip()
            items.append((kind == "<DIR>", name, size))
        else:
            # Fallback line
            items.append((False, line, ""))
    return items


class DirectoryGridView(QWidget):
    """Clean grid/list presentation for directory entries with folder/file icons."""

    def __init__(self, items: list[tuple[bool, str, str]], theme, parent=None):
        super().__init__(parent)
        self.setObjectName("directoryGrid")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 8)
        layout.setSpacing(4)

        for is_dir, name, size in items:
            row = QHBoxLayout()
            row.setContentsMargins(0, 2, 0, 2)
            row.setSpacing(8)

            glyph = QLabel()
            if is_dir:
                glyph.setPixmap(icon("folder", 16, theme.orbit_accent).pixmap(16, 16))
            else:
                glyph.setPixmap(icon("file", 16, theme.muted).pixmap(16, 16))
            row.addWidget(glyph)

            name_label = QLabel(name)
            name_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            if is_dir:
                name_label.setStyleSheet(f"color: {theme.accent}; font-weight: 600;")
            else:
                name_label.setStyleSheet(f"color: {theme.text};")
            row.addWidget(name_label)

            row.addStretch(1)

            if size and size != "-":
                size_label = QLabel(size)
                size_label.setStyleSheet(f"color: {theme.muted}; font-size: 8.5pt;")
                row.addWidget(size_label)

            layout.addLayout(row)


class CommandBlockWidget(QFrame):
    """An individual command card with status, duration, hover toolbar, and output."""

    rerun_requested = Signal(str)

    def __init__(
        self,
        command: str,
        from_orbit: bool = False,
        theme_key: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.command = command
        self.from_orbit = from_orbit
        self.theme = get_theme(theme_key)
        self.output_text = ""
        self.is_collapsed = False
        self.success = True
        self.duration_seconds = 0.0

        self.setProperty("class", "commandBlock")
        self.setObjectName("commandBlock")

        self._setup_ui()
        self.set_running()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 10)
        main_layout.setSpacing(6)

        # Header bar
        self.header = QFrame()
        self.header.setObjectName("commandBlockHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Status icon
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(16, 16)
        header_layout.addWidget(self.status_icon)

        # Prompt symbol PROMPT_GLYPH
        self.prompt_label = QLabel("\u276f")
        self.prompt_label.setObjectName("commandBlockPrompt")
        self.prompt_label.setStyleSheet(f"color: {self.theme.accent}; font-weight: bold; font-size: 11pt;")
        header_layout.addWidget(self.prompt_label)

        # Command text
        self.command_label = QLabel(self.command)
        self.command_label.setObjectName("commandBlockText")
        self.command_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.command_label.setStyleSheet(f"color: {self.theme.text}; font-weight: 600; font-size: 10pt;")
        header_layout.addWidget(self.command_label)

        # Orbit badge
        if self.from_orbit:
            self.orbit_badge = QLabel("Orbit")
            self.orbit_badge.setObjectName("commandBlockOrbitBadge")
            self.orbit_badge.setToolTip("Command triggered by Orbit assistant")
            header_layout.addWidget(self.orbit_badge)

        header_layout.addStretch(1)

        # Duration label
        self.duration_label = QLabel("")
        self.duration_label.setObjectName("commandBlockDuration")
        self.duration_label.setStyleSheet(f"color: {self.theme.muted}; font-size: 8.5pt;")
        header_layout.addWidget(self.duration_label)

        # Hover toolbar
        self.toolbar = QWidget()
        toolbar_layout = QHBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(4)

        self.copy_cmd_btn = QPushButton()
        self.copy_cmd_btn.setIcon(icon("copy", 14))
        self.copy_cmd_btn.setProperty("class", "blockToolBtn")
        self.copy_cmd_btn.setToolTip("Copy command")
        self.copy_cmd_btn.setFixedSize(24, 24)
        self.copy_cmd_btn.clicked.connect(self._copy_command)
        toolbar_layout.addWidget(self.copy_cmd_btn)

        self.copy_out_btn = QPushButton()
        self.copy_out_btn.setIcon(icon("copy", 14))
        self.copy_out_btn.setProperty("class", "blockToolBtn")
        self.copy_out_btn.setToolTip("Copy output")
        self.copy_out_btn.setFixedSize(24, 24)
        self.copy_out_btn.clicked.connect(self._copy_output)
        toolbar_layout.addWidget(self.copy_out_btn)

        self.rerun_btn = QPushButton()
        self.rerun_btn.setIcon(icon("rerun", 14))
        self.rerun_btn.setProperty("class", "blockToolBtn")
        self.rerun_btn.setToolTip("Re-run command")
        self.rerun_btn.setFixedSize(24, 24)
        self.rerun_btn.clicked.connect(self._request_rerun)
        toolbar_layout.addWidget(self.rerun_btn)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setIcon(icon("chevron-down", 14))
        self.collapse_btn.setProperty("class", "blockToolBtn")
        self.collapse_btn.setToolTip("Collapse output")
        self.collapse_btn.setFixedSize(24, 24)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        toolbar_layout.addWidget(self.collapse_btn)

        header_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.header)

        # Body output area
        self.body_container = QWidget()
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(4, 4, 4, 4)
        self.body_layout.setSpacing(4)

        self.output_view = QTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setUndoRedoEnabled(False)
        self.output_view.setLineWrapMode(QTextEdit.NoWrap)
        self.output_view.setStyleSheet(
            f"background-color: transparent; border: none; color: {self.theme.output}; padding: 0px;"
        )
        self.output_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.output_view.document().setDocumentMargin(2)
        self.body_layout.addWidget(self.output_view)

        main_layout.addWidget(self.body_container)

    def set_running(self):
        self.status_icon.setPixmap(icon("spinner", 14, self.theme.accent).pixmap(14, 14))
        self.duration_label.setText("running…")
        self.copy_out_btn.setEnabled(False)

    def set_completed(self, output: str, success: bool = True, duration_seconds: float = 0.0):
        self.output_text = output
        self.success = success
        self.duration_seconds = duration_seconds

        # Duration formatting
        if duration_seconds < 1.0:
            dur_str = f"{int(duration_seconds * 1000)}ms"
        else:
            dur_str = f"{duration_seconds:.2f}s"
        self.duration_label.setText(dur_str)

        # Status icon
        if success:
            self.status_icon.setPixmap(icon("check", 14, self.theme.success).pixmap(14, 14))
        else:
            self.status_icon.setPixmap(icon("error", 14, self.theme.error).pixmap(14, 14))

        self.copy_out_btn.setEnabled(bool(output))

        # Check if output is directory listing
        if success and is_directory_listing(output):
            items = parse_directory_listing(output)
            # Replace text edit with clean directory grid
            self.output_view.hide()
            grid = DirectoryGridView(items, self.theme, self)
            self.body_layout.addWidget(grid)
        else:
            self.output_view.show()
            self.output_view.setPlainText(output)
            # Adjust height to content
            doc_height = int(self.output_view.document().size().height()) + 8
            self.output_view.setMaximumHeight(min(max(doc_height, 28), 450))
            if not success:
                self.output_view.setStyleSheet(
                    f"background-color: transparent; border: none; color: {self.theme.error}; padding: 0px;"
                )
            else:
                self.output_view.setStyleSheet(
                    f"background-color: transparent; border: none; color: {self.theme.output}; padding: 0px;"
                )

        if not output.strip():
            self.body_container.hide()

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        self.body_container.setVisible(not self.is_collapsed)
        if self.is_collapsed:
            self.collapse_btn.setIcon(icon("chevron-right", 14))
            self.collapse_btn.setToolTip("Expand output")
        else:
            self.collapse_btn.setIcon(icon("chevron-down", 14))
            self.collapse_btn.setToolTip("Collapse output")

    def _copy_command(self):
        QApplication.clipboard().setText(self.command)

    def _copy_output(self):
        if self.output_text:
            QApplication.clipboard().setText(self.output_text)

    def _request_rerun(self):
        self.rerun_requested.emit(self.command)


class CommandBlocksArea(QScrollArea):
    """Scrollable view containing command block cards."""

    rerun_command = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("commandBlocksArea")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.container = QWidget()
        self.container.setObjectName("commandBlocksContainer")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)
        self.layout.addStretch(1)

        self.setWidget(self.container)
        self.blocks: list[CommandBlockWidget] = []
        self._active_block: CommandBlockWidget | None = None

    def add_block(self, command: str, from_orbit: bool = False, theme_key: str | None = None) -> CommandBlockWidget:
        block = CommandBlockWidget(command, from_orbit, theme_key, self.container)
        block.rerun_requested.connect(self.rerun_command.emit)
        # Insert before stretch
        self.layout.insertWidget(self.layout.count() - 1, block)
        self.blocks.append(block)
        self._active_block = block
        self.scroll_to_bottom()
        return block

    def finish_active_block(self, output: str, success: bool = True, duration: float = 0.0):
        if self._active_block:
            self._active_block.set_completed(output, success, duration)
            self._active_block = None
            self.scroll_to_bottom()

    def scroll_to_bottom(self):
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def clear(self):
        self._active_block = None
        for block in self.blocks:
            self.layout.removeWidget(block)
            block.deleteLater()
        self.blocks.clear()

    def toPlainText(self) -> str:
        lines = []
        for block in self.blocks:
            lines.append(f"\u276f {block.command}")
            if block.output_text:
                lines.append(block.output_text)
        return "\n".join(lines)

    def highlight_command(self, command: str):
        """Scroll to and highlight a block by matching command text."""
        cmd_clean = command.strip().lower()
        for block in reversed(self.blocks):
            if block.command.strip().lower() == cmd_clean:
                self.ensureWidgetVisible(block)
                # Visual highlight ring
                theme = block.theme
                block.setStyleSheet(f"border: 2px solid {theme.orbit_accent}; border-radius: 8px;")
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1500, lambda b=block: b.setStyleSheet(""))
                break
