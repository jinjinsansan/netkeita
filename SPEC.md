# netkeita (ネットケイタ) — 仕様書

## 概要

毎週のJRA全レースの出走馬を **8項目のランク指数** で可視化する競馬データサイト。
予測サイトではなく「データ閲覧サイト」。netkeiba風の白基調UI、モバイルファーストで横スクロールのランクマトリクス表示。

- **サービス名**: netkeita (ネットケイタ)
- **対象**: JRA全レース (土日)
- **Dロジくんとは完全に独立** した新規サービス
- **ターゲット**: 新規ユーザー獲得 (Dlogic既存ユーザーとは別)

---

## アーキテクチャ

```
[ユーザー]
    ↓
[Vercel] Next.js (App Router, Tailwind CSS)
    ↓ API呼び出し
[VPS :5001] netkeita API (FastAPI)
    ├── GET  /api/races?date=YYYYMMDD        ← レース一覧
    ├── GET  /api/race/{race_id}/matrix      ← 8項目ランクマトリクス
    ├── GET  /api/race/{race_id}/entries      ← 出馬表
    ├── GET  /api/horse/{horse_id}            ← 馬詳細 (過去走)
    ├── POST /api/auth/line                   ← LINEログイン
    └── GET  /api/user/favorites              ← お気に入り馬
    ↓ 内部呼び出し
[VPS :8000] 既存 Dlogic Backend API (共有)
    ├── /api/v2/predictions/newspaper         ← 4エンジン予想
    ├── /api/v2/analysis/race-flow            ← 展開分析
    ├── /api/v2/analysis/jockey-analysis      ← 騎手分析
    ├── /api/v2/analysis/bloodline-analysis   ← 血統分析
    └── /api/v2/analysis/recent-runs          ← 近走分析
    ↓
[Supabase] netkeita専用プロジェクト (Dlogicとは別)
[既存 data/prefetch/] プリフェッチJSON (読み取り共有)
```

### 技術スタック

| 層 | 技術 | デプロイ先 |
|---|---|---|
| フロントエンド | Next.js (App Router) + Tailwind CSS | Vercel (別プロジェクト) |
| バックエンドAPI | FastAPI (Python) | VPS :5001 |
| 予想エンジン | 既存 Dlogic Backend | VPS :8000 (共有) |
| DB | Supabase | 別プロジェクト |
| 認証 | LINE Login | 新規チャネル |
| キャッシュ | Redis (既存共有) or ファイルベース | VPS |

---

## 評価項目 (8項目)

| # | 項目名 | データソース | ランク化の方法 |
|---|--------|-------------|---------------|
| 1 | **総合** | MetaLogicスコア (全頭) | スコア順で相対ランク |
| 2 | **スピード** | D-Logicスコア (total_score) | スコア順で相対ランク |
| 3 | **展開** | ViewLogic flow_score (本線シナリオ) | flow_score順で相対ランク |
| 4 | **騎手** | jockey_course_stats.fukusho_rate | コース複勝率で相対ランク |
| 5 | **血統** | sire_course_stats.place_rate + broodmare平均 | コース複勝率平均で相対ランク |
| 6 | **近走** | 直近5走の着順平均 + 上昇/下降トレンド | 着順平均が低い(=好走)ほど上位 |
| 7 | **馬場** | track_adjustment係数 (0.8〜1.2) | 補正係数順で相対ランク |
| 8 | **期待値** | 予測勝率 ÷ オッズ | EV値順で相対ランク |

### データソース詳細

- **直近5走**: 各馬の着順・タイム・会場・距離・オッズの全数値あり
- **馬場補正**: 3層ヒエラルキー方式 (基礎能力40% + 適応能力35% + 当日要因25%) の補正係数 0.8〜1.2
- **オッズ → 予測勝率/複勝率**: executor内の `_calc_win_probability()` / `_calc_place_probability()` で計算

### バックエンドAPI拡張が必要

**現状の問題**: 既存の `/api/v2/predictions/newspaper` は上位5頭しか返さない。全頭のスコアが必要。

**解決策**: バックエンドAPIに全頭スコア返却エンドポイントを追加
```
POST /api/v2/predictions/full-scores
  → 全頭の { horse_number, dlogic_score, ilogic_score, viewlogic_score, metalogic_score } を返す
```

---

## ランク体系 (S / A / B / C / D)

出走頭数に応じた相対ランク。頭数が変わっても割合で判定。

### 16頭立ての場合

