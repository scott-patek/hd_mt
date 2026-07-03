from pathlib import Path

from setuptools import setup

from app.metadata import APP_NAME, APP_VERSION


APP = ["run_app.py"]
ICON_PATH = Path("app/ui/assets/app_icon.png")

OPTIONS = {
    "argv_emulation": False,
    "iconfile": str(ICON_PATH) if ICON_PATH.exists() else None,
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleExecutable": APP_NAME,
        "CFBundleIdentifier": "com.halfdeaf.masteringtool",
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription": "This app needs microphone access for Live Input spectrum analysis and mastering guidance.",
    },
    "packages": [
        "numpy",
        "pyqtgraph",
        "scipy",
        "soundfile",
        "sounddevice",
        "pydub",
        "ffmpeg",
        "colorama",
        "app",
    ],
    # Exclude unnecessary test data and debug symbols to reduce bundle size
    "excludes": [
        "scipy.tests",
        "numpy.tests",
        "matplotlib.tests",
        "test",
        "tests",
    ],
    "strip": True,
    "semi_standalone": True,
}


setup(
    app=APP,
    name=APP_NAME,
    version=APP_VERSION,
    options={"py2app": OPTIONS},
)
