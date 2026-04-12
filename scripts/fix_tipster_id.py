"""Fix tipster_id on existing articles posted by admin on behalf of K-SuKe."""
import json
import redis

r = redis.Redis(host="localhost", port=6379, db=5, decode_responses=True)

TIPSTER_ID = "managed_c56714ae5ad24e099ff8c09824ddb2ad"
TARGET_SLUGS = ["k-suke-2604081248", "k-suke-2604072310"]

for slug in TARGET_SLUGS:
    key = f"nk:article:{slug}"
    raw = r.get(key)
    if not raw:
        print(f"NOT FOUND: {slug}")
        continue
    data = json.loads(raw)
    old_tipster = data.get("tipster_id", "")
    old_ct = data.get("content_type", "")
    data["tipster_id"] = TIPSTER_ID
    if not data.get("content_type") or data["content_type"] not in ("article", "prediction"):
        data["content_type"] = "article"
    r.set(key, json.dumps(data, ensure_ascii=False))
    print(f"Fixed {slug}: tipster_id '{old_tipster}' -> '{TIPSTER_ID}', content_type '{old_ct}' -> '{data['content_type']}'")

print("Done.")
