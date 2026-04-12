import json
d = json.load(open(r"E:\dev\Cusor\netkeita\tmp_matrix.json", encoding="utf-8"))
print("=== All horses: EV + track scores ===")
for h in d["horses"]:
    s = h["scores"]
    r = h["ranks"]
    print(f'{h["horse_number"]:2d}. {h["horse_name"]:<12s}  ev={s["ev"]:<8}  ev_rank={r["ev"]}  track={s["track"]:<8}  track_rank={r["track"]}  odds={h.get("odds","N/A")}  popularity={h.get("popularity","N/A")}')

print("\n=== Scores that are all zero or identical? ===")
keys = ["total","speed","flow","jockey","bloodline","recent","track","ev"]
for k in keys:
    vals = [h["scores"][k] for h in d["horses"]]
    unique = set(vals)
    all_zero = all(v == 0 for v in vals)
    print(f"  {k:12s}: unique={len(unique)}, all_zero={all_zero}, min={min(vals)}, max={max(vals)}")
