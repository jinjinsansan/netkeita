python3 << 'PYEOF'
import json, urllib.request

url = "http://localhost:5002/api/race/20260404-%E4%B8%AD%E5%B1%B1-11/matrix"
d = json.loads(urllib.request.urlopen(url, timeout=60).read().decode("utf-8"))

print(f"Race: {d['race_name']} ({d['venue']} {d['race_number']}R)")
print(f"Horses: {len(d['horses'])}")
print()

keys = ["total","speed","flow","jockey","bloodline","recent","track","ev"]
for k in keys:
    vals = [h["scores"][k] for h in d["horses"]]
    unique = len(set(vals))
    print(f"  {k:12s}: unique={unique:2d}, min={min(vals):.1f}, max={max(vals):.1f}")

print()
print("=== Top 5 horses (by total) ===")
sorted_h = sorted(d["horses"], key=lambda h: h["scores"]["total"], reverse=True)
for h in sorted_h[:5]:
    s = h["scores"]
    r = h["ranks"]
    print(f"  #{h['horse_number']:2d} {h['horse_name']:<14s}  total={s['total']:6.1f}({r['total']})  speed={s['speed']:6.1f}({r['speed']})  track={s['track']:.3f}({r['track']})  ev={s['ev']:6.1f}({r['ev']})")
PYEOF
