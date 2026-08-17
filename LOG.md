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

## 2026-08-17 (動作確認とPauseバグ修正)

- **動作確認**: `QT_QPA_PLATFORM=offscreen` でPyQt6アプリを実起動し、合成音源(440Hz+倍音, 3秒)を用いてOpen→Play→Pause→Resume→Stopの一連の流れをスクリーンショット付きで検証
- **app.py**: `_AudioPlayer.pause()` が `self._stream.pause()` を呼んでいたが、`sounddevice.OutputStream` には `pause()` メソッドが存在せず、**再生中にPauseを押すとAttributeErrorで失敗する重大バグ**を発見。`self._stream.stop()` に修正（`resume()` 側は `self._stream.start()` で再開できることを確認済み）
- 修正後、Pauseで音声とスペクトラムが凍結し、Resumeで一時停止位置から再開、Stopでサイレント基線に戻ることを画面キャプチャで確認
- **test_smoke.py**: 2件のバグを修正
  - `MainWindow`（QWidget）を生成する前に`QApplication`が存在しておらず `QWidget: Must construct a QApplication before a QWidget` でクラッシュしていたため、モジュール先頭で `QApplication` を一度だけ生成するように修正
  - `testMainWindow_creates_seeksilder()` が `MainWindow` 内部で起動する `QThread` を停止せずに関数を抜けており、オブジェクト破棄時に `QThread: Destroyed while thread '' is still running` で異常終了していたため、`win.close()` を `finally` で呼び出すように修正
  - 修正後 `uv run python test_smoke.py` が exit 0 で正常終了することを確認
- 計算機: macOS (Apple Silicon) / User: Shu Manabe

## 2026-08-17 (最大周波数コントロールの追加とサンプルレート起因の再生不具合の修正)

- **不具合の切り分け**: 「音声が実時間の1秒あたり0.5秒程度しか進まない」という報告について実機検証したところ、ユーザーの症状は「音自体がスロー・低音化して聞こえる」であることを確認。`spectrum_analyzer.py` が `librosa.load(..., sr=22050)` で全ファイルを22050Hzに強制ダウンサンプルしており、出力デバイスが22050Hzを正しくネゴシエートできない環境ではサンプルレート不整合により再生が実質半速・低ピッチになりうることが原因と判断
- **spectrum_analyzer.py**: `SpectrumAnalyzer.__init__` のデフォルト `sr` を `22050` → `None` に変更し、`librosa.load` が元ファイルのネイティブサンプリングレートを保持するように修正
- **app.py**: `_load_audio_file` も `SpectrumAnalyzer(sr=None)` に合わせて修正。ネイティブレートの保持によりナイキスト周波数が実際の音源帯域まで拡大（例: 44.1kHz音源なら22050Hzまで表示可能に）
- **app.py**: 新機能として「Max Freq」スピンボックスをツールバーに追加。ファイル読み込み時にナイキスト周波数を上限として初期化され、値を変更するとスペクトラム表示のX軸範囲(`plot_widget.setXRange`)に即座に反映される。FFTサイズ変更時は選択中の表示範囲を維持
- README.md の Features セクションを更新
- 計算機: macOS (Apple Silicon) / User: Shu Manabe

## 2026-08-17 (再生0.5倍速・スペクトラム表示ズレの根本修正)

- **症状**: サンプリングレートのネイティブ化後も「音声が0.5倍速程度で低音化して再生される」「音が聞こえるタイミングとスペクトラムのピーク表示のタイミングがズレる（無音なのにピークが出る／音が鳴っているのに出ない）」という報告があり、原因を実測で切り分けた
- **原因1（表示ズレ）**: `spectrum_analyzer.py` の `compute_full_spectrogram` が `librosa.stft(y, n_fft=n_fft)` を `hop_length` 未指定で呼んでいたため実際には `n_fft // 4` が使われる一方、続く `librosa.frames_to_time` では `hop_length=n_fft // 2` を指定しており、**表示用の時間軸が実際のフレーム間隔の2倍に引き伸ばされていた**。合成音源（1kHzクリックを0/1/2/3/4秒に配置した5秒間のマーカー音源）で検証したところ、真の2.0秒地点で無音判定(-80dB)になるなど、常に実際の再生位置の半分の時点の内容が表示されていたことを確認
  - `compute_full_spectrogram` に `hop_length` 引数を追加し、`librosa.stft` と `librosa.frames_to_time` の両方に同じ値（デフォルト `n_fft // 4`）を明示的に渡すよう修正
