from pathlib import Path

from setuptools import setup


APP = ["run_app.py"]
APP_NAME = "Half Deaf Mastering Tool"
ICON_PATH = Path("app/ui/assets/app_icon.png")

OPTIONS = {
    "argv_emulation": False,
    "iconfile": str(ICON_PATH) if ICON_PATH.exists() else None,
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleExecutable": APP_NAME,
        "CFBundleIdentifier": "com.halfdeaf.masteringtool",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
    },
    "packages": [
        "numpy",
        "pyqtgraph",
        "scipy",
        "soundfile",
        "sounddevice",
        "pydub",
        "ffmpeg",
        "app",
    ],
}


setup(
    app=APP,
    name=APP_NAME,
    options={"py2app": OPTIONS},
)
