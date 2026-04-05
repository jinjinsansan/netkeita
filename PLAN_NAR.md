# 地方競馬（NAR）対応 — 実装計画書

## 前提条件（調査結果）

### 既に対応済みのもの
1. **プレフェッチファイル**: 地方競馬データも完全に含まれている
   - 全フィールド揃っている（馬名、騎手、オッズ、人気、枠、性齢、斤量、馬番、netkeiba race_id）
   - サンプル: 2026/04/05 → JRA 24R + NAR 34R（水沢・高知・佐賀）
   - `is_local: true` で区別されている
2. **Dロジくんバックエンド**: NAR用エンジン・ナレッジ・騎手データが完備
   - `api/v2/viewlogic_analysis.py` の `_get_engine()` で venue 名により自動切替
   - 対応会場: 大井、川崎、船橋、浦和、園田、姫路、名古屋、笠松、金沢、高知、佐賀、盛岡、水沢、門別、帯広
   - ナレッジファイル: `nar_unified_knowledge_*.json`, `nankan_jockey_knowledge_*.json`

### 未対応（今回の作業範囲）
- netkeita API サーバーが `is_local=True` を除外している
- netkeita フロントエンドは JRA 専用の UI

---

## 実装フェーズ

### Phase 1: バックエンドAPI対応（20分）

**対象ファイル**: `api/services/data_fetcher.py`, `api/main.py`

#### 1-1. `get_available_dates()` のフィルタ削除
```python
# BEFORE: JRA レースがある日のみ
jra_races = [r for r in pf.get("races", []) if not r.get("is_local", False)]
if jra_races:
    dates.append(date_str)

# AFTER: レースが1つでもあれば追加
if pf.get("races"):
    dates.append(date_str)
```

#### 1-2. `get_races()` のフィルタ削除 + `is_local` 情報を返す
```python
# Filter削除、各レースに is_local を含める
for r in races:
    result.append({
        "race_id": r.get("race_id", ""),
        "race_number": r.get("race_number", 0),
        "race_name": r.get("race_name", ""),
        "venue": r.get("venue", ""),
        "distance": r.get("distance", ""),
        "headcount": len(r.get("horses", [])),
        "start_time": r.get("start_time", ""),
        "track_condition": r.get("track_condition", ""),
        "is_local": r.get("is_local", False),  # NEW
    })
```

#### 1-3. `get_race_entries()` も `is_local` を含めて返す

#### 1-4. `/api/races/{date}` レスポンスに `is_local` を含める

#### 1-5. フルスコアAPI、horse-detail API の NAR 動作確認
- Dロジくん側は venue で自動切替なので、そのまま動くはず
- 念のため大井・川崎等で動作確認

---

### Phase 2: フロントエンド型定義とAPI呼び出し（10分）

**対象ファイル**: `frontend/src/lib/api.ts`

- `RaceSummary` 型に `is_local: boolean` 追加
- `RaceMatrix` に `is_local` 追加

---

### Phase 3: レース一覧UI（30分）

**対象ファイル**: `frontend/src/app/page.tsx` (トップページ)

#### 3-1. レースをJRA/NAR別にグルーピング
```
中山 12R
阪神 12R
---
大井 11R（地方）
川崎 12R（地方）
水沢 10R（地方）
```

#### 3-2. NARレースカードにバッジ表示
- 「地方」ラベルを右上に小さく表示
- 色分け（JRA=緑、NAR=紫 or オレンジ）

#### 3-3. トグルスイッチ追加（オプション）
- 「地方競馬を表示」のON/OFFトグル
- デフォルトON（全部表示）
- localStorage で記憶

---

### Phase 4: レース詳細ページ対応（20分）

**対象ファイル**: `frontend/src/app/race/[raceId]/page.tsx`, `frontend/src/components/HorseDetailPanel.tsx`

#### 4-1. NARレース時の調整
- 「コース別成績」は netkeiba のJRAデータなのでNARでは非表示 or 別ソース
- 「直近5走」はNARナレッジから取得されるはず（venue名で自動切替）
- 「厩舎コメント」はNAR馬にはない → 「-」表示 or セクション非表示
- 「インターネット予想」はJRAベースなので非表示 or NAR用差し替え

#### 4-2. NAR時に非表示/差替するセクションをチェック
- Stable comment tab → NARは非表示
- Internet predictions → NARは非表示  
- Jockey analysis → NAR騎手データがあるならそのまま、ないなら非表示
- Bloodline → NAR馬に適用可能か確認
- Course stats (netkeiba) → NARは非表示 or 別取得

---

### Phase 5: 動作確認・デプロイ（15分）

#### 5-1. 大井11Rなどで動作確認
- レース一覧表示
- ランキング表示
- 馬詳細ドロワー
- オッズ表示

#### 5-2. JRA側が壊れていないか確認
- 中山11R ダービー卿CT で全機能動作確認

#### 5-3. ビルド + Vercelデプロイ
- `npm run build` でエラーなし確認
- コミット + プッシュ

---

## 推定作業時間

| Phase | 内容 | 時間 |
|-------|------|------|
| 1 | バックエンドAPI対応 | 20分 |
| 2 | 型定義 | 10分 |
| 3 | レース一覧UI | 30分 |
| 4 | 詳細ページ対応 | 20分 |
| 5 | 動作確認・デプロイ | 15分 |
| **合計** | | **約1時間40分** |

---

## リスク・留意点

1. **NAR馬の近5走がJRA馬名と重複する可能性**
   - Dロジくん側のナレッジは別ファイル（`nar_unified_knowledge`）なので venue で自動切替され問題ないはず
   - 念のため確認

2. **netkeiba コース別成績**
   - netkeiba はJRA主体なのでNARレースではURL構造が違う可能性
   - NARでは非表示が無難

3. **厩舎コメント・インターネット予想**
   - これらはJRA専用のスクレイピングデータ
   - NARレースでは表示しない（データなし）

4. **CTAボタン、投票機能**
   - そのまま使えるはず（race_idベース）

5. **オッズ更新cron**
   - 現在の `scripts/update_odds.py` は JRAのみ対象
   - NARオッズは別のタイミングで更新されるため、既存プレフェッチで十分かも

---

## 段階的リリース案

- **Step 1（最小）**: レース一覧だけNAR表示、詳細は既存のまま → ユーザーが地方競馬の開催を見られるだけでも価値あり
- **Step 2**: 詳細ページもNAR対応、ランキング・直近5走・騎手分析を表示
- **Step 3**: NAR専用機能（地方競馬場ごとの特色、地方→中央移籍情報など）

## ステータス
**今日実装可能**（JRA開催中だが、既存機能を壊さないよう注意）
