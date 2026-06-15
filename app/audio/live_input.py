"""Live audio capture via microphone or system-audio loopback devices."""

from __future__ import annotations

import collections
import platform

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, QTimer, Signal

#: Sample rate for live capture (matches most modern audio hardware).
LIVE_SAMPLERATE: int = 48_000
#: Input channels (stereo).
LIVE_CHANNELS: int = 2
#: Block size in frames (~42 ms at 48 kHz).
LIVE_BLOCK_SIZE: int = 2_048
#: RMS threshold to transition LISTENING → CAPTURING (~-50 dBFS).
LIVE_THRESHOLD_RMS: float = 0.003


WINDOWS_SYSTEM_CAPTURE_HINTS: tuple[str, ...] = (
    "stereo mix",
    "what u hear",
    "waveout mix",
    "mixed output",
    "loopback",
)


def find_system_capture_device(platform_name: str | None = None) -> int | str | None:
    """Return a capture device suited for system-audio input on the host OS."""
    system_name = (platform_name or platform.system()).lower()
    if system_name.startswith("darwin"):
        hints = ("blackhole",)
    elif system_name.startswith("win"):
        hints = WINDOWS_SYSTEM_CAPTURE_HINTS
    else:
        hints = ("blackhole", "stereo mix", "what u hear", "loopback")

    for index, info in enumerate(sd.query_devices()):
        if info["max_input_channels"] <= 0:
            continue
        device_name = str(info["name"]).lower()
        if any(hint in device_name for hint in hints):
            return index

    return None


def system_capture_setup_hint(platform_name: str | None = None) -> str:
    """Return user-facing setup guidance for system-audio capture."""
    system_name = (platform_name or platform.system()).lower()
    if system_name.startswith("darwin"):
        return (
            "Install BlackHole. In Audio MIDI Setup, create a Multi-Output Device "
            "with both BlackHole and your speakers/headphones, then set macOS output "
            "to that Multi-Output Device."
        )
    if system_name.startswith("win"):
        return (
            "Use the built-in Windows playback capture path. Enable Stereo Mix or "
            "another loopback-capable capture device, then select the intended "
            "Windows playback device in the app."
        )
    return (
        "Configure a loopback-capable system-audio device for this platform, then "
        "return to the app and select System Output again."
    )


