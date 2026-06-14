"""Live audio input capture via the system default microphone/input device."""

from __future__ import annotations

import collections

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, QTimer, Signal

#: Sample rate for live capture (matches most modern audio hardware).
LIVE_SAMPLERATE: int = 48_000
#: Input channels (stereo).
LIVE_CHANNELS: int = 2
#: Block size in frames (~42 ms at 48 kHz).
LIVE_BLOCK_SIZE: int = 2_048
#: RMS threshold to transition LISTENING → CAPTURING (~-40 dBFS).
LIVE_THRESHOLD_RMS: float = 0.01


class LiveInputCapture(QObject):
    """Captures audio from the default system input in real time.

    Mirrors AudioPlayer's Qt signal API so MainWindow can swap sources
    transparently.  There is no Pause — Stop resets capture.

    State machine::

        idle ──play()──► listening ──threshold crossed──► capturing ──stop()──► idle
    """

    chunk_available = Signal(object)   # np.ndarray (stereo float32, LIVE_CHANNELS ch)
    position_changed = Signal(float)   # elapsed seconds since capture threshold crossed
    playback_stopped = Signal()
    playback_error = Signal(str)
    state_changed = Signal(str)        # "idle" | "listening" | "capturing"

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state: str = "idle"
        self._stream: sd.InputStream | None = None
        self._elapsed_s: float = 0.0

        # Thread-safe queue: audio thread appends, main thread drains.
        self._chunk_queue: collections.deque[np.ndarray] = collections.deque(maxlen=128)
        # Flag written on audio thread, consumed on main thread (GIL-safe bool assign).
        self._pending_capturing: bool = False

        # Drain timer: runs on Qt main thread, delivers chunks every ~20 ms.
        self._drain_timer = QTimer(self)
        self._drain_timer.setInterval(20)
        self._drain_timer.timeout.connect(self._drain_queue)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        """Current state: 'idle', 'listening', or 'capturing'."""
        return self._state

    def play(self) -> None:
        """Open the default input and enter the LISTENING state."""
        if self._state != "idle":
            return
        self._elapsed_s = 0.0
        self._chunk_queue.clear()
        self._pending_capturing = False
        try:
            self._stream = sd.InputStream(
                samplerate=LIVE_SAMPLERATE,
                channels=LIVE_CHANNELS,
                dtype="float32",
                blocksize=LIVE_BLOCK_SIZE,
                callback=self._sd_callback,
            )
            self._stream.start()
        except Exception as exc:
            self._stream = None
            self.playback_error.emit(str(exc))
            return
        self._state = "listening"
        self._drain_timer.start()
        self.state_changed.emit("listening")

    def stop(self) -> None:
        """Stop capture and return to IDLE."""
        self._drain_timer.stop()
        stream = self._stream
        self._stream = None
        was_active = self._state != "idle"
        self._state = "idle"
        self._chunk_queue.clear()
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        if was_active:
            self.playback_stopped.emit()
            self.state_changed.emit("idle")

    # ------------------------------------------------------------------
    # PortAudio audio-thread callback — only queues data, no Qt calls
    # ------------------------------------------------------------------

    def _sd_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        if self._state == "listening":
            mono = indata[:, 0] if indata.ndim > 1 else indata.ravel()
            rms = float(np.sqrt(np.mean(mono * mono)))
            if rms > LIVE_THRESHOLD_RMS:
                self._state = "capturing"
                self._pending_capturing = True
                self._chunk_queue.append(indata.copy())
        elif self._state == "capturing":
            self._chunk_queue.append(indata.copy())
            self._elapsed_s += frames / LIVE_SAMPLERATE

    # ------------------------------------------------------------------
    # Main-thread drain — called by QTimer every 20 ms
    # ------------------------------------------------------------------

    def _drain_queue(self) -> None:
        # Emit state transition if audio thread flagged one
        if self._pending_capturing:
            self._pending_capturing = False
            self.state_changed.emit("capturing")

        if self._state != "capturing":
            return

        while self._chunk_queue:
            chunk = self._chunk_queue.popleft()
            self.chunk_available.emit(chunk)

        self.position_changed.emit(self._elapsed_s)
