# -*- coding: utf-8 -*-
"""SAX Spectrum Analyzer - PyQt6 real-time synchronized audio visualization."""

import sys
import threading
from pathlib import Path

import numpy as np
import pyqtgraph as pg
import sounddevice as sd
from PyQt6.QtCore import QThread, QTimer, QObject, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from spectrum_analyzer import SpectrumAnalyzer


def _load_audio_file(file_path):
    """Load audio file as mono, return (data, sr)."""
    analyzer = SpectrumAnalyzer(sr=22050)
    y, sr_raw = analyzer.load_audio(file_path)
    return y, sr_raw


# ==============================================================================
# _AudioPlayer - sounddevice wrapper running inside a QThread
# ==============================================================================

class _AudioPlayer(QObject):
    playbackFinished = pyqtSignal()
    # Emits (position_s, duration_s, is_finished) when poll_position() is called
    positionPollResult = pyqtSignal(float, float, bool)

    def __init__(self):
        super().__init__()
        self._stream = None
        self._data: np.ndarray | None = None
        self._sr: int = 0
        self._pos_frames: int = 0
        self._finished: bool = False
        self._play_lock = threading.Lock()

    def _cb(self, outdata, frames, tinfo, status):
        """Audio callback - MUST be as fast as possible. No Qt signal emit."""
        data = self._data
        if data is None:
            return
        n = data.shape[1] if data.ndim == 2 else len(data)
        with self._play_lock:
            c = self._pos_frames
            if c >= n:
                outdata[:] = 0.0
                self._finished = True
                return
            e = min(c + frames, n)
            av = e - c
            if data.ndim == 2:
                for ch in range(min(outdata.shape[0], data.shape[0])):
                    outdata[ch, :av] = data[ch, c:e]
                    outdata[ch, av:] = 0.0
            else:
                outdata[:, :av] = np.expand_dims(data[c:e], axis=1)
                outdata[:, av:] = 0.0
            self._pos_frames = e
            if e >= n:
                self._finished = True

    @pyqtSlot()
    def poll_position(self):
        """Called from main thread via queued connection - returns state via signal."""
        with self._play_lock:
            current_pos = self._pos_frames / self._sr if self._sr else 0.0
            finished = self._finished
        d = self._data
        n = d.shape[1] if d is not None and d.ndim == 2 else len(d) if d is not None else 0
        dur = (n / self._sr) if self._sr else 0.0
        self.positionPollResult.emit(current_pos, dur, finished)

    @pyqtSlot(np.ndarray, int)
    def load(self, data: np.ndarray, sr: int):
        self._data = data
        self._sr = sr
        with self._play_lock:
            self._pos_frames = 0
            self._finished = False

    @property
    def duration_on_this_thread(self) -> float:
        """Only call from the player's own thread."""
        d = self._data
        if d is None or self._sr == 0:
            return 0.0
        n = d.shape[1] if d.ndim == 2 else len(d)
        return n / self._sr

    @pyqtSlot()
    def play(self):
        with self._play_lock:
            if self._stream and not self._stream.closed:
                return
            ch = self._data.shape[0] if self._data.ndim == 2 else 1
            self._finished = False
            self._stream = sd.OutputStream(
                samplerate=self._sr,
                channels=ch,
                callback=self._cb,
                blocksize=1024,
            )
            self._stream.start()

    @pyqtSlot()
    def pause(self):
        if self._stream and not self._stream.closed:
            self._stream.stop()

    @pyqtSlot()
    def resume(self):
        if self._stream and not self._stream.closed:
            self._stream.start()

    @pyqtSlot(float)
    def seek(self, time_s: float):
        """Seek to a given timestamp in seconds."""
        self._close_stream_safely()
        target_frames = int(time_s * self._sr)
        with self._play_lock:
            self._pos_frames = max(0, min(target_frames, len(self._data)))
            self._finished = False

    @pyqtSlot()
    def stop(self):
        self._close_stream_safely()
        with self._play_lock:
            self._pos_frames = 0
            self._finished = False

    def _close_stream_safely(self):
        if self._stream and not self._stream.closed:
            try:
                self._stream.close()
            except Exception:
                pass


# ==============================================================================
# MainWindow - GUI with pyqtgraph spectrum display + seek bar
# ==============================================================================

