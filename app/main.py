from pathlib import Path
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def _set_macos_process_name(name: str) -> None:
    """Set process name so macOS menu/Cmd+Tab label shows app name instead of 'python'."""
    try:
        from Foundation import NSProcessInfo  # type: ignore

        NSProcessInfo.processInfo().setProcessName_(name)
    except Exception:
        # Not on macOS or PyObjC unavailable
        return


def _activate_macos_app() -> None:
    """Ensure the app is a regular foreground macOS app with a native menu bar."""
    if not sys.platform.startswith("darwin"):
        return

    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyRegular  # type: ignore

        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyRegular)
    except Exception:
        return


def main() -> None:
    app = QApplication([])
    _set_macos_process_name("Half Deaf Mastering Tool")
    _activate_macos_app()
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
