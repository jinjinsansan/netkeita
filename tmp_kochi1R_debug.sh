#!/bin/bash
cd /opt/dlogic/netkeita-api
/opt/dlogic/backend/venv/bin/python3 - <<'PY'
import asyncio, sys, json
sys.path.insert(0, '/opt/dlogic/netkeita-api')
from services.data_fetcher import get_race_entries, async_get_analysis, async_get_full_scores

async def main():
    rid = "20260405-高知-1"
    rd = get_race_entries("20260405", rid)
    print(f"entries: {len(rd['entries'])}")
    print(f"horses: {[e['horse_name'] for e in rd['entries']]}")
    print()
    fs = await async_get_full_scores(rd)
    print(f"full-scores top keys: {list(fs.keys())}")
    for h in fs.get("horses", [])[:3]:
        print(f"  {h}")
    print()
    fd = await async_get_analysis("/api/v2/analysis/race-flow", rd)
    print(f"race-flow: {list(fd.keys())}")
    print(f"  flow_scores: {fd.get('flow_scores', {})}")
    print(f"  error: {fd.get('error')}")

asyncio.run(main())
PY
