#!/bin/bash
python3 - <<'PY'
import json
d = json.load(open('/opt/dlogic/linebot/data/prefetch/races_20260405.json'))
print('type:', type(d).__name__)
if isinstance(d, dict):
    print('keys:', list(d.keys()))
    for k, v in d.items():
        if isinstance(v, list) and v:
            print(f'  {k}: list[{len(v)}], first item keys:', list(v[0].keys())[:20] if isinstance(v[0], dict) else type(v[0]).__name__)
            # look for track_condition
            if isinstance(v[0], dict):
                for field in ['track_condition', 'baba', 'track', 'condition']:
                    if field in v[0]:
                        print(f'    {field}: {v[0][field]!r}')
            break
elif isinstance(d, list):
    print(f'list[{len(d)}]')
    if d and isinstance(d[0], dict):
        print('first item keys:', list(d[0].keys())[:20])
        for field in ['track_condition', 'baba', 'track', 'condition']:
            if field in d[0]:
                print(f'  {field}: {d[0][field]!r}')

# Also grep all fields mentioning baba/condition
def walk(obj, path=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(x in str(k).lower() for x in ('baba','condition','track','馬場')):
                if not isinstance(v, (dict, list)):
                    print(f'  found: {path}.{k} = {v!r}')
            walk(v, f'{path}.{k}')
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:3]):
            walk(item, f'{path}[{i}]')

walk(d)
PY
