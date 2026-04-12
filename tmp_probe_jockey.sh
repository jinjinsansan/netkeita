#!/bin/bash
set -e
PAYLOAD='{"race_id":"20260405-中山-11","horses":["シャドウレテオ","ルクスビッグスター","ドゥカート","ロマニアドホック","スパークルシャーリー","フクノブレーク","フリームファード","クリミナール","マイネルニコラス","タイキハフター","ダンツファイター","ホウオウスーペリア","トーアアイデル","ジェタ","アマイ","アルトゥール"],"horse_numbers":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16],"jockeys":["津村 明秀","石橋 脩","古川 吉洋","石川 裕紀人","池田 鷹一","北村 友一","原 優介","岩田 望","池田 敦哉","三浦 皇成","戸崎 圭太","北村 宏司","柴山 雄一","武 豊","田中 勝春","横山 武史"],"posts":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16],"venue":"中山","race_number":11,"distance":"芝1600m","track_condition":"良"}'
curl -s -X POST http://localhost:8000/api/v2/analysis/jockey-analysis -H 'Content-Type: application/json' -d "$PAYLOAD" > /tmp/jockey_resp.json
python3 <<'PY'
import json
d = json.load(open('/tmp/jockey_resp.json','r'))
print('top keys:', list(d.keys()))
jcs = d.get('jockey_course_stats', {})
jps = d.get('jockey_post_stats', {})
print(f'jockey_course_stats entries: {len(jcs)}')
for k, v in list(jcs.items())[:20]:
    print(f'  {k!r}: {v}')
print()
print(f'jockey_post_stats entries: {len(jps)}')
for k, v in list(jps.items())[:20]:
    print(f'  {k!r}: {v}')
print()
# horse-level
horses = d.get('horses', [])
print(f'horses (flat list): {len(horses)}')
for h in horses[:20]:
    print(f'  {h}')
PY
