# みんなの予想 (Community Vote) 機能仕様

新規公開直後のサイトでも「投票数が寂しくない」体験を出しつつ、ユーザーが実際に的中率・回収率をマイページで追えるようにする単勝ベースの投票機能です。

---

## 1. ユーザーフロー

1. レースページ右端の **「みんなの予想」** ボタンを開く
2. 未ログインなら既存ダミー集計のみを表示
3. ログイン済みなら単勝1頭を選び「この馬に投票する」
4. 投票直後は結果ビューに切り替わり、自分の票が反映される
5. レース発走後、cron (`scripts/update_race_results.py`) が netkeiba から 1 着・単勝配当を取得
6. マイページの **投票履歴・的中率・回収率** が自動で更新される

発走時刻を過ぎたレースには **403** を返して投票を拒否します（結果を見てから投票する抜け穴を防止）。

---

## 2. バックエンド構成

### エンドポイント

| メソッド | パス | 用途 |
|---|---|---|
| `GET`  | `/api/votes/{race_id}/results` | 投票集計（ダミー + 実票）取得 |
| `POST` | `/api/votes/{race_id}`         | 投票の新規・変更（要ログイン） |
| `GET`  | `/api/votes/my-history`        | 自分の投票履歴と ROI（要ログイン） |

### Redis キー (db=3)

| キー | 型 | TTL | 用途 |
|---|---|---|---|
| `nk:votes:{race_id}` | hash `{user_id: horse_number}` | 90 日 | ユーザー投票先 |
| `nk:votes:count:{race_id}` | hash `{horse_number: count}` | 90 日 | 集計カウンタ |
| `nk:votes:dummy:{race_id}` | string `"1"` (NX lock) | 90 日 | ダミー生成フラグ |
| `nk:votes:history:{user_id}` | hash `{race_id: horse_number}` | 90 日 | ユーザー履歴 |
| `nk:votes:odds:{user_id}` | hash `{race_id: odds}` | 90 日 | 投票時オッズスナップショット |

### Redis キー (db=4 — 結果キャッシュ)

| キー | TTL | 内容 |
|---|---|---|
| `nk:race_result:{race_id}` | 30 日 | `{winner_horse_numbers, win_payouts, finalized, cancelled}` |
| `nk:race_result:neg:{race_id}` | 15 分 | スクレイプ失敗・未確定の短期マーカー |

### ダミー投票ロジック (`api/main.py::_ensure_dummy_votes`)

- マトリクスキャッシュ or プリフェッチから出馬表を取得
- 総合スコア上位 25% / 中位 35% / 下位 40% に `3.0-5.0 / 1.5-3.0 / 0.3-1.5` の重みを割当
- 30〜80票を重み付きランダム分配
- **SET NX EX で原子的にロック** (複数ワーカー間の衝突防止)
- pipeline でバッチ書き込み (最大 80 hincrby を 1 往復に集約)

### 投票バリデーション (`api/main.py::api_vote`)

1. `_RACE_ID_RE = r"^\d{8}-[^:\s/\\]{1,20}-\d{1,2}$"` で race_id 形式検査
2. `_get_valid_horse_numbers()` がキャッシュ不在時はプリフェッチから馬番集合を取得（cold cache でのバリデーションバイパスを閉塞）
3. `_parse_start_datetime()` で発走時刻を JST 比較 → 発走済みなら 403
4. 投票時点のオッズを `nk:votes:odds:{user_id}` にスナップショット
5. すべての書き込みを pipeline (transaction=True) で実行

### 結果判定 (`api/main.py::api_my_vote_history`)

- 履歴を `date_str` でグループ化してプリフェッチ読み込みを日付ごとに 1 回に削減 (N+1 解消)
- オッズ表示は **スナップショット優先 → プリフェッチ entries → オッズ辞書** の 3 段 fallback
- 結果は `winner_horse_numbers`（list）と `win_payouts`（dict）で照合し、**同着**にも対応
- ステータス: `pending` / `hit` / `miss` / `hit_no_payout` / `cancelled`
- 的中率・回収率は **確定レースのみ** を母数に計算

---

## 3. 結果スクレイパー (`api/services/race_results.py`)

### 設計方針

- **純粋関数を分離**: `_extract_yen`, `_parse_winners`, `_parse_win_payouts`, `_detect_cancellation` は Redis にも HTTP にも触れない → `test_race_results.py` で単体テスト可能
- **多段セレクタ**: netkeiba の HTML 変更に耐えられるよう複数の候補を試す
- **リトライ**: 最大 3 回、指数バックオフ（1.5s → 3s → 6s）
- **サニティキャップ**: 単勝払戻金 1,000,000 円を超える値は破棄（JRA 単勝史上最高は 83,000 円程度）
- **負キャッシュ**: 未確定・失敗時は 15 分 TTL のマーカーを書き込んで連続リトライを抑制
- **エンコーディング自動判定**: `apparent_encoding` に委任（新ページ UTF-8 / 旧ページ EUC-JP 両対応）
- **中止検出**: "中止" / "取止" / "発走取止" / "開催中止" / "取りやめ" を検出してキャッシュに `cancelled=true` を保存

