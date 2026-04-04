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
**来週月曜日に対応予定**
