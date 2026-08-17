# SAX Spectrum Analyzer

Real-time audio spectrum analyzer built with Python, PyQt6, and pyqtgraph. Open an audio file, play it back, and visualize its frequency spectrum synchronized with playback.

## Features

- Open audio files via file dialog (wav, flac, mp3, ogg, m4a)
- Built-in audio playback via sounddevice, at the file's native sample rate
- Play / Pause / Stop controls
- Real-time spectrum visualization synchronized with playback (~30 fps)
- Adjustable FFT size (1024, 2048, 4096, 8192)
- Adjustable max displayed frequency (spin box, capped at the file's Nyquist frequency)

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

A native window will appear. Click "Open File" to load audio, then use Play/Pause/Stop controls. The spectrum plot updates in real time during playback.

## Project Structure

| File | Description |
|------|-------------|
| `app.py` | PyQt6 GUI (file dialog, playback controls, pyqtgraph spectrum) |
| `spectrum_analyzer.py` | Core FFT / STFT analysis logic (librosa based) |
| `test_smoke.py` | Smoke test with synthetic audio |
| `pyproject.toml` | uv dependency manifest |

## License

Private / Non-commercial.
