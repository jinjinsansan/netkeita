python3 << 'PYEOF'
import json, urllib.request
url = "http://localhost:5002/api/race/20260404-%E4%B8%AD%E5%B1%B1-11/matrix"
d = json.loads(urllib.request.urlopen(url, timeout=60).read().decode("utf-8"))
for h in d["horses"][:5]:
    print(f"  #{h['horse_number']:2d} {h['horse_name']:<14s}  odds={h.get('odds','MISSING')}")
PYEOF
