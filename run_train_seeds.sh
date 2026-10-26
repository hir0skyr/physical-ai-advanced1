#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
mkdir -p logs_train

ITERS=1500
SEEDS="1 2 3"
# 名前:variant（v2rは、variantがv2）
METHODS="v1:v1 v3:v3 v3a:v3a v3b:v3b v1b:v1b v2r:v2"

mk_exp () { if [ "$2" = 1 ]; then echo "go2-$1"; else echo "go2-$1s$2"; fi; }

# ベースライン v0（101反復、最終モデルは model_100.pt）
for s in $SEEDS; do
  exp=$(mk_exp v0 $s)
  if [ -f "logs/${exp}/model_100.pt" ]; then echo "skip ${exp}"; continue; fi
  python go2_train.py -e "$exp" --variant v0 --seed "$s" --max-iterations 101 > "logs_train/${exp}.log" 2>&1
done

for m in $METHODS; do
  name=${m%%:*}; var=${m##*:}
  for s in $SEEDS; do
    exp=$(mk_exp "$name" "$s")
    if [ -f "logs/${exp}/model_$((ITERS-1)).pt" ]; then echo "skip ${exp}"; continue; fi
    echo "=== train ${exp} (variant=${var}, seed=${s}) ==="
    python go2_train.py -e "$exp" --variant "$var" --seed "$s" --max-iterations $ITERS > "logs_train/${exp}.log" 2>&1
  done
done