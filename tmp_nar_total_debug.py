"""Find out why NAR total rank disagrees with odds."""
import json, urllib.request, urllib.parse

BASE = "https://bot.dlogicai.in/nk"
def get_json(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

data = get_json("/api/races?date=20260405")
# Look at 高知6R (spearman -0.782)
for r in data["races"]:
    if r["venue"] == "高知" and r["race_number"] == 6:
        rid = r["race_id"]; break

m = get_json(f"/api/race/{urllib.parse.quote(rid)}/matrix")
print(f"=== {r['venue']}{r['race_number']}R ===")
print(f"{'#':<3}{'name':<18}{'odds':>7}{'total':>8}{'rank':>5}  {'speed':>6}{'flow':>6}{'jockey':>7}{'blood':>6}{'recent':>7}")
horses = m["horses"]
for h in sorted(horses, key=lambda x: x.get("odds", 9999)):
    sc = h["scores"]
    rk = h["ranks"]
    name = h["horse_name"][:16]
    print(f"{h['horse_number']:<3}{name:<18}{h.get('odds',0):>7.1f}{sc['total']:>8.1f}{rk['total']:>5}  "
          f"{sc['speed']:>6.1f}{sc['flow']:>6.1f}{sc['jockey']:>7.1f}{sc['bloodline']:>6.1f}{sc['recent']:>7.1f}")

# Check: what is the source of 'total'? it's metalogic_score from full-scores API
# Print the distinct totals and speeds side by side
print(f"\nrace field max/min:")
for d in ["total","speed","flow","jockey","bloodline","recent","ev"]:
    vals = [h["scores"][d] for h in horses]
    print(f"  {d}: min={min(vals):.1f} max={max(vals):.1f} range={max(vals)-min(vals):.1f}")
