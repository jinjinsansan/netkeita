import json, urllib.request, urllib.parse
BASE = "https://bot.dlogicai.in/nk"

def get_json(path):
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

data = get_json("/api/races?date=20260405")
races = data.get("races", [])
venues = {}
for r in races:
    venues.setdefault(r["venue"], []).append(r)

def summarize(rid, venue, rno, label):
    try:
        m = get_json(f"/api/race/{urllib.parse.quote(rid)}/matrix")
        horses = m.get("horses", [])
        if not horses:
            print(f"[{label}] {venue}{rno}R: NO HORSES")
            return None
        dims = ["total","speed","flow","jockey","bloodline","recent","track","ev"]
        totals = {d: [] for d in dims}
        for h in horses:
            sc = h.get("scores", {}) or {}
            for d in dims:
                v = sc.get(d, 0)
                try: totals[d].append(float(v))
                except: totals[d].append(0.0)
        nh = len(horses)
        score = {}
        for d in dims:
            vals = totals[d]
            nz = sum(1 for v in vals if v > 0)
            score[d] = (nz, nh, max(vals), sum(vals)/nh)
        t = score["total"]
        print(f"[{label}] {venue}{rno}R ({nh}頭) total: nz={t[0]}/{t[1]} max={t[2]:.1f} avg={t[3]:.1f}")
        # Per-dim coverage
        bad = [d for d in dims if score[d][0] == 0]
        low = [d for d in dims if 0 < score[d][0] < nh]
        if bad: print(f"   全馬0点項目: {bad}")
        if low: print(f"   一部0点項目: {[(d, f'{score[d][0]}/{nh}') for d in low]}")
        return score
    except Exception as e:
        print(f"[{label}] {venue}{rno}R ERROR: {e}")
        return None

print(f"=== 4/5 全 {len(races)} レース ===")
for v, rs in venues.items():
    lab = "NAR" if rs[0].get("is_local") else "JRA"
    print(f"\n--- {lab} {v} ({len(rs)}R) ---")
    # sample 3 races: first, middle, last
    idxs = [0, len(rs)//2, len(rs)-1]
    for i in sorted(set(idxs)):
        r = rs[i]
        summarize(r["race_id"], r["venue"], r["race_number"], lab)
