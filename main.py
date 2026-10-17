import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    if sys.platform == "win32":
        import ctypes

        # Keep RiftShell's taskbar identity separate from the Python launcher.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RiftShell.Orbit")

    app = QApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "assets" / "icon.ico"
    icon = QIcon(str(icon_path))
    app.setWindowIcon(icon)
    window = MainWindow()
    # Give the native top-level window its own icon for the Windows taskbar.
    window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
