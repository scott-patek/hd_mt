from __future__ import annotations

import ctypes
import ctypes.util
import sys

from PySide6.QtCore import QCoreApplication


APP_NAME = "Half Deaf Mastering Tool"


def _is_macos() -> bool:
    return sys.platform.startswith("darwin")


def _set_macos_process_name(name: str) -> None:
    if not _is_macos():
        return

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
    if not _is_macos():
        return

    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyRegular  # type: ignore

        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyRegular)
    except Exception:
        return


def _force_macos_menu_title(name: str) -> None:
    if not _is_macos():
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


def set_qt_app_name(name: str) -> None:
    QCoreApplication.setApplicationName(name)
    if hasattr(QCoreApplication, "setApplicationDisplayName"):
        QCoreApplication.setApplicationDisplayName(name)


def bootstrap_macos_app_identity(name: str) -> None:
    # Run before QApplication creation.
    set_qt_app_name(name)
    _set_macos_process_name(name)
    _activate_macos_app()


def reassert_macos_app_identity(name: str) -> None:
    # Reapply on known native menu refresh boundaries (startup/dialog return).
    set_qt_app_name(name)
    _set_macos_process_name(name)
    _force_macos_menu_title(name)
