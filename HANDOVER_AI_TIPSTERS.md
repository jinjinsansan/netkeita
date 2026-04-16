# AI予想家自動記事作成機能 — 作業引継ぎ

**最終更新**: 2026-04-16 21:00頃 JST
**担当**: Droid (次セッションへ引き継ぎ)
**関連仕様書**: `PLAN_AI_TIPSTERS.md`

---

## 1. 現在のステータス

**Phase 0 (PoC) 進行中**。v1 PoC 成功 → 設計方針を途中で変更 → v2 PoC を実装中にバリデーションエラーで中断。

### 完了済み
- [x] 仕様書 `PLAN_AI_TIPSTERS.md` 作成・プル完了 (コミット `c9dc7b5`)
- [x] PoC v1 実装 (`scripts/tipster_personas.py`, `scripts/poc_auto_tipster.py`)
- [x] VPS転送・環境整備 (`/opt/dlogic/netkeita-api/scripts/` に配置済み)
- [x] Anthropic APIキー更新 (VPS `.env.local` に反映、`systemctl restart netkeita-api` 済み)
- [x] PoC v1 で3キャラ全員に対し実生成成功 (門別1R、バリデーション通過、`output/` に保存)
- [x] 既存ドロワー `/api/votes/{id}/predictions` との比較で **印が一致しない** ことを確認
- [x] 設計方針変更決定 (ユーザー判断、詳細は §3)
- [x] PoC v2 実装 (印をドロワーから取得し Claude に固定値として渡す方式)
- [x] PoC v2 を VPS へ転送、honshi キャラで実行
- [ ] **PoC v2 でバリデーションエラー発生 → ここで中断**

### 中断時点のバグ
Claude Sonnet 4 が `picks` を `{honmei: 12}` ではなく `{honmei: {number: 12, name: "ステーション"}}` という dict 形式で返している。バリデーションは `want=12, got={'number': 12, 'name': 'ステーション'}` で不一致を検出。

**原因**: システムプロンプトで picks を「ユーザープロンプトで与えられたものを一字一句そのまま出力」と指示したが、ユーザープロンプト内の `fixed_picks_with_names` (dict形式の可読版) を Claude が picks 値として採用してしまった。

**修正方針**:
- ユーザープロンプトから `fixed_picks_with_names` を削除するか、picks 本体のみを参照させるように明示する
- もしくは system_prompt で出力例 (picks: {honmei: int, taikou: int, ...}) を明示
- バリデーションで Claude 出力の dict 形式を許容して正規化するヘルパーを追加するのも可

---

## 2. 作成/変更済みファイル

### 新規
| パス | 役割 | 状態 |
|---|---|---|
| `scripts/tipster_personas.py` | 3キャラのペルソナ定義 (v2: ドロワー印前提) | VPS/ローカル両方に最新版 |
| `scripts/poc_auto_tipster.py` | PoC実行スクリプト (v2: ドロワー印取得→Claude) | VPS/ローカル両方に最新版 |
| `output/poc_*.md` | 生成結果 (v1: 3キャラ分、v2: honshi 1件のみ、エラー状態) | gitignored |
| `HANDOVER_AI_TIPSTERS.md` | このファイル | — |

### 変更
| パス | 変更内容 |
|---|---|
| `.gitignore` | `output/`, `APIキー.txt`, `.anthropic_key.txt` を追加 |

### VPS側の変更
| パス | 変更内容 |
|---|---|
| `/opt/dlogic/netkeita-api/.env.local` | `ANTHROPIC_API_KEY` を新キーに更新 |
| `/opt/dlogic/netkeita-api/scripts/tipster_personas.py` | 新規追加 (最新版) |
| `/opt/dlogic/netkeita-api/scripts/poc_auto_tipster.py` | 新規追加 (最新版) |
| `/opt/dlogic/netkeita-api/output/` | 生成記事MDが複数存在 |
| `netkeita-api.service` | 1回再起動済み (新APIキー反映のため) |

---

## 3. 設計判断の履歴 (重要)

### 決定事項 (ユーザー確認済み)

| 項目 | 決定 | 根拠 |
|---|---|---|
| 3キャラ | 提案通り継続 | PLAN_AI_TIPSTERS.md 準拠 |
| リリース範囲 | **JRA+NAR 同時** | ユーザー選択 |
| モデル | **Sonnet 4** (品質優先) | ユーザー選択 |
| 進め方 | PoC先行 | ユーザー選択 |
| **印の一致** | **ドロワー印を正とし、記事はその解説** | ユーザー選択 |
| **キャラID** | **既存ドロワー ID (honshi/data/anaba) に寄せる** | ユーザー選択 |
| **選定ロジック** | **記事側のロジックを廃止、ドロワーロジックをそのまま使う** | ユーザー: 「既存ドロワーの予想はなかなかいい予想なので、ペルソナをドロワーに合わせるべき」 |

### 放棄した方針 (v1)
- 各キャラ独自の選定ロジック (「総合A以上の人気上位」「EV最上位」「7番人気以下」) は廃止
- キャラ表示名の「山田」「西村」「ケンジ」などの個人名は廃止
- v1 の PoC は参考として output/ に残っている

### ID/表示名の対応表 (最終)
| v1 (廃止) | v2 (採用) | 表示名 | ドロワー既存と一致 |
|---|---|---|---|
| honshi_yamada | **honshi** | netkeita本紙 | ✓ |
| data_nishimura | **data** | データ分析 | ✓ |
| anatou_kenji | **anaba** | 穴党記者 | ✓ |

