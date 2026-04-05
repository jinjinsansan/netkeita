# 記事エディタ v2 (本格 WYSIWYG) 実装計画

**ステータス**: 未着手 (v1 軽量アップグレード = `f7a6806` 完了後の次フェーズ)
**対象**: `frontend/src/components/ArticleEditor.tsx` と関連コンポーネント
**目標**: note.com と同等の執筆体験をスマホでも提供する

---

## 0. v1 との差分 (なぜ v2 が必要か)

v1 (現状) は Markdown テキストエリア + ツールバーで「実用」ラインに到達したが、
以下の弱点が残っている。

| 項目 | v1 の状況 | v2 で解決したい |
|---|---|---|
| WYSIWYG | ❌ 生の Markdown 記号が見える | ✅ 見たまま編集 (ProseMirror ベース) |
| ドラッグ&ドロップ画像 | ❌ ファイル選択のみ | ✅ D&D とクリップボード貼付 |
| リンクカード | ❌ ただのリンク | ✅ YouTube / X / Amazon 等の自動カード展開 |
| インライン装飾 | ❌ `**` などの記号を手動入力 | ✅ 選択してボタンで即装飾 |
| 画像キャプション | ❌ alt のみ | ✅ 画像下のキャプション編集 |
| 画像サイズ調整 | ❌ 不可 | ✅ 左右寄せ / 100% / 50% |
| 目次自動生成 | ❌ 無し | ✅ H2/H3 から TOC 自動生成 |
| マルチカラム / 引用ブロック | ❌ 最小限 | ✅ 囲み枠 / ノート / 警告 |
| コラボ編集 | ❌ 無し | 🟡 将来 (Yjs) |
| モバイル IME フォーカス | ⚠️ Markdown 記号の入力が面倒 | ✅ 記号入力ゼロ |

---

## 1. 技術選定

### 1.1 エディタコア: **TipTap 2.x**

| 項目 | TipTap | Slate | Lexical | Draft.js |
|---|---|---|---|---|
| コミュニティ | ★★★ (26k stars) | ★★ | ★★ (Meta) | ❌ 開発停止 |
| React 統合 | ネイティブ | 要ラッパー | 公式 | 古い |
| 拡張機能 | ★★★ 公式+サードパーティ豊富 | ★ 自作必要 | ★ 自作必要 | ★ |
| 学習コスト | 中 | 高 | 高 | 中 |
| Markdown I/O | プラグインで対応 | 自作 | 自作 | 自作 |
| モバイル IME | ◎ ProseMirror 経由で安定 | △ | ◎ | × |
| ライセンス | MIT | MIT | MIT | BSD |

**採用理由**:
1. ProseMirror をラップしているため、note.com / Notion / Atlassian と同じ基盤
2. `@tiptap/starter-kit` で基本装飾が 1 行で揃う
3. Markdown の import/export は `tiptap-markdown` で相互変換できる (=既存記事の移行が楽)
4. カスタムノード (リンクカード / 引用枠) を React コンポーネントで書ける

### 1.2 必要パッケージ一覧

```bash
npm install --save \
  @tiptap/react \
  @tiptap/pm \
  @tiptap/starter-kit \
  @tiptap/extension-image \
  @tiptap/extension-link \
  @tiptap/extension-placeholder \
  @tiptap/extension-character-count \
  @tiptap/extension-code-block-lowlight \
  @tiptap/extension-table \
  @tiptap/extension-table-row \
  @tiptap/extension-table-cell \
  @tiptap/extension-table-header \
  @tiptap/extension-typography \
  @tiptap/extension-youtube \
  lowlight \
  tiptap-markdown
```

見込みサイズ増加: 約 +200 KB (gzip 後)

### 1.3 画像処理
v1 で作った `POST /api/articles/upload-image` とバケット `article-images` をそのまま流用。
TipTap の `Image` 拡張にカスタムアップロードハンドラを差すだけで D&D / クリップボード貼付が動く。