### 重要な修正: 単勝金額パース

旧実装は `re.sub(r"[^\d]", "", text)` でテキスト内の全数字を連結していたため、
`"430円 2人気"` が **4302** 円と誤認される致命バグがありました。新実装は:

```python
_YEN_PATTERN = re.compile(r"(\d[\d,]*)")

def _extract_yen(text: str) -> int:
    first_line = text.splitlines()[0] if "\n" in text else text
    m = _YEN_PATTERN.search(first_line)
    return int(m.group(1).replace(",", "")) if m else 0
```

ユニットテスト (`test_race_results.py::test_with_popularity_suffix_must_not_concatenate`) でこの挙動を固定しています。

---

## 4. cron ジョブ

`scripts/update_race_results.py` を 17:00 / 20:00 / 23:30 JST に実行します。

```cron
0 17 * * * /opt/dlogic/venv/bin/python /opt/dlogic/netkeita-api/scripts/update_race_results.py
0 20 * * * /opt/dlogic/venv/bin/python /opt/dlogic/netkeita-api/scripts/update_race_results.py
30 23 * * * /opt/dlogic/venv/bin/python /opt/dlogic/netkeita-api/scripts/update_race_results.py --days 3
```

主要機能:
- `--days N` : 過去 N 日分を巻き戻してキャッチアップ
- `--force` : キャッシュ無視で全レース再スクレイプ（負キャッシュもバイパス）
- **flock**: `/tmp/netkeita_update_race_results.lock` で二重起動を防止（POSIX）
- リクエスト間 0.6 秒スロットリング
- 同着・中止レースを正しくログ出力

---

## 5. フロントエンド

### コンポーネント

- `components/MinnaVoteDrawer.tsx` — 右ドロワー。投票ビューと結果ビューの 2 モード
- `app/mypage/page.tsx` — 履歴リスト + ROI 統計カード

### UX 改善

- **オートリフレッシュ**: マイページは 60 秒ごと + visibilitychange で再取得
- **ステータスラベル**: `hit` / `hit_no_payout` / `miss` / `pending` / `cancelled` をバッジで区別
- **配当 0 円の処理**: 的中+配当未取得は「的中 (配当情報未取得)」表示で「+-100円」のような矛盾を回避
- **中止レース**: 「投票無効・返還」ラベル。的中率・回収率の分母から除外
- **ブレイクダウン表示**: 確定 / 結果待ち / 中止 の件数を統計カードの下に表示
- **a11y**: `role="radiogroup"` / `aria-checked` / `aria-label` / `aria-live="assertive"` を付与
- **エラートースト**: 403 (発走後投票)、400 (不正馬番) 等のサーバエラーをドロワー内で表示

---

## 6. テスト

```bash
# 単体テスト（Redis / ネットワーク不要）
python api/services/test_race_results.py
```

**カバレッジ対象**:
- `_extract_yen`: 通常 / カンマ / 人気サフィックス連結バグ / 空文字 / 複数行
- `_parse_winners`: 単勝 / 同着 / 空 HTML
- `_extract_tansho_payout`: 標準テーブル / サニティキャップ
- `_parse_win_payouts`: 同着時に同額を配分
- `_detect_cancellation`: 中止表記 / 通常レース

---

## 7. 主な TTL 一覧

| 対象 | TTL | 理由 |
|---|---|---|
| 投票ハッシュ / カウント | 90 日 | ROI 集計期間に揃える |
| ダミーフラグ | 90 日 | 同一レースに対する再生成防止 |
| ユーザー履歴 | 90 日 | 回収率のローリング窓 |
| 投票時オッズスナップショット | 90 日 | 履歴と同期 |
| 確定済みレース結果 | 30 日 | 履歴表示に必要な期間 |
| 負キャッシュ（失敗・未確定） | 15 分 | cron 単位のリトライ抑制 |

---

## 8. セキュリティ配慮

- race_id regex 検証で **Redis キー注入** を遮断
- 発走時刻後の投票を **403** で拒否し「結果を見てから投票」を防止
- matrix cache が cold でも馬番検証がバイパスされない (`_get_valid_horse_numbers`)
- LINE Bearer token 必須 (`_get_user_from_token`)
