curl -s http://127.0.0.1:5002/api/horse-detail/20260406-川崎-11/1 | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d['recent_runs'][:3]:
    print(json.dumps({
        'race_name': r.get('race_name',''),
        'venue': r.get('venue',''),
        'date': r.get('date',''),
        'race_level': r.get('race_level'),
        'race_level_detail': r.get('race_level_detail'),
    }, ensure_ascii=False))
"
