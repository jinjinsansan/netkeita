python3 << 'PYEOF'
import json, os, glob

prefetch_dir = "/opt/dlogic/linebot/data/prefetch"
files = sorted(glob.glob(os.path.join(prefetch_dir, "races_*.json")))

print("=== Prefetch files ===")
for f in files[-6:]:
    d = json.load(open(f))
    date = os.path.basename(f).replace("races_","").replace(".json","")
    races = d.get("races", [])
    jra = [r for r in races if not r.get("is_local", False)]
    # Check first JRA race
    if jra:
        r = jra[0]
        hn = r.get("horse_numbers", [])
        odds = r.get("odds", [])
        has_nums = any(x > 0 for x in hn)
        has_odds = any(x > 0 for x in odds)
        print(f"  {date}: {len(jra)} JRA races, horse_nums_ok={has_nums}, odds_ok={has_odds}, sample_nums={hn[:5]}, sample_odds={odds[:5]}")
    else:
        print(f"  {date}: no JRA races")
PYEOF
