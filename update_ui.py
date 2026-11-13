"""update_ui.py - Background QThread workers and UI controller for RiftShell updates.

Built natively with PySide6 for smooth non-blocking background operations.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from updater import check_update, download_update, apply_update


class CheckWorker(QThread):
    """Worker thread that fetches the update manifest in the background."""
    found = Signal(dict)
    none = Signal()

    def run(self) -> None:
        manifest = check_update()
        if manifest:
            self.found.emit(manifest)
        else:
            self.none.emit()


class DownloadWorker(QThread):
    """Worker thread that downloads and verifies the update package."""
    progress = Signal(int)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, manifest: dict, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.manifest = manifest
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            path = download_update(
                self.manifest,
                on_progress=self.progress.emit,
                is_cancelled=lambda: self._cancelled,
            )
            self.done.emit(path)
        except Exception as exc:
            self.failed.emit(str(exc))


class UpdateController(QObject):
    """Coordinates checking, prompting, downloading, and applying updates."""

    def __init__(self, window: QObject | None = None) -> None:
        super().__init__(window)
        self.window = window
        self.check_worker: CheckWorker | None = None
        self.download_worker: DownloadWorker | None = None
        self.progress_dialog: QProgressDialog | None = None
        self._silent: bool = True

    def check(self, silent: bool = True) -> None:
        """Start a background update check."""
        self._silent = silent
        if self.check_worker and self.check_worker.isRunning():
            return

        self.check_worker = CheckWorker(self)
        self.check_worker.found.connect(self._on_update_found)
        self.check_worker.none.connect(self._on_update_none)
        self.check_worker.start()

    def _on_update_found(self, manifest: dict) -> None:
        version = manifest.get("version", "")
        notes = manifest.get("notes", "No release notes provided.")
        msg = (
            f"A new version of RiftShell (v{version}) is available.\n\n"
            f"Release notes:\n{notes}\n\n"
            "Update now?"
        )
        reply = QMessageBox.question(
            self.window,
            "Update Available",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._start_download(manifest)

    def _on_update_none(self) -> None:
        if not self._silent:
            QMessageBox.information(
                self.window,
                "RiftShell Update",
                "You are on the latest version.",
            )

    def _start_download(self, manifest: dict) -> None:
        version = manifest.get("version", "")
        self.progress_dialog = QProgressDialog(
            f"Downloading RiftShell v{version}...",
            "Cancel",
            0,
            100,
            self.window,
        )
        self.progress_dialog.setWindowTitle("Updating RiftShell")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()

        self.download_worker = DownloadWorker(manifest, self)
        self.download_worker.progress.connect(self.progress_dialog.setValue)
        self.download_worker.done.connect(self._on_download_done)
        self.download_worker.failed.connect(self._on_download_failed)
        self.progress_dialog.canceled.connect(self._on_download_canceled)
        self.download_worker.start()

    def _on_download_canceled(self) -> None:
        if self.download_worker:
            self.download_worker.cancel()

    def _on_download_done(self, path: str) -> None:
        if self.progress_dialog:
            self.progress_dialog.close()
        try:
            apply_update(path)
            QApplication.quit()
        except Exception as exc:
            QMessageBox.warning(
                self.window,
                "Update Error",
                f"Could not apply update:\n{exc}",
            )

    def _on_download_failed(self, msg: str) -> None:
        if self.progress_dialog:
            self.progress_dialog.close()
        if "cancelled by user" in msg.lower():
            return
        QMessageBox.warning(
            self.window,
            "Update Failed",
            f"Update download failed:\n{msg}",
        )
