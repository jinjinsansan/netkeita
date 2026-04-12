#!/bin/bash
set -e
PAYLOAD='{"race_id":"20260405-中山-11","horses":["シャドウレテオ","ルクスビッグスター","ドゥカート","ロマニアドホック","スパークルシャーリー","フクノブレーク","フリームファード","クリミナール","マイネルニコラス","タイキハフター","ダンツファイター","ホウオウスーペリア","トーアアイデル","ジェタ","アマイ","アルトゥール"],"horse_numbers":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16],"jockeys":["津村 明秀","石橋 脩","古川 吉洋","石川 裕紀人","池田 鷹一","北村 友一","原 優介","岩田 望","池田 敦哉","三浦 皇成","戸崎 圭太","北村 宏司","柴山 雄一","武 豊","田中 勝春","横山 武史"],"posts":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16],"venue":"中山","race_number":11,"distance":"芝1600m","track_condition":"良"}'
echo "=== race-flow raw response ==="
curl -s -X POST http://localhost:8000/api/v2/analysis/race-flow -H 'Content-Type: application/json' -d "$PAYLOAD" > /tmp/flow_resp.json
python3 -c "
import json
d = json.load(open('/tmp/flow_resp.json','r'))
print('top keys:', list(d.keys()))
fs = d.get('flow_scores', {})
print(f'flow_scores entries: {len(fs)}')
for k, v in fs.items():
    print(f'  {k!r}: {v}')
print()
print('full JSON snippet (first 1500):')
import json as J
print(J.dumps(d, ensure_ascii=False)[:1500])
"
