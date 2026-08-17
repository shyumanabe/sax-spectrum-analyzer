# SAX Spectrum Analyzer

Real-time audio spectrum analyzer built with Python, PyQt6, and pyqtgraph. Open up to two audio files (File A / File B), play them back independently, and visually compare their frequency spectra side by side.

## Features

- Load two independent audio files at once (File A / File B) for spectrum comparison, e.g. two saxophone recordings
- Each file has its own Open / Play / Pause / Stop controls and seek bar, so the two can be played independently
- Switchable layout: side-by-side (左右に並べて表示) or stacked (上下に並べて表示), via the Layout dropdown
- FFT size and max displayed frequency are shared between both channels so the comparison stays fair
- Open audio files via file dialog (wav, flac, mp3, ogg, m4a)
- Built-in audio playback via sounddevice, at the file's native sample rate
- Real-time spectrum visualization synchronized with playback (~30 fps)
- Adjustable FFT size (1024, 2048, 4096, 8192)
- Adjustable max displayed frequency (spin box, capped at the loaded files' Nyquist frequency)

## Requirements

- Python 3.9+
- **uv** for dependency management ([install here](https://github.com/astral-sh/uv))
- **ffmpeg** (required by librosa to decode m4a, mp3, etc.)
  ```bash
    # macOS
    brew install ffmpeg
  ```

## Setup

```bash
uv sync
```

## Usage

```bash
uv run python app.py
```

A native window will appear with two panels, **File A** and **File B**. Click each panel's own "Open File" button to load an audio file into it, then use that panel's Play/Pause/Stop controls and seek bar — the two files play back completely independently. The "FFT size", "Max Freq", and "Layout" controls at the top apply to both panels at once, keeping the comparison fair. Use "Layout" to switch between side-by-side and stacked panels.

## Project Structure

| File | Description |
|------|-------------|
| `app.py` | PyQt6 GUI: `ChannelPanel` (one independent audio channel) x2 + `MainWindow` (shared FFT/frequency/layout controls) |
| `spectrum_analyzer.py` | Core FFT / STFT analysis logic (librosa based) |
| `test_smoke.py` | Smoke test with synthetic audio, covering both channels independently |
| `verify_dual_channel.py` | Visual verification script; renders both layouts with two synthetic tones to `verify_dual_channel_output/` |
| `pyproject.toml` | uv dependency manifest |

## License

Private / Non-commercial.