class SpectrumWorker(QObject):
    """Helper to extract spectrum column from precomputed spectrogram at given time."""
    finished = pyqtSignal(np.ndarray, np.ndarray)

    def compute(self, freqs, spec_db, times, timestamp):
        col_idx = np.searchsorted(times, timestamp, side="left")
        col_idx = min(col_idx, len(times) - 1)
        mag = spec_db[:, col_idx]
        self.finished.emit(freqs, mag)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SAX Spectrum Analyzer")
        self.resize(900, 600)

        # Audio state (cached on main thread to avoid cross-thread access)
        self._audio_data: np.ndarray | None = None
        self._audio_sr: int = 0
        self._duration_s: float = 0.0
        self._current_time: float = 0.0
        self._is_playing: bool = False
        self._is_paused: bool = False

        # Spectrogram state
        self._spec_freqs: np.ndarray | None = None
        self._spec_db: np.ndarray | None = None
        self._spec_times: np.ndarray | None = None
        self._n_fft: int = 4096

        # Thread / player
        self._thread = QThread()
        self._player = _AudioPlayer()
        self._player.moveToThread(self._thread)
        self._thread.start()

        # Connect poll signal back to main thread
        self._player.positionPollResult.connect(self._on_poll_result)

        # Worker for spectrum extraction
        self._worker = SpectrumWorker()
        self._worker.finished.connect(self._on_spectrum_ready)

        # Timer for real-time ui updates (~30 fps)
        self._timer = QTimer(self)
        self._timer.setInterval(34)
        self._timer.timeout.connect(self._update_spectrum)

        self._build_ui()
        self._connect_signals()
        self._init_plot()
        self._disable_seek()

    def _disable_seek(self):
        """Disable seek slider when no file is loaded."""
        self.seek_slider.setEnabled(False)
        self.seek_slider.setValue(0)

    def _enable_seek(self, duration: float):
        """Enable seek slider and set range for the loaded file."""
        steps = max(int(duration * 100), 1)
        self.seek_slider.setMinimum(0)
        self.seek_slider.setMaximum(steps)
        self.seek_slider.setEnabled(True)
        self.seek_slider.setValue(0)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Controls row
        ctrl_row = QHBoxLayout()
        self.btn_open = QPushButton("Open File")
        self.btn_play = QPushButton("Play")
        self.btn_pause = QPushButton("Pause")
        self.btn_stop = QPushButton("Stop")
        self.lbl_status = QLabel("No file loaded")

        self.cmb_fft = QComboBox()
        self.cmb_fft.addItems(["1024", "2048", "4096", "8192"])
        self.cmb_fft.setCurrentText("4096")

        ctrl_row.addWidget(self.btn_open)
        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_pause)
        ctrl_row.addWidget(self.btn_stop)
        ctrl_row.addWidget(QLabel("FFT size:"))
        ctrl_row.addWidget(self.cmb_fft)
        ctrl_row.addStretch()
        ctrl_row.addWidget(self.lbl_status)

        # Seek bar row
        seek_row = QHBoxLayout()
        self.lbl_time = QLabel("Time: 0.00 s / 0.00 s")
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.seek_slider.setTracking(True)

        seek_row.addWidget(self.lbl_time)
        seek_row.addWidget(self.seek_slider, 1)

        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("left", "Magnitude [dB]")
        self.plot_widget.setLabel("bottom", "Frequency [Hz]")
        self.plot_widget.setYRange(-80, 5)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        main_layout.addLayout(ctrl_row)
        main_layout.addLayout(seek_row)
        main_layout.addWidget(self.plot_widget)

    def _connect_signals(self):
        self.btn_open.clicked.connect(self._on_open_file)
        self.btn_play.clicked.connect(self._on_play)
        self.btn_pause.clicked.connect(self._on_pause)
        self.btn_stop.clicked.connect(self._on_stop)
        self.cmb_fft.currentTextChanged.connect(self._on_fft_changed)

        # Player signals
        self._player.playbackFinished.connect(self._on_playback_finished)

        # Seek slider
        self.seek_slider.valueChanged.connect(self._on_seek_slider_changed)

    def _init_plot(self):
        pen = pg.mkPen((100, 150, 255), width=2)
        self._curve = self.plot_widget.plot(pen=pen)
        baseline = np.full(1000, -80.0)
        self._base_curve = self.plot_widget.plot(baseline, pen=None)
        self._fill = pg.FillBetweenItem(
            self._curve, self._base_curve, brush=pg.mkBrush(100, 150, 255, 64)
        )
        self.plot_widget.addItem(self._fill)

    def _slider_time(self, value: int) -> float:
        """Convert slider value to seconds using main-thread cached duration."""
        steps = self.seek_slider.maximum()
        if steps == 0 or self._duration_s == 0.0:
            return 0.0
        return value * self._duration_s / steps

    def _on_seek_slider_changed(self):
        """Handle seek slider drag - update position and recompute spectrum immediately."""
        target_time = self._slider_time(self.seek_slider.value())
        if self._is_playing:
            self._player.seek(target_time)
            was_paused = self._is_paused
            if not was_paused:
                self._player.resume()
        self._current_time = target_time
        self.lbl_time.setText(f"Time: {target_time:.2f} s / {self._duration_s:.2f} s")
        self._update_spectrum_at_time(target_time)

    # File handling

    @pyqtSlot()
    def _on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", "",
            "Audio Files (*.wav *.flac *.mp3 *.ogg *.m4a);;All Files (*)",
        )
        if not path:
            return

        try:
            self._stop_timer()
            self._player.stop()

            y, sr = _load_audio_file(path)
            self._audio_data = y
            self._audio_sr = sr
            self._current_time = 0.0
            self._duration_s = len(y) / sr
            self._is_playing = False
            self._is_paused = False

            # Pre-compute full spectrogram
            analyzer = SpectrumAnalyzer(sr=sr)
            self._spec_freqs, self._spec_db, self._spec_times = (
                analyzer.compute_full_spectrogram(y, sr, n_fft=self._n_fft)
            )

            file_name = Path(path).name
            duration = self._duration_s
            self.lbl_status.setText(f"Loaded: {file_name}  ({duration:.1f} s)")

            self._player.load(y, sr)

            # Enable seek slider with proper range
            self._enable_seek(duration)

            hi_freq = float(self._spec_freqs[-1])
            self.plot_widget.setXRange(0, hi_freq)

            self._show_silent_spectrum()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load file:\n{e}")

    def _recompute_spectrogram(self):
        """Recompute spectrogram when FFT size changes."""
        if self._audio_data is None:
            return
        analyzer = SpectrumAnalyzer(sr=self._audio_sr)
        self._spec_freqs, self._spec_db, self._spec_times = (
            analyzer.compute_full_spectrogram(
                self._audio_data, self._audio_sr, n_fft=self._n_fft
            )
        )
        hi_freq = float(self._spec_freqs[-1])
        self.plot_widget.setXRange(0, hi_freq)

    def _on_fft_changed(self, text: str):
        self._n_fft = int(text)
        was_playing = self._is_playing and not self._is_paused
        if was_playing:
            self._on_pause()
        self._recompute_spectrogram()
        if was_playing and self._audio_data is not None:
            self._on_play()

    # Playback controls

    @pyqtSlot()
    def _on_play(self):
        if self._audio_data is None:
            return
        if self._is_paused:
            self._player.resume()
            self._is_paused = False
            self._is_playing = True
            self._start_timer()
            return

        self._player.play()
        self._is_playing = True
        self._is_paused = False
        self._start_timer()

    @pyqtSlot()
    def _on_pause(self):
        if not self._is_playing:
            return
        self._player.pause()
        self._stop_timer()
        self._is_paused = True

    @pyqtSlot()
    def _on_stop(self):
        self._player.stop()
        self._stop_timer()
        self._is_playing = False
        self._is_paused = False
        self._current_time = 0.0
        if self.seek_slider.isEnabled():
            self.seek_slider.setValue(0)
        self.lbl_time.setText(f"Time: 0.00 s / {self._duration_s:.2f} s")
        self._show_silent_spectrum()

    @pyqtSlot()
    def _on_playback_finished(self):
        self._player.stop()
        self._stop_timer()
        self._is_playing = False
        self._is_paused = False
        self._show_silent_spectrum()

    # Timer & spectrum update

    def _start_timer(self):
        self._timer.start()

    def _stop_timer(self):
        if self._timer.isActive():
            self._timer.stop()

    def _update_spectrum(self):
        if not self._is_playing:
            return
        # Poll player position from background thread via queued slot
        self._player.poll_position()

    def _on_poll_result(self, current_pos: float, duration: float, finished: bool):
        """Callback triggered each timer tick with fresh position data."""
        if finished:
            self._on_playback_finished()
            return

        self._current_time = current_pos
        self.lbl_time.setText(f"Time: {current_pos:.2f} s / {duration:.2f} s")

        # Update seek slider without emitting (avoid seek loop)
        steps = self.seek_slider.maximum()
        if steps > 0 and duration > 0:
            val = int(current_pos * steps / duration)
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(min(val, steps))
            self.seek_slider.blockSignals(False)

        # Extract and display spectrum at current time
        self._update_spectrum_at_time(current_pos)

    def _update_spectrum_at_time(self, timestamp: float):
        """Compute and display spectrum for a given timestamp."""
        if self._spec_freqs is None or self._spec_db is None:
            return
        if self._spec_times is None or len(self._spec_times) == 0:
            return
        self._worker.compute(
            self._spec_freqs, self._spec_db, self._spec_times, timestamp
        )

    def _on_spectrum_ready(self, freqs, mag):
        self._curve.setData(freqs, mag)
        self._base_curve.setData(freqs, np.full(len(freqs), -80.0))

    def _show_silent_spectrum(self):
        if self._spec_freqs is None:
            return
        silence = np.full(len(self._spec_freqs), -80.0)
        self._curve.setData(self._spec_freqs, silence)
        self._base_curve.setData(self._spec_freqs, silence)

    # Cleanup

    def closeEvent(self, event):
        self._stop_timer()
        self._player.stop()
        self._thread.quit()
        self._thread.wait()
        event.accept()


# ==============================================================================
# main
# ==============================================================================

def main():
    pg.setConfigOptions(antialias=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
