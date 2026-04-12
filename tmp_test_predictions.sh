curl -s http://127.0.0.1:5002/api/race/20260406-川崎-11/matrix | python3 -c "
import sys, json
d = json.load(sys.stdin)
horses = d.get('horses', [])
for h in horses[:9]:
    print(f\"  #{h['horse_number']} {h['horse_name'].strip()} total={h['scores']['total']} speed={h['scores']['speed']} ev={h['scores']['ev']}\")
"
