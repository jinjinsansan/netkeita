#!/bin/bash
cd /opt/dlogic/netkeita-api
/opt/dlogic/backend/venv/bin/python3 - <<'PY'
import asyncio, json, sys
sys.path.insert(0, '/opt/dlogic/netkeita-api')
from services.data_fetcher import get_race_entries, async_get_analysis

async def main():
    rd = get_race_entries("20260405", "20260405-水沢-6")
    fd = await async_get_analysis("/api/v2/analysis/race-flow", rd)
    print("main_pace:", fd.get("main_pace"))
    print("scenarios:")
    for s in fd.get("scenarios", []):
        print(f"  label={s.get('label')} pace={s.get('pace')} prob={s.get('probability')}")
        fs = s.get("flow_scores", {})
        for k, v in fs.items():
            print(f"    {k}: {v}")
    print()
    print("top-level flow_scores:", fd.get("flow_scores"))

asyncio.run(main())
PY
