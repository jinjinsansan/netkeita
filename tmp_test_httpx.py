import sys
sys.path.insert(0, "/opt/dlogic/netkeita-api")

import httpx

payload = {
    "race_id": "20260408-川崎-11",
    "horses": ["サクラトップキッド","グリューヴルム","カゼノランナー","テスト","テスト2","テスト3","テスト4","テスト5","テスト6","テスト7","セラフィックコール"],
    "horse_numbers": [1,2,3,4,5,6,7,8,9,10,11],
}

try:
    resp = httpx.post(
        "http://localhost:8000/api/v2/predictions/newspaper",
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    print("SUCCESS:", resp.json())
except Exception as e:
    print(f"EXCEPTION TYPE: {type(e).__name__}")
    print(f"EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
