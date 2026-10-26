#!/usr/bin/env bash
# 撮影したクリップを編集用に加工する（out/seg/ に出力）。字幕・スライドは編集ソフトで入れる。
set -eu
cd "$(dirname "$0")"
mkdir -p out/seg
ENC="-c:v libx264 -pix_fmt yuv420p -crf 18 -an"

# 1) 従来版(v0)：冒頭20秒（失敗が分かる区間に、必要なら -ss で調整）
ffmpeg -loglevel error -y -i out/s1_v0_fail.mp4 -t 20 -vf "fps=25" $ENC out/seg/c1_v0_fail.mp4

# 2) 旋回の実演：そのまま（8秒）
ffmpeg -loglevel error -y -i out/s2_turn.mp4 -vf "fps=25" $ENC out/seg/c2_turn.mp4

# 3) v1の巡回：2倍速（45秒 → 22.5秒）
ffmpeg -loglevel error -y -i out/s3_v1_patrol_top.mp4 -vf "setpts=0.5*PTS,fps=25" $ENC out/seg/c3_v1_patrol_2x.mp4

# 4) 同じ外乱の対比（左：v1、右：v3）：等倍12秒 ＋ 押された瞬間のスロー再生5.5秒 ＝ 17.5秒
#    各映像は 640x360 に縮小し、1280x720の黒帯付きキャンバスの中央に配置（上下の帯に字幕を入れる）
ffmpeg -loglevel error -y -i out/s4_v1_push1.5.mp4 -i out/s5_v3_push1.5.mp4 -filter_complex "
[0:v]fps=25,split=2[a1][a2];
[1:v]fps=25,split=2[b1][b2];
[a1]trim=start=2,setpts=PTS-STARTPTS,scale=640:360,tpad=stop_mode=clone:stop_duration=10[l1];
[b1]trim=start=2:end=14,setpts=PTS-STARTPTS,scale=640:360[r1];
[l1][r1]hstack=inputs=2,trim=duration=12,setpts=PTS-STARTPTS[p1];
[a2]trim=start=8,setpts=2*(PTS-STARTPTS),scale=640:360,fps=25,tpad=stop_mode=clone:stop_duration=10[l2];
[b2]trim=start=8:end=10.75,setpts=2*(PTS-STARTPTS),scale=640:360,fps=25[r2];
[l2][r2]hstack=inputs=2,trim=duration=5.5,setpts=PTS-STARTPTS[p2];
[p1][p2]concat=n=2:v=1:a=0,pad=1280:720:0:180:black[v]
" -map "[v]" $ENC out/seg/c4_compare.mp4

# 5) v3の巡回と外乱：2倍速（46秒 → 23秒）
ffmpeg -loglevel error -y -i out/s6_v3_patrol_push.mp4 -vf "setpts=0.5*PTS,fps=25" $ENC out/seg/c5_v3_patrol_push_2x.mp4

echo "--- 出力した長さ（秒）---"
for f in out/seg/*.mp4; do
  printf "%s\t" "$f"; ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"
done