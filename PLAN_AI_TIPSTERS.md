# AI予想家キャラクター自動投稿機能 — 開発仕様書

**作成日**: 2026-04-16
**ステータス**: 設計フェーズ（未着手）
**作成者**: マネージャー（Droid）
**監督**: 仁さん

---

## 1. 概要

netkeita に **3キャラクターの AI 予想家** を常駐させ、毎日すべてのレース（JRA + NAR）に対して、各キャラの個性に沿った **日本語の予想記事を自動生成・自動投稿** する機能。

新規公開直後でもサイト内に「予想家が毎日予想を書いている」賑わいを演出し、ユーザーが **キャラごとに予想を追体験・比較・信頼できる予想家を発見** する体験を提供する。

### 1.1 目的

- 予想記事の「量」を確保して SEO・回遊率を上げる
- キャラクターの個性差で **同レース3記事 = 多角的な視点** を提供
- 的中率・回収率を自動集計し、キャラ別の「成績表」で継続的にユーザーを呼び戻す
- 生身の予想家が揃うまでの **初動ブート** としても機能する

### 1.2 スコープ外（Non-Goals）

- リアルタイム予想（直前のオッズ変動に追従）は対象外（初版は朝一発）
- 画像付きサムネイル自動生成（Phase 2 で検討）
- 3キャラ以上のスケールアウト（将来拡張、初版は3固定）
- 有料記事（`is_premium: true`）の自動生成（初版は全て無料）

---

## 2. 3キャラクター仕様

### 2.1 キャラクター一覧（初版案）

| ID (表示名) | キャッチフレーズ | パーソナリティ | 本命選定ロジック |
|---|---|---|---|
| **netkeita本紙・山田** | 重賞を中心に本命主義で読み解く | 本紙記者風・堅実・文章は新聞記事調 | 総合ランク A 以上の最上位人気馬 |
| **データ分析官・西村** | 8項目スコアと期待値で勝つ | データ派・淡々・数値引用多め | 期待値（予測勝率 ÷ オッズ）最上位 |
| **穴党のケンジ** | 人気薄の一発で回収率重視 | 穴党・熱血・煽り気味 | 7番人気以下 × 総合 B 以上 |

※ 最終的なキャラ名・ロジックは着手前に仁さん承認。

### 2.2 各キャラの出力フォーマット

各記事に以下を含む：

- **タイトル**: `{レース名} 予想｜{キャラ名}の本命は◎{馬名}`
- **preview_body**: 100字前後の導入（無料プレビュー・OGP用）
- **body (Markdown)**:
  - ①レース概要（距離・馬場・頭数）
  - ②キャラ視点の軸馬解説（◎）
  - ③相手馬（○△）の選定理由
  - ④消しポイント（✖）※ケンジのみ
  - ⑤買い目（bet_method に同期）
  - ⑥締め（キャラの決め台詞）
- **bet_method**: 馬連 / 3連複 / ワイド 等（キャラ固有）
- **ticket_count**: 点数

---

## 3. アーキテクチャ

### 3.1 全体フロー

```
┌──────────────────────────────────────────────────────────────┐
│  cron (VPS: /opt/dlogic/netkeita-api/scripts/)                │
│   - JRA: 土日 6:00 JST                                         │
│   - NAR: 毎日 14:00 JST(地方競馬発表後)                        │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
  ①  data_fetcher.get_races(today)
     → 今日の JRA + NAR レース一覧（race_id, venue, 発走時刻）
                           │
                           ▼
  ②  各レースごとに以下を並行取得:
     - ranking.calculate_matrix(race_id) → 8項目スコア
     - data_fetcher.get_race_entries(race_id) → 出走馬・オッズ
     - get_full_scores() → Dlogic バックエンドの詳細スコア
                           │
                           ▼
  ③  3キャラ × レース数 回、Claude API を呼び出し
     - システムプロンプト: キャラ固有のパーソナリティ
     - ユーザープロンプト: レースデータ（JSON）
     - 出力形式: 厳格 JSON（title/body/preview_body/picks/bet_method/ticket_count）
                           │
                           ▼
  ④  バリデーション
     - 馬名がデータに存在するか
     - 本命/対抗/単穴が重複しないか
     - 本文文字数（300〜3000字）
     - 失敗した記事はスキップしてログのみ
                           │
                           ▼
  ⑤  POST /api/articles  (X-Internal-Key ヘッダー認証)
     - content_type: "prediction"
     - tipster_id: <各キャラの managed_xxx ID>
     - race_id: <レースID>
     - status: "published"
     - is_premium: false（初版）
                           │
                           ▼
  ⑥  Next.js 側で自動表示
     - /tipsters/{managed_id}    → キャラの予想一覧
     - /race/{race_id}           → レースに紐づく全予想
     - /articles                 → サイト全体の最新記事フィード
     - /sitemap.xml              → SEO用に自動反映
```

