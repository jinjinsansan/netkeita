import json
from collections import defaultdict

with open(r"E:\dev\Cusor\netkeita\scripts\jra_race_level_20260406.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Deduplicate by race_number key
seen = set()
composites = []
for key, val in data.items():
    uid = f"{val['date']}_{val['venue']}_{val.get('race_number','')}"
    if uid in seen:
        continue
    seen.add(uid)
    wr = val["win_rate"]
    pr = val["place_rate"]
    comp = wr * 0.4 + pr * 0.6
    composites.append((comp, val))

composites.sort(key=lambda x: x[0], reverse=True)

# Print percentiles
print(f"Total unique races: {len(composites)}")
for pct in [5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90]:
    idx = int(len(composites) * pct / 100)
    print(f"  Top {pct}%: composite >= {composites[idx][0]:.1f}")

# Print distribution with different thresholds
print("\n--- Threshold: S>=30, A>=20, B>=12, C>=5 ---")
dist = defaultdict(int)
for comp, val in composites:
    if comp >= 30: dist["S"] += 1
    elif comp >= 20: dist["A"] += 1
    elif comp >= 12: dist["B"] += 1
    elif comp >= 5: dist["C"] += 1
    else: dist["D"] += 1
for lv in "SABCD":
    print(f"  {lv}: {dist[lv]} ({dist[lv]/len(composites)*100:.1f}%)")

print("\n--- Threshold: S>=35, A>=22, B>=12, C>=5 ---")
dist2 = defaultdict(int)
for comp, val in composites:
    if comp >= 35: dist2["S"] += 1
    elif comp >= 22: dist2["A"] += 1
    elif comp >= 12: dist2["B"] += 1
    elif comp >= 5: dist2["C"] += 1
    else: dist2["D"] += 1
for lv in "SABCD":
    print(f"  {lv}: {dist2[lv]} ({dist2[lv]/len(composites)*100:.1f}%)")

# Sample S-level races
print("\n--- サンプル: S レベル (上位5件) ---")
for comp, val in composites[:5]:
    print(f"  {val['date']} {val['venue']} {val['race_name'].strip()} "
          f"win={val['win_count']}/{val['win_total']} "
          f"place={val['place_count']}/{val['place_total']} "
          f"comp={comp:.1f}")

# Sample D-level races
print("\n--- サンプル: D レベル (下位5件) ---")
for comp, val in composites[-5:]:
    print(f"  {val['date']} {val['venue']} {val['race_name'].strip()} "
          f"win={val['win_count']}/{val['win_total']} "
          f"place={val['place_count']}/{val['place_total']} "
          f"comp={comp:.1f}")
