"""
py2app hook for sounddevice.

Extracts sounddevice's vendored PortAudio binaries from the venv and places them
outside the zip file so sounddevice can load them at runtime. This fixes the
"OSError: cannot load library .../libportaudio.dylib" crash when launching the
bundled app.

The issue: sounddevice bundles PortAudio dylibs in _sounddevice_data/, but py2app
zips them into python313.zip, and dylib loading fails from inside a zip.

Solution: Extract the dylib to Contents/Resources/ where it can be loaded.
"""

import os
import sys
import shutil
from pathlib import Path

def check_hook_conditions(cmd, mf):
    """
    Return True if sounddevice is imported.
    This hook only runs if sounddevice is in the app.
    """
    return mf.findNode("sounddevice") is not None

def hook(cmd, mf):
    """
    Main hook function called by py2app.
    Extracts PortAudio dylibs from sounddevice package to app bundle Resources.
    """
    try:
        import sounddevice
    except ImportError:
        print("[hook-sounddevice] sounddevice not found, skipping hook")
        return
    
    # Find sounddevice's _sounddevice_data directory
    sounddevice_root = Path(sounddevice.__file__).parent
    portaudio_src = sounddevice_root / "_sounddevice_data" / "portaudio-binaries"
    
    if not portaudio_src.exists():
        print(f"[hook-sounddevice] WARNING: PortAudio binaries not found at {portaudio_src}")
        print(f"[hook-sounddevice] sounddevice location: {sounddevice_root}")
        print(f"[hook-sounddevice] Listing _sounddevice_data contents:")
        sounddevice_data_dir = sounddevice_root / "_sounddevice_data"
        if sounddevice_data_dir.exists():
            for item in sounddevice_data_dir.iterdir():
                print(f"  - {item.name}")
        return
    
    # py2app creates Resources dir in the app bundle
    # The path depends on build stage, but we can infer from cmd structure
    # For py2app, the bundle goes to dist/APPNAME.app/Contents/Resources/
    if hasattr(cmd, 'dist_dir'):
        dist_dir = Path(cmd.dist_dir)
    else:
        dist_dir = Path("dist")
    
    # Find the .app bundle
    app_bundle = None
    if dist_dir.exists():
        for item in dist_dir.glob("*.app"):
            app_bundle = item
            break
    
    if app_bundle is None:
        print(f"[hook-sounddevice] App bundle not found in {dist_dir}, will copy after build")
        return
    
    resources_dir = app_bundle / "Contents" / "Resources"
    resources_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy PortAudio binaries to Resources
    portaudio_dest = resources_dir / "portaudio-binaries"
    if portaudio_dest.exists():
        shutil.rmtree(portaudio_dest)
    
    shutil.copytree(portaudio_src, portaudio_dest)
    print(f"[hook-sounddevice] Extracted PortAudio binaries to {portaudio_dest}")
