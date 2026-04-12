"""Try different total reweighting strategies and measure odds correlation."""
import json, urllib.request, urllib.parse, math, collections

BASE = "https://bot.dlogicai.in/nk"
def get_json(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def spearman(x, y):
    n = len(x)
    if n < 2: return 0.0
    rx = {v: i for i,v in enumerate(sorted(set(x)))}
    ry = {v: i for i,v in enumerate(sorted(set(y)))}
    rxs = [rx[v] for v in x]; rys = [ry[v] for v in y]
    mx = sum(rxs)/n; my = sum(rys)/n
    num = sum((rxs[i]-mx)*(rys[i]-my) for i in range(n))
    dx = math.sqrt(sum((v-mx)**2 for v in rxs))
    dy = math.sqrt(sum((v-my)**2 for v in rys))
    if dx*dy == 0: return 0.0
    return num/(dx*dy)

data = get_json("/api/races?date=20260405")
races = data["races"]

all_matrices = []
for r in races:
    try:
        m = get_json(f"/api/race/{urllib.parse.quote(r['race_id'])}/matrix")
        all_matrices.append((r, m))
    except Exception: pass

# Formulas to test (each returns a new "total")
def f_current(h):  # current
    return h["scores"]["total"]
def f_speed_only(h):  # speed
    return h["scores"]["speed"]
def f_mix_a(h):
    s = h["scores"]
    return 0.40*s["speed"] + 0.15*s["recent"] + 0.15*s["jockey"] + 0.10*s["flow"] + 0.10*s["bloodline"] + 0.10*s["total"]
def f_mix_b(h):
    s = h["scores"]
    # Components normalized to approximately 0-100 range
    return 0.30*s["speed"] + 0.20*s["recent"] + 0.20*s["jockey"] + 0.15*s["flow"] + 0.10*s["bloodline"] + 0.05*s["total"]
def f_mix_c(h):
    s = h["scores"]
    # Lean on recent + speed + jockey strongly
    return 0.35*s["speed"] + 0.25*s["recent"] + 0.20*s["jockey"] + 0.10*s["flow"] + 0.10*s["bloodline"]
def f_mix_d(h):
    s = h["scores"]
    # Pair metalogic total with market-aligned boosters
    base = s["total"]  # 25-50 range
    # Add components normalized around 0
    return base * 0.4 + s["speed"] * 0.3 + s["recent"] * 0.15 + s["jockey"] * 0.15
def f_mix_e(h):
    s = h["scores"]
    # Heavy on recent form + speed
    return s["speed"] * 0.5 + s["recent"] * 0.3 + s["jockey"] * 0.2
def f_mix_c_plus_meta(h):
    s = h["scores"]
    c = 0.35*s["speed"] + 0.25*s["recent"] + 0.20*s["jockey"] + 0.10*s["flow"] + 0.10*s["bloodline"]
    return c * 0.85 + s["total"] * 0.15
def f_mix_c_70(h):
    s = h["scores"]
    c = 0.35*s["speed"] + 0.25*s["recent"] + 0.20*s["jockey"] + 0.10*s["flow"] + 0.10*s["bloodline"]
    return c * 0.70 + s["total"] * 0.30
def f_mix_c_90(h):
    s = h["scores"]
    c = 0.35*s["speed"] + 0.25*s["recent"] + 0.20*s["jockey"] + 0.10*s["flow"] + 0.10*s["bloodline"]
    return c * 0.90 + s["total"] * 0.10

FORMS = {
    "current": f_current,
    "speed_only": f_speed_only,
    "mix_a": f_mix_a,
    "mix_b": f_mix_b,
    "mix_c": f_mix_c,
    "mix_d": f_mix_d,
    "mix_e": f_mix_e,
    "mix_c+meta15": f_mix_c_plus_meta,
    "mix_c70+meta30": f_mix_c_70,
    "mix_c90+meta10": f_mix_c_90,
}

for name, f in FORMS.items():
    jra_rhos = []; nar_rhos = []
    fav_ranks_jra = collections.Counter()
    fav_ranks_nar = collections.Counter()
    for (r, m) in all_matrices:
        horses = [h for h in m["horses"] if h.get("odds",0) > 0]
        if len(horses) < 3: continue
        totals = [f(h) for h in horses]
        inv_odds = [-h["odds"] for h in horses]
        rho = spearman(totals, inv_odds)
        if r.get("is_local"):
            nar_rhos.append(rho)
        else:
            jra_rhos.append(rho)
        # Favorite rank check: is fav in top 30% by this formula?
        sorted_h = sorted(range(len(horses)), key=lambda i: totals[i], reverse=True)
        fav_idx = min(range(len(horses)), key=lambda i: horses[i]["odds"])
        fav_rank_pos = sorted_h.index(fav_idx) + 1
        n = len(horses)
        pct = fav_rank_pos / n
        if pct == 1/n: grade = "S"
        elif pct <= 0.25: grade = "A"
        elif pct <= 0.50: grade = "B"
        elif pct <= 0.75: grade = "C"
        else: grade = "D"
        if r.get("is_local"): fav_ranks_nar[grade] += 1
        else: fav_ranks_jra[grade] += 1

    jra_avg = sum(jra_rhos)/len(jra_rhos) if jra_rhos else 0
    nar_avg = sum(nar_rhos)/len(nar_rhos) if nar_rhos else 0
    print(f"{name:<12}  JRA rho={jra_avg:+.3f}  NAR rho={nar_avg:+.3f}   "
          f"JRA fav-top{{S+A+B}}={fav_ranks_jra['S']+fav_ranks_jra['A']+fav_ranks_jra['B']}/{sum(fav_ranks_jra.values())}  "
          f"NAR fav-top{{S+A+B}}={fav_ranks_nar['S']+fav_ranks_nar['A']+fav_ranks_nar['B']}/{sum(fav_ranks_nar.values())}")
