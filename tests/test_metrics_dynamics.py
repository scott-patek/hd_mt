from __future__ import annotations

import numpy as np

from app.analysis.metrics import MetricsEngine


def test_crest_factor_db_is_non_negative_for_silence() -> None:
    engine = MetricsEngine(48000)
    chunk = np.zeros((2048, 2), dtype=np.float32)

    snapshot = engine.update(chunk)

    assert snapshot.crest_factor_db >= 0.0
    assert not snapshot.dynamics_ready


def test_crest_factor_db_for_sine_is_reasonable() -> None:
    sr = 48000
    engine = MetricsEngine(sr)
    t = np.arange(2048, dtype=np.float32) / sr
    sine = 0.5 * np.sin(2.0 * np.pi * 1000.0 * t).astype(np.float32)
    chunk = np.column_stack([sine, sine]).astype(np.float32)

    snapshot = engine.update(chunk)

    # Sine crest is about 3.01 dB in ideal conditions.
    assert 2.0 <= snapshot.crest_factor_db <= 4.5


def test_dynamic_range_becomes_ready_after_enough_frames() -> None:
    engine = MetricsEngine(48000)
    rng = np.random.default_rng(42)

    ready_seen = False
    for _ in range(40):
        mono = (0.06 * rng.standard_normal(2048)).astype(np.float32)
        chunk = np.column_stack([mono, mono]).astype(np.float32)
        snapshot = engine.update(chunk)
        if snapshot.dynamics_ready:
            ready_seen = True
            assert np.isfinite(snapshot.dynamic_range_db)
            assert snapshot.dynamic_range_db >= 0.0
            break

    assert ready_seen


def test_reset_clears_dynamic_readiness() -> None:
    engine = MetricsEngine(48000)
    rng = np.random.default_rng(123)

    for _ in range(20):
        mono = (0.05 * rng.standard_normal(2048)).astype(np.float32)
        chunk = np.column_stack([mono, mono]).astype(np.float32)
        engine.update(chunk)

    engine.reset()
    chunk = np.zeros((2048, 2), dtype=np.float32)
    snapshot = engine.update(chunk)

    assert not snapshot.dynamics_ready
