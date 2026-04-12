#!/bin/bash
cd /opt/dlogic/netkeita-api
/opt/dlogic/backend/venv/bin/python3 - <<'PY'
import sys, json
sys.path.insert(0, '/opt/dlogic/netkeita-api')
from services.data_fetcher import get_race_entries

for rid in ["20260405-中山-11", "20260405-高知-6", "20260405-水沢-6"]:
    rd = get_race_entries("20260405", rid)
    print(f"{rid}: track_condition={rd.get('track_condition')!r}  is_local={rd.get('is_local')}")
PY
