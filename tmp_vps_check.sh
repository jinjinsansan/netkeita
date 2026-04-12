python3 << 'PYEOF'
import json
d = json.load(open("/opt/dlogic/linebot/data/prefetch/races_20260405.json"))
for r in d["races"]:
    if "中山" in r.get("race_id","") and r.get("race_number") == 11:
        print("keys:", sorted(r.keys()))
        print("horses[:3]:", r.get("horses",[])[: 3])
        print("horse_numbers[:3]:", r.get("horse_numbers",[])[: 3])
        print("posts[:3]:", r.get("posts",[])[: 3])
        print("odds[:3]:", r.get("odds",[])[: 3])
        print("jockeys[:3]:", r.get("jockeys",[])[: 3])
        break
PYEOF