### 1.4 リンクカード (OGP 展開)
- フロントで URL を検出 → API 経由で OGP を取得 → JSON で返却 → TipTap カスタムノードで描画
- 新規エンドポイント: `GET /api/oembed?url=...`
  - サーバー側で URL fetch → `<meta og:*>` をパース → 1 時間 Redis キャッシュ
  - ホワイトリスト: youtube.com, x.com, twitter.com, instagram.com, amazon.co.jp, netkeita.com 等
- クライアントは貼り付けた URL を検出 → API 叩く → 成功したらカードノードに置換、失敗したら通常リンク

---

## 2. データモデル (重要な決定)

**採用案**: TipTap の JSON を「正」として保存、Markdown は読み取り専用の派生データ

| 項目 | 正規形 | 補助形 |
|---|---|---|
| Body (DB) | **TipTap JSON** (`doc` object) | Markdown (検索・RSS 用にレンダリング時生成) |
| API レスポンス (admin) | `body_json` + `body_markdown` | 編集時は JSON を使う |
| API レスポンス (public) | **Server-side rendered HTML** | 読者はいつも HTML を受け取る |
| 全文検索 | Markdown or plain text | JSON を都度パースしない |

### 移行手順
v1 時代の記事は `body` が Markdown 文字列のみ。
1. 新スキーマ: `body_json` (TipTap JSON), `body_markdown` (互換), `body_html` (SSR キャッシュ)
2. 旧記事を読み込む時、`body_json` が無ければ `body` (Markdown) を `tiptap-markdown` で JSON に変換
3. 編集保存時に `body_json` / `body_markdown` / `body_html` を同時に書き込む
4. 公開 API は `body_html` をそのまま返す (SSR 不要、CDN キャッシュ可能)
5. 1 週間ほどで全記事が自然移行したら `body` フィールドを deprecated に

---

## 3. 機能スコープ

### 3.1 必須 (v2 リリースに含む)

**テキスト装飾**
- [x] 見出し H2 / H3
- [x] 太字 / 斜体 / 取り消し線 / 下線
- [x] リスト (順序あり / 順序なし / チェックリスト)
- [x] 引用
- [x] インラインコード / コードブロック (syntax highlight)
- [x] 水平線
- [x] リンク (Ctrl+K でも可)
- [x] テーブル (追加 / 削除 / 行列操作)

**メディア**
- [x] 画像 D&D アップロード
- [x] クリップボード貼り付けでも動く (スクリーンショット → Ctrl+V)
- [x] 画像左右寄せ / 中央 / フル幅
- [x] 画像キャプション (画像下に editable)
- [x] YouTube 埋め込み
- [x] リンクカード (X, Amazon, 自サイト記事を自動展開)

**UX**
- [x] スラッシュコマンド `/` でメニュー展開 (Notion 風)
- [x] フローティングバブルメニュー (選択範囲のみ装飾)
- [x] キーボードショートカット (Markdown ライクに `**太字**` と打てば自動変換)
- [x] 文字数カウンタ (現在の `_estimate_reading_time` を拡張)
- [x] 画像ロード中スケルトン
- [x] Undo / Redo (エディタ内 Ctrl+Z)
- [x] 自動保存 (既存 localStorage 機構を流用)

**モバイル特化**
- [x] ツールバーはキーボード上に追従 (visualViewport API)
- [x] スラッシュコマンドはボトムシートで展開
- [x] 画像は「カメラから撮影」ボタン対応 (input capture="environment")
- [x] 長押しでテキスト選択 → フローティングメニュー

### 3.2 推奨 (リソースがあれば)

- [ ] 目次 (TOC) 自動生成と記事サイドに表示
- [ ] 囲み枠 (Info / Warning / Note / Tip) カラー付きコールアウト
- [ ] 脚注 (Markdown 拡張)
- [ ] 数式 (KaTeX) — 競馬予想にはたぶん不要
- [ ] タグ / カテゴリ (現状 `status` のみ)
- [ ] 関連記事の手動ピック (埋め込み)

