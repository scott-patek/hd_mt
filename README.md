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

## macOS prerequisite
Install ffmpeg if needed:

```bash
brew install ffmpeg
```

## Run
```bash
make venv
make install
make run
```

## Test
```bash
make test
```
