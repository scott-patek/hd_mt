from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def _set_macos_process_name(name: str) -> None:
    """Set process name via PyObjC so macOS menu/Cmd+Tab label is not 'python'."""
    try:
        from Foundation import NSProcessInfo  # type: ignore

        NSProcessInfo.processInfo().setProcessName_(name)
    except Exception:
        # Optional on non-macOS or when PyObjC is unavailable.
        return


def main() -> None:
    app = QApplication([])
    _set_macos_process_name("Half Deaf Mastering Tool")
    app.setApplicationDisplayName("Half Deaf Mastering Tool")
    app.setApplicationName("Half Deaf Mastering Tool")
    icon_path = Path(__file__).resolve().parent / "ui" / "assets" / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
