# -*- coding: utf-8 -*-
"""Basic smoke tests for app.py, including dual-channel (File A / File B) support."""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from app import _AudioPlayer, ChannelPanel, MainWindow

import numpy as np

# QWidget subclasses (e.g. MainWindow) require a QApplication to exist first.
_qapp = QApplication.instance() or QApplication([])


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


def test_no_positionChanged_signal():
    """The old positionChanged signal must no longer exist."""
    p = _AudioPlayer()
    assert not hasattr(p, "positionChanged"), \
        "Old positionChanged signal must be removed"
    print("[PASS] Old positionChanged signal is removed")


def test_mainwindow_has_two_independent_channels():
    win = MainWindow()
    try:
        assert isinstance(win.channel_a, ChannelPanel), "MainWindow must have channel_a"
        assert isinstance(win.channel_b, ChannelPanel), "MainWindow must have channel_b"
        assert win.channel_a is not win.channel_b, "channels must be independent instances"
        assert not win.channel_a.seek_slider.isEnabled(), "channel_a slider should be disabled before loading"
        assert not win.channel_b.seek_slider.isEnabled(), "channel_b slider should be disabled before loading"
        print("[PASS] MainWindow has two independent ChannelPanels, both initially disabled")
    finally:
        # MainWindow spins up a QThread per channel in __init__; they must be
        # stopped before the object is destroyed or Qt aborts the process.
        win.close()


def test_shared_fft_and_max_freq_controls():
    win = MainWindow()
    try:
        assert hasattr(win, "cmb_fft"), "MainWindow must have a shared FFT size combo"
        assert hasattr(win, "spin_max_freq"), "MainWindow must have a shared max-freq spin box"
        assert not win.spin_max_freq.isEnabled(), "max-freq spin box should be disabled before any file loads"
        print("[PASS] Shared FFT size / max frequency controls exist and start disabled")
    finally:
        win.close()


def test_layout_toggle_switches_splitter_orientation():
    win = MainWindow()
    try:
        assert win.splitter.orientation() == Qt.Orientation.Horizontal, \
            "default layout should be side-by-side (Horizontal)"
        win.cmb_layout.setCurrentIndex(1)
        assert win.splitter.orientation() == Qt.Orientation.Vertical, \
            "selecting the second layout option should stack channels vertically"
        win.cmb_layout.setCurrentIndex(0)
        assert win.splitter.orientation() == Qt.Orientation.Horizontal, \
            "switching back should restore side-by-side layout"
        print("[PASS] Layout combo toggles the splitter between side-by-side and stacked")
    finally:
        win.close()


def test_channels_load_and_play_independently():
    """Loading/playing one channel must not affect the other channel's state."""
    win = MainWindow()
    try:
        sr = 22050
        duration_s = 1.0
        t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
        y_a = (0.3 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)
        y_b = (0.3 * np.sin(2 * np.pi * 880.0 * t)).astype(np.float32)

        win.channel_a._audio_data = y_a
        win.channel_a._audio_sr = sr
        win.channel_a._duration_s = duration_s
        from spectrum_analyzer import SpectrumAnalyzer
        analyzer = SpectrumAnalyzer(sr=sr)
        win.channel_a._spec_freqs, win.channel_a._spec_db, win.channel_a._spec_times = (
            analyzer.compute_full_spectrogram(y_a, sr, n_fft=win.channel_a._n_fft)
        )
        win.channel_a._player.load(y_a, sr)
        win.channel_a._enable_seek(duration_s)
        win.channel_a.fileLoaded.emit(float(win.channel_a._spec_freqs[-1]))

        assert win.channel_a.seek_slider.isEnabled(), "channel_a should be enabled after loading"
        assert not win.channel_b.seek_slider.isEnabled(), \
            "channel_b must remain untouched by channel_a's load"
        assert win.spin_max_freq.isEnabled(), \
            "shared max-freq control should enable once any channel has data"

        win.channel_b._audio_data = y_b
        win.channel_b._audio_sr = sr
        win.channel_b._duration_s = duration_s
        win.channel_b._spec_freqs, win.channel_b._spec_db, win.channel_b._spec_times = (
            analyzer.compute_full_spectrogram(y_b, sr, n_fft=win.channel_b._n_fft)
        )
        win.channel_b._player.load(y_b, sr)
        win.channel_b._enable_seek(duration_s)
        win.channel_b.fileLoaded.emit(float(win.channel_b._spec_freqs[-1]))

        assert win.channel_b.seek_slider.isEnabled(), "channel_b should be enabled after loading"

        # Flip channel_a's playing state directly rather than opening a real
        # sounddevice stream (which would audibly play through the machine's
        # speakers during an automated test run).
        assert win.channel_a._player is not win.channel_b._player, \
            "each channel must own its own _AudioPlayer instance"
        win.channel_a._is_playing = True
        assert not win.channel_b._is_playing, "channel_b must stay stopped while only channel_a plays"

        win.channel_a._on_stop()
        assert not win.channel_a._is_playing
        print("[PASS] Channels A and B load independently and own separate players")
    finally:
        win.close()


def test_shared_fft_size_applies_to_both_loaded_channels():
    win = MainWindow()
    try:
        sr = 22050
        duration_s = 0.5
        t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
        y = (0.3 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)

        from spectrum_analyzer import SpectrumAnalyzer
        analyzer = SpectrumAnalyzer(sr=sr)
        for ch in (win.channel_a, win.channel_b):
            ch._audio_data = y
            ch._audio_sr = sr
            ch._duration_s = duration_s
            ch._spec_freqs, ch._spec_db, ch._spec_times = (
                analyzer.compute_full_spectrogram(y, sr, n_fft=ch._n_fft)
            )
            ch._player.load(y, sr)
            ch._enable_seek(duration_s)

        win._on_fft_changed("1024")
        assert win.channel_a._n_fft == 1024
        assert win.channel_b._n_fft == 1024
        print("[PASS] Changing the shared FFT size combo updates both channels")
    finally:
        win.close()


if __name__ == "__main__":
    test_player_signal_exists()
    test_player_seek_method()
    test_no_positionChanged_signal()
    test_mainwindow_has_two_independent_channels()
    test_shared_fft_and_max_freq_controls()
    test_layout_toggle_switches_splitter_orientation()
    test_channels_load_and_play_independently()
    test_shared_fft_size_applies_to_both_loaded_channels()
    print("\nAll smoke tests passed.")
