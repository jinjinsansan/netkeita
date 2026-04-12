#!/bin/bash
set -e
cd /opt/dlogic/netkeita-api
/opt/dlogic/backend/venv/bin/python3 - <<'PY'
import asyncio, json, sys
sys.path.insert(0, '/opt/dlogic/netkeita-api')
from services.data_fetcher import get_race_entries, async_get_analysis

async def main():
    for rid in ["20260405-水沢-6", "20260405-高知-6", "20260405-佐賀-6"]:
        date = "20260405"
        rd = get_race_entries(date, rid)
        print(f"=== {rid} ({len(rd['entries'])} horses) ===")
        print("entries jockeys:", [e.get("jockey") for e in rd["entries"]])
        fd = await async_get_analysis("/api/v2/analysis/race-flow", rd)
        print("flow top keys:", list(fd.keys()))
        print("flow_scores:", fd.get("flow_scores", {}))
        print("style_summary:", fd.get("style_summary", {}))
        print()
        jd = await async_get_analysis("/api/v2/analysis/jockey-analysis", rd)
        print("jockey top keys:", list(jd.keys()))
        jcs = jd.get("jockey_course_stats", {})
        print(f"jcs: {len(jcs)} entries")
        for k, v in list(jcs.items())[:5]:
            print(f"  {k}: {v}")
        jps = jd.get("jockey_post_stats", {})
        print(f"jps: {len(jps)} entries")
        for k, v in list(jps.items())[:5]:
            print(f"  {k}: {v}")
        print("="*60)
        print()

asyncio.run(main())
PY