### 3.3 将来 (v3 以降)

- [ ] Yjs による協調編集 (多人数同時編集)
- [ ] コメント / 変更提案 (Google Docs 風)
- [ ] 履歴 (バージョン管理) と diff 表示
- [ ] AI 補助 (下書き生成、校正、SEO 最適化提案)
- [ ] 予約投稿 (cron で自動公開)

---

## 4. 画面構成

### 4.1 新しいエディタ画面のレイアウト

```
┌─────────────────────────────────────────────────────┐
│  [←戻る] [下書き] [プレビュー] [公開]   [文字数 1,234] │  ← ヘッダーバー
├─────────────────────────────────────────────────────┤
│                                                      │
│  [タイトルをここに入力...]                             │  ← h1 インラインエディタ
│                                                      │
│  [説明文 (SNS シェア用、1-2行)...]                    │
│                                                      │
│  [🖼 サムネイル画像をドラッグまたはクリックで追加]      │
│                                                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ## ここに本文を書いてください                         │
│                                                      │
│  選択した文字の周りに [B I U S • / > </ > ] が         │  ← バブルメニュー
│  フローティング表示される                              │
│                                                      │
│  行頭で [+ /] を押すとスラッシュメニュー              │
│  ├─ 📝 見出し H2                                      │
│  ├─ 📝 見出し H3                                      │
│  ├─ 📋 リスト                                         │
│  ├─ ✅ チェックリスト                                  │
│  ├─ 💬 引用                                           │
│  ├─ 🖼 画像                                           │
│  ├─ 🎬 YouTube                                        │
│  ├─ 🔗 リンクカード                                    │
│  ├─ 📊 テーブル                                        │
│  ├─ </> コードブロック                                 │
│  └─ ━ 区切り線                                         │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 4.2 スマホ時のフッターバー

```
┌─────────────────────────────────────────────────────┐
│  本文エリア (スクロール可能)                           │
│                                                      │
├─────────────────────────────────────────────────────┤
│  [H] [B] [I] [•] [🖼] [🔗] [/]    [公開▼]             │  ← キーボード上に吸着
└─────────────────────────────────────────────────────┘
```
`visualViewport.addEventListener('resize')` でキーボード高さを検知し CSS transform で追従。

---

## 5. 実装フェーズ

### Phase 1: 基盤置き換え (3〜4日)
1. TipTap パッケージを追加、`ArticleEditorV2.tsx` を新規作成
2. `StarterKit` + `Placeholder` + `CharacterCount` で基本動作
3. `ArticleEditor` (v1) と両立できるように feature flag で切替 (`NEXT_PUBLIC_EDITOR_V2=1`)
4. TipTap JSON ↔ Markdown の相互変換を `tiptap-markdown` で用意
5. 既存 v1 記事を開いて編集できることを確認 (Markdown → JSON → 編集 → Markdown で保存)

### Phase 2: 画像 & リンクカード (2〜3日)
1. `@tiptap/extension-image` にカスタムアップロードを差す
2. 既存の `/api/articles/upload-image` を再利用 (変更不要)
3. D&D ハンドラ追加 (`editor.chain().focus().setImage({ src }).run()`)
4. クリップボード貼り付けイベント (`handlePaste`)
5. バックエンドに `GET /api/oembed?url=` を新規作成 (Redis db=6 で 1時間キャッシュ)
6. 貼り付けた URL を検出してリンクカードノードに置換する extension を自作

### Phase 3: スラッシュコマンド & バブルメニュー (2日)
1. `@tiptap/suggestion` と `tippy.js` でスラッシュコマンド UI
2. コマンド一覧 (上記 4.1 の ├─ リスト) を作成
3. `BubbleMenu` でテキスト選択時の装飾メニュー
4. キーボードナビゲーション (上下キーで選択、Enter で確定)

### Phase 4: モバイル最適化 (2〜3日)
1. `visualViewport` API でキーボード高さを検知
2. ツールバーを `position: fixed; bottom: {keyboardHeight}px` で追従
3. スラッシュコマンドをボトムシートに切替 (画面 < 768px)
4. タッチ領域を最低 44x44px に
5. iOS Safari 固有の挙動 (ズーム防止、慣性スクロール) を調整
6. 実機テスト (iPhone Safari / Android Chrome 必須)

### Phase 5: データ移行 & 公開 (2日)
1. Redis の記事 JSON に `body_json` / `body_html` フィールド追加
2. 読み込み時の自動マイグレーション: `body_json` 不在なら Markdown から生成
3. 公開 API を `body_html` 返却に切替
4. SSR ページは `dangerouslySetInnerHTML` で body_html を描画
5. Feature flag OFF で v1 エディタをまだ使えるようにしておく (ロールバック保険)
6. 1 週間経過を待ち、問題が無ければ v1 削除

**合計**: 11〜14 人日 (実働 2 週間)

---

## 6. API 変更一覧

### 6.1 新規エンドポイント

| Method | Path | 用途 |
|---|---|---|
| GET | `/api/oembed?url=` | URL の OGP を取得 (1h キャッシュ) |
| POST | `/api/articles/upload-image` | 既存 (変更なし) |

### 6.2 変更エンドポイント

| Method | Path | 変更 |
|---|---|---|
| POST | `/api/articles` | リクエストボディに `body_json` / `body_html` を追加 |
| PUT | `/api/articles/{slug}` | 同上 |
| GET | `/api/articles/{slug}` | public view は `body_html` を返す、admin view は `body_json` も返す |
| GET | `/api/articles` | 一覧は要約のみ (変更なし) |

### 6.3 データスキーマ (services/articles.py)

```python
# 新しい内部スキーマ
{
  "slug": str,
  "title": str,
  "description": str,
  "body": str,            # 既存 — Markdown (deprecated, 一定期間は書き戻す)
  "body_json": dict,      # TipTap JSON (新: 正)
  "body_markdown": str,   # Markdown (新: 検索 / RSS 用)
  "body_html": str,       # SSR 済み HTML (新: 公開用キャッシュ)
  "body_schema_version": int,  # 現状 2、将来スキーマ変更時に使用
  ...既存フィールド...
}
```

### 6.4 XSS 対策 (重要)

TipTap で作った HTML をそのまま `dangerouslySetInnerHTML` で描画するため、
**サーバー側でサニタイズが必須**。

- Python: `bleach` パッケージを追加 (`bleach>=6.1`)
- 許可タグホワイトリスト: `h2, h3, p, strong, em, u, s, ul, ol, li, blockquote, code, pre, a, img, hr, table, thead, tbody, tr, th, td, figure, figcaption, iframe` (iframe は YouTube ドメインのみ)
- 許可属性: `href, src, alt, title, class (prose-nk 系のみ), width, height, target, rel`
- JavaScript URL / on* イベント属性は完全拒否

```python
# api/services/html_sanitizer.py (新規予定)
import bleach
ALLOWED_TAGS = [...]
ALLOWED_ATTRIBUTES = {...}
def sanitize(html: str) -> str:
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
```

---

## 7. テスト戦略

### 7.1 単体テスト
- `test_articles.py` に `body_json` / `body_html` ラウンドトリップテスト追加
- `test_html_sanitizer.py` で XSS ペイロード全種を拒否することを確認
  - `<script>alert(1)</script>`, `<img onerror=alert(1)>`, `javascript:`, `<iframe src="evil">`, `<a href="javascript:...">`, `<svg onload>` 等

### 7.2 E2E テスト (Playwright 導入)
- 新規記事作成: タイトル入力 → 本文入力 → 画像アップロード → 公開 → 一覧に表示
- 既存 v1 記事編集: 開く → 内容が正しく表示 → 編集 → 保存 → 表示が正しい
- モバイル (iPhone 14 viewport) でスラッシュコマンド動作確認
- XSS: `<img src=x onerror=alert(1)>` を本文に貼ってもアラートが出ない

### 7.3 本番前チェックリスト
- [ ] 既存 Markdown 記事を 10 本開いて編集 → 保存 → 崩れていない
- [ ] iOS Safari 実機で画像 D&D, スラッシュコマンド, キーボード追従
- [ ] Android Chrome 実機で同上
- [ ] PC Chrome / Firefox / Safari でスラッシュコマンド
- [ ] ネット断状態で localStorage autosave が動くか
- [ ] 大きな記事 (50KB+) で動作が重くならないか

---

## 8. リスク & 対策

| リスク | 影響度 | 対策 |
|---|---|---|
| TipTap の学習コスト | 中 | 公式 docs とサンプルが豊富。1人で 1 週間で理解可能 |
| 既存 Markdown 記事の崩れ | 高 | Feature flag + 1週間の並行運用 + ロールバック保険 |
| HTML サニタイズ漏れ | **致命** | bleach + 許可リスト方式 + セキュリティテスト必須 |
| バンドルサイズ増加 (+200KB) | 中 | 記事ページでのみ dynamic import、TOPページへの影響ゼロ |
| モバイル IME の奇妙な挙動 | 中 | ProseMirror は iOS/Android で実績あり。実機テストで担保 |
| リンクカード API の外部依存 | 低 | 取得失敗時は通常リンクにフォールバック、1時間キャッシュ |
| 画像 CDN の容量 | 低 | Supabase Storage は 1GB 無料枠。10MB/記事で 100 記事分 |
| TipTap v3 移行 | 低 | 現 v2 系で 2 年は十分。将来マイナーアップデートのみ |

---

## 9. コスト見積もり (Supabase Storage)

現在: 無料プラン (1 GB storage, 2 GB egress/月)

| シナリオ | 月間記事数 | 画像/記事 | 平均サイズ | 月次ストレージ増加 | 無料枠超過時期 |
|---|---|---|---|---|---|
| 低 | 4 | 3 | 500 KB | 6 MB | 年 72 MB → 超過なし |
| 中 | 10 | 5 | 800 KB | 40 MB | 年 480 MB → 2 年目半ば |
| 高 | 30 | 10 | 1 MB | 300 MB | 4 ヶ月で超過 → Pro プラン ($25/月) |

**対策**:
- アップロード時に自動圧縮 (1920px 幅にリサイズ, JPEG quality 85)
- Next.js `<Image>` の `<source type="image/webp">` で配信時さらに削減
- 1 年以上アクセス無い記事の画像は Glacier 的アーカイブに移動 (将来)

---

## 10. 実装開始の前提条件

このプランを実装するには、以下が必要:
1. v1 エディタ (現状) で実際に 5〜10 記事書いてみて不足点を体感
2. note.com の自分の記事編集画面を再度触って「必須機能」を再確認
3. ユーザー 2 名 (仁 / a さん) の執筆スタイルから要件を絞る
   - スマホで書くのか PC で書くのか
   - 画像メイン / テキストメイン
   - 記事の長さ (短文連投 / 長文じっくり)
4. 1〜2 週間の開発時間を確保できるスケジュール
5. Playwright の E2E テスト環境を整備 (現状のテストは単体のみ)

---

## 11. 参考リンク

- TipTap 公式: https://tiptap.dev
- TipTap x React チュートリアル: https://tiptap.dev/docs/editor/installation/react
- tiptap-markdown: https://github.com/aguingand/tiptap-markdown
- ProseMirror Guide: https://prosemirror.net/docs/guide/
- bleach (HTML sanitizer): https://bleach.readthedocs.io
- Supabase Storage docs: https://supabase.com/docs/guides/storage
- visualViewport API (モバイルキーボード検知): https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport

---

**このプランは実装開始時に再度精査すること**。技術選定、パッケージバージョン、
ライブラリの API はその時点で最新を確認して差分があれば更新する。
