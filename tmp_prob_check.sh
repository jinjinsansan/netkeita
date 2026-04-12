python3 << 'PYEOF'
import json, urllib.request
url = "http://localhost:5002/api/race/20260404-%E4%B8%AD%E5%B1%B1-11/matrix"
d = json.loads(urllib.request.urlopen(url, timeout=60).read().decode("utf-8"))
print(f"Race: {d['race_name']}")
sorted_h = sorted(d["horses"], key=lambda h: h.get("win_prob",0), reverse=True)
for h in sorted_h[:8]:
    print(f"  #{h['horse_number']:2d} {h['horse_name']:<14s}  odds={h.get('odds',0):6.1f}  win={h.get('win_prob',0):5.1f}%  place={h.get('place_prob',0):5.1f}%")
PYEOF
