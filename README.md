# SAX Spectrum Analyzer

Real-time audio spectrum analyzer built with Python and Streamlit. Upload an audio file, play it back, and visualize its frequency spectrum at any point in time.

## Features

- File upload for multiple audio formats (m4a, mp3, wav, flac, ogg, aac)
- Built-in audio playback
- Interactive slider to select playback position
- Instant frequency spectrum visualization at selected time
- Full spectrogram heatmap with time cursor overlay
- Adjustable max frequency and FFT resolution via sidebar

## Requirements

- Python 3.9+
- **uv** for dependency management ([install here](https://github.com/astral-sh/uv))
- **ffmpeg** (required by audioread/librosa to decode m4a, mp3, etc.)
  ```bash
    # macOS
    brew install ffmpeg
  ```

## Setup

```bash
# Sync dependencies
uv sync
```

## Usage

```bash
uv run streamlit run app.py --server.headless true
```

The application will open in your default browser. Upload a file, move the slider to inspect different frames, and listen via the playback widget.

## Project Structure

| File | Description |
|------|-------------|
| `app.py` | Streamlit UI (upload, playback, charts) |
| `spectrum_analyzer.py` | Core FFT / STFT analysis logic (librosa based) |
| `pyproject.toml` | uv dependency manifest |

## License

Private / Non-commercial.
