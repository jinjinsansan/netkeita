# 記事投稿機能（note風）— 開発計画書

## 概要
管理者が競馬予想の記事を投稿できる機能。note.com風のUIで、Xシェア機能付き。

## 画面構成

| ページ | パス | 権限 | 内容 |
|--------|------|------|------|
| 記事一覧 | `/articles` | 誰でも | カード形式の記事リスト |
| 記事詳細 | `/articles/[slug]` | 誰でも | 本文表示 + Xシェアボタン |
| 記事作成 | `/articles/new` | 管理者のみ | Markdownエディタ + プレビュー |
| 記事編集 | `/articles/[slug]/edit` | 管理者のみ | 既存記事の編集 |

---

## Phase 1: バックエンド API（30分）

### 1-1. データ構造設計（Redis db=5）

```
キー: nk:article:{slug}
値: {
  "slug": "derby-kyo-2026-preview",
  "title": "ダービー卿CT 2026 全馬分析",
  "description": "中山芝1600mの重賞を8項目AIデータで徹底分析",
  "body": "## 注目馬\n\n今回の...",  // Markdown
  "thumbnail_url": "",  // OGP用サムネイル画像URL
  "author": "netkeita",
  "status": "published",  // published | draft
  "created_at": "2026-04-05T10:00:00",
  "updated_at": "2026-04-05T10:00:00"
}

キー: nk:articles:index
値: ["derby-kyo-2026-preview", "hanshin-11r-analysis", ...]  // slug一覧（新しい順）
```

### 1-2. API エンドポイント

| メソッド | パス | 権限 | 説明 |
|----------|------|------|------|
| GET | `/api/articles` | 公開 | 記事一覧（title, slug, description, thumbnail, created_at） |
| GET | `/api/articles/{slug}` | 公開 | 記事詳細（全フィールド） |
| POST | `/api/articles` | 管理者 | 記事作成 |
| PUT | `/api/articles/{slug}` | 管理者 | 記事更新 |
| DELETE | `/api/articles/{slug}` | 管理者 | 記事削除 |

### 1-3. 管理者判定

```python
# config.py に追加
ADMIN_LINE_USER_IDS = os.getenv("ADMIN_LINE_USER_IDS", "").split(",")

# エンドポイントで判定
def is_admin(request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return False
    user_data = redis_sessions.get(f"session:{session_id}")
    return user_data and json.loads(user_data)["user_id"] in ADMIN_LINE_USER_IDS
```

### 1-4. 実装ファイル

- `api/main.py` に5エンドポイント追加
- `api/config.py` に `ADMIN_LINE_USER_IDS` 追加
- VPS `.env.local` に管理者のLINE user_id設定

---

## Phase 2: フロントエンド — 記事一覧・詳細ページ（45分）

### 2-1. 記事一覧 `/articles`

- カード形式のグリッドレイアウト
- 各カード: サムネイル + タイトル + 説明 + 日付
- ヘッダーに「記事」リンク追加
- 管理者のみ「新規作成」ボタン表示

### 2-2. 記事詳細 `/articles/[slug]`

- note風のクリーンなレイアウト（最大幅680px、中央寄せ）
- Markdownレンダリング（`react-markdown` + `remark-gfm`）
- 見出し、太字、リスト、コードブロック、画像対応
- 記事下部にXシェアボタン
- 管理者のみ「編集」ボタン表示

### 2-3. Xシェアボタン

```tsx
const shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(articleUrl)}`;
```

### 2-4. 実装ファイル

- `frontend/src/app/articles/page.tsx` — 一覧
- `frontend/src/app/articles/[slug]/page.tsx` — 詳細
- `frontend/src/components/ArticleCard.tsx` — カードコンポーネント
- `frontend/src/components/ShareButton.tsx` — Xシェアボタン
- `frontend/src/components/HeaderLoginButton.tsx` — 「記事」リンク追加

---

## Phase 3: フロントエンド — 記事エディタ（60分）

### 3-1. 記事作成 `/articles/new`

- 左右2カラム: 左=Markdownエディタ、右=リアルタイムプレビュー
- モバイル: タブ切替（編集/プレビュー）
- 入力フィールド:
  - タイトル（テキスト）
  - スラッグ（自動生成 or 手入力）
  - 説明文（textarea、OGP用）
  - サムネイルURL（テキスト、後から画像アップロード対応可）
  - 本文（Markdownテキストエリア）
- ボタン: 「下書き保存」「公開」

### 3-2. 記事編集 `/articles/[slug]/edit`

- 作成ページと同じUI、既存データをプリフィル
- 「更新」「削除」ボタン

### 3-3. 実装ファイル

- `frontend/src/app/articles/new/page.tsx` — 作成
- `frontend/src/app/articles/[slug]/edit/page.tsx` — 編集
- `frontend/src/components/ArticleEditor.tsx` — エディタコンポーネント
- `frontend/src/lib/api.ts` — 記事CRUD関数追加

---

## Phase 4: OGP対応（20分）

### 4-1. 動的OGPメタタグ

`/articles/[slug]` ページで動的にOGPを設定：

```tsx
export async function generateMetadata({ params }): Promise<Metadata> {
  const article = await fetchArticle(params.slug);
  return {
    title: article.title,
    description: article.description,
    openGraph: {
      title: article.title,
      description: article.description,
      images: [article.thumbnail_url],
      url: `https://www.netkeita.com/articles/${params.slug}`,
    },
    twitter: {
      card: "summary_large_image",
      title: article.title,
      description: article.description,
      images: [article.thumbnail_url],
    },
  };
}
```

### 4-2. OGP確認

- https://cards-dev.twitter.com/validator でXカード表示確認
- シェア時にタイトル+サムネ+説明が表示されることを確認

---

## Phase 5: デプロイ・動作確認（15分）

1. VPSにAPI変更デプロイ + 再起動
2. 管理者LINE user_idを`.env.local`に設定
3. Vercelにフロントデプロイ
4. 記事作成 → 公開 → 一覧表示 → Xシェアボタン動作確認

---

## 依存パッケージ（追加が必要）

```bash
cd frontend
npm install react-markdown remark-gfm
```

---

## 将来拡張（Phase 2以降で対応可能）

- [ ] 画像アップロード（Cloudflare R2 or Vercel Blob）
- [ ] 記事へのいいね機能
- [ ] 記事カテゴリ/タグ
- [ ] 記事内にレースデータ埋め込み（特定レースのmatrixを記事内に表示）
- [ ] 予約投稿（指定日時に自動公開）
- [ ] RSSフィード

---

## 推定作業時間

| Phase | 内容 | 時間 |
|-------|------|------|
| 1 | バックエンドAPI | 30分 |
| 2 | 一覧・詳細ページ | 45分 |
| 3 | エディタ | 60分 |
| 4 | OGP対応 | 20分 |
| 5 | デプロイ・確認 | 15分 |
| **合計** | | **約3時間** |

## ステータス
**日曜日 JRA終了後に開発開始予定**
