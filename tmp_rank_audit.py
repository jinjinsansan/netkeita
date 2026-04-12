"""Deep audit of SABCD rank fairness for all 4/5 races."""
import json, urllib.request, urllib.parse, collections, statistics, math, sys

BASE = "https://bot.dlogicai.in/nk"
DIMS = ["total","speed","flow","jockey","bloodline","recent","track","ev"]
GRADES = ["S","A","B","C","D"]

def get_json(path):
    req = urllib.request.Request(BASE + path, headers={"Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))

def expected_grades(n):
    """Expected counts for n horses: S=1, rest 25/25/25/25 of remaining."""
    if n <= 0: return {}
    counts = {"S": 1}
    rest = n - 1
    # A: <=25% of total, then B <=50%, C <=75%, D >75%
    import math as m
    # Use the same rules as ranking.score_to_grade
    a = 0; b = 0; c = 0; d = 0
    for rank in range(2, n+1):
        pct = rank / n
        if pct <= 0.25: a += 1
        elif pct <= 0.50: b += 1
        elif pct <= 0.75: c += 1
        else: d += 1
    counts.update({"A": a, "B": b, "C": c, "D": d})
    return counts

def spearman(x, y):
    """Spearman rank correlation coefficient."""
    n = len(x)
    if n < 2: return 0.0
    rx = {v: i for i, v in enumerate(sorted(set(x)))}
    ry = {v: i for i, v in enumerate(sorted(set(y)))}
    rxs = [rx[v] for v in x]
    rys = [ry[v] for v in y]
    mx = sum(rxs)/n; my = sum(rys)/n
    num = sum((rxs[i]-mx)*(rys[i]-my) for i in range(n))
    dx = math.sqrt(sum((v-mx)**2 for v in rxs))
    dy = math.sqrt(sum((v-my)**2 for v in rys))
    if dx*dy == 0: return 0.0
    return num/(dx*dy)

# ---------- main ----------
data = get_json("/api/races?date=20260405")
races = data["races"]
print(f"Fetched {len(races)} races\n")

matrices = []
for r in races:
    rid = r["race_id"]
    try:
        m = get_json(f"/api/race/{urllib.parse.quote(rid)}/matrix")
        matrices.append((r, m))
    except Exception as e:
        print(f"ERR {rid}: {e}")

print(f"Loaded {len(matrices)} matrices\n")
print("="*80)

# -------- 1. Grade distribution check --------
print("\n### 1. Grade distribution (exp vs actual) ###")
dist_issues = []
for (r, m) in matrices:
    horses = m["horses"]
    n = len(horses)
    exp = expected_grades(n)
    for d in DIMS:
        actual = collections.Counter(h["ranks"][d] for h in horses)
        for g in GRADES:
            if actual.get(g, 0) != exp.get(g, 0):
                dist_issues.append((r["venue"], r["race_number"], n, d, g, actual.get(g,0), exp.get(g,0)))
if dist_issues:
    print(f"  FAIL: {len(dist_issues)} distribution mismatches")
    for ven, rn, n, d, g, a, e in dist_issues[:10]:
        print(f"    {ven}{rn}R n={n} dim={d} {g}: actual={a} exp={e}")
else:
    print("  OK: all races have correct S/A/B/C/D distribution")

# -------- 2. Tie explosion --------
print("\n### 2. Tie explosion (horses with same score within a race) ###")
tie_issues = []
total_dim_checks = 0
for (r, m) in matrices:
    horses = m["horses"]
    n = len(horses)
    for d in DIMS:
        vals = [round(h["scores"][d], 3) for h in horses]
        cnt = collections.Counter(vals)
        total_dim_checks += 1
        # Flag if any single value has >= 4 horses (or >50% of field)
        worst_tie = max(cnt.values())
        if worst_tie >= 4 or worst_tie > n * 0.5:
            tie_issues.append((r["venue"], r["race_number"], n, d, worst_tie, dict(cnt.most_common(3))))
print(f"  Total dim-race checks: {total_dim_checks}")
if tie_issues:
    print(f"  WARN: {len(tie_issues)} dim-races have heavy ties")
    for ven, rn, n, d, w, top in tie_issues[:20]:
        print(f"    {ven}{rn}R n={n} {d}: max_tie={w} top3_values={top}")
else:
    print("  OK: no heavy ties")

# -------- 3. Neutral-value pollution --------
print("\n### 3. Neutral value pollution (how many horses got fallback value) ###")
# Heuristic: for each race, find mode and count how many horses share it per dim
neutral_stats = {d: [] for d in DIMS}
for (r, m) in matrices:
    horses = m["horses"]
    n = len(horses)
    for d in DIMS:
        vals = [round(h["scores"][d], 3) for h in horses]
        cnt = collections.Counter(vals)
        mode_val, mode_cnt = cnt.most_common(1)[0]
        ratio = mode_cnt / n if n else 0
        neutral_stats[d].append((ratio, mode_cnt, n, r["venue"], r["race_number"], r.get("is_local",False)))
for d in DIMS:
    rs = [x[0] for x in neutral_stats[d]]
    avg = sum(rs)/len(rs) if rs else 0
    mx = max(rs) if rs else 0
    print(f"  {d}: avg mode share={avg*100:.1f}%, worst={mx*100:.1f}%")

# JRA vs NAR comparison for flow neutral pollution
print("\n  JRA vs NAR comparison (flow mode share):")
jra_flow = [x[0] for x in neutral_stats["flow"] if not x[5]]
nar_flow = [x[0] for x in neutral_stats["flow"] if x[5]]
print(f"    JRA flow mode share avg: {sum(jra_flow)/len(jra_flow)*100:.1f}%")
print(f"    NAR flow mode share avg: {sum(nar_flow)/len(nar_flow)*100:.1f}%")

# -------- 4. total vs other correlation --------
print("\n### 4. total vs component correlation (Spearman) ###")
all_total = []
all_components = {d: [] for d in DIMS if d != "total"}
for (r, m) in matrices:
    for h in m["horses"]:
        all_total.append(h["scores"]["total"])
        for d in all_components:
            all_components[d].append(h["scores"][d])
for d, vals in all_components.items():
    rho = spearman(all_total, vals)
    print(f"  total vs {d}: rho={rho:+.3f}")

# -------- 5. Odds vs total correlation --------
print("\n### 5. Odds vs total rank correlation (market agreement) ###")
total_race_rho = []
for (r, m) in matrices:
    horses = m["horses"]
    valid = [(h["scores"]["total"], h.get("odds",0)) for h in horses if h.get("odds",0) > 0]
    if len(valid) < 3: continue
    totals = [v[0] for v in valid]
    # Lower odds = higher expected strength, so invert
    inv_odds = [-v[1] for v in valid]
    rho = spearman(totals, inv_odds)
    total_race_rho.append((rho, r["venue"], r["race_number"], r.get("is_local",False)))
if total_race_rho:
    jra_rho = [x[0] for x in total_race_rho if not x[3]]
    nar_rho = [x[0] for x in total_race_rho if x[3]]
    if jra_rho:
        print(f"  JRA avg rho(total, -odds): {sum(jra_rho)/len(jra_rho):+.3f} ({len(jra_rho)} races)")
    if nar_rho:
        print(f"  NAR avg rho(total, -odds): {sum(nar_rho)/len(nar_rho):+.3f} ({len(nar_rho)} races)")
    worst = sorted(total_race_rho)[:5]
    print("  Worst-correlated races (total disagrees with odds):")
    for rho, v, rn, loc in worst:
        lab = "NAR" if loc else "JRA"
        print(f"    [{lab}] {v}{rn}R rho={rho:+.3f}")

# -------- 6. Score variance --------
print("\n### 6. Per-race score spread (std/mean) ###")
for d in ["total","speed","flow","jockey","bloodline","recent"]:
    spreads_jra = []; spreads_nar = []
    for (r, m) in matrices:
        vals = [h["scores"][d] for h in m["horses"]]
        if len(vals) < 2: continue
        mv = sum(vals)/len(vals)
        if mv == 0: continue
        sd = statistics.pstdev(vals)
        (spreads_nar if r.get("is_local") else spreads_jra).append(sd/mv)
    jra_avg = sum(spreads_jra)/len(spreads_jra) if spreads_jra else 0
    nar_avg = sum(spreads_nar)/len(spreads_nar) if spreads_nar else 0
    print(f"  {d}: JRA cv={jra_avg:.3f}  NAR cv={nar_avg:.3f}")

# -------- 7. Sanity: favorite (lowest odds) rank distribution --------
print("\n### 7. Favorite (lowest odds) total-rank distribution ###")
fav_ranks_jra = collections.Counter()
fav_ranks_nar = collections.Counter()
for (r, m) in matrices:
    horses = [h for h in m["horses"] if h.get("odds",0) > 0]
    if not horses: continue
    fav = min(horses, key=lambda h: h["odds"])
    rank = fav["ranks"]["total"]
    if r.get("is_local"):
        fav_ranks_nar[rank] += 1
    else:
        fav_ranks_jra[rank] += 1
print(f"  JRA favorites total-rank: {dict(fav_ranks_jra)}")
print(f"  NAR favorites total-rank: {dict(fav_ranks_nar)}")
print("  (healthy: S/A dominates -- favorites should often be top-rated)")
