echo "=== JRA horse detail with race level ==="
curl -s http://127.0.0.1:5002/api/races | python3 -c "
import sys, json
d = json.load(sys.stdin)
jra = [r for r in d['races'] if not r.get('is_local')]
if jra:
    print(f'JRA race found: {jra[0][\"race_id\"]}')
else:
    print('No JRA races today, trying recent date...')
"

# Try a recent JRA race's horse detail
# Use a fixed known JRA race from recent data
echo ""
echo "=== Testing horse detail ==="
curl -s "http://127.0.0.1:5002/api/horse-detail/20260301-中山-11/1?date=20260301" | python3 -c "
import sys, json
d = json.load(sys.stdin)
runs = d.get('recent_runs', [])
print(f'Horse: {d.get(\"horse_name\", \"?\")}')
print(f'Recent runs: {len(runs)}')
for r in runs[:5]:
    lv = r.get('race_level', '?')
    det = r.get('race_level_detail')
    det_str = f'勝{det[\"win\"]} 複{det[\"place\"]}' if det else '-'
    print(f'  {r.get(\"date\",\"\")} {r.get(\"venue\",\"\")} {r.get(\"race_name\",\"\").strip()} => Lv.{lv} ({det_str})')
"
