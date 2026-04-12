"""Find which NAR races have favorite ranked D."""
import json, urllib.request, urllib.parse
BASE = "https://bot.dlogicai.in/nk"
def get_json(p):
    with urllib.request.urlopen(BASE + p, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))

data = get_json("/api/races?date=20260405")
for r in data["races"]:
    if not r.get("is_local"): continue
    m = get_json(f"/api/race/{urllib.parse.quote(r['race_id'])}/matrix")
    horses = [h for h in m["horses"] if h.get("odds",0) > 0]
    if not horses: continue
    fav = min(horses, key=lambda h: h["odds"])
    if fav["ranks"]["total"] == "D":
        print(f"\n=== {r['venue']}{r['race_number']}R (fav is D) ===")
        print(f"  Favorite: #{fav['horse_number']} {fav['horse_name']} odds={fav['odds']:.1f}")
        print(f"  total={fav['scores']['total']:.1f} speed={fav['scores']['speed']:.1f} "
              f"flow={fav['scores']['flow']:.1f} jockey={fav['scores']['jockey']:.1f} "
              f"recent={fav['scores']['recent']:.1f}")
        print("  All horses sorted by total:")
        for h in sorted(m["horses"], key=lambda x: x["scores"]["total"], reverse=True):
            print(f"    #{h['horse_number']:02d} odds={h.get('odds',0):6.1f} "
                  f"total={h['scores']['total']:5.1f} rank={h['ranks']['total']}")
