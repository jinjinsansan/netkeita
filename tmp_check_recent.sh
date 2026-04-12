curl -s http://127.0.0.1:5002/api/horse-detail/20260406-川崎-11/1 | python3 -c "
import sys, json
d = json.load(sys.stdin)
runs = d.get('recent_runs', [])
if runs:
    print(json.dumps(runs[0], indent=2, ensure_ascii=False))
    print(f'\n--- Total {len(runs)} runs, keys: {list(runs[0].keys())}')
else:
    print('No recent runs')
"
