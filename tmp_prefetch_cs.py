import sys
sys.path.insert(0, "/opt/dlogic/netkeita-api")
sys.path.insert(0, "/opt/dlogic/linebot")
from services.course_stats_scraper import fetch_course_stats_for_race

stats = fetch_course_stats_for_race("202606030311")
print(f"Fetched: {len(stats)} horses")
for num, s in sorted(stats.items()):
    labels = list(s.keys()) if s else []
    print(f"  #{num}: {labels}")