| ランク | 順位 | 割合 | 表示 |
|--------|------|------|------|
| **S** | 1位 | トップ | 金バッジ |
| **A** | 2〜4位 | 上位25% | 赤バッジ |
| **B** | 5〜8位 | 上位50% | 青バッジ |
| **C** | 9〜12位 | 上位75% | 緑バッジ |
| **D** | 13〜16位 | 下位25% | グレーバッジ |

### ランク判定ロジック

```python
def score_to_grade(rank: int, total: int) -> str:
    if rank == 1:
        return "S"
    pct = rank / total
    if pct <= 0.25:
        return "A"
    if pct <= 0.50:
        return "B"
    if pct <= 0.75:
        return "C"
    return "D"
```

---

## UI/UX設計

### デザイン方針

- **白基調** (netkeiba風)
- **モバイルファースト**
- 馬名は左カラム固定、8項目は横スクロール
- ランクは色付きバッジで視覚的に一目瞭然

### ページ構成

```
/ (トップ)
├── 今週のレース一覧 (土曜/日曜タブ)
├── 競馬場別タブ (中山/阪神/中京...)
│
/race/{race_id} (レース詳細)
├── ランクマトリクス表 (メインコンテンツ)
├── レース情報ヘッダー (距離/馬場/天候)
│
/horse/{horse_id} (馬詳細)
├── 過去5走の成績テーブル
├── コース別成績
├── 血統情報
│
/login (LINEログイン)
/mypage (お気に入り馬/閲覧履歴)
```

### ランクマトリクス表 (モバイル版レイアウト)

```
┌─────────────────────────────────────────────────────────┐
│ 中山 12R 4歳以上2勝クラス ダ1200m 良                    │
│ [土曜] [日曜]  [中山] [阪神] [中京]                      │
├──────────┬──────────────── 横スクロール →→→ ─────────────┤
│ 馬名      │ 総合 │ 速度 │ 展開 │ 騎手 │ 血統 │ 近走 │ 馬場 │ EV │
├──────────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼────┤
│ 1.ショウナン│  S   │  A   │  B   │  A   │  S   │  A   │  B   │ S  │
│           │ 金   │ 赤   │ 青   │ 赤   │ 金   │ 赤   │ 青   │ 金 │
├──────────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼────┤
│ 2.タイセイ  │  A   │  B   │  A   │  C   │  A   │  B   │  A   │ A  │
│           │ 赤   │ 青   │ 赤   │ 緑   │ 赤   │ 青   │ 赤   │ 赤 │
└──────────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴────┘
 ← 固定 →  │← ──────── 横スクロール ──────── →│
```

### 操作フロー

1. トップページ → 日付タブ(土/日) + 競馬場タブで絞り込み
2. レース一覧からレースをタップ → ランクマトリクス表示
3. 馬名をタップ → 馬詳細ページ (過去走・血統)
4. ヘッダーの項目名タップ → その項目でソート切替
5. フィルタ: ランクS/A以上の馬だけ表示 (将来)

### 配色

```css
/* ベース (白基調) */
--bg: #ffffff;
--text: #333333;
--border: #e0e0e0;
--header-bg: #f5f5f5;

/* ランクバッジ */
--rank-s: #FFD700;  --rank-s-text: #333;   /* 金 */
--rank-a: #E53935;  --rank-a-text: #fff;   /* 赤 */
--rank-b: #1E88E5;  --rank-b-text: #fff;   /* 青 */
--rank-c: #43A047;  --rank-c-text: #fff;   /* 緑 */
--rank-d: #9E9E9E;  --rank-d-text: #fff;   /* グレー */

/* 枠番色 (JRA標準) */
--frame-1: #fff;  /* 白 */
--frame-2: #000;  /* 黒 */
--frame-3: #e00;  /* 赤 */
--frame-4: #06f;  /* 青 */
--frame-5: #fc0;  /* 黄 */
--frame-6: #0a0;  /* 緑 */
--frame-7: #f80;  /* 橙 */
--frame-8: #f6c;  /* 桃 */
```

---

## ランク算出ロジック (詳細)

