#!/bin/bash
cd /opt/dlogic/netkeita-api
/opt/dlogic/backend/venv/bin/python3 - <<'PY'
import asyncio, sys, json
sys.path.insert(0, '/opt/dlogic/netkeita-api')
from services.data_fetcher import get_race_entries, async_get_full_scores

async def main():
    for rid in ["20260405-中山-11", "20260405-高知-6", "20260405-水沢-6"]:
        rd = get_race_entries("20260405", rid)
        fs = await async_get_full_scores(rd)
        print(f"=== {rid} ===")
        print(f"top keys: {list(fs.keys())}")
        for h in fs.get("horses", []):
            print(f"  #{h.get('horse_number'):02d} track_adj={h.get('track_adjustment')} dlogic={h.get('dlogic_score')} meta={h.get('metalogic_score')}")
        print()

asyncio.run(main())
PY
