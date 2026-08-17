# -*- coding: utf-8 -*-
"""Visual verification for the two-file (File A / File B) comparison feature.

Generates two synthetic saxophone-like tones with clearly different harmonic
content, loads them into MainWindow's channel_a / channel_b through the real
QFileDialog-driven load path (the dialog itself is monkeypatched to avoid a
GUI popup), and screenshots both the side-by-side and stacked layouts so the
result can be inspected without a physical display.

All output files from this script (synthetic input wavs + screenshots) are
collected under verify_dual_channel_output/.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf
from PyQt6.QtWidgets import QApplication

from app import MainWindow

OUTPUT_DIR = Path(__file__).parent / "verify_dual_channel_output"


def _make_tone(fundamental_hz: float, harmonics: list[float], sr: int, duration_s: float) -> np.ndarray:
    """Synthesize a simple harmonic tone (fundamental + weighted overtones)."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    y = np.zeros_like(t)
    for n, weight in enumerate(harmonics, start=1):
        y += weight * np.sin(2 * np.pi * fundamental_hz * n * t)
    y = y / np.max(np.abs(y))
    return (0.5 * y).astype(np.float32)


def _write_synthetic_inputs(sr: int, duration_s: float) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    # File A: alto-sax-like tone, strong fundamental at A3 (220 Hz)
    y_a = _make_tone(220.0, [1.0, 0.6, 0.4, 0.25, 0.15, 0.08], sr, duration_s)
    # File B: a brighter tone an octave + a bit higher, different harmonic mix,
    # so the two spectra are clearly distinguishable in the plot.
    y_b = _make_tone(330.0, [0.5, 1.0, 0.7, 0.5, 0.35, 0.2, 0.1], sr, duration_s)

    path_a = OUTPUT_DIR / "synthetic_input_file_a.wav"
    path_b = OUTPUT_DIR / "synthetic_input_file_b.wav"
    sf.write(path_a, y_a, sr)
    sf.write(path_b, y_b, sr)
    return path_a, path_b


def main():
    sr = 44100
    duration_s = 2.0
    path_a, path_b = _write_synthetic_inputs(sr, duration_s)

    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.resize(1400, 700)

    try:
        # Drive the real "Open File" code path for each channel, with the
        # native file-picker dialog mocked out to return our synthetic files.
        with patch(
            "app.QFileDialog.getOpenFileName",
            return_value=(str(path_a), ""),
        ):
            win.channel_a._on_open_file()
        with patch(
            "app.QFileDialog.getOpenFileName",
            return_value=(str(path_b), ""),
        ):
            win.channel_b._on_open_file()

        assert win.channel_a.seek_slider.isEnabled(), "File A did not load correctly"
        assert win.channel_b.seek_slider.isEnabled(), "File B did not load correctly"
        assert win.spin_max_freq.isEnabled(), "shared max-freq control did not enable"
        print(f"[OK] File A loaded: nyquist={win.channel_a.nyquist():.0f} Hz")
        print(f"[OK] File B loaded: nyquist={win.channel_b.nyquist():.0f} Hz")
        print(f"[OK] Shared max freq range now: {win.spin_max_freq.value():.0f} Hz")

        # Show a non-silent spectrum for both channels at t=1.0s, as if the
        # user had scrubbed the seek bar there (no real audio playback needed
        # for a visual spectrum comparison).
        win.channel_a._update_spectrum_at_time(1.0)
        win.channel_b._update_spectrum_at_time(1.0)

        win.show()
        for _ in range(5):
            app.processEvents()

        # Layout 1: side-by-side (default)
        pix = win.grab()
        out_path = OUTPUT_DIR / "layout_side_by_side.png"
        pix.save(str(out_path))
        print(f"[OK] Saved screenshot: {out_path}")

        # Layout 2: stacked (top-bottom)
        win.cmb_layout.setCurrentIndex(1)
        for _ in range(5):
            app.processEvents()
        pix = win.grab()
        out_path = OUTPUT_DIR / "layout_stacked.png"
        pix.save(str(out_path))
        print(f"[OK] Saved screenshot: {out_path}")

        print("\nAll dual-channel verification steps passed.")
    finally:
        win.close()


if __name__ == "__main__":
    main()
