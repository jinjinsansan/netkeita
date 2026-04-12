import sys, os
sys.path.insert(0, "/opt/dlogic/dlogic-agent")
os.chdir("/opt/dlogic/dlogic-agent")
from scrapers.stable_comment import fetch_comments_for_race
import json
result = fetch_comments_for_race("20260404", "中山", 11, is_chihou=False)
if result:
    for num, data in sorted(result.items()):
        print(f"#{num} {data['horse_name']} mark={data['mark']} status={data['status']}")
        if data['comment']:
            print(f"   → {data['comment'][:80]}")
else:
    print("No data")
