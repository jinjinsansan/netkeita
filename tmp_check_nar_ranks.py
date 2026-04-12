import json, urllib.request, urllib.parse, collections
BASE = "https://bot.dlogicai.in/nk"
def get_json(p):
    with urllib.request.urlopen(BASE + p, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))
data = get_json("/api/races?date=20260405")
dims = ["total","speed","flow","jockey","bloodline","recent","track","ev"]
for v_target in ["水沢", "高知", "佐賀"]:
    for r in data["races"]:
        if r["venue"] == v_target and r["race_number"] == 6:
            rid = r["race_id"]; break
    else:
        continue
    m = get_json(f"/api/race/{urllib.parse.quote(rid)}/matrix")
    hs = m["horses"]
    print(f"\n=== {v_target}6R ({len(hs)}頭) ===")
    # Print scores for all
    for h in hs:
        sc = h["scores"]
        rk = h["ranks"]
        print(f"  #{h['horse_number']:02d} {h['horse_name'][:14]:<14s} total={sc['total']:5.1f}({rk['total']}) "
              f"speed={sc['speed']:5.1f}({rk['speed']}) flow={sc['flow']:5.1f}({rk['flow']}) "
              f"jockey={sc['jockey']:5.1f}({rk['jockey']}) blood={sc['bloodline']:5.1f}({rk['bloodline']}) "
              f"recent={sc['recent']:5.1f}({rk['recent']})")
