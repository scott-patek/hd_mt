from __future__ import annotations

import numpy as np

import app.audio.audio_loader as audio_loader


class _FakeSegment:
    frame_rate = 48000
    channels = 2
    sample_width = 2

    def get_array_of_samples(self):
        # Two stereo frames in int16 format.
        return [32767, 0, -32768, 16384]


class _FakeAudioSegment:
    @staticmethod
    def from_file(_file_path: str):
        return _FakeSegment()


class _FailingAudioSegment:
    @staticmethod
    def from_file(_file_path: str):
        raise RuntimeError("ffmpeg decode failed")


def test_decode_audio_falls_back_to_pydub_when_soundfile_fails(monkeypatch) -> None:
    loader = audio_loader.AudioLoader()

    monkeypatch.setattr(loader, "_read_with_soundfile", lambda _p: (_ for _ in ()).throw(RuntimeError("soundfile unavailable")))
    monkeypatch.setattr(audio_loader, "AudioSegment", _FakeAudioSegment)

    samples, sr = loader._decode_audio_file("dummy.mp3")

    assert sr == 48000
    assert isinstance(samples, np.ndarray)
    assert samples.shape == (2, 2)
    assert np.isclose(samples[0, 0], 32767 / 32768, atol=1e-5)


def test_decode_audio_raises_clear_error_when_no_fallback(monkeypatch) -> None:
    loader = audio_loader.AudioLoader()

    monkeypatch.setattr(loader, "_read_with_soundfile", lambda _p: (_ for _ in ()).throw(RuntimeError("soundfile unavailable")))
    monkeypatch.setattr(audio_loader, "AudioSegment", None)

    try:
        loader._decode_audio_file("dummy.mp3")
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Install pydub" in str(exc)


def test_decode_audio_raises_combined_backend_error(monkeypatch) -> None:
    loader = audio_loader.AudioLoader()

    monkeypatch.setattr(loader, "_read_with_soundfile", lambda _p: (_ for _ in ()).throw(RuntimeError("soundfile unavailable")))
    monkeypatch.setattr(audio_loader, "AudioSegment", _FailingAudioSegment)

    try:
        loader._decode_audio_file("dummy.mp3")
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        msg = str(exc)
        assert "soundfile error" in msg
        assert "pydub/ffmpeg error" in msg