---

## 4. 次セッションで最初にすべきこと

### A. PoC v2 のバグ修正 (最優先)

`scripts/poc_auto_tipster.py` の `call_claude()` を修正:

**問題**: ユーザープロンプトに `fixed_picks_with_names` (dict形式) を含めると、Claude が出力 picks にもその dict を採用してしまう。

**修正案1 (推奨)**: `to_prompt_json()` から `fixed_picks_with_names` を削除し、picks_summary の日本語テキストだけで馬名を伝える:
```python
# before
payload = {..., "fixed_picks": ..., "fixed_picks_with_names": ...}
# after
payload = {..., "fixed_picks": {"honmei": 12, "taikou": 7, ...}}
# picks_summary (人間可読) は別セクションでプロンプトに含める (既に実装済み)
```

**修正案2**: システムプロンプトに出力例を追加:
```
【出力例 (picks の値はすべて int)】
"picks": {"honmei": 12, "taikou": 7, "tanana": 1, "renka": 9, "keshi": 5}
```

両方適用が堅実。

### B. 3キャラ全員で再実行

```bash
# VPS上で (ローカルの PowerShell から)
ssh root@220.158.24.157 "cd /opt/dlogic/netkeita-api && set -a; . ./.env.local; set +a; /opt/dlogic/backend/venv/bin/python scripts/poc_auto_tipster.py --persona honshi"
ssh root@220.158.24.157 "cd /opt/dlogic/netkeita-api && set -a; . ./.env.local; set +a; /opt/dlogic/backend/venv/bin/python scripts/poc_auto_tipster.py --persona data"
ssh root@220.158.24.157 "cd /opt/dlogic/netkeita-api && set -a; . ./.env.local; set +a; /opt/dlogic/backend/venv/bin/python scripts/poc_auto_tipster.py --persona anaba"

# 結果を取得
scp "root@220.158.24.157:/opt/dlogic/netkeita-api/output/poc_*.md" "E:\dev\Cusor\netkeita\output\"
```

### C. 品質OKなら Phase 1 着手

PLAN_AI_TIPSTERS.md §8 Phase 1 の内容:
1. `api/services/articles.py` にスキーマ拡張 (`ai_generated`, `ai_model`, `picks`)
2. `api/main.py::ArticleCreateRequest` に同フィールド追加
3. `scripts/setup_managed_tipsters.py` で3キャラを本番作成 (Redis db=6 の tipsters.py 経由)
4. 動作確認

---

## 5. 技術メモ

### VPS環境
- ホスト: `root@220.158.24.157`
- netkeita-api: `/opt/dlogic/netkeita-api/`
- Python venv: `/opt/dlogic/backend/venv/` (共有。`anthropic==0.84.0`, `httpx==0.28.1` 利用可能)
- 環境変数: `/opt/dlogic/netkeita-api/.env.local` に `ANTHROPIC_API_KEY`, `INTERNAL_API_KEY` 等
- systemd: `netkeita-api.service` (workers=4)

### ローカル環境 (Windows)
- リポジトリ: `E:\dev\Cusor\netkeita\`
- git: `main` ブランチ、origin = `jinjinsansan/netkeita.git`
- ssh鍵はエージェント経由で `root@220.158.24.157` に接続可

### APIエンドポイント
- 本番: `https://bot.dlogicai.in/nk/`
- 使用: `/api/dates`, `/api/races?date=`, `/api/race/{id}/matrix`, `/api/votes/{id}/predictions`

### ドロワー印データ構造 (サンプル)
`GET /api/votes/20260417-大井-1/predictions` のレスポンス:
```json
{
  "race_id": "20260417-大井-1",
  "predictions": [
    {
      "id": "honshi",
      "name": "netkeita本紙",
      "description": "本命重視の正統派",
      "emoji": "📰",
      "marks": {"12": "◎", "7": "○", "1": "▲", "9": "△", "5": "✖"}
    },
    {"id": "data", ...},
    {"id": "anaba", ...}
  ]
}
```

### 印 → picks キー対応
| 印 | キー |
|---|---|
| ◎ | honmei |
| ○ | taikou |
| ▲ | tanana |
| △ | renka |
| ✖ | keshi |

### コスト実績 (これまで)
- v1 PoC 3キャラ × 1レース = 約 $0.12
- v2 PoC honshi 1件 = 約 $0.04
- 合計 約 $0.16

---

## 6. セキュリティメモ

- ローカル `APIキー.txt` は削除済み (gitignore済みだが念のため)
- 新APIキーはユーザー発行、VPS `.env.local` にのみ存在
- PoC検証が全て終わったら、ユーザーはAnthropic Consoleで該当キーをローテートすることを推奨

---

## 7. 参考リンク (netkeita 内)

- `PLAN_AI_TIPSTERS.md` — 仕様書 (本プランの正)
- `MINNA_YOSOU.md` — ドロワー投票機能の仕様 (関連)
- `api/main.py::_generate_character_predictions()` — ドロワー印生成ロジック (行数: main.py 内で `CHARACTER_PROFILES` を検索)
- `api/services/tipsters.py::create_managed_tipster()` — キャラ本番作成用 (Phase 1 で使用)
- `api/services/rewriter.py` — Claude API 呼び出しの参考実装
- `~/dlogic-note/` (隣接プロジェクト) — 参考: note自動投稿システム