### 3.2 使用する既存リソース

| 機能 | 既存パス | 流用内容 |
|---|---|---|
| キャラクター管理 | `api/services/tipsters.py::create_managed_tipster()` | `managed_*` 予想家を3体作成 |
| 記事投稿 API | `POST /api/articles` | `content_type=prediction` で投稿 |
| 内部API認証 | `api/main.py::_get_user_from_internal_key()` | `X-Internal-Key` ヘッダー経由で管理者権限取得 |
| レースデータ | `api/services/data_fetcher.py` | `get_races` / `get_race_entries` / `get_full_scores` |
| 8項目スコア | `api/services/ranking.py::calculate_matrix()` | データコンテキストとして AI に渡す |
| AI呼び出し | `anthropic>=0.34.0`（既に requirements.txt 済み） | Claude Sonnet 4 を使用 |
| API鍵 | `config.ANTHROPIC_API_KEY` + `config.INTERNAL_API_KEY` | `.env.local` に既存 |

---

## 4. データモデル

### 4.1 投稿される記事レコード（既存スキーマに準拠）

```python
{
    "slug": "tokyo-11r-derby-kyo-managed_aaa-20260418",  # {race_id}-{tipster_id}-{date}
    "title": "ダービー卿CT 予想｜netkeita本紙・山田の本命は◎サンライズジパング",
    "description": "中山芝1600m、本紙が狙う軸馬と3連複フォーメーション...",
    "body": "## レース概要\n\n...",  # Markdown
    "thumbnail_url": "",  # 初版は空（Phase 2で自動生成）
    "author": "netkeita本紙・山田",
    "author_id": "",  # 内部キー経由なので空
    "status": "published",
    "race_id": "20260418-tokyo-11",
    "content_type": "prediction",
    "tipster_id": "managed_aaaaaaaaaaaaa",
    "bet_method": "3連複フォーメーション",
    "ticket_count": 12,
    "preview_body": "本紙が今週の重賞で狙う軸馬を解説。人気馬の中から堅実に1頭を選ぶ理由とは...",
    "is_premium": false,
    "ai_generated": true,       # ★新規フィールド（AI生成を明示）
    "ai_model": "claude-sonnet-4-20250514",  # ★新規フィールド
    "picks": {                  # ★新規フィールド（◎○△✖の構造化）
        "honmei": 5,
        "taikou": 3,
        "tanana": 11,
        "keshi": 1
    },
    "created_at": "2026-04-18T06:05:00+09:00",
    "updated_at": "2026-04-18T06:05:00+09:00"
}
```

### 4.2 スキーマ拡張（初版で必要）

`api/services/articles.py` に以下フィールドを追加：

- `ai_generated: bool` — True の場合、UI で「AI生成」バッジを表示
- `ai_model: str` — 記録のみ（"claude-sonnet-4-20250514" 等）
- `picks: dict` — `{honmei, taikou, tanana, keshi}` の馬番辞書

これらは **オプションフィールド** として追加し、既存の Markdown 記事には影響させない。

### 4.3 キャラクター別成績キャッシュ（Redis db=6）

```
キー: nk:tipster_stats:{tipster_id}
値: {
    "total_predictions": 1234,
    "hit_count": 156,
    "hit_rate": 0.1264,
    "roi": 1.08,
    "last_updated": "2026-04-16T23:45:00+09:00"
}
TTL: 7日
```

