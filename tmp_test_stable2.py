import sys, json
sys.path.insert(0, "/opt/dlogic/netkeita-api")
from services.data_fetcher import get_stable_comments

# Detailed check for 中山1R - all fields
result = get_stable_comments("20260404", "中山", 1)
if result:
    for num, data in sorted(result.items()):
        has_comment = bool(data.get("comment", "").strip())
        has_mark = bool(data.get("mark", "").strip())
        has_status = bool(data.get("status", "").strip())
        has_trainer = bool(data.get("trainer", "").strip())
        print(f"  #{num}: mark={'Y' if has_mark else 'N'} status={'Y' if has_status else 'N'} trainer={'Y' if has_trainer else 'N'} comment={'Y' if has_comment else 'N'}")

print()
# 中山11R - check all
result11 = get_stable_comments("20260404", "中山", 11)
if result11:
    count_with_comment = sum(1 for d in result11.values() if d.get("comment", "").strip())
    count_with_mark = sum(1 for d in result11.values() if d.get("mark", "").strip())
    print(f"中山11R: {len(result11)} horses, {count_with_mark} with mark, {count_with_comment} with comment")