```python
def calculate_matrix(race_id: str) -> list[dict]:
    """全頭の8項目ランクを算出"""

    # 1. 全データ取得 (バックエンドAPI + スクレイピング)
    entries = get_entries(race_id)
    preds = get_full_scores(race_id)        # 全頭スコア (新規API)
    flow = get_race_flow(race_id)
    jockey = get_jockey_analysis(race_id)
    blood = get_bloodline_analysis(race_id)
    recent = get_recent_runs(race_id)
    odds = get_odds(race_id)

    horses = []

    for horse in entries:
        num = horse["horse_number"]

        scores = {
            # 1. 総合: MetaLogicスコア
            "total": preds[num]["metalogic_score"],
            # 2. スピード: D-Logicスコア
            "speed": preds[num]["dlogic_score"],
            # 3. 展開: ViewLogic flow_score
            "flow": get_horse_flow_score(flow, num),
            # 4. 騎手: コース別複勝率
            "jockey": get_jockey_course_place_rate(jockey, num),
            # 5. 血統: sire + broodmare コース複勝率平均
            "bloodline": get_bloodline_avg_place_rate(blood, num),
            # 6. 近走: 着順平均 (低いほど良い → 反転してスコア化)
            "recent": calc_recent_run_score(recent, num),
            # 7. 馬場: track_adjustment係数
            "track": get_track_adjustment(preds, num),
            # 8. 期待値: 予測勝率 / (1/オッズ)
            "ev": calc_expected_value(odds, num, preds),
        }

        horses.append({
            "horse_number": num,
            "horse_name": horse["horse_name"],
            "jockey": horse["jockey"],
            "post": horse["post"],
            "scores": scores,
        })

    # 項目ごとに相対ランク付与
    num_horses = len(horses)
    for key in ["total", "speed", "flow", "jockey", "bloodline", "recent", "track", "ev"]:
        sorted_by = sorted(horses, key=lambda h: h["scores"][key], reverse=True)
        for rank, h in enumerate(sorted_by, 1):
            h.setdefault("ranks", {})[key] = score_to_grade(rank, num_horses)
            h.setdefault("raw_ranks", {})[key] = rank

    return horses
```

---

## データパイプライン

### 日次フロー

```
[毎週金曜夜] 既存 daily_prefetch.py が土日のJRA全レースをプリフェッチ
    ↓
data/prefetch/races_YYYYMMDD.json (出馬表+オッズ+予想)
    ↓
[土日朝] netkeita API 起動時にプリフェッチ読み込み
    ↓
[ユーザーアクセス] /api/race/{id}/matrix → ランク算出 → キャッシュ
    ↓
[レース当日] オッズ更新 → EV再計算 (5分間隔)
```

### キャッシュ戦略

| データ | キャッシュTTL | 更新タイミング |
|--------|-------------|---------------|
| レース一覧 | ISR 1時間 | 前日プリフェッチ時 |
| ランクマトリクス (前日) | 1時間 | プリフェッチ更新時 |
| ランクマトリクス (当日) | 5分 | オッズ変動時にEV再計算 |
| 馬詳細 (過去走) | 24時間 | ほぼ不変 |

---

## Supabase スキーマ (netkeita専用)

```sql
-- ユーザー (LINE Login)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_user_id TEXT UNIQUE NOT NULL,
    display_name TEXT,
    picture_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_seen_at TIMESTAMPTZ DEFAULT now()
);

-- お気に入り馬
CREATE TABLE favorite_horses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    horse_name TEXT NOT NULL,
    horse_id TEXT,  -- netkeiba horse_id (将来用)
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, horse_name)
);

-- 閲覧履歴 (将来用)
CREATE TABLE view_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    race_id TEXT NOT NULL,
    viewed_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 実装ロードマップ

### Phase 1: MVP (2週間)
- [ ] Next.js プロジェクト初期化 (App Router, Tailwind CSS)
- [ ] netkeita API サーバー構築 (FastAPI, VPS :5001)
- [ ] バックエンドに全頭スコアAPI追加 (`/api/v2/predictions/full-scores`)
- [ ] レース一覧ページ (日付 + 競馬場タブ)
- [ ] ランクマトリクス表 (横スクロール + 左カラム固定)
- [ ] 8項目のランク算出ロジック実装
- [ ] モバイルレスポンシブ対応
- [ ] Vercel デプロイ

### Phase 2: 馬詳細 + 認証 (1週間)
- [ ] 馬詳細ページ (過去5走 + コース別成績)
- [ ] LINE Login 連携 (新規チャネル)
- [ ] お気に入り馬機能
- [ ] Supabase セットアップ

### Phase 3: 磨き込み (1週間)
- [ ] ソート機能 (項目タップでソート切替)
- [ ] フィルタ (ランクS/A以上の馬だけ表示)
- [ ] オッズ・人気の表示カラム追加
- [ ] SEO対策 (レースごとのOGP画像)
- [ ] キャッシュ戦略 (ISR: 当日5分 / 前日1時間)
