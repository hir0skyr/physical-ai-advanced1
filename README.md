# Go2 巡回警備タスク（Genesis × 強化学習）

PAI最終課題の提出コードです。Genesis上の四脚ロボット Unitree Go2 が4地点を巡回し、巡回中に押されても転倒しない歩行方策を、強化学習（PPO）で学習します。

- **ベース**：Genesis公式の歩行学習サンプル（`examples/locomotion/go2_env.py`、`go2_train.py`）
- **発見した課題**：サンプルは前進0.5 m/sの指令だけで学習するため、旋回できず巡回に使えない
- **工夫**：指令範囲の拡張、外乱（押し）を含む学習、ウェイポイント巡回の航法、全条件3シードでの評価

詳細は、提出したレポート（PDF）を参照してください。

## 結果の要約（完走した割合：完走数/3シード）

「完走」は、転倒せずに4地点×2周（全8到達）を終えたことです。外乱は、巡回中の10・20・30秒に、y方向へ速度インパルスを加えました。

| 方策 | 外乱の学習 | 終了条件 | 外乱なし | 1.2 m/s | 1.5 m/s | 1.75 m/s | 2.0 m/s |
|---|---|---|---|---|---|---|---|
| v0（サンプル設定） | なし | 10度 | 0/3 | - | - | - | - |
| v1 | なし | 10度 | 3/3 | 1/3 | 0/3 | 未評価 | 0/3 |
| v2r | 弱い（6秒ごと、±0.5 m/s） | 10度 | 3/3 | 0/3 | 0/3 | 未評価 | 0/3 |
| v1b | なし | 30度 | 3/3 | 1/3 | 0/3 | 未評価 | 0/3 |
| v3b | 弱い（6秒ごと、±0.5 m/s） | 30度 | 3/3 | 2/3 | 1/3 | 0/3 | 0/3 |
| v3a | 強い（3秒ごと、±1.0 m/s） | 10度 | 3/3 | 3/3 | 3/3 | 0/3 | 0/3 |
| v3 | 強い（3秒ごと、±1.0 m/s） | 30度 | 3/3 | 3/3 | 3/3 | 1/3 | 0/3 |

- 強い外乱で学習した方策（v3、v3a）が、1.5 m/sまで耐えた。終了条件の緩和だけの効果は、確認できなかった。
- 1.75 m/sの評価水準は、シード1の予備評価を見て追加した。
- 全シード・全条件の結果は `results/summary_runs.csv`、集計は `results/summary_matrix.csv`。
- 制約：評価は1環境・決定的な推論、外乱は瞬間的な速度インパルス、シミュレーションのみ（実機は未検証）、シード数は各条件3。

## ファイル構成

| ファイル | 内容 |
|---|---|
| `go2_env.py` | 環境。サンプルに、外乱（`apply_push`）、ウェイポイントのマーカー、録画カメラを追加 |
| `go2_train.py` | 学習。`--variant` で学習条件（v0、v1、v2、v3、v3a、v3b、v1b）を切り替え |
| `patrol_eval.py` | 巡回の航法、外乱の印加、録画、評価（結果をJSONに保存） |
| `run_train_seeds.sh` | 全方策×3シードの学習 |
| `run_matrix.sh` | 全方策×3シード×外乱条件の評価と集計 |
| `run_175.sh` | 1.75 m/sの追加評価（v3、v3a、v3bのシード2・3） |
| `summarize.py` | 評価結果（`results/*.json`）の集計 |
| `run_record.sh`、`prep_clips.sh` | 動画用の録画と、編集用クリップの加工 |
| `results/` | 評価結果（集計CSV） |

## 学習条件（`--variant`）

| variant | 指令範囲（vx / vy / 旋回） | 旋回の重み | 外乱 | 終了条件 |
|---|---|---|---|---|
| v0 | [0.5, 0.5] / [0, 0] / [0, 0]（サンプルのまま） | 0.2 | なし | 10度 |
| v1 | [0, 0.8] / [-0.3, 0.3] / [-1.0, 1.0] | 0.5 | なし | 10度 |
| v2 | v1と同じ | 0.5 | 6秒ごと、±0.5 m/s | 10度 |
| v3 | v1と同じ | 0.5 | 3秒ごと、±1.0 m/s | 30度 |
| v3a | v1と同じ | 0.5 | 3秒ごと、±1.0 m/s | 10度 |
| v3b | v1と同じ | 0.5 | 6秒ごと、±0.5 m/s | 30度 |
| v1b | v1と同じ | 0.5 | なし | 30度 |

レポートの「v2r」は、`--variant v2` で学習した方策です（外乱の実装後に学習し直したため、`r` を付けています）。

## 環境

- Windows 11 + WSL2（Ubuntu26.04）、Python 3.10、NVIDIA RTX 5060 Ti 16GB
- Genesis：1.4.4
- rsl-rl-lib：5.5.1
- PyTorch : 2.14.1
- tensordict: 0.15.2
- tensorboard: 2.21.0

Genesis本体は、公式の手順に従ってインストールしてください。コードは、Genesisのリポジトリの `examples/locomotion/` に置いて実行する想定です。

## 使い方

```bash
cd examples/locomotion   # Genesisの examples/locomotion に、このリポジトリのファイルを置く

# 学習（例：v3、シード1。実験名は「go2-<名称>」、シード2以降は「go2-<名称>s<シード>」）
python go2_train.py -e go2-v3 --variant v3 --seed 1 --max-iterations 1500
python go2_train.py -e go2-v3s2 --variant v3 --seed 2 --max-iterations 1500

# 評価（巡回。10・20・30秒に、y方向へ1.5 m/sの外乱）
python patrol_eval.py -e go2-v3 --ckpt 1499 --push-at 10 20 30 --push-vel 0 1.5

# 録画（俯瞰カメラ）
python patrol_eval.py -e go2-v3 --ckpt 1499 --cam top --record out/v3_patrol.mp4

# 全方策・全シードの学習、評価、集計
bash run_train_seeds.sh     # 約11分 × 方策数 × シード数
bash run_matrix.sh
bash run_175.sh
python summarize.py
```

- v0のベースラインは、`--variant v0 --max-iterations 101`（サンプルの既定値）で学習し、`--ckpt 100` で評価します。
- 実験名にアンダースコア（`_`）を使わないでください。`summarize.py` が、`_` で区切って条件を読み取ります。
- 学習1回（1500反復、4096並列環境）は、上記のGPUで約11分です。

## 出典とライセンス

本リポジトリのコードは、[Genesis](https://github.com/Genesis-Embodied-AI/Genesis) のサンプル（`examples/locomotion/go2_env.py`、`go2_train.py`）をベースにした派生物です。Genesisのライセンス（Apache License 2.0）に従い、`LICENSE` を同梱しています。サンプルからの変更点は、上のファイル構成の表のとおりです。
