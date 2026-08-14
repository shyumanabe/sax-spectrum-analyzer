import os
import tempfile

import numpy as np
import plotly.graph_objs as go
import streamlit as st

from spectrum_analyzer import SpectrumAnalyzer


MIME_MAP = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".aac": "audio/aac",
}


def main():
    st.set_page_config(
        page_title="SAX Spectrum Analyzer",
        layout="wide",
    )

    st.title("SAX Spectrum Analyzer")
    st.caption(
        "Upload an audio file, play it, and inspect the frequency spectrum "
        "at any position with the slider below."
    )

    # --- Sidebar settings ---
    with st.sidebar:
        st.header("Settings")
        max_freq = st.slider(
            "Max Frequency (Hz)",
            min_value=2000,
            max_value=18000,
            value=8000,
            step=500,
        )
        n_fft_val = int(st.selectbox(
            "Resolution (n_fft)",
            options=[1024, 2048, 4096, 8192],
            index=2,
        ))

    # --- File upload ---
    uploaded_file = st.file_uploader(
        "Upload an audio file",
        type=["m4a", "mp3", "wav", "flac", "ogg", "aac"],
    )
    st.caption("Supported formats: m4a, mp3, wav, flac, ogg, aac")

    if uploaded_file is None:
        return

    # Write to temp file for librosa compatibility
    ext = os.path.splitext(uploaded_file.name)[1] or ".wav"
    tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=ext).name
    audio_bytes = uploaded_file.getvalue()
    with open(tmp_path, "wb") as f:
        f.write(audio_bytes)

    analyzer = SpectrumAnalyzer(sr=22050)

    # --- Load audio ---
    with st.spinner("Loading audio..."):
        try:
            y, sr_raw = analyzer.load_audio(tmp_path)
        except Exception as exc:
            st.error(f"Failed to load the audio file: {exc}")
            os.remove(tmp_path)
            return

    duration = analyzer.get_duration(y, sr_raw)

    st.success(
        f"**Loaded:** {uploaded_file.name}  |  "
        f"**Duration:** {duration:.2f}s  |  "
        f"**Sample Rate:** {sr_raw} Hz"
    )

    # --- Audio playback ---
    mime_type = MIME_MAP.get(ext.lower(), "audio/mpeg")
    st.audio(audio_bytes, format=mime_type)

    # --- Time slider ---
    timestamp = st.slider(
        "Position in audio (seconds)",
        min_value=0.0,
        max_value=float(duration),
        value=0.0,
        step=max(duration / 500.0, 0.001),
        format="%.3f s",
    )

    # --- Compute spectrum at selected time ---
    freqs, magnitudes_db, _, _ = analyzer.compute_spectrum_at_time(
        y, sr_raw, timestamp, n_fft=n_fft_val,
    )

    # Apply max_freq filter
    if len(freqs) > 0:
        mask = freqs <= max_freq
        plot_freqs = freqs[mask]
        plot_mag = magnitudes_db[mask] if magnitudes_db.ndim > 0 else magnitudes_db[:len(mask)]
    else:
        plot_freqs = np.array([])
        plot_mag = np.array([])

    # --- Instant spectrum figure ---
    fig_spectrum = go.Figure()
    fig_spectrum.add_trace(go.Scatter(
        x=plot_freqs,
        y=plot_mag.flatten() if hasattr(plot_mag, "flatten") else plot_mag,
        mode="lines",
        line=dict(color="#4c78af", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(76, 120, 175, 0.25)",
    ))
    fig_spectrum.update_layout(
        title=f"Instant Spectrum at {timestamp:.3f}s",
        xaxis_title="Frequency (Hz)",
        yaxis_title="Magnitude (dB)",
        xaxis_range=[0, max_freq],
        margin=dict(l=50, r=20, t=50, b=50),
        height=380,
    )

    # --- Full spectrogram (cached in session state) ---
    if "spectrogram_db" not in st.session_state:
        spec_freqs, spec_db, spec_times = analyzer.compute_full_spectrogram(
            y, sr_raw, n_fft=n_fft_val,
        )
        st.session_state.spectrogram_freqs = spec_freqs
        st.session_state.spectrogram_db = spec_db
        st.session_state.spectrogram_times = spec_times

    spec_freqs = st.session_state.spectrogram_freqs
    spec_db = st.session_state.spectrogram_db
    spec_times = st.session_state.spectrogram_times

    max_dB = float(np.max(spec_db))
    min_dB = float(np.percentile(spec_db, 5))  # avoid extreme outliers

    fig_specgram = go.Figure()
    fig_specgram.add_trace(go.Heatmap(
        z=spec_db.T,           # transpose: rows=freq, cols=time for plotly heatmap
        x=spec_times,
        y=spec_freqs,
        colorscale="YlGnBu",
        zmin=min_dB,
        zmax=max_dB,
    ))
    fig_specgram.add_vline(
        x=timestamp,
        line_width=2,
        line_dash="solid",
        line_color="red",
        annotation_text=f"{timestamp:.1f}s",
        annotation_position="top right",
    )
    fig_specgram.update_layout(
        title="Full Spectrogram (dB)",
        xaxis_title="Time (s)",
        yaxis_title="Frequency (Hz)",
        yaxis_range=[0, max_freq],
        margin=dict(l=60, r=20, t=50, b=50),
        height=420,
    )

    # --- Render charts side by side ---
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_spectrum, use_container_width=True)
    with col2:
        st.plotly_chart(fig_specgram, use_container_width=True)

    # Cleanup
    os.remove(tmp_path)

    # --- About section ---
    with st.expander("About this tool"):
        st.write(
            "Upload an audio file and inspect its frequency spectrum. "
            "The left chart shows the instantaneous magnitude at the selected time, "
            "and the right chart displays the full spectrogram with a red vertical "
            "cursor marking your current position."
        )


if __name__ == "__main__":
    main()
