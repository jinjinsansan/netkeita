import os, sys, json
sys.path.insert(0, '/opt/dlogic/linebot')

if 'scrapers.stable_comment' in sys.modules:
    del sys.modules['scrapers.stable_comment']

from scrapers.stable_comment import fetch_race_id_map, fetch_stable_comments

print('=== 20260404 中山 R1 ===')
race_map = fetch_race_id_map('20260404', '中山', is_chihou=False)
r1_id = race_map.get(1)
result = fetch_stable_comments(r1_id, is_chihou=False)
if result:
    print(f'Got {len(result)} horses')
    for k in sorted(result.keys())[:5]:
        v = result[k]
        m = v["mark"]
        t = v["trainer"]
        c = v["comment"][:80]
        print(f'  #{k}: mark={m} trainer={t} comment={c}')
else:
    print('EMPTY!')
