# -*- coding: utf-8 -*-
"""Basic smoke tests for app.py modifications."""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app import _AudioPlayer, MainWindow

import numpy as np


def test_player_signal_exists():
    p = _AudioPlayer()
    assert hasattr(p, "positionPollResult")
    assert hasattr(p, "poll_position")
    print("[PASS] positionPollResult signal and poll_position slot exist")


def test_player_seek_method():
    p = _AudioPlayer()
    sr = 44100
    data = np.random.randn(2 * sr).astype(np.float32)
    p.load(data, sr)
    assert callable(p.seek), "seek method must be callable"
    print("[PASS] seek method is callable after loading audio")


def testMainWindow_creates_seeksilder():
    win = MainWindow()
    assert hasattr(win, "seek_slider"), "MainWindow must have seek_slider"
    assert not win.seek_slider.isEnabled(), "slider should be disabled before loading"
    print("[PASS] QSlider exists and is initially disabled")


def test_no_positionChanged_signal():
    """The old positionChanged signal must no longer exist."""
    p = _AudioPlayer()
    assert not hasattr(p, "positionChanged"), \
        "Old positionChanged signal must be removed"
    print("[PASS] Old positionChanged signal is removed")


if __name__ == "__main__":
    test_player_signal_exists()
    test_player_seek_method()
    testMainWindow_creates_seeksilder()
    test_no_positionChanged_signal()
    print("\nAll smoke tests passed.")
