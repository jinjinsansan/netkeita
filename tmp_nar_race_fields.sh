#!/bin/bash
cd /opt/dlogic/backend
./venv/bin/python3 - <<'PY'
import sys
sys.path.insert(0, '/opt/dlogic/backend')
from services.local_viewlogic_engine_v2 import LocalViewLogicEngineV2
e = LocalViewLogicEngineV2()
hd = e.local_data_manager.get_horse_data("マコトダイトウレン") if hasattr(e, 'local_data_manager') else None
if hd is None and hasattr(e, 'data_manager'):
    hd = e.data_manager.get_horse_data("マコトダイトウレン")
print("type:", type(hd).__name__)
if hd:
    print("top keys:", list(hd.keys())[:20])
    races = hd.get("races", [])
    print(f"races count: {len(races)}")
    if races:
        print("first race keys:", list(races[0].keys())[:30])
        for f in ["ZENHAN_3F", "KOHAN_3F", "CORNER1_JUNI", "CORNER3_JUNI", "CORNER4_JUNI", "TIME"]:
            if f in races[0]:
                print(f"  {f}: {races[0][f]!r}")
PY
