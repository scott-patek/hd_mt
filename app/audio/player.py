from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal

from app.audio.audio_loader import AudioTrack


@dataclass
class PlaybackState:
    is_playing: bool = False
    position_s: float = 0.0


class AudioPlayer(QObject):
    chunk_available = Signal(object)
    position_changed = Signal(float)
    playback_stopped = Signal()
    playback_error = Signal(str)

    def __init__(self, block_size: int = 2048) -> None:
        super().__init__()
        self.block_size = block_size
        self.track: Optional[AudioTrack] = None
        self._stream: Optional[sd.OutputStream] = None
        self._cursor = 0
        self.state = PlaybackState()

    def load_track(self, track: AudioTrack, keep_position_s: float = 0.0) -> None:
        self.stop()
        self.track = track
        self.seek(keep_position_s)

    def play(self) -> None:
        if self.track is None:
            return
        if self.state.is_playing:
            return

        channels = self.track.channels
        try:
            self._stream = sd.OutputStream(
                samplerate=self.track.samplerate,
                channels=channels,
                dtype="float32",
                blocksize=self.block_size,
                callback=self._callback,
                finished_callback=self._on_finished,
            )
            self._stream.start()
            self.state.is_playing = True
        except Exception as exc:
            self.playback_error.emit(str(exc))

    def pause(self) -> None:
        if not self.state.is_playing:
            return
        self._close_stream()
        self.state.is_playing = False

    def stop(self) -> None:
        self._close_stream()
        self.state.is_playing = False
        self._cursor = 0
        self.state.position_s = 0.0
        self.position_changed.emit(0.0)
        self.playback_stopped.emit()

    def seek(self, position_s: float) -> None:
        if self.track is None:
            return
        clamped = max(0.0, min(position_s, self.track.duration_s))
        self._cursor = int(clamped * self.track.samplerate)
        self.state.position_s = clamped
        self.position_changed.emit(clamped)

    def set_block_size(self, block_size: int) -> None:
        self.block_size = block_size

    def _close_stream(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _on_finished(self) -> None:
        self.state.is_playing = False
        self.playback_stopped.emit()

    def _callback(self, outdata, frames, _time, status) -> None:
        if status:
            self.playback_error.emit(str(status))

        if self.track is None:
            outdata.fill(0)
            return

        samples = self.track.samples
        end = self._cursor + frames

        if samples.ndim == 1:
            chunk = samples[self._cursor:end]
            if len(chunk) < frames:
                padded = np.zeros(frames, dtype=np.float32)
                padded[: len(chunk)] = chunk
                chunk = padded
            outdata[:, 0] = chunk
        else:
            chunk = samples[self._cursor:end, :]
            if chunk.shape[0] < frames:
                padded = np.zeros((frames, samples.shape[1]), dtype=np.float32)
                padded[: chunk.shape[0], :] = chunk
                chunk = padded
            outdata[:, :] = chunk

        self._cursor = end
        self.state.position_s = min(self._cursor / self.track.samplerate, self.track.duration_s)
        self.position_changed.emit(self.state.position_s)
        self.chunk_available.emit(chunk.copy())

        if self._cursor >= samples.shape[0]:
            raise sd.CallbackStop
