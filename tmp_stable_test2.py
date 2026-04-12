import sys, os
sys.path.insert(0, "/opt/dlogic/linebot")
os.chdir("/opt/dlogic/linebot")
from scrapers.stable_comment import fetch_comments_for_race
import json
result = fetch_comments_for_race("20260404", "\u4e2d\u5c71", 11, is_chihou=False)
if result:
    print(json.dumps({str(k):v for k,v in sorted(result.items())}, ensure_ascii=False, indent=2)[:3000])
else:
    print("No data")
