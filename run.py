#!/usr/bin/env python3
"""
Cross-platform app launcher: creates venv, installs deps, runs app.
Works on macOS, Windows, and Linux.
"""

import os
import sys
import subprocess
import venv
from pathlib import Path


def run_command(cmd, **kwargs):
    """Run a command and exit on failure."""
    result = subprocess.run(cmd, shell=isinstance(cmd, str), **kwargs)
    if result.returncode != 0:
        sys.exit(result.returncode)


def check_ffmpeg():
    """Check if ffmpeg is installed; print platform-specific guidance if not."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def get_ffmpeg_hint():
    """Return platform-specific ffmpeg installation guidance."""
    if sys.platform == "darwin":
        return "brew install ffmpeg"
    elif sys.platform == "win32":
        return "winget install ffmpeg  (or: choco install ffmpeg)"
    else:
        return "apt install ffmpeg  (or equivalent for your distro)"


def get_system_output_hint():
    """Return platform-specific system-output setup guidance."""
    if sys.platform == "darwin":
        return (
            "Install BlackHole, create a Multi-Output Device with BlackHole + your "
            "speakers/headphones, then set macOS output to that device for System mode."
        )
    if sys.platform == "win32":
        return (
            "Enable a loopback-capable input such as Stereo Mix if your audio driver offers it, "
            "then choose it in the app's System mode."
        )
    return (
        "Use a loopback-capable input device if your platform exposes one, then choose it in the app's System mode."
    )


def main():
    repo_root = Path(__file__).parent
    venv_path = repo_root / ".venv"

    print("Half Deaf Mastering Tool")
    print("=" * 40)

    # 1. Create venv if missing
    if not venv_path.exists():
        print("\n📦 Creating virtual environment...")
        venv.create(venv_path, with_pip=True)
        print(f"   ✓ Created at {venv_path}")
    else:
        print(f"\n✓ Using existing venv at {venv_path}")

    # 2. Get platform-specific Python/pip paths
    if sys.platform == "win32":
        python_bin = venv_path / "Scripts" / "python.exe"
        pip_bin = venv_path / "Scripts" / "pip.exe"
    else:
        python_bin = venv_path / "bin" / "python"
        pip_bin = venv_path / "bin" / "pip"

    # 3. Install dependencies
    print("\n📚 Installing dependencies...")
    run_command([str(pip_bin), "install", "-q", "--upgrade", "pip"])
    run_command([str(pip_bin), "install", "-q", "-r", str(repo_root / "requirements.txt")])
    print("   ✓ Dependencies installed")

    # 4. Check ffmpeg
    print("\n🔊 Checking ffmpeg...")
    if check_ffmpeg():
        print("   ✓ ffmpeg is available")
    else:
        print(f"\n   ⚠️  ffmpeg not found.")
        print(f"   Install it: {get_ffmpeg_hint()}")
        sys.exit(1)

    # 4b. Print system-output guidance.
    print("\n🎧 System Output mode setup:")
    print(f"   {get_system_output_hint()}")

    # 5. Launch app
    print("\n🎵 Launching app...\n")
    os.chdir(repo_root)

    if sys.platform == "darwin":
        # On macOS, launch detached so the shell prompt returns immediately.
        subprocess.Popen(
            ["Half Deaf Mastering Tool", "run_app.py"],
            executable=str(python_bin),
            cwd=str(repo_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print("   ✓ App launched in background")
        return

    # Always run from source with the active venv.
    # This avoids stale dist/app-bundle environments and keeps dependency behavior consistent.
    argv0 = str(python_bin)
    if sys.platform == "darwin":
        argv0 = "Half Deaf Mastering Tool"
    os.execv(str(python_bin), [argv0, "run_app.py"])


if __name__ == "__main__":
    main()