cron `scripts/update_race_results.py` の拡張で、結果確定後にキャラ別集計を書き込む。

---

## 5. プロンプト設計

### 5.1 システムプロンプト（キャラごと）

共通部分：
```
あなたは netkeita の専属 AI 予想家「{キャラ名}」です。
以下のレースデータをもとに、あなたのキャラクターに沿った予想記事を書いてください。

【絶対守るルール】
- データに存在しない馬名は絶対に出さないこと
- 馬番は 1〜18 の範囲、出走表に存在するもののみ使用
- 本命/対抗/単穴は全て異なる馬番
- 文字数は 600〜1500 字
- 出力は必ず厳格な JSON 形式（下記スキーマ）

【あなたのキャラクター】
{各キャラのパーソナリティ記述}

【あなたの選定ロジック】
{各キャラの本命選定ルール}
```

個性部分（例：山田）：
```
あなたは競馬新聞「netkeita」の本紙記者、山田。
文体は落ち着いた新聞記事調で、データより経験と直感を信頼する。
本命（◎）は「総合ランク A 以上の中で最上位人気」から選ぶ。
相手（○△）はコース実績・騎手・血統のどれかで裏付けがある馬を優先。
買い目は「馬連」を好む。決め台詞は「本紙の本命、今週も自信あり」。
```

### 5.2 ユーザープロンプト（データコンテキスト）

```json
{
    "race": {
        "race_id": "20260418-tokyo-11",
        "race_name": "ダービー卿チャレンジトロフィー",
        "venue": "中山",
        "distance": "芝1600m",
        "track_condition": "良",
        "headcount": 16
    },
    "horses": [
        {
            "number": 1,
            "name": "サンライズジパング",
            "jockey": "ルメール",
            "odds": 4.2,
            "popularity": 2,
            "ranks": {
                "meta": "A", "dlogic": "A", "view": "B",
                "jockey": "A", "pedigree": "B", "recent": "A",
                "track": "S", "ev": "B"
            }
        }
    ]
}
```

### 5.3 期待する出力（JSON）

```json
{
    "title": "ダービー卿CT 予想｜本紙・山田の本命は◎サンライズジパング",
    "preview_body": "本紙が今週の重賞で狙う軸馬を解説...",
    "body": "## レース概要\n\n中山芝1600m、良馬場で...",
    "picks": {"honmei": 1, "taikou": 5, "tanana": 11, "keshi": 3},
    "bet_method": "馬連",
    "ticket_count": 6
}
```

---

## 6. 実装ファイル一覧

### 6.1 バックエンド変更

| ファイル | 変更内容 |
|---|---|
| `api/services/articles.py` | `ai_generated` / `ai_model` / `picks` フィールドを追加 |
| `api/main.py::ArticleCreateRequest` | 同フィールドをリクエストモデルに追加 |
| `api/services/tipster_stats.py` | **新規**。キャラ別成績集計サービス |
| `api/main.py` | `GET /api/tipsters/{id}/stats` エンドポイントを追加 |

### 6.2 新規スクリプト

| ファイル | 役割 |
|---|---|
| `scripts/auto_generate_predictions.py` | **メインcron**。1日1回起動して全レース×3キャラで記事生成 |
| `scripts/tipster_personas.py` | 3キャラのプロンプト・選定ロジック定義 |
| `scripts/setup_managed_tipsters.py` | 初回に3キャラを作成するワンショット |
| `scripts/update_tipster_stats.py` | 結果確定後にキャラ別成績を再計算 |

### 6.3 フロントエンド変更

| ファイル | 変更内容 |
|---|---|
| `frontend/src/components/PredictionCard.tsx` | `ai_generated` バッジ表示 |
| `frontend/src/app/tipsters/[id]/page.tsx` | 成績カード（的中率・回収率）を表示 |
| `frontend/src/app/articles/[slug]/ArticleDetailView.tsx` | 記事末尾に「この記事はAIが生成しています」注記 |
| `frontend/src/app/race/[raceId]/page.tsx` | レースに紐づく3キャラ予想を横並び表示 |

### 6.4 インフラ

