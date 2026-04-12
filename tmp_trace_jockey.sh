#!/bin/bash
set -e
cd /opt/dlogic/netkeita-api
/opt/dlogic/backend/venv/bin/python3 - <<'PY'
import asyncio, json, sys
sys.path.insert(0, '/opt/dlogic/netkeita-api')
from services.data_fetcher import get_race_entries, async_get_analysis
from services.ranking import _build_jockey_map

async def main():
    rd = get_race_entries("20260405", "20260405-中山-11")
    print("entries count:", len(rd["entries"]))
    print("entry jockeys:", [e.get("jockey") for e in rd["entries"]])
    print()
    jd = await async_get_analysis("/api/v2/analysis/jockey-analysis", rd)
    print("jockey_data top keys:", list(jd.keys()))
    print()
    print("jcs sample:", list(jd.get("jockey_course_stats", {}).keys())[:5])
    print()
    jmap = _build_jockey_map(jd, rd["entries"])
    print("jmap:")
    for k, v in jmap.items():
        print(f"  {k!r}: {v}")
    print()
    print("lookup for each entry jockey:")
    for e in rd["entries"]:
        j = e.get("jockey","")
        print(f"  #{e['horse_number']:02d} {j!r} -> {jmap.get(j, 'MISS')}")

asyncio.run(main())
PY
