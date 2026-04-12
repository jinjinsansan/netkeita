import json
import redis

r = redis.Redis(host="127.0.0.1", port=6379, db=3, decode_responses=True)
PREFIX = "nk:racelevel"
TTL = 86400 * 365

with open("/tmp/jra_race_level.json", "r", encoding="utf-8") as f:
    data = json.load(f)

pipe = r.pipeline(transaction=False)
for key, val in data.items():
    pipe.set(f"{PREFIX}:{key}", json.dumps(val, ensure_ascii=False), ex=TTL)
pipe.execute()
print(f"Loaded {len(data)} entries into Redis db=3")
