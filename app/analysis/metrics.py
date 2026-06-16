from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, lfilter, resample_poly


@dataclass
class AnalysisSnapshot:
    analyzed_seconds: float
    sample_peak_dbfs: float
    true_peak_dbtp: float
    lufs_integrated: float
    lufs_short_term: float
    lufs_momentary: float
    stereo_width: float
    correlation: float
    mono_warning: bool
    clipping: bool
    sub_db: float
    bass_db: float
    low_mid_db: float
    mids_db: float
    crest_factor_db: float
    dynamic_range_db: float
    dynamics_ready: bool


class LUFSMeter:
    def __init__(self, samplerate: int) -> None:
        self.sr = samplerate
        self.integrated_blocks: list[float] = []
        self.short_term_blocks: list[float] = []
        self.momentary_blocks: list[float] = []

        self.b_hp, self.a_hp = butter(2, 38.0 / (self.sr / 2.0), btype="high")
        self.b_hs, self.a_hs = butter(1, 1500.0 / (self.sr / 2.0), btype="high")

    def _k_weight(self, mono: np.ndarray) -> np.ndarray:
        y = lfilter(self.b_hp, self.a_hp, mono)
        y = lfilter(self.b_hs, self.a_hs, y)
        return y

    def update(self, mono: np.ndarray) -> tuple[float, float, float]:
        weighted = self._k_weight(mono)
        ms = float(np.mean(weighted * weighted) + 1e-12)
        block_lufs = -0.691 + 10.0 * np.log10(ms)

        self.momentary_blocks.append(block_lufs)
        self.short_term_blocks.append(block_lufs)
        self.integrated_blocks.append(block_lufs)

        if len(self.momentary_blocks) > 8:
            self.momentary_blocks.pop(0)
        if len(self.short_term_blocks) > 60:
            self.short_term_blocks.pop(0)

        momentary = float(np.mean(self.momentary_blocks))
        short_term = float(np.mean(self.short_term_blocks))

        gated = [v for v in self.integrated_blocks if v > -70.0]
        integrated = float(np.mean(gated)) if gated else -70.0
        return integrated, short_term, momentary


class MetricsEngine:
    def __init__(self, samplerate: int) -> None:
        self.samplerate = samplerate
        self.lufs = LUFSMeter(samplerate)
        self.total_samples = 0
        self.max_sample_peak = 0.0
        self.max_true_peak = 0.0
        self.floor_rms_history: deque[float] = deque(maxlen=320)

    def update(self, chunk: np.ndarray) -> AnalysisSnapshot:
        if chunk.ndim == 1:
            mono = chunk
            left = chunk
            right = chunk
        else:
            left = chunk[:, 0]
            right = chunk[:, 1] if chunk.shape[1] > 1 else chunk[:, 0]
            mono = np.mean(chunk[:, :2], axis=1)

        self.total_samples += mono.shape[0]

        sample_peak = float(np.max(np.abs(chunk)))
        self.max_sample_peak = max(self.max_sample_peak, sample_peak)

        rms = float(np.sqrt(np.mean(mono * mono) + 1e-12))
        self.floor_rms_history.append(rms)

        peak_db = self._to_db(sample_peak)
        rms_db = self._to_db(rms)
        crest_factor_db = max(0.0, peak_db - rms_db)

        dynamics_ready = len(self.floor_rms_history) >= 16 and (self.total_samples / self.samplerate) >= 1.2
        if dynamics_ready:
            floor_rms = float(np.percentile(np.array(self.floor_rms_history, dtype=np.float32), 10.0))
            floor_db = self._to_db(floor_rms)
            dynamic_range_db = max(0.0, peak_db - floor_db)
        else:
            dynamic_range_db = float("nan")

        up = resample_poly(mono, 4, 1)
        true_peak = float(np.max(np.abs(up)))
        self.max_true_peak = max(self.max_true_peak, true_peak)

        lufs_i, lufs_s, lufs_m = self.lufs.update(mono)

        corr = self._correlation(left, right)
        width = float(np.std(left - right) / (np.std(left + right) + 1e-6))

        sub, bass, low_mid, mids = self._band_levels(mono)
        clipping = self.max_sample_peak >= 0.999 or self.max_true_peak >= 1.0

        return AnalysisSnapshot(
            analyzed_seconds=self.total_samples / self.samplerate,
            sample_peak_dbfs=self._to_db(self.max_sample_peak),
            true_peak_dbtp=self._to_db(self.max_true_peak),
            lufs_integrated=lufs_i,
            lufs_short_term=lufs_s,
            lufs_momentary=lufs_m,
            stereo_width=width,
            correlation=corr,
            mono_warning=corr < 0.05,
            clipping=clipping,
            sub_db=sub,
            bass_db=bass,
            low_mid_db=low_mid,
            mids_db=mids,
            crest_factor_db=crest_factor_db,
            dynamic_range_db=dynamic_range_db,
            dynamics_ready=dynamics_ready,
        )

    def reset(self) -> None:
        """Reset all accumulated metrics to initial state."""
        self.lufs = LUFSMeter(self.samplerate)
        self.total_samples = 0
        self.max_sample_peak = 0.0
        self.max_true_peak = 0.0
        self.floor_rms_history.clear()

    def _to_db(self, v: float) -> float:
        return 20.0 * np.log10(max(v, 1e-9))

    def _correlation(self, left: np.ndarray, right: np.ndarray) -> float:
        l = left - np.mean(left)
        r = right - np.mean(right)
        denom = np.sqrt(np.sum(l * l) * np.sum(r * r)) + 1e-12
        return float(np.sum(l * r) / denom)

    def _band_levels(self, mono: np.ndarray) -> tuple[float, float, float, float]:
        fft = np.abs(np.fft.rfft(mono * np.hanning(mono.shape[0])))
        freqs = np.fft.rfftfreq(mono.shape[0], d=1.0 / self.samplerate)

        def band_db(lo: float, hi: float) -> float:
            idx = (freqs >= lo) & (freqs < hi)
            if not np.any(idx):
                return -120.0
            energy = float(np.mean(fft[idx] ** 2))
            return 10.0 * np.log10(max(energy, 1e-12))

        sub = band_db(20.0, 60.0)
        bass = band_db(60.0, 120.0)
        low_mid = band_db(120.0, 350.0)
        mids = band_db(350.0, 2000.0)
        return sub, bass, low_mid, mids
