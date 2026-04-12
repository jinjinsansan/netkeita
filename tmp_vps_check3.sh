python3 << 'PYEOF'
import json

d = json.load(open("/opt/dlogic/linebot/data/prefetch/races_20260404.json"))
for r in d["races"]:
    if not r.get("is_local", False):
        venue = r.get("venue","")
        rnum = r.get("race_number",0)
        odds = r.get("odds", [])
        nums = r.get("horse_numbers", [])
        has_odds = any(x > 0 for x in odds)
        print(f"  {venue} {rnum:2d}R  nums={nums[:3]}  odds={odds[:3]}  has_odds={has_odds}")
PYEOF
