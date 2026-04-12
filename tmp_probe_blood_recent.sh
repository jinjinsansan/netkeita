#!/bin/bash
set -e
cd /opt/dlogic/netkeita-api
/opt/dlogic/backend/venv/bin/python3 - <<'PY'
import asyncio, json, sys
sys.path.insert(0, '/opt/dlogic/netkeita-api')
from services.data_fetcher import get_race_entries, async_get_analysis
from services.ranking import _build_bloodline_map, _build_recent_map, _build_flow_map

async def main():
    rd = get_race_entries("20260405", "20260405-中山-11")
    bd = await async_get_analysis("/api/v2/analysis/bloodline-analysis", rd)
    rcd = await async_get_analysis("/api/v2/analysis/recent-runs", rd)
    fd = await async_get_analysis("/api/v2/analysis/race-flow", rd)

    print("=== BLOODLINE ===")
    print("top keys:", list(bd.keys()))
    bl = bd.get("bloodline", [])
    print(f"count: {len(bl)}")
    for h in bl[:20]:
        print(f"  #{h.get('horse_number'):02d} {h.get('horse_name','')[:14]:<14s} sire={h.get('sire_performance',{})} bm={h.get('broodmare_performance',{})}")
    bmap = _build_bloodline_map(bd)
    print("bmap:", bmap)
    print()

    print("=== RECENT-RUNS ===")
    print("top keys:", list(rcd.keys()))
    hs = rcd.get("horses", [])
    print(f"count: {len(hs)}")
    for h in hs[:20]:
        num = h.get("horse_number")
        runs = h.get("runs", [])
        finishes = [r.get("finish") or r.get("position") for r in runs]
        print(f"  #{num:02d} runs={len(runs)} finishes={finishes}")
    rmap = _build_recent_map(rcd)
    print("rmap:", rmap)
    print()

    print("=== FLOW ===")
    print("top keys:", list(fd.keys()))
    print("flow_scores:", fd.get("flow_scores", {}))
    print("style_summary:", fd.get("style_summary", {}))
    fmap = _build_flow_map(fd, rd["entries"])
    print("fmap (with fallback):")
    for e in rd["entries"]:
        n = e.get("horse_name","")
        print(f"  #{e['horse_number']:02d} {n[:14]:<14s} -> {fmap.get(n, 'MISS')}")

asyncio.run(main())
PY
