from pathlib import Path
import sys
import ctypes
import ctypes.util

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, QTimer

from app.ui.main_window import MainWindow


def _set_macos_process_name(name: str) -> None:
    """Set process name so macOS menu/Cmd+Tab label shows app name instead of 'python'."""
    if not sys.platform.startswith("darwin"):
        return

    # Preferred path when available: updates process title early and reliably.
    try:
        import setproctitle  # type: ignore

        setproctitle.setproctitle(name)
        return
    except Exception:
        pass

    try:
        from Foundation import NSProcessInfo  # type: ignore

        NSProcessInfo.processInfo().setProcessName_(name)
        return
    except Exception:
        pass

    # Fallback for environments without PyObjC.
    try:
        libc_path = ctypes.util.find_library("c")
        if not libc_path:
            return
        libc = ctypes.CDLL(libc_path)
        setprogname = getattr(libc, "setprogname", None)
        if setprogname is None:
            return
        setprogname.argtypes = [ctypes.c_char_p]
        setprogname.restype = None
        setprogname(name.encode("utf-8"))
    except Exception:
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


def _force_macos_menu_title(name: str) -> None:
    """Force the first native macOS menu title to the app name (replaces 'python')."""
    if not sys.platform.startswith("darwin"):
        return

    try:
        from AppKit import NSApplication  # type: ignore

        app = NSApplication.sharedApplication()
        main_menu = app.mainMenu()
        if main_menu is None:
            return
        app_menu_item = main_menu.itemAtIndex_(0)
        if app_menu_item is not None:
            app_menu_item.setTitle_(name)
    except Exception:
        return


def main() -> None:
    app_name = "Half Deaf Mastering Tool"
    # Set app/process names before QApplication is created so macOS menu bar uses it.
    QCoreApplication.setApplicationName(app_name)
    if hasattr(QCoreApplication, "setApplicationDisplayName"):
        QCoreApplication.setApplicationDisplayName(app_name)
    _set_macos_process_name(app_name)
    _activate_macos_app()

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
    # Qt may recreate/refresh native menu shortly after show; apply title twice.
    QTimer.singleShot(0, lambda: _force_macos_menu_title(app_name))
    QTimer.singleShot(200, lambda: _force_macos_menu_title(app_name))
    app.exec()


if __name__ == "__main__":
    main()
