# Safe Mastering Assistant

Python desktop app for objective mastering guidance with strong low-end safety checks.

## Website

Project site (GitHub Pages):

- https://scott-patek.github.io/hd_mt/
- Source for site content: `docs/index.html`

## License and Security

- License: MIT ([LICENSE](LICENSE))
- Security policy: [SECURITY.md](SECURITY.md)

## Features
- Audio/video file loading from picker (WAV/MP3 and MP4/MOV support).
- Real-time playback, seek, and timing.
- Spectrum analyzer (log-frequency bars) + spectrogram.
- Peak hold, 0 dBFS line, clipping warnings.
- LUFS (integrated/short-term/momentary), sample peak, true peak, stereo correlation/width.
- Low-end diagnostics for Sub (20-60 Hz), Bass (60-120 Hz), Low-mid (120-350 Hz).
- Continuous coaching and manual Analyze report with trend history.
- Optional reference track with level-matched A/B comparison.
- System Output mode for listening to computer playback through a loopback-capable audio device.

## Prerequisites

**Python 3.11+** — [Download](https://www.python.org/downloads/) if needed.

**ffmpeg** — Install via your package manager:

- **macOS:** `brew install ffmpeg`
- **Windows:** `winget install ffmpeg` (or `choco install ffmpeg`)
- **Linux:** `apt install ffmpeg` (or equivalent)

## Quick Start

### macOS / Linux
```bash
python3 run.py
```

Or make it executable once:
```bash
chmod +x run
./run
```

### Windows
```powershell
python run.py
```

Or double-click `run.bat` in File Explorer.

## System Output mode

When you choose System Output, the app listens to a loopback-capable input instead of a microphone.

- **macOS:** install BlackHole, then route output through a Multi-Output Device that includes both BlackHole and your speakers/headphones.
- **Windows:** use Stereo Mix or another driver-provided loopback input if your audio device exposes one.
- The launcher prints the platform-specific setup hint before opening the app.

### macOS BlackHole setup (recommended)

Use this when you want to analyze browser/app playback (YouTube, Apple Music, Spotify, etc.) in System mode.

1. Install BlackHole 2ch:
	- `brew install --cask blackhole-2ch`
	- Or install from the BlackHole project website if you prefer a manual installer.
2. Open **Audio MIDI Setup** (Applications > Utilities).
3. Click the **+** button at bottom-left, then choose **Create Multi-Output Device**.
4. In the right panel, enable both:
	- **BlackHole 2ch**
	- Your physical output (**Mac Speakers**, headphones, or audio interface)
5. Optionally enable **Drift Correction** for the non-clock device if you hear timing drift.
6. In macOS sound output settings, choose the new **Multi-Output Device**.
7. In this app, choose **System** mode.

Important behavior:
- If macOS output is set to **BlackHole only**, you will capture audio but hear silence.
- If macOS output is set to the **Multi-Output Device**, audio is duplicated: you hear it and the app captures it.
- When finished using System mode, switch macOS output back to your normal speakers/headphones if desired.

---

## What the launcher does
1. Creates/activates `.venv` (virtual environment)
2. Installs Python dependencies from `requirements.txt`
3. Verifies ffmpeg is available
4. Launches the app from source

## Testing
```bash
# Create/activate venv and run tests
python3 run.py --test

# Or manually:
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux: .venv\Scripts\activate on Windows
pip install -r requirements.txt
pytest tests/ -q
```

## Versioning and Releases (GHA)

This repo uses a p6cc-style release model with three workflows:

- `.github/workflows/version-bump.yml` (manual): updates `APP_VERSION` in `app/metadata.py` and opens a PR.
- `.github/workflows/release-test.yml` (manual): builds prerelease DMG + Windows installer from any ref.
- `.github/workflows/release.yml` (tag-driven): builds and publishes production releases for `vX.Y.Z` tags.

### Version source of truth

`APP_VERSION` in `app/metadata.py` is the canonical version for packaging and releases.

### Production release flow

1. Run **Version Bump** workflow with target `X.Y.Z`.
2. Merge the generated PR.
3. Create and push tag `vX.Y.Z` on `main`.
4. Release workflow validates:
	- tag format (`vX.Y.Z`)
	- tag commit is on `main`
	- tag version equals `APP_VERSION`
5. Workflow publishes:
	- `half-deaf-mastering-tool-X.Y.Z-macos.dmg`
	- `half-deaf-mastering-tool-X.Y.Z-windows-setup.exe`
	- `SHA256SUMS.txt`

### Local release helpers

```bash
# Generate release metadata json
make release_metadata

# Build macOS app + dmg (macOS only)
make release_macos_dmg

# Build Windows installer exe (Windows only)
make release_windows_installer
```
