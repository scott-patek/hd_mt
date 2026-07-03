"""
py2app hook for sounddevice PortAudio library bundling.

This hook auto-detects the system PortAudio dylib and includes it in the
app bundle under Contents/Frameworks/, ensuring sounddevice can find and
load PortAudio at runtime.

Supports both Intel and Apple Silicon Macs via Homebrew or pkg-config.
"""

import os
import subprocess
from pathlib import Path


def get_binaries():
    """
    Locate and return the PortAudio dylib for bundling.
    
    Returns:
        list: List of (source, dest) tuples for py2app to copy into the bundle.
              Dest is 'Contents/Frameworks' so dylib is placed in the frameworks folder.
    
    Raises:
        RuntimeError: If PortAudio library cannot be found anywhere.
    """
    
    # Try pkg-config first (most portable)
    try:
        result = subprocess.run(
            ['pkg-config', '--variable=libdir', 'portaudio-2.0'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            libdir = result.stdout.strip()
            dylib_path = os.path.join(libdir, 'libportaudio.dylib')
            if os.path.exists(dylib_path):
                return [(dylib_path, 'Contents/Frameworks')]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Try Homebrew paths (Intel x86_64)
    homebrew_intel = '/usr/local/opt/portaudio/lib/libportaudio.dylib'
    if os.path.exists(homebrew_intel):
        return [(homebrew_intel, 'Contents/Frameworks')]
    
    # Try Homebrew paths (Apple Silicon arm64)
    homebrew_apple_silicon = '/opt/homebrew/opt/portaudio/lib/libportaudio.dylib'
    if os.path.exists(homebrew_apple_silicon):
        return [(homebrew_apple_silicon, 'Contents/Frameworks')]
    
    # PortAudio not found anywhere
    raise RuntimeError(
        "PortAudio library not found during app bundling.\n\n"
        "Please install PortAudio:\n"
        "  brew install portaudio\n\n"
        "Alternatively, ensure pkg-config can locate portaudio-2.0:\n"
        "  pkg-config --variable=libdir portaudio-2.0"
    )
