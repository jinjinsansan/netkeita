"""NAR Quality Check — exhaustive comparison of NAR vs JRA data quality."""
import json, urllib.request, urllib.parse

BASE = "http://localhost:5002"

def get(url):
    return json.loads(urllib.request.urlopen(url, timeout=120).read())

# Test both JRA and NAR races
test_races = [
    ("20260405-中山-11", "JRA"),  # JRA中山11R
    ("20260405-水沢-1", "NAR水沢"),
    ("20260405-高知-11", "NAR高知"),
    ("20260405-佐賀-11", "NAR佐賀"),
]

for raw_rid, label in test_races:
    print(f"\n{'='*70}")
    print(f"=== {label}: {raw_rid} ===")
    rid = urllib.parse.quote(raw_rid)
    
    # 1. Matrix
    try:
        m = get(f"{BASE}/api/race/{rid}/matrix")
    except Exception as e:
        print(f"  MATRIX ERROR: {e}")
        continue
    
    print(f"\n[MATRIX]")
    print(f"  race_name: {m.get('race_name')}")
    print(f"  venue: {m.get('venue')}")
    print(f"  distance: {m.get('distance')}")
    print(f"  track_condition: {m.get('track_condition', '-')}")
    print(f"  is_local: {m.get('is_local')}")
    print(f"  horses: {len(m.get('horses', []))}")
    
    # Check scores quality
    horses = m.get("horses", [])
    if horses:
        score_keys = ["total", "speed", "flow", "jockey", "bloodline", "recent", "track", "ev"]
        # Count horses with all scores > 0
        scored = 0
        zero_scores = {k: 0 for k in score_keys}
        for h in horses:
            s = h.get("scores", {})
            if all(s.get(k, 0) > 0 for k in score_keys):
                scored += 1
            for k in score_keys:
                if s.get(k, 0) == 0:
                    zero_scores[k] += 1
        print(f"\n  Horses with all scores>0: {scored}/{len(horses)}")
        print(f"  Zero-score counts per category:")
        for k, v in zero_scores.items():
            if v > 0:
                print(f"    {k}: {v}/{len(horses)}")
        
        # Sample horse
        h = horses[0]
        print(f"\n  Sample #{h['horse_number']} {h['horse_name']} post={h.get('post')} jockey={h.get('jockey','-')}")
        print(f"    odds={h.get('odds','-')} win_prob={h.get('win_prob','-')} place_prob={h.get('place_prob','-')}")
        print(f"    scores: {h.get('scores')}")
        print(f"    ranks: {h.get('ranks')}")
    
    # Check jockey_data
    jd = m.get("jockey_data", {})
    print(f"\n  jockey_post_stats count: {len(jd.get('jockey_post_stats', {}))}")
    print(f"  jockey_course_stats count: {len(jd.get('jockey_course_stats', {}))}")
    if jd.get("jockey_course_stats"):
        k = list(jd["jockey_course_stats"].keys())[0]
        print(f"  Sample jockey_course_stats[{k}]: {jd['jockey_course_stats'][k]}")
    
    # 2. Horse Detail for horse #1
    try:
        d = get(f"{BASE}/api/horse-detail/{rid}/1")
    except Exception as e:
        print(f"\n  HORSE DETAIL ERROR: {e}")
        continue
    
    print(f"\n[HORSE DETAIL #1]")
    print(f"  horse_name: {d.get('horse_name')}")
    print(f"  is_local: {d.get('is_local')}")
    
    # Stable comment
    sc = d.get("stable_comment", {})
    print(f"  stable_comment: {bool(sc)} (mark={sc.get('mark','-')}, has_comment={bool(sc.get('comment'))})")
    
    # Course stats
    cs = d.get("course_stats", {})
    print(f"  course_stats: {len(cs)} entries, keys={list(cs.keys())[:3]}")
    
    # Recent runs
    runs = d.get("recent_runs", [])
    print(f"  recent_runs: {len(runs)} races")
    for r in runs[:3]:
        fields_present = sum(1 for v in r.values() if v not in (None, "", 0))
        total_fields = len(r)
        print(f"    {r.get('date')} {r.get('venue')} {r.get('race_name','?')} {r.get('finish','?')}着")
        print(f"      jockey={r.get('jockey','-')} time={r.get('time','-')} agari={r.get('agari','-')} popularity={r.get('popularity','-')}")
        print(f"      corner={r.get('corner','-')} weight={r.get('weight','-')} class={r.get('class_name','-')}")
        print(f"      fields filled: {fields_present}/{total_fields}")
    
    # Bloodline
    bl = d.get("bloodline", {})
    print(f"  bloodline: sire={bl.get('sire','-')} bms={bl.get('broodmare_sire','-')}")
    sp = bl.get("sire_performance", {})
    print(f"    sire_performance: total_races={sp.get('total_races','-')} place_rate={sp.get('place_rate','-')}")
    cs_bl = bl.get("sire_course_stats", {})
    print(f"    sire_course_stats: {bool(cs_bl)} {cs_bl}")
