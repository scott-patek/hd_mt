from pathlib import Path
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from app.macos_identity import APP_NAME, bootstrap_macos_app_identity, reassert_macos_app_identity
from app.ui.main_window import MainWindow


def main() -> None:
    app_name = APP_NAME
    # Set names before QApplication is created so native macOS menus resolve correctly.
    bootstrap_macos_app_identity(app_name)

    qt_argv = [app_name, *sys.argv[1:]]
    app = QApplication(qt_argv)
    if hasattr(app, "setApplicationDisplayName"):
        app.setApplicationDisplayName(app_name)
    app.setApplicationName(app_name)
    icon_path = Path(__file__).resolve().parent / "ui" / "assets" / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    # Native menu can refresh during first show; reassert in queued startup ticks.
    QTimer.singleShot(0, lambda: reassert_macos_app_identity(app_name))
    QTimer.singleShot(200, lambda: reassert_macos_app_identity(app_name))
    QTimer.singleShot(700, lambda: reassert_macos_app_identity(app_name))
    app.exec()


if __name__ == "__main__":
    main()
