# LOG.md

## 2025-xx-xx (実装日)

- **環境構築**: uv で仮想環境作成、依存パッケージインストール（streamlit, librosa, plotly, numpy, pydub, sounddevice, scipy）
- **spectrum_analyzer.py**: librosa を用いた音声ロード、FFT/STFT による周波数解析モジュールを実装
- **app.py**: Streamlit ベースの Web UI。ファイルアップロード、オーディオ再生、スライダーで時刻選択、左に即時スペクトル、右に全体スペクトログラムを Plotly で表示
- **README.md**: プロジェクト概要・セットアップ手順・使用方法を記述
- 計算機: macOS (Apple Silicon) / User: Shu Manabe

## 2026-08-15 (バグ修正と動作確認)

- **app.py**: `_thread.started.connect(self._player.load_wrapped)` が未定義メソッドを参照するバグを修正。`_thread.start()` に変更し、ファイルロード時に直接 `_player.load(y, sr)` を呼ぶように改善
- **app.py**: `_on_playback_finished` で `_player.stop()` と `_show_silent_spectrum()` を呼び出す処理を追加（再生完了後にストリームが終了しない問題を解消）
- **app.py**: `_load_audio_file` 内の不要なステレオチェックを削除（`librosa.load(mono=True)` ですでに Mono に変換されるため）
- **pyproject.toml**: `soundfile` を依存リストに追加（スモークテストで必要なパッケージだった）
- **pyproject.toml**: entry point を `sax_spectrum_analyzer:main` から `app:main` に修正（実際のメイン関数の場所と一致させる）
- **README.md**: Streamlit → PyQt6 への移行を反映し、使用方法を `uv run python app.py` に更新
- スモークテスト (`test_smoke.py`) を正常に通過確認
- 計算機: macOS (Apple Silicon) / User: Shu Manabe
