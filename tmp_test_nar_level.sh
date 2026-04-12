echo "=== NAR horse detail with race level ==="
curl -s "http://127.0.0.1:5002/api/horse-detail/20260406-川崎-11/1" | python3 -c "
import sys, json
d = json.load(sys.stdin)
runs = d.get('recent_runs', [])
print(f'Horse: {d.get(\"horse_name\", \"?\")}')
print(f'is_local: {d.get(\"is_local\")}')
print(f'Recent runs: {len(runs)}')
for r in runs[:5]:
    lv = r.get('race_level', '?')
    det = r.get('race_level_detail')
    det_str = f'win={det[\"win\"]} place={det[\"place\"]}' if det else '-'
    rn = (r.get('race_name') or '').strip()
    print(f'  {r.get(\"date\",\"\")} {r.get(\"venue\",\"\")} {rn} => Lv.{lv} ({det_str})')
"
