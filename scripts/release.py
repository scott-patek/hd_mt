#!/usr/bin/env python3
"""Cross-platform release helper for local and CI builds.

This script intentionally mirrors the shape used in the p6cc repo:
- macOS: produces a DMG
- Windows: produces an installer EXE (Inno Setup)
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
WINDOWS_PACKAGING_DIR = ROOT / "packaging" / "windows"

# Ensure imports resolve when script is run from CI shells.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.metadata import APP_NAME, APP_SLUG, APP_VERSION


class ReleaseError(RuntimeError):
    """Raised for predictable release/build failures."""


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def ensure_tools(*tool_names: str) -> None:
    missing = [tool for tool in tool_names if shutil.which(tool) is None]
    if missing:
        raise ReleaseError(f"Missing required tool(s): {', '.join(missing)}")


def clean_dirs() -> None:
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    shutil.rmtree(DIST_DIR, ignore_errors=True)


def fix_portaudio_bundling(app_bundle: Path) -> None:
    """Fix PortAudio bundling by extracting site-packages.zip so dylib can be loaded.
    
    py2app zips all site-packages including sounddevice's _sounddevice_data/, but
    dylib loading fails from inside a zip file. This function extracts site-packages.zip
    to a directory so sounddevice can find and load the PortAudio dylib.
    """
    import zipfile
    
    resources_dir = app_bundle / "Contents" / "Resources"
    
    # Find site-packages.zip for the current Python version
    zip_file = None
    for py_ver in ["3.13", "3.12", "3.11"]:
        candidate = resources_dir / "lib" / f"python{py_ver}" / "site-packages.zip"
        if candidate.exists():
            zip_file = candidate
            break
    
    if not zip_file:
        print("WARNING: site-packages.zip not found in any Python version directory")
        return
    
    # Extract to site-packages directory
    site_packages_dir = zip_file.parent / "site-packages"
    
    if site_packages_dir.exists():
        shutil.rmtree(site_packages_dir)
    
    site_packages_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Extracting {zip_file.name}...")
    with zipfile.ZipFile(zip_file, 'r') as zf:
        zf.extractall(site_packages_dir)
    
    # Delete the zip file so Python uses the extracted directory instead
    # This ensures compiled extensions (.so files) and dylibs can be found
    
    print(f"Extracted site-packages; PortAudio dylib should now be loadable")
    
    # Set DYLD_LIBRARY_PATH in plist so dylib can be found at runtime
    try:
        import plistlib
        plist_path = app_bundle / "Contents" / "Info.plist"
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f)
        # Point to the portaudio binaries directory
        plist['LSEnvironment'] = {'DYLD_LIBRARY_PATH': '@loader_path/../Resources/lib/python3.13/site-packages/_sounddevice_data/portaudio-binaries'}
        with open(plist_path, 'wb') as f:
            plistlib.dump(plist, f)
        print("Set DYLD_LIBRARY_PATH in plist")
    except Exception as e:
        print(f"Warning: Could not update plist: {e}")
    
    # Verify PortAudio dylib exists
    portaudio_dylib = site_packages_dir / "_sounddevice_data" / "portaudio-binaries" / "libportaudio.dylib"
    if portaudio_dylib.exists():
        print(f"✓ PortAudio dylib found")
    else:
        print(f"WARNING: PortAudio dylib not found at expected location")
        # Check if it's in a different location
        for dylib in site_packages_dir.rglob("libportaudio.dylib"):
            print(f"  Found: {dylib.relative_to(site_packages_dir)}")


def artifact_name_macos_dmg() -> str:
    return f"{APP_SLUG}-{APP_VERSION}-macos.dmg"


def artifact_name_windows_installer() -> str:
    return f"{APP_SLUG}-{APP_VERSION}-windows-setup.exe"


def write_metadata(path: Path) -> None:
    payload = {
        "name": APP_NAME,
        "slug": APP_SLUG,
        "version": APP_VERSION,
        "artifacts": {
            "macos_dmg": artifact_name_macos_dmg(),
            "windows_installer": artifact_name_windows_installer(),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote metadata to {path}")


def create_macos_executable_wrapper(app_bundle: Path) -> None:
    """Create a wrapper script for the macOS executable to set DYLD_LIBRARY_PATH."""
    macos_dir = app_bundle / "Contents" / "MacOS"
    original_exe = macos_dir / "Half Deaf Mastering Tool"
    wrapper_exe = macos_dir / "Half Deaf Mastering Tool.real"
    
    # Rename original executable to .real
    original_exe.rename(wrapper_exe)
    
    # Create wrapper script that sets DYLD_LIBRARY_PATH
    wrapper_script = '''#!/bin/bash
export DYLD_LIBRARY_PATH="${DYLD_LIBRARY_PATH:+$DYLD_LIBRARY_PATH:}$(cd "$(dirname "$0")" && pwd)/../Resources/lib/python3.13/site-packages/_sounddevice_data/portaudio-binaries"
exec "$(dirname "$0")/Half Deaf Mastering Tool.real" "$@"
'''
    original_exe.write_text(wrapper_script)
    original_exe.chmod(0o755)
    print("Created executable wrapper with DYLD_LIBRARY_PATH")
def build_macos_dmg() -> Path:
    if platform.system() != "Darwin":
        raise ReleaseError("macos-dmg can only run on macOS")

    ensure_tools("hdiutil")

    # py2app still uses setup.py in this project.
    run([sys.executable, "setup.py", "py2app"], cwd=ROOT)

    app_bundle = DIST_DIR / f"{APP_NAME}.app"
    if not app_bundle.exists():
        raise ReleaseError(f"Expected app bundle not found: {app_bundle}")

    # Post-build: Copy PortAudio dylib from sounddevice so it can be loaded at runtime
    # (not from inside a zip file, which would fail)
    fix_portaudio_bundling(app_bundle)
    create_macos_executable_wrapper(app_bundle)

    # Ensure filesystem changes are flushed before DMG creation (wrapper must be included in DMG)
    run(["sync"])

    dmg_path = DIST_DIR / artifact_name_macos_dmg()
    if dmg_path.exists():
        dmg_path.unlink()

    run(
        [
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
            "-srcfolder",
            str(app_bundle),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
    )

    print(f"Built {dmg_path}")
    return dmg_path


def build_windows_installer() -> Path:
    if platform.system() != "Windows":
        raise ReleaseError("windows-installer can only run on Windows")

    spec_file = WINDOWS_PACKAGING_DIR / "Half Deaf Mastering Tool-windows.spec"
    if not spec_file.exists():
        raise ReleaseError(f"Missing PyInstaller spec: {spec_file}")

    ensure_tools("pyinstaller")
    run(["pyinstaller", "--clean", "--noconfirm", str(spec_file)], cwd=ROOT)

    installer_script = WINDOWS_PACKAGING_DIR / "Half Deaf Mastering Tool.iss"
    if not installer_script.exists():
        raise ReleaseError(f"Missing Inno Setup script: {installer_script}")

    iscc = shutil.which("iscc")
    if iscc is None:
        raise ReleaseError("Inno Setup compiler (iscc) is required for windows-installer")

    out_base = f"{APP_SLUG}-{APP_VERSION}-windows-setup"
    run(
        [
            iscc,
            str(installer_script),
            f"/DMyAppVersion={APP_VERSION}",
            f"/DOutputBaseFilename={out_base}",
            f"/O{DIST_DIR}",
        ],
        cwd=ROOT,
    )

    installer_candidates = [
        DIST_DIR / f"{out_base}.exe",
        WINDOWS_PACKAGING_DIR / "dist" / f"{out_base}.exe",
    ]
    installer_path = next((p for p in installer_candidates if p.exists()), None)
    if installer_path is None:
        candidate_text = ", ".join(str(p) for p in installer_candidates)
        raise ReleaseError(f"Expected installer not found. Looked in: {candidate_text}")

    print(f"Built {installer_path}")
    return installer_path


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Release/build helper")
    p.add_argument(
        "command",
        choices=["metadata", "macos-dmg", "windows-installer", "all", "clean"],
        help="Operation to perform",
    )
    p.add_argument(
        "--metadata-path",
        default=str(DIST_DIR / "release-metadata.json"),
        help="Path for metadata output when command=metadata",
    )
    return p


def main() -> int:
    args = parser().parse_args()
    os.chdir(ROOT)

    try:
        if args.command == "clean":
            clean_dirs()
            return 0
        if args.command == "metadata":
            write_metadata(Path(args.metadata_path))
            return 0
        if args.command == "macos-dmg":
            build_macos_dmg()
            return 0
        if args.command == "windows-installer":
            build_windows_installer()
            return 0
        if args.command == "all":
            if platform.system() == "Darwin":
                build_macos_dmg()
            elif platform.system() == "Windows":
                build_windows_installer()
            else:
                raise ReleaseError("all is only supported on macOS or Windows")
            return 0
    except (subprocess.CalledProcessError, ReleaseError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())