class LiveInputCapture(QObject):
    """Captures audio from a live input source in real time.

    Mirrors AudioPlayer's Qt signal API so MainWindow can swap sources
    transparently. There is no Pause — Stop resets capture.

    When possible, opens a duplex stream and monitors captured input to the
    default output so users can hear the live signal.

    State machine::

        idle ──play()──► listening ──threshold crossed──► capturing ──stop()──► idle
    """

    chunk_available = Signal(object)   # np.ndarray (stereo float32, LIVE_CHANNELS ch)
    position_changed = Signal(float)   # elapsed seconds since capture threshold crossed
    playback_stopped = Signal()
    playback_error = Signal(str)
    state_changed = Signal(str)        # "idle" | "listening" | "capturing"

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        device_query: int | str | None = None,
        monitoring_enabled: bool = True,
        capture_label: str = "live input",
        setup_hint: str | None = None,
        allow_fallback_to_default: bool = True,
    ) -> None:
        super().__init__(parent)
        self._state: str = "idle"
        self._stream: sd.InputStream | sd.Stream | None = None
        self._elapsed_s: float = 0.0
        self._capture_channels: int = LIVE_CHANNELS
        self._samplerate: int = LIVE_SAMPLERATE
        self._monitoring_enabled: bool = monitoring_enabled
        self._device_query: int | str | None = device_query
        self._capture_label: str = capture_label
        self._setup_hint: str | None = setup_hint
        self._allow_fallback_to_default: bool = allow_fallback_to_default

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

    @property
    def device_query(self) -> int | str | None:
        return self._device_query

    def has_capture_device(self) -> bool:
        return self._device_query is not None

    @property
    def samplerate(self) -> int:
        return self._samplerate

    def _selected_samplerate(self) -> int:
        if self._device_query is None:
            return LIVE_SAMPLERATE
        try:
            info = sd.query_devices(self._device_query)
        except Exception:
            return LIVE_SAMPLERATE
        device_rate = int(info.get("default_samplerate") or LIVE_SAMPLERATE)
        return device_rate if device_rate > 0 else LIVE_SAMPLERATE

    def set_device_query(self, device_query: int | str | None) -> None:
        self._device_query = device_query

    def setup_message(self) -> str:
        if self._setup_hint:
            return self._setup_hint
        return f"Select a capture device for {self._capture_label}."

    def play(self) -> None:
        """Open the configured input and enter the LISTENING state."""
        if self._state != "idle":
            return
        if self._device_query is None and not self._allow_fallback_to_default:
            self.playback_error.emit(self.setup_message())
            return
        self._samplerate = self._selected_samplerate()
        self._elapsed_s = 0.0
        self._chunk_queue.clear()
        self._pending_capturing = False
        open_errors: list[str] = []
        self._stream = None
        for channels in (LIVE_CHANNELS, 1):
            # First try duplex monitoring (input -> output) so live mode is audible.
            if self._monitoring_enabled:
                try:
                    self._stream = sd.Stream(
                        samplerate=self._samplerate,
                        channels=(channels, channels),
                        dtype="float32",
                        blocksize=LIVE_BLOCK_SIZE,
                        device=self._device_query,
                        callback=self._sd_duplex_callback,
                    )
                    self._stream.start()
                    self._capture_channels = channels
                    break
                except Exception as exc:
                    open_errors.append(f"duplex {channels}ch: {exc}")
                    self._stream = None

            # Fallback to capture-only if duplex cannot be opened.
            try:
                self._stream = sd.InputStream(
                    samplerate=self._samplerate,
                    channels=channels,
                    dtype="float32",
                    blocksize=LIVE_BLOCK_SIZE,
                    device=self._device_query,
                    callback=self._sd_input_callback,
                )
                self._stream.start()
                self._capture_channels = channels
                break
            except Exception as exc:
                open_errors.append(f"input {channels}ch: {exc}")
                self._stream = None

        if self._stream is None:
            detail = " | ".join(open_errors) if open_errors else "unknown input stream error"
            if self._setup_hint and not self._allow_fallback_to_default:
                self.playback_error.emit(
                    f"Could not open {self._capture_label} stream ({detail}). {self._setup_hint}"
                )
            else:
                self.playback_error.emit(f"Could not open {self._capture_label} stream ({detail}).")
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

    def _sd_input_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            self.playback_error.emit(str(status))

        if self._state not in ("listening", "capturing"):
            return

        self._process_captured_chunk(indata.copy(), frames)

    def _sd_duplex_callback(
        self,
        indata: np.ndarray,
        outdata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            self.playback_error.emit(str(status))

        outdata.fill(0.0)
        if self._state not in ("listening", "capturing"):
            return

        chunk = indata.copy()

        # Monitor live input to speakers/headphones.
        if chunk.ndim == 1:
            outdata[:, 0] = chunk
            if outdata.shape[1] > 1:
                outdata[:, 1] = chunk
        else:
            ch = min(chunk.shape[1], outdata.shape[1])
            outdata[:, :ch] = chunk[:, :ch]

        self._process_captured_chunk(chunk, frames)

    def _process_captured_chunk(self, chunk: np.ndarray, frames: int) -> None:
        self._chunk_queue.append(chunk)

        mono = chunk.ravel() if chunk.ndim == 1 else np.mean(chunk, axis=1)
        rms = float(np.sqrt(np.mean(mono * mono)))

        if self._state == "listening":
            if rms > LIVE_THRESHOLD_RMS:
                self._state = "capturing"
                self._elapsed_s = 0.0
                self._pending_capturing = True
        else:
            self._elapsed_s += frames / float(self._samplerate)

    # ------------------------------------------------------------------
    # Main-thread drain — called by QTimer every 20 ms
    # ------------------------------------------------------------------

    def _drain_queue(self) -> None:
        # Emit state transition if audio thread flagged one
        if self._pending_capturing:
            self._pending_capturing = False
            self.state_changed.emit("capturing")

        if self._state == "idle":
            return

        while self._chunk_queue:
            chunk = self._chunk_queue.popleft()
            self.chunk_available.emit(chunk)

        if self._state == "capturing":
            self.position_changed.emit(self._elapsed_s)


class SystemOutputCapture(LiveInputCapture):
    """Captures system playback from the platform's loopback-capable device."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(
            parent,
            device_query=find_system_capture_device(),
            monitoring_enabled=False,
            capture_label="system output",
            setup_hint=system_capture_setup_hint(),
            allow_fallback_to_default=False,
        )

    def refresh_device(self) -> None:
        self.set_device_query(find_system_capture_device())

    def play(self) -> None:
        self.refresh_device()
        super().play()