- **原因2（0.5倍速再生）**: このMacのデフォルト出力デバイスが Bluetooth接続の AirPods Pro（ネイティブレート48000Hz固定）であり、音声ファイル自身のサンプリングレート（多くの場合44100Hzなど）でそのまま `sounddevice.OutputStream` を開いていたため、Bluetooth側でレート変換が正しく行われず速度・ピッチがずれていたと判明
  - `app.py` に `_playback_samplerate()`（`sounddevice.query_devices(kind="output")` でデフォルト出力デバイスの実際のサンプルレートを取得）と `_resample_for_playback()`（`librosa.resample` で再生用データのみをそのレートに変換）を追加。周波数解析・スペクトログラム表示は引き続きファイルのネイティブレートを使用し、再生用データだけをデバイスのネイティブレートにリサンプルするよう分離
- **検証**: マーカー音源を実際に `sounddevice` で再生し、壁時計時刻とアプリの再生位置・スペクトラムピーク出現タイミングを比較。真のクリック時刻(0/1/2/3/4秒)に対し `reported_pos` が0.021/1.003/2.005/2.987/3.989秒とほぼ一致し、ズレは再生開始時の固定バッファリング遅延(~0.08秒)のみで時間経過に伴う拡大は見られず、速度・表示ズレとも解消したことを確認
- 既存のスモークテスト・Open/Play/Pause/Resume/Stopフローに回帰がないことも再確認
- 計算機: macOS (Apple Silicon) / User: Shu Manabe

## 2026-08-17 (再生ズレの真因: リアルタイムコールバックとGILの競合を特定・修正)

