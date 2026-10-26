#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
mkdir -p results logs_eval
for exp in go2-v3s2 go2-v3s3 go2-v3as2 go2-v3as3 go2-v3bs2 go2-v3bs3; do
  dst="results/${exp}_1499_push1.75.json"
  [ -f "$dst" ] && { echo "skip $dst"; continue; }
  rm -f "results/${exp}_1499.json"
  python patrol_eval.py -e "$exp" --ckpt 1499 --push-at 10 20 30 --push-vel 0 1.75 \
    > "logs_eval/${exp}_1499_push1.75.log" 2>&1
  [ -f "results/${exp}_1499.json" ] && mv "results/${exp}_1499.json" "$dst" || echo "!! failed $exp"
done
python summarize.py