| 項目 | 内容 |
|---|---|
| cron登録先 | VPS（220.158.24.157）`/opt/dlogic/netkeita-api/` |
| cron時刻 | JRA: 土日 6:00 JST / NAR: 毎日 14:00 JST |
| ログ | `/var/log/netkeita/auto_tipsters.log`（logrotate 7日保持） |
| 二重起動防止 | `flock /tmp/netkeita_auto_tipsters.lock` |
| 失敗通知 | Telegram Bot 経由で仁さんに通知（既存の通知経路を流用） |

---

## 7. コスト試算

### 7.1 Claude API 利用料（Sonnet 4 前提）

| 項目 | 値 |
|---|---|
| 入力tokens/記事 | 約 3,000（システムプロンプト + レースデータ） |
| 出力tokens/記事 | 約 2,000（Markdown本文 + JSON構造） |
| 単価 | 入力 $3/1M, 出力 $15/1M |
| 1記事あたりコスト | **約 $0.039** |

### 7.2 月間コスト

| シナリオ | 記事数/月 | 月間コスト |
|---|---|---|
| JRA のみ（土日 × 36レース × 3キャラ × 8日） | 約 864 | **約 $34** |
| JRA + NAR（平日NAR 22日 × 30レース × 3キャラ + JRA分） | 約 2,844 | **約 $111** |
| 有馬記念など重賞の細やかな記事強化 | +20% | +20% |

→ **月額 $40〜$130 の範囲**（約 ¥6,000〜¥20,000/月）

### 7.3 コスト最適化オプション

- Claude Haiku 4 使用で約 1/5 に削減可（品質とのトレードオフ）
- NAR は軽量モデル、JRA は Sonnet 4 のハイブリッド
- 記事キャッシュ（同一レース再生成時）

---

## 8. 実装フェーズ

### Phase 1: 基盤準備（1日）
1. `api/services/articles.py` スキーマ拡張（`ai_generated` / `picks`）
2. `scripts/setup_managed_tipsters.py` で3キャラを本番作成
3. `scripts/tipster_personas.py` にプロンプト実装

### Phase 2: 生成エンジン（2日）
1. `scripts/auto_generate_predictions.py` の雛形実装
2. ローカルで1レース×1キャラのPoC
3. バリデーション実装（馬名存在チェック・picks重複チェック）
4. 3キャラ × 5レース程度のサンプル実行・記事品質レビュー

### Phase 3: 本番投入（1日）
1. cron登録（JRA土日のみ先行）
2. Telegram失敗通知接続
3. 1週間監視・品質調整

### Phase 4: 成績可視化（1日）
1. `tipster_stats.py` サービス実装
2. フロントに成績カード追加
3. `update_race_results.py` に成績集計処理を統合

### Phase 5: NAR 対応（0.5日）
1. NAR 向け cron を追加
2. NAR 特有のデータ差分をプロンプトに反映

**合計: 約 5.5人日**

---

## 9. 品質管理・運用

### 9.1 生成記事の品質保証

- **バリデーション**:
  - 馬名がレースデータに存在するか
  - 本命/対抗/単穴の馬番が異なるか
  - 本文文字数（600〜1500）
  - 禁止ワード（差別・中傷・過度な煽り）除去
- **失敗時の挙動**:
  - 3回リトライ → それでも失敗したらスキップして Telegram 通知
  - 部分失敗（3キャラ中1キャラ失敗）でも他キャラは投稿継続
- **人間による抜き打ちレビュー**:
  - 仁さんが週1で10記事程度をサンプリング
  - 問題あればプロンプト修正

### 9.2 モニタリング指標

- 記事生成成功率（目標 95%以上）
- 記事あたり API コスト
- キャラ別の的中率推移
- 記事ごとの PV / 滞在時間（将来：分析基盤導入後）

### 9.3 フラグキル（緊急停止）

環境変数 `AI_TIPSTERS_ENABLED=false` で cron が即座に no-op を返す。プロンプト暴走や API 障害時の応急停止策。

---

## 10. 法務・倫理

### 10.1 AI 生成の明示