- **背景**: 前回のサンプルレート起因説の修正後も「音が途切れる・カクツキする」「音とスペクトラム表示がズレる」という報告が続いたため、ユーザー提供の実サンプル(`example/2025-08-28 22_13_35 gots 2.5.m4a`, 1ch/48000Hz/37.1秒, AirPods Pro #2＝Bluetooth接続・ネイティブレート48000Hzで一致)を使い、実際のGUIウィンドウを表示した状態で `app.exec()` の本物のイベントループを回して壁時計と再生位置を比較する診断を実施
- **切り分け1**: `sd.play(y, sr, blocking=True)`（sounddeviceの単純なブロッキング再生）で同じファイルを再生したところ 37.29秒で完了（ファイル長37.10秒、比率0.995）と完全に正常。→ **Bluetooth/AirPods自体の帯域や相性の問題ではない**ことを確定
- **原因1（確定・修正）**: `_AudioPlayer._cb()`（PortAudioのリアルタイムオーディオコールバック、48kHz/blocksize=1024で約21msごとに呼ばれる）が `threading.Lock`（`self._play_lock`）を取得していた。GUIスレッド側で30fpsごとに呼ばれる `poll_position()` も同じロックを取得するため、ロックの奪い合いによりコールバックが遅延し、それが蓄積して再生が実時間からどんどん遅れていくことを実測で確認（25秒再生で比率0.62まで悪化）。`_pos_frames`/`_finished` は単純な属性でCPythonのGILの下では読み書きが原子的なため、ロックなしで安全にアクセスできる。`_cb()` と `poll_position()` からロックを除去（`load()`/`play()`/`seek()`/`stop()` 等の非リアルタイム経路のロックはそのまま維持）
  - 副次的に `_cb()` のモノラル書き込み時のインデックス処理（`outdata[:, :av] = ...`）がファイル終端の端数フレームで軸を取り違えるバグも `outdata[:av, 0] = ...` に修正
- **原因2（確定・修正）**: ロック除去後も実ウィンドウ表示時のみ比率0.83〜0.90程度のズレが残存。オフスクリーン（実描画なし）では比率0.997と完全に正常だったため、**pyqtgraphのアンチエイリアス付きカーブ再描画（30fps）がGILを長時間占有し、リアルタイムオーディオコールバックの実行機会を奪っている**ことを特定。`main()` の `pg.setConfigOptions(antialias=True)` を `antialias=False` に変更
- **検証**: 上記2点の修正後、実際のm4aファイル・実ウィンドウ・実AirPods出力で全編(37.7秒)を再生し、壁時計37.71秒に対し再生位置37.077秒（比率0.983）、スモークテスト・Open/Play/Pause/Resume/Stopの回帰テストも含めて全て正常に完走することを確認。実サックス音の倍音列（基音+高調波、~16kHzまで）がスペクトラムに正しく表示されることも画面キャプチャで確認
- 計算機: macOS (Apple Silicon) / User: Shu Manabe

## 2026-08-17 (2音源比較機能の追加)

- **背景**: 2つのサックス音源を入力し、スペクトラムの違いを目視で比較したいという要望を受けて実装。実装方針はユーザーに以下をインタビューし決定
  - 表示レイアウト: 「重ねて表示」「上下2段」の提案に対し、ユーザーは「左右に分けるviewと上下にわけるviewを使い分けられるようにしたい」と回答 → レイアウト切替コンボボックスを追加する方針に変更
  - 再生方式: 「個別に再生」を選択（各ファイルが独立したPlay/Pause/Stop/シークバーを持つ）
  - FFT設定: 「共通設定」を選択（両ファイルに同じFFTサイズ・最大表示周波数を適用し、比較の公平性を担保）
- **app.py**: 単一チャンネル前提だった `MainWindow` を大幅にリファクタリング
  - 音声プレイヤー・スペクトログラム状態・Open/Play/Pause/Stop/シーク・プロット描画を1チャンネル分にまとめた `ChannelPanel(QWidget)` クラスを新設し、`_AudioPlayer` + 専用 `QThread` + `SpectrumWorker` + `QTimer` を各チャンネルが個別に保持するようにした（既存の単一チャンネル実装をそのまま2重化する形）
  - `MainWindow` は `ChannelPanel` を2つ（File A: 青, File B: オレンジ）生成し、`QSplitter` で並べて表示。共有のFFTサイズコンボ・最大周波数スピンボックス・レイアウト切替コンボ（「左右に並べて表示」/「上下に並べて表示」、`QSplitter.setOrientation()` を切り替え）を追加し、両チャンネルに同じ設定を適用
  - 最大周波数スピンボックスの範囲は、ロード済みチャンネルのナイキスト周波数の最大値を都度採用（片方だけロード済みでも動作し、2つ目をロードすると再計算される）
  - Python 3.9 (`.python-version` 指定) では `def foo() -> float | None:` のようなPEP 604の関数シグネチャ型注釈が実行時に `TypeError` になることが判明（変数注釈は評価されないため既存コードでは問題化していなかった）。`from __future__ import annotations` をファイル先頭に追加して解消
  - `_AudioPlayer`・`SpectrumWorker`・音声ロード/リサンプル関連のヘルパー関数は無変更（過去のGILロック競合・サンプルレート・表示ズレ修正をそのまま維持）
- **test_smoke.py**: `MainWindow.seek_slider` への直接アクセスを `channel_a`/`channel_b` 経由に修正し、2チャンネルが独立して動作すること・共有FFT設定が両チャンネルに反映されること・レイアウト切替でSplitterの向きが変わることを検証するテストを追加。実オーディオデバイスへのアクセス（スピーカーからの実再生）はテストでは行わず、状態フラグの直接確認に留めた
- **verify_dual_channel.py**（新規・動作確認用スクリプト、保存済み）: 倍音構成の異なる合成音（File A: 220Hz基音、File B: 330Hz基音）を生成し、`QFileDialog.getOpenFileName` をモックして実際のOpen File経路でFile A/Bにロード、左右レイアウト・上下レイアウトそれぞれでスクリーンショットを撮影し `verify_dual_channel_output/` に保存。2つのスペクトラムが色分けされ、周波数成分の違いが目視で明確に区別できることを確認
- `uv run python test_smoke.py` (8件) ・ `uv run python verify_dual_channel.py` ともに正常終了を確認
- README.md の Features / Usage / Project Structure を2音源比較機能に合わせて更新
- 計算機: macOS (Apple Silicon) / User: Shu Manabe
