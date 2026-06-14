# Safe Mastering Assistant

Python desktop app for objective mastering guidance with strong low-end safety checks.

## Features
- Audio/video file loading from picker (WAV/MP3 and MP4/MOV support).
- Real-time playback, seek, and timing.
- Spectrum analyzer (log-frequency bars) + spectrogram.
- Peak hold, 0 dBFS line, clipping warnings.
- LUFS (integrated/short-term/momentary), sample peak, true peak, stereo correlation/width.
- Low-end diagnostics for Sub (20-60 Hz), Bass (60-120 Hz), Low-mid (120-350 Hz).
- Continuous coaching and manual Analyze report with trend history.
- Optional reference track with level-matched A/B comparison.

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