- 各記事末尾に **「※この記事は AI が生成しています」** 注記
- `/tipsters/[id]` ページにも **「AI 予想家」** バッジ
- 利用規約 `/terms` に AI 予想家に関する条項を追記

### 10.2 景表法・金商法配慮

- 「必ず勝てる」「絶対」などの断定表現禁止（プロンプトで明示）
- 払戻金額・的中保証の表現禁止
- 公営競技法の「予想家」扱いに該当しないよう、「参考意見」であることを明示

### 10.3 著作権

- 記事本文は AI 生成物（著作権は netkeita に帰属する運用）
- 馬名・レース名・騎手名などの固有名詞は公開データ（問題なし）

---

## 11. リスクと対策

| リスク | 影響 | 対策 |
|---|---|---|
| Claude API が幻覚を起こし存在しない馬名を出す | 記事の信頼失墜 | バリデーションで馬名チェック → 失敗なら破棄 |
| 3キャラの記事が似通う | 差別化失敗 | 選定ロジック・文体を明確に分離、定期的にサンプリングレビュー |
| API コスト爆発 | 月数万円の予期せぬ支出 | 1日の上限記事数を設定、Prometheus 的に Telegram 通知 |
| AI 記事への批判（「AIに予想はできない」） | ブランド毀損 | AI 明示 + 成績公開で誠実な運用をアピール |
| cron が落ちて記事が出ない日がある | サイト賑わい低下 | flock + systemd timer + 失敗時 Telegram 通知 |
| レースデータが未取得のまま生成 | 全馬無名の記事になる | `data_fetcher` のエラーハンドリング、データ欠損レースはスキップ |
| プロンプトインジェクション | 予期せぬ出力 | 外部入力（ユーザー名等）を prompt に入れない |

---

## 12. 将来拡張

- **Phase 6（将来）**: キャラクター画像・アイコンの AI 生成（FLUX2 等）
- **Phase 7**: 結果記事の自動生成（的中/不的中の振り返り）
- **Phase 8**: キャラ数拡張（5〜10キャラに増やしてユーザーが「推しキャラ」を選べる）
- **Phase 9**: X (Twitter) への自動投稿連携（dlogic-note 方式を参考）
- **Phase 10**: 音声予想（Qwen3-TTS で読み上げ、YouTube Shorts 化）
- **Phase 11**: リアルタイム予想（直前オッズを反映した最終予想を発走10分前に生成）

---

## 13. 関連ファイル・参考実装

- **参考**: `~/dlogic-note/`（Claude API で note 記事を自動生成・投稿する既存システム）
  - `generator.py` — 記事生成ロジック
  - `adapter.py` — Dlogic API からのデータ取得
  - cron 登録済み
- **既存仕様書**:
  - `MINNA_YOSOU.md` — みんなの予想機能（予想印の関連）
  - `PLAN_ARTICLES.md` — 記事投稿機能 v1
  - `PLAN_EDITOR_V2.md` — 記事エディタ v2（TipTap）
  - `TODO_2026-04-07.md` #4 — みんなの予想に3キャラ予想印を追加
- **既存サービス**:
  - `api/services/tipsters.py` — 予想家管理（`create_managed_tipster` 済み）
  - `api/services/articles.py` — 記事CRUD
  - `api/services/rewriter.py` — Claude API 呼び出し参考
  - `api/services/ranking.py` — 8項目ランクマトリクス算出
- **管理画面**:
  - `/admin/tipsters` — 3キャラを手動作成する入口

---

## 14. 未解決事項・要決定

- [ ] 3キャラの最終的な名前・キャッチフレーズ
- [ ] 各キャラの本命選定ロジックの詳細調整
- [ ] 初版でJRAのみか、NARも同時リリースか
- [ ] 記事生成モデル（Sonnet 4 / Haiku 4 / 併用）
- [ ] 1日の上限記事数（コスト上限）
- [ ] アイコン画像（手動用意 or AI生成）
- [ ] 公開スケジュール（初回リリース日）

---

**このプランは着手前に再精査すること**。技術選定・パッケージバージョン・ライブラリAPIはその時点の最新を確認し差分があれば更新する。
