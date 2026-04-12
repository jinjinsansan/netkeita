import json, urllib.request

# Previously broken horses
checks = [
    ("20260404-%E4%B8%AD%E5%B1%B1-11", 7, "タイムトゥヘヴン"),
    ("20260404-%E4%B8%AD%E5%B1%B1-1", 9, "ウィザードオブマリ"),
    ("20260404-%E4%B8%AD%E5%B1%B1-1", 12, "エコロセレナ"),
]

for race_id, hnum, expected_name in checks:
    url = f"http://localhost:5002/api/horse-detail/{race_id}/{hnum}"
    data = json.loads(urllib.request.urlopen(url, timeout=30).read())
    name = data.get("horse_name", "?")
    runs = data.get("recent_runs", [])

    print(f"#{hnum} {name}:")
    seen = set()
    has_dupe = False
    for r in runs:
        key = f"{r.get('date','')}-{r.get('venue','')}-{r.get('race_name','')}"
        if key in seen:
            has_dupe = True
        seen.add(key)
        print(f"  {r.get('date','')} {r.get('venue','')} {r.get('race_name','?')} {r.get('finish','')}着")

    status = "STILL DUPED!" if has_dupe else "OK"
    print(f"  -> {status} ({len(runs)} runs)\n")
