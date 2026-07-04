import os
import sys

def _configure_bundled_runtime() -> None:
    app_resources = os.path.dirname(os.path.abspath(__file__))
    lib_dir = os.path.join(app_resources, "lib")

    if not os.path.isdir(lib_dir):
        return

    python_lib_dir = None
    for entry in sorted(os.listdir(lib_dir), reverse=True):
        candidate = os.path.join(lib_dir, entry)
        if entry.startswith("python3.") and os.path.isdir(candidate):
            python_lib_dir = candidate
            break

    if not python_lib_dir:
        return

    if python_lib_dir in sys.path:
        sys.path.remove(python_lib_dir)
    sys.path.insert(0, python_lib_dir)

    portaudio_dir = os.path.join(python_lib_dir, "_sounddevice_data", "portaudio-binaries")
    if os.path.isdir(portaudio_dir):
        current = os.environ.get("DYLD_LIBRARY_PATH", "")
        os.environ["DYLD_LIBRARY_PATH"] = portaudio_dir if not current else f"{portaudio_dir}:{current}"


_configure_bundled_runtime()

from app.main import main


if __name__ == "__main__":
    main()
