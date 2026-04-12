python3 << 'PYEOF'
import json, urllib.request

# Check 4/4 中山11R matrix
url = "http://localhost:5002/api/race/20260404-%E4%B8%AD%E5%B1%B1-11/matrix"
d = json.loads(urllib.request.urlopen(url).read().decode("utf-8"))

print(f"Race: {d['race_name']} ({d['venue']} {d['race_number']}R)")
print(f"Horses: {len(d['horses'])}")
print()

keys = ["total","speed","flow","jockey","bloodline","recent","track","ev"]
for k in keys:
    vals = [h["scores"][k] for h in d["horses"]]
    unique = len(set(vals))
    print(f"  {k:12s}: unique={unique:2d}, min={min(vals):.1f}, max={max(vals):.1f}")

print()
print("=== Top 3 horses ===")
for h in d["horses"][:3]:
    print(f"  #{h['horse_number']} {h['horse_name']:<12s}  scores={h['scores']}  ranks={h['ranks']}")
PYEOF
