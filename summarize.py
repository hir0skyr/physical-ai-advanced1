import collections, csv, glob, json, os, re

EXCLUDE = {"go2-v2"}   # 外乱コード実装前に学習した旧v2（脚注用）
runs = []
for f in sorted(glob.glob("results/*_*_*.json")):
    exp, ckpt, cond = os.path.basename(f)[:-5].split("_", 2)
    m = re.match(r"^(.+?)(?:s(\d+))?$", exp)
    method, seed = m.group(1), int(m.group(2) or 1)
    if method in EXCLUDE:
        continue
    d = json.load(open(f))
    runs.append(dict(method=method, seed=seed, cond=cond,
                     reached=d["reached"], target=d["target"], fell=d["fell"],
                     done=(not d["fell"]) and d["reached"] >= d["target"],
                     vx=d["mean_vx_err"], wz=d["mean_wz_err"]))

def cond_key(c):
    m = re.match(r"^push([\d.]+)$", c)
    return (0, 0.0) if c == "nopush" else ((1, float(m.group(1))) if m else (2, 0.0))

# 1) 1回ごとの結果
with open("results/summary_runs.csv", "w", newline="") as fp:
    w = csv.writer(fp)
    w.writerow(["method", "seed", "cond", "reached", "target", "fell", "complete", "vx_err", "wz_err"])
    for r in sorted(runs, key=lambda r: (r["method"], cond_key(r["cond"]), r["seed"])):
        w.writerow([r["method"], r["seed"], r["cond"], r["reached"], r["target"],
                    r["fell"], r["done"], round(r["vx"], 3), round(r["wz"], 3)])

# 2) 方策×条件の集計（完走数 / シード数、完走した試行の平均誤差）
g = collections.defaultdict(list)
for r in runs:
    g[(r["method"], r["cond"])].append(r)
conds = sorted({r["cond"] for r in runs}, key=cond_key)
methods = sorted({r["method"] for r in runs})

print("完走した割合（完走数/シード数）")
print("method\t" + "\t".join(conds))
for m in methods:
    cells = []
    for c in conds:
        rs = g.get((m, c), [])
        cells.append(f"{sum(x['done'] for x in rs)}/{len(rs)}" if rs else "-")
    print(m + "\t" + "\t".join(cells))

with open("results/summary_matrix.csv", "w", newline="") as fp:
    w = csv.writer(fp)
    w.writerow(["method", "cond", "seeds", "complete", "mean_reached", "vx_err_completed", "wz_err_completed"])
    for m in methods:
        for c in conds:
            rs = g.get((m, c), [])
            if not rs:
                continue
            ok = [x for x in rs if x["done"]]
            w.writerow([m, c, len(rs), len(ok), round(sum(x["reached"] for x in rs) / len(rs), 2),
                        round(sum(x["vx"] for x in ok) / len(ok), 3) if ok else "",
                        round(sum(x["wz"] for x in ok) / len(ok), 3) if ok else ""])
print("\n-> results/summary_runs.csv, results/summary_matrix.csv")