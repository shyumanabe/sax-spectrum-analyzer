# LOG.md

## 2025-xx-xx (実装日)

- **環境構築**: uv で仮想環境作成、依存パッケージインストール（streamlit, librosa, plotly, numpy, pydub, sounddevice, scipy）
- **spectrum_analyzer.py**: librosa を用いた音声ロード、FFT/STFT による周波数解析モジュールを実装
- **app.py**: Streamlit ベースの Web UI。ファイルアップロード、オーディオ再生、スライダーで時刻選択、左に即時スペクトル、右に全体スペクトログラムを Plotly で表示
- **README.md**: プロジェクト概要・セットアップ手順・使用方法を記述
- 計算機: macOS (Apple Silicon) / User: Shu Manabe
