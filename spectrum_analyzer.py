import librosa
import numpy as np
from scipy.fft import fft, fftfreq


class SpectrumAnalyzer:
    """Core audio spectrum analysis logic."""

    def __init__(self, sr=None):
        self.sr = sr

    def load_audio(self, file_path):
        # Load audio and convert to mono, preserving the file's native
        # sample rate (sr=None) unless a specific rate was requested.
        y, sr = librosa.load(file_path, sr=self.sr, mono=True)
        return y, sr

    def get_duration(self, y, sr):
        return len(y) / sr

    def compute_spectrum_at_time(self, y, sr, timestamp, n_fft=4096, hop_length=None):
        """Compute magnitude spectrum at a given timestamp.

        Returns (frequencies, magnitudes_db, time_axis, specgram) for visualization.
        """
        if hop_length is None:
            hop_length = n_fft // 2

        sample_index = int(timestamp * sr)
        # Window of audio around the timestamp
        half_win = n_fft // 2
        start = max(0, sample_index - half_win)
        end = min(len(y), sample_index + half_win)

        segment = y[start:end]
        if len(segment) == 0:
            return np.array([]), np.array([]), np.array([]), np.array([])

        # Pad if needed
        if len(segment) < n_fft:
            segment = np.pad(segment, (0, n_fft - len(segment)), mode="constant")

        # Compute STFT for the spectrogram
        window = np.hanning(n_fft)
        stft_matrix = librosa.stft(segment, n_fft=n_fft, hop_length=hop_length, win_length=n_fft, window=window)
        magnitudes = np.abs(stft_matrix)

        # Convert to dB scale and average over time frames for a single spectrum shape
        magnitudes_db = librosa.amplitude_to_db(magnitudes, ref=np.max).mean(axis=1)

        freqs = fftfreq(n_fft, 1 / sr)[:magnitudes.shape[0]]
        times = librosa.frames_to_time(np.arange(magnitudes.shape[1]), sr=sr, hop_length=hop_length)

        return freqs, magnitudes_db, times, stft_matrix

    def compute_full_spectrogram(self, y, sr, n_fft=4096, hop_length=None):
        """Compute full spectrogram for the entire audio.

        hop_length must match what librosa.stft actually used, or the
        returned time axis will be mislabeled relative to the true frame
        positions (librosa.stft defaults hop_length to n_fft // 4 when
        not given explicitly).
        """
        if hop_length is None:
            hop_length = n_fft // 4
        S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
        S_abs = np.abs(S)
        S_db = librosa.amplitude_to_db(S_abs, ref=np.max)
        freqs = np.fft.rfftfreq(n_fft, 1 / sr)
        times = librosa.frames_to_time(np.arange(S_db.shape[1]), sr=sr, hop_length=hop_length)
        return freqs, S_db, times

    def compute_instant_spectrum(self, y, sr, timestamp, n_fft=4096):
        """Compute single-frame frequency magnitude at a specific timestamp."""
        sample_index = int(timestamp * sr)
        half_win = n_fft // 2
        start = max(0, sample_index - half_win)
        end = min(len(y), sample_index + half_win)

        segment = y[start:end]
        if len(segment) == 0:
            return np.array([]), np.array([]), np.array([])

        if len(segment) < n_fft:
            segment = np.pad(segment, (0, n_fft - len(segment)), mode="constant")

        window = np.hanning(n_fft)
        spectrum = fft(segment * window)
        freqs = fftfreq(n_fft, 1 / sr)
        magnitude = np.abs(spectrum)

        # Only positive frequencies
        pos_mask = freqs >= 0
        return freqs[pos_mask], magnitude[pos_mask], timestamp


def sanitize_file(file_obj):
    """Convert an uploaded file to a temporary path for librosa/audioread compatibility."""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.write(file_obj.read())
    tmp.flush()
    tmp.close()
    return tmp.name
