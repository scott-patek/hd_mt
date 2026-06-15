from __future__ import annotations

import app.audio.live_input as live_input


def test_find_system_capture_device_mac(monkeypatch) -> None:
    devices = [
        {"name": "Built-in Microphone", "max_input_channels": 2},
        {"name": "BlackHole 2ch", "max_input_channels": 2},
    ]
    monkeypatch.setattr(live_input.sd, "query_devices", lambda: devices)

    assert live_input.find_system_capture_device("darwin") == 1


def test_find_system_capture_device_windows(monkeypatch) -> None:
    devices = [
        {"name": "Microphone Array", "max_input_channels": 2},
        {"name": "Stereo Mix (Realtek)", "max_input_channels": 2},
    ]
    monkeypatch.setattr(live_input.sd, "query_devices", lambda: devices)

    assert live_input.find_system_capture_device("win32") == 1


def test_system_capture_setup_hint_mac() -> None:
    hint = live_input.system_capture_setup_hint("darwin")

    assert "BlackHole" in hint
    assert "Audio MIDI Setup" in hint


def test_system_capture_setup_hint_windows() -> None:
    hint = live_input.system_capture_setup_hint("win32")

    assert "Stereo Mix" in hint
    assert "Windows" in hint
