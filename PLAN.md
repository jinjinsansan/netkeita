# netkeita 開発計画書

## Phase 1: MVP (目標: 2週間)

### Step 1: プロジェクト基盤構築
- [x] GitHub リポジトリ作成・連携
- [ ] 1-1. Next.js プロジェクト初期化 (App Router + Tailwind CSS + TypeScript)
- [ ] 1-2. ディレクトリ構成・ESLint・Prettier 設定
- [ ] 1-3. Vercel デプロイ設定 (プレビュー環境)
- [ ] 1-4. `.env` 設計 (API URL, LINE Login等)

### Step 2: netkeita API サーバー構築 (FastAPI)
- [ ] 2-1. FastAPI プロジェクト初期化 (`api/` ディレクトリ)
- [ ] 2-2. エンドポイント雛形作成
  - `GET /api/races?date=YYYYMMDD` — レース一覧
  - `GET /api/race/{race_id}/matrix` — ランクマトリクス
  - `GET /api/race/{race_id}/entries` — 出馬表
- [ ] 2-3. 既存プリフェッチJSON読み込みモジュール
- [ ] 2-4. 既存バックエンド(:8000)への内部HTTPクライアント
- [ ] 2-5. VPS デプロイ設定 (systemd, port 5001)

### Step 3: バックエンドAPI拡張 (既存VPS :8000)
- [ ] 3-1. `/api/v2/predictions/full-scores` エンドポイント追加
  - 全頭の dlogic_score / ilogic_score / viewlogic_score / metalogic_score を返す
- [ ] 3-2. 展開分析 (flow_score) の全頭データ返却確認
- [ ] 3-3. 騎手・血統分析の全頭データ返却確認

### Step 4: 8項目ランク算出ロジック
- [ ] 4-1. ランク算出コアモジュール (`services/ranking.py`)
  - score_to_grade() — 相対ランク判定 (S/A/B/C/D)
  - calculate_matrix() — 全頭の8項目スコア算出+ランク付与
- [ ] 4-2. 各項目のスコア抽出関数
  - 総合 (MetaLogic)
  - スピード (D-Logic)
  - 展開 (ViewLogic flow_score)
  - 騎手 (コース別複勝率)
  - 血統 (sire + broodmare コース複勝率平均)
  - 近走 (着順平均 + トレンド)
  - 馬場 (track_adjustment)
  - 期待値 (予測勝率 / オッズ)
- [ ] 4-3. ランク算出のユニットテスト
- [ ] 4-4. APIレスポンスのキャッシュ (ファイルベース or Redis)

### Step 5: フロントエンド — レース一覧ページ
- [ ] 5-1. 共通レイアウト (ヘッダー・ナビ・フッター)
- [ ] 5-2. トップページ `/` — 今週のレース一覧
  - 日付タブ (土曜/日曜)
  - 競馬場タブ (中山/阪神/中京...)
  - レースカード (R番号, レース名, 距離, 頭数)
- [ ] 5-3. API連携 (SWR or fetch + ISR)
- [ ] 5-4. モバイルレスポンシブ

### Step 6: フロントエンド — ランクマトリクス表
- [ ] 6-1. レース詳細ページ `/race/[race_id]`
  - レース情報ヘッダー (距離/馬場/天候)
- [ ] 6-2. マトリクステーブルコンポーネント
  - 左カラム固定 (枠番色 + 馬番 + 馬名)
  - 8項目は横スクロール
  - 各セル: ランク文字 + 色付きバッジ (S=金, A=赤, B=青, C=緑, D=グレー)
- [ ] 6-3. ソート機能 (項目ヘッダータップで切替)
- [ ] 6-4. モバイル横スクロール最適化 (sticky left column)

### Step 7: MVP仕上げ・デプロイ
- [ ] 7-1. Vercel 本番デプロイ
- [ ] 7-2. VPS に netkeita API デプロイ (systemd)
- [ ] 7-3. 動作確認 (実際の土日レースデータで検証)
- [ ] 7-4. パフォーマンス確認 (Lighthouse)

---

## Phase 2: 馬詳細 + 認証 (目標: 1週間)

### Step 8: 馬詳細ページ
- [ ] 8-1. `/horse/[horse_id]` ページ
- [ ] 8-2. 過去5走テーブル (着順, 会場, 距離, タイム, 騎手)
- [ ] 8-3. コース別成績サマリー
- [ ] 8-4. 血統情報表示

### Step 9: LINE Login
- [ ] 9-1. LINE Developers で新規チャネル作成
- [ ] 9-2. OAuth フロー実装 (FastAPI側)
- [ ] 9-3. フロントのログイン画面・認証状態管理
- [ ] 9-4. JWTトークン発行・検証

### Step 10: Supabase + お気に入り
- [ ] 10-1. Supabase プロジェクト作成
- [ ] 10-2. スキーマ作成 (users, favorite_horses, view_history)
- [ ] 10-3. お気に入り馬 追加/削除 API
- [ ] 10-4. マイページ UI

---

## Phase 3: 磨き込み (目標: 1週間)

### Step 11: UX改善
- [ ] 11-1. フィルタ機能 (ランクS/A以上のみ表示)
- [ ] 11-2. オッズ・人気カラム追加
- [ ] 11-3. 馬名タップで馬詳細へ遷移

### Step 12: パフォーマンス・SEO
- [ ] 12-1. ISRキャッシュ戦略 (当日5分 / 前日1時間)
- [ ] 12-2. OGP画像自動生成 (レースごと)
- [ ] 12-3. sitemap.xml / robots.txt
- [ ] 12-4. Lighthouse スコア最適化

---

## 現在の着手ポイント

**→ Step 1 から開始: Next.js プロジェクト初期化**
