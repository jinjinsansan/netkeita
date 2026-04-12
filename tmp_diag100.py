import sys, json, urllib.request, urllib.parse
BASE = "https://bot.dlogicai.in/nk"

def get_json(path):
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

data = get_json("/api/races?date=20260405")
races = data.get("races", [])
venues = {}
for r in races:
    v = r.get("venue")
    venues.setdefault(v, []).append(r)

print(f"Total races: {len(races)}")
for v, rs in venues.items():
    jl = "NAR" if rs[0].get("is_local") else "JRA"
    print(f"  {jl} {v}: {len(rs)}R")

def diag_race(race_id, venue, rno, label):
    try:
        m = get_json(f"/api/race/{urllib.parse.quote(race_id)}/matrix")
        rows = m.get("horses") or m.get("rows") or []
        if not rows:
            print(f"[{label}] {venue}{rno}R: NO ROWS. keys={list(m.keys())[:10]}")
            return
        scores = [h.get("total_score", h.get("score", 0)) for h in rows]
        nonzero = sum(1 for s in scores if s and s > 0)
        smax = max(scores)
        smin = min(scores)
        print(f"[{label}] {venue}{rno}R ({len(rows)}頭): max={smax:.1f}, min={smin:.1f}, nonzero={nonzero}/{len(rows)}")
    except Exception as e:
        print(f"[{label}] {venue}{rno}R ERROR: {e}")

# JRA 中山11R, 阪神11R
# NAR 水沢, 高知, 佐賀 の 1R と上位R
targets = []
for v, rs in venues.items():
    lab = "NAR" if rs[0].get("is_local") else "JRA"
    if lab == "JRA":
        # pick R11
        for r in rs:
            if r.get("race_number") == 11:
                targets.append((r, lab))
                break
    else:
        # pick first and last
        if rs:
            targets.append((rs[0], lab))
            if len(rs) > 1:
                targets.append((rs[-1], lab))

for r, lab in targets:
    diag_race(r["race_id"], r["venue"], r["race_number"], lab)
