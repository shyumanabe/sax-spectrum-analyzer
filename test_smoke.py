"""Quick smoke test for SpectrumAnalyzer with synthetic audio."""
import os
import tempfile

import numpy as np
import soundfile as sf

from spectrum_analyzer import SpectrumAnalyzer


def generate_test_audio(filepath, duration=2.0, sr=22050):
    """Generate a short test tone (440 Hz + 880 Hz) for testing."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.3 * np.sin(2 * np.pi * 880 * t)
    sf.write(filepath, signal, sr)


def main():
    print("[TEST] Generating synthetic audio...")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()
    generate_test_audio(tmp.name)

    analyzer = SpectrumAnalyzer(sr=22050)

    print("[TEST] Loading audio...")
    y, sr_raw = analyzer.load_audio(tmp.name)
    print(f"  Loaded {len(y)} samples at {sr_raw} Hz")

    print("[TEST] Computing duration...")
    dur = analyzer.get_duration(y, sr_raw)
    print(f"  Duration: {dur:.2f}s")

    print("[TEST] Computing full spectrogram...")
    freqs, S_db, times = analyzer.compute_full_spectrogram(y, sr_raw)
    print(f"  Freq bins: {len(freqs)}, Time frames: {S_db.shape[1]}")

    print("[TEST] Computing instant spectrum at 0.5s...")
    f, m, *_ = analyzer.compute_spectrum_at_time(y, sr_raw, 0.5)
    print(f"  Instant freq bins: {len(f)}")

    os.remove(tmp.name)
    print("[PASS] All tests passed.")


if __name__ == "__main__":
    main()
