from __future__ import annotations

import os
import platform
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import ffmpeg
import numpy as np
import soundfile as sf

try:
    from pydub import AudioSegment
except Exception:  # pragma: no cover
    AudioSegment = None


AUDIO_EXTENSIONS = {".wav", ".flac", ".ogg", ".aiff", ".aif", ".mp3", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".m4v"}


def _ffmpeg_install_hint() -> str:
    if platform.system() == "Darwin":
        return "On macOS run: brew install ffmpeg"
    if platform.system() == "Windows":
        return "On Windows run: winget install ffmpeg (or choco install ffmpeg)"
    return "Install ffmpeg and ensure it is available on your PATH"


@dataclass
class AudioTrack:
    path: str
    samples: np.ndarray
    samplerate: int
    duration_s: float
    temp_artifacts: list[str] = field(default_factory=list)

    @property
    def channels(self) -> int:
        return 1 if self.samples.ndim == 1 else self.samples.shape[1]


class AudioLoader:
    def __init__(self) -> None:
        self._temp_artifacts: list[str] = []

    def load_media(self, file_path: str) -> AudioTrack:
        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = src.suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            wav_path = self._extract_audio_to_wav(file_path)
            samples, sr = self._read_with_soundfile(wav_path)
            return AudioTrack(
                path=file_path,
                samples=samples,
                samplerate=sr,
                duration_s=float(samples.shape[0] / sr),
                temp_artifacts=[wav_path],
            )

        if ext in AUDIO_EXTENSIONS:
            samples, sr = self._decode_audio_file(file_path)
            return AudioTrack(
                path=file_path,
                samples=samples,
                samplerate=sr,
                duration_s=float(samples.shape[0] / sr),
            )

        raise ValueError(f"Unsupported file type: {ext}")

    def cleanup(self) -> None:
        for path in list(self._temp_artifacts):
            try:
                os.remove(path)
            except OSError:
                pass
            finally:
                self._temp_artifacts.remove(path)

    def _decode_audio_file(self, file_path: str) -> tuple[np.ndarray, int]:
        try:
            return self._read_with_soundfile(file_path)
        except Exception:
            if AudioSegment is None:
                raise RuntimeError(
                    "Could not decode this file with soundfile. "
                    "Install pydub for fallback decoding and ensure ffmpeg is installed."
                )
            segment = AudioSegment.from_file(file_path)
            sr = int(segment.frame_rate)
            channels = int(segment.channels)
            raw = np.array(segment.get_array_of_samples(), dtype=np.float32)
            raw /= float(1 << (8 * segment.sample_width - 1))
            if channels > 1:
                raw = raw.reshape((-1, channels))
            return raw, sr

    def _read_with_soundfile(self, file_path: str) -> tuple[np.ndarray, int]:
        data, sr = sf.read(file_path, dtype="float32", always_2d=True)
        if data.shape[1] == 1:
            data = data[:, 0]
        return data, int(sr)

    def _extract_audio_to_wav(self, video_path: str) -> str:
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file.close()
        output_path = temp_file.name

        try:
            (
                ffmpeg.input(video_path)
                .output(output_path, acodec="pcm_s16le", ac=2, ar=48000)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as exc:
            msg = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
            raise RuntimeError(
                "Failed to extract audio from video. "
                f"{_ffmpeg_install_hint()}\n"
                f"Details: {msg}"
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"ffmpeg is not installed. {_ffmpeg_install_hint()}") from exc

        self._temp_artifacts.append(output_path)
        return output_path
