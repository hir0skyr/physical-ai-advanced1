#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
mkdir -p out logs_eval

shoot () {   # 出力名 [patrol_eval.pyの引数...]
  local name=$1; shift
  if [ -f "out/${name}.mp4" ]; then echo "skip ${name}"; return; fi
  echo "=== ${name} ==="
  python patrol_eval.py "$@" --record "out/${name}.mp4" > "logs_eval/rec_${name}.log" 2>&1 \
    && echo "  -> out/${name}.mp4" || echo "  !! 失敗: logs_eval/rec_${name}.log を確認"
}

# S1 従来版(v0)：旋回できず失敗（俯瞰）
shoot s1_v0_fail        -e go2-v0 --ckpt 100  --max-time 25 --cam top
# S2 旋回の実演（任意）
shoot s2_turn           -e go2-v1 --ckpt 1499 --cmd 0.0 0 1.0 --max-time 8
# S3 改良版(v1)：2周の巡回（俯瞰、編集で2倍速）
shoot s3_v1_patrol_top  -e go2-v1 --ckpt 1499 --laps 2 --cam top
# S4 v1：1.5 m/sで押す（追従カメラ。転倒した時点で終了）
shoot s4_v1_push1.5     -e go2-v1 --ckpt 1499 --push-at 10 --push-vel 0 1.5 --max-time 20
# S5 v3：同じ外乱（追従カメラ）
shoot s5_v3_push1.5     -e go2-v3 --ckpt 1499 --push-at 10 --push-vel 0 1.5 --max-time 20
# S6 v3：2周、10・20・30秒に押す（俯瞰、編集で2倍速）
shoot s6_v3_patrol_push -e go2-v3 --ckpt 1499 --laps 2 --push-at 10 20 30 --push-vel 0 1.5 --cam top