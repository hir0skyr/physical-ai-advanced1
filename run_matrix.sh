#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
mkdir -p results logs_eval

CKPT=1499
CONDS="nopush push1.2 push1.5 push1.75 push2.0"
METHODS="v1 v3 v3a v3b v1b v2r"
SEEDS="1 2 3"
PUSH_TIMES="10 20 30"

mk_exp () { if [ "$2" = 1 ]; then echo "go2-$1"; else echo "go2-$1s$2"; fi; }

run_one () {   # exp ckpt tag [追加引数...]
  local exp=$1 ckpt=$2 tag=$3; shift 3
  local src="results/${exp}_${ckpt}.json" dst="results/${exp}_${ckpt}_${tag}.json"
  [ -f "$dst" ] && { echo "skip ${dst}"; return; }
  [ -f "logs/${exp}/model_${ckpt}.pt" ] || { echo "!! no model: ${exp}"; return; }
  rm -f "$src"
  echo "=== ${exp} ${tag} ==="
  python patrol_eval.py -e "$exp" --ckpt "$ckpt" "$@" > "logs_eval/${exp}_${ckpt}_${tag}.log" 2>&1
  [ -f "$src" ] && mv "$src" "$dst" || echo "  !! 結果なし: logs_eval/${exp}_${ckpt}_${tag}.log"
}

# v0：外乱なしのみ（旋回できず失敗する想定）
for s in $SEEDS; do
  run_one "$(mk_exp v0 $s)" 100 nopush --max-time 60
done

for m in $METHODS; do
  for s in $SEEDS; do
    exp=$(mk_exp "$m" "$s")
    for c in $CONDS; do
      if [ "$c" = nopush ]; then
        run_one "$exp" $CKPT nopush
      else
        lv=${c#push}
        run_one "$exp" $CKPT "$c" --push-at $PUSH_TIMES --push-vel 0 "$lv"
      fi
    done
  done
done

python summarize.py