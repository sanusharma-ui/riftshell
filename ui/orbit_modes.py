"""Desktop editor for user-defined Orbit profiles; saving affects the next task."""
from dataclasses import replace

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
)

from ai.desktop_settings import load_mode_preferences
from ai.modes import MODE_LIMITS, OrbitMode, decode_modes, encode_modes


class OrbitModesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Orbit Execution Modes")
        self.setMinimumWidth(500)
        modes, selected = load_mode_preferences()
        self.modes = list(modes)
        self.index = -1

        eyebrow = QLabel("◈  ORBIT EXECUTION MODES")
        eyebrow.setObjectName("eyebrow")

        note_card = QFrame()
        note_card.setObjectName("infoCard")
        note_layout = QVBoxLayout(note_card)
        note_layout.setContentsMargins(12, 10, 12, 10)
        note = QLabel(
            "Configure token budgets, context depth, and autonomous planning steps for Orbit AI.\n"
            "Duplicate any profile to create a custom workflow. Changes apply to new tasks."
        )
        note.setWordWrap(True)
        note_layout.addWidget(note)

        self.selector = QComboBox()
        self.name = QLineEdit()
        self.fields = {}
        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 6, 0, 6)
        form.addRow("Active profile", self.selector)
        form.addRow("Profile name", self.name)
        labels = {
            "prompt_tokens": "Prompt budget (est. tokens)",
            "output_tokens": "Maximum output tokens",
            "history_turns": "Recent conversation turns",
            "max_files": "Max files per task",
            "file_chars": "Characters per file",
            "max_steps": "Max planning / action steps",
            "inspection_passes": "Inspection passes per task",
        }
        for key, (low, high) in MODE_LIMITS.items():
            field = QSpinBox()
            field.setRange(low, high)
            self.fields[key] = field
            form.addRow(labels[key], field)
        self.compact = QCheckBox("Use compact system prompt and concise shell answers")
        form.addRow("Response style", self.compact)

        duplicate = QPushButton("+  Duplicate Profile")
        duplicate.clicked.connect(self._duplicate)
        remove = QPushButton("Remove Profile")
        remove.setObjectName("dismissButton")
        remove.clicked.connect(self._remove)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(duplicate)
        row.addWidget(remove)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        if save_btn := buttons.button(QDialogButtonBox.Save):
            save_btn.setObjectName("primaryButton")
            save_btn.setText("Save Modes")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(eyebrow)
        layout.addWidget(note_card)
        layout.addLayout(form)
        layout.addLayout(row)
        layout.addSpacing(4)
        layout.addWidget(buttons)

        self.selector.currentIndexChanged.connect(self._select)
        self._refresh(next(i for i, mode in enumerate(modes) if mode == selected))

    def _stash(self):
        if self.index < 0:
            return
        values = {key: field.value() for key, field in self.fields.items()}
        values.update(name=self.name.text().strip(), compact_prompt=self.compact.isChecked())
        self.modes[self.index] = OrbitMode(**values)

    def _select(self, index):
        self._stash()
        self.index = index
        mode = self.modes[index]
        self.name.setText(mode.name)
        for key, field in self.fields.items():
            field.setValue(getattr(mode, key))
        self.compact.setChecked(mode.compact_prompt)

    def _refresh(self, index):
        self.index = -1
        self.selector.blockSignals(True)
        self.selector.clear()
        self.selector.addItems([mode.name for mode in self.modes])
        self.selector.setCurrentIndex(index)
        self.selector.blockSignals(False)
        self._select(index)

    def _duplicate(self):
        self._stash()
        if len(self.modes) >= 20:
            return
        name = "Custom"
        number = 2
        while name.casefold() in {mode.name.casefold() for mode in self.modes}:
            name = f"Custom {number}"
            number += 1
        self.modes.append(replace(self.modes[self.index], name=name))
        self._refresh(len(self.modes) - 1)

    def _remove(self):
        if len(self.modes) > 1:
            self.modes.pop(self.index)
            self._refresh(0)

    def _save(self):
        self._stash()
        try:
            modes = decode_modes(encode_modes(tuple(self.modes)))
        except ValueError as exc:
            QMessageBox.warning(self, "Orbit modes", str(exc))
            return
        settings = QSettings("RiftShell", "RiftShell")
        settings.setValue("ai/modes", encode_modes(modes))
        settings.setValue("ai/mode", modes[self.index].name)
        settings.sync()
        self.accept()
