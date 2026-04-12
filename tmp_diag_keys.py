import json, urllib.request, urllib.parse
BASE = "https://bot.dlogicai.in/nk"

def get_json(path):
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

# pick 中山11R race_id
data = get_json("/api/races?date=20260405")
for r in data["races"]:
    if r.get("venue") == "中山" and r.get("race_number") == 11:
        rid = r["race_id"]
        print("race_id:", rid)
        m = get_json(f"/api/race/{urllib.parse.quote(rid)}/matrix")
        print("top keys:", list(m.keys()))
        for k in ["horses", "rows", "entries", "matrix"]:
            if k in m:
                print(f"  {k}: {type(m[k])}, len={len(m[k]) if hasattr(m[k], '__len__') else '?'}")
                if isinstance(m[k], list) and m[k]:
                    print(f"    first item keys: {list(m[k][0].keys())[:20]}")
                    print(f"    first item sample: {json.dumps(m[k][0], ensure_ascii=False)[:500]}")
        break
