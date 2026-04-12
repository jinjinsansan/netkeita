import json, urllib.request, time

checks = [
    ("20260404-%E4%B8%AD%E5%B1%B1-11", 7, "タイムトゥヘヴン"),
    ("20260404-%E4%B8%AD%E5%B1%B1-1", 9, "ウィザードオブマリ"),
    ("20260404-%E4%B8%AD%E5%B1%B1-1", 12, "エコロセレナ"),
]

for race_id, hnum, name in checks:
    url = f"http://localhost:5002/api/horse-detail/{race_id}/{hnum}"
    data = json.loads(urllib.request.urlopen(url, timeout=60).read())
    runs = data.get("recent_runs", [])
    keys = [f"{r.get('date','')}{r.get('race_name','')}" for r in runs]
    unique = len(set(keys))
    status = "FIXED" if unique == len(keys) else "STILL DUPED!"
    print(f"{name}: {len(runs)} runs, {unique} unique -> {status}")
    for r in runs:
        print(f"  {r.get('date','')} {r.get('venue','')} {r.get('race_name','?')} {r.get('finish','')}着")
    print()
