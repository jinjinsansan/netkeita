# 海外レース成績の取得対応 — 来週対応予定

## 問題
直近5走のドロワーに海外遠征の成績が表示されない。

## 原因
`/opt/dlogic/backend/scripts/update_jra_weekly.py` のSQLクエリで競馬場コードを国内10場に限定している。

```sql
AND se.keibajo_code IN ('01','02','03','04','05','06','07','08','09','10')
```

JRA-VANのDBには海外遠征成績も格納されているが、このフィルタで除外されている。

## 修正箇所
1. `update_jra_weekly.py` のWHERE句から `keibajo_code` 制限を緩和（海外コード追加）
2. `KEIBAJO_MAP` に海外競馬場コードを追加（香港、ドバイ、欧州等）
3. ViewLogicEngineの `_get_venue_name` にも海外場を追加
4. 週次更新を再実行してナレッジファイルを再構築

## 確認が必要な点
- JRA-VANの海外競馬場コード一覧（A0=香港? C0=ドバイ? 等）
- jvd_seテーブルに海外レースデータが実際に存在するか確認
- 海外レースのデータ項目（タイム形式、距離単位等）が国内と同じ形式か

## 関連ファイル
- `/opt/dlogic/backend/scripts/update_jra_weekly.py` — 週次更新メインスクリプト
- `/opt/dlogic/backend/services/viewlogic_engine.py` — _get_venue_name, _get_grade_name
- `/opt/dlogic/backend/services/viewlogic_data_manager.py` — ナレッジ読み込み

## ステータス
**2026-04-07 対応完了**

## 実施内容 (2026-04-07)
- `chatbot/uma/backend/scripts/create_jra_knowledge_v2.py` の `KEIBAJO_MAP` に海外14コードを追加
- `chatbot/uma/backend/scripts/create_jra_jockey_knowledge.py` の `KEIBAJO_MAP` に同じ海外14コードを追加
- SQL WHERE 句は元々 keibajo_code フィルタが無かったため変更不要
- コメントを「JRA国内+海外遠征レースを含む」に修正

### 追加した海外競馬場コード
| コード | 国/地域 | 馬数 |
|---|---|---|
| A4 | アメリカ | 395 |
| A6 | イギリス(アスコット等) | 115 |
| A8 | イギリス(ニューマーケット等) | 194 |
| B2 | アイルランド | 30 |
| B6 | オーストラリア | 211 |
| B8 | カナダ | 1 |
| C0 | イタリア | 1 |
| C2 | ドイツ | 2 |
| C7 | UAE(ドバイ) | 390 |
| F0 | 韓国 | 14 |
| G0 | 香港 | 259 |
| K6 | サウジアラビア | 198 |
| M8 | カタール | 7 |
| N2 | バーレーン | 3 |

### 検証結果
- 直近9走に海外成績を持つ馬: **228頭**
- 着順あり (valid): **172,825件** — データ品質良好
- 地方競馬コード (30-55) は NAR ナレッジの担当範囲のため JRA 側では対象外
