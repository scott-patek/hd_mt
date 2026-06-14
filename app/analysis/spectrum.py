from __future__ import annotations

import numpy as np
from scipy.signal import get_window, spectrogram


class SpectrumAnalyzer:
    def __init__(
        self,
        samplerate: int,
        fft_size: int = 4096,
        display_min_hz: float | None = None,
        display_max_hz: float | None = None,
        group_hz: float = 100.0,
    ) -> None:
        self.samplerate = samplerate
        self.fft_size = fft_size
        self.window = get_window("hann", fft_size, fftbins=True).astype(np.float32)

        # Allow custom frequency range or use defaults.
        if display_min_hz is None:
            self.display_min_hz = 20.0
        else:
            self.display_min_hz = display_min_hz

        if display_max_hz is None:
            self.display_max_hz = min(20000.0, samplerate * 0.49)
        else:
            self.display_max_hz = min(display_max_hz, samplerate * 0.49)

        self.group_hz = group_hz
        self.min_reliable_hz = 20.0
        split_hz = self.display_max_hz

        edges = np.arange(
            self.display_min_hz,
            split_hz + self.group_hz,
            self.group_hz,
            dtype=np.float32,
        )

        if edges[-1] < self.display_max_hz:
            edges = np.append(edges, self.display_max_hz)

        if edges.shape[0] < 2:
            edges = np.array([self.display_min_hz, self.display_min_hz + self.group_hz], dtype=np.float32)
        self.band_edges = np.column_stack([edges[:-1], edges[1:]])
        self.band_centers = (self.band_edges[:, 0] + self.band_edges[:, 1]) * 0.5
        self.band_widths = self.band_edges[:, 1] - self.band_edges[:, 0]
        n_bands = self.band_centers.shape[0]
        self.fft_amplitude_scale = max(float(0.5 * np.sum(self.window)), 1e-9)
        self.peak_hold_db = np.full(n_bands, -120.0, dtype=np.float32)
        self.peak_hold_age_s = np.full(n_bands, 999.0, dtype=np.float32)
        self.peak_hold_window_s = 3.0
        self.display_floor_db = -72.0

    def reset_state(self) -> None:
        """Reset peak-hold buffers for a fresh analysis run."""
        self.peak_hold_db.fill(-120.0)
        self.peak_hold_age_s.fill(999.0)

    def compute_bars(self, mono_samples: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if mono_samples.shape[0] < self.fft_size:
            padded = np.zeros(self.fft_size, dtype=np.float32)
            padded[: mono_samples.shape[0]] = mono_samples
            mono_samples = padded
        else:
            mono_samples = mono_samples[-self.fft_size :]

        # Remove DC bias so the 0 Hz bin does not dominate the display.
        mono_samples = mono_samples - np.mean(mono_samples)
        windowed = mono_samples * self.window
        fft_mag = np.abs(np.fft.rfft(windowed)) / self.fft_amplitude_scale
        freqs = np.fft.rfftfreq(self.fft_size, d=1.0 / self.samplerate)

        band_db = []
        for low, high in self.band_edges:
            lo = max(float(low), self.min_reliable_hz)
            idx = np.where((freqs >= lo) & (freqs < float(high)))[0]
            if idx.size == 0:
                # Narrow display bands can fall between FFT bins. Sample the band center
                # so the display remains continuous instead of dropping to the floor.
                center_hz = 0.5 * (lo + float(high))
                val = float(np.interp(center_hz, freqs, fft_mag))
                db = 20.0 * np.log10(max(val, 1e-9))
                band_db.append(db)
                continue
            # Use band energy (RMS) instead of max-bin spikes for a steadier calibrated dBFS readout.
            val = float(np.sqrt(np.mean(fft_mag[idx] ** 2)))
            db = 20.0 * np.log10(max(val, 1e-9))
            band_db.append(db)

        band_db = np.array(band_db, dtype=np.float32)
        band_db = np.clip(band_db, -80.0, 6.0)
        band_db[band_db < self.display_floor_db] = self.display_floor_db

        frame_seconds = mono_samples.shape[0] / float(self.samplerate)
        self.peak_hold_age_s += frame_seconds

        higher_now = band_db >= self.peak_hold_db
        self.peak_hold_db[higher_now] = band_db[higher_now]
        self.peak_hold_age_s[higher_now] = 0.0

        expired = self.peak_hold_age_s > self.peak_hold_window_s
        self.peak_hold_db[expired] = band_db[expired]
        self.peak_hold_age_s[expired] = 0.0

        return self.band_centers, band_db, self.peak_hold_db.copy()


class SpectrogramBuffer:
    def __init__(self, samplerate: int, max_frames: int = 220) -> None:
        self.samplerate = samplerate
        self.max_frames = max_frames
        self.image = np.zeros((256, max_frames), dtype=np.float32)

    def update(self, mono_samples: np.ndarray) -> np.ndarray:
        if mono_samples.size < 1024:
            return self.image

        freqs, _, spec = spectrogram(
            mono_samples,
            fs=self.samplerate,
            nperseg=1024,
            noverlap=768,
            scaling="spectrum",
            mode="magnitude",
        )
        if spec.size == 0:
            return self.image

        db = 20.0 * np.log10(np.maximum(spec, 1e-9))
        db = np.clip(db, -90.0, 0.0)

        # Downsample freq bins for stable rendering cost.
        target_bins = 256
        take = np.linspace(0, db.shape[0] - 1, target_bins).astype(int)
        frame = db[take, -1]

        self.image = np.roll(self.image, -1, axis=1)
        self.image[:, -1] = frame
        return self.image
