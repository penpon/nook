# TASK-048: フロントエンドカテゴリ別番号付け修正

## タスク概要
Tech News、Business Newsでカテゴリ（フィード）ごとに通し番号をリセットするよう修正。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
なし（フロントエンドのみの修正）

## worktree名
`worktrees/TASK-048-frontend-category-numbering`

## 作業内容

### 1. Tech News番号付けロジック修正（L827-840）

**現在の問題**：
```typescript
let articleCount = 0;
return processedItems.map((item, index) => {
  const isArticle = item.isArticle;
  const articleIndex = isArticle ? articleCount++ : undefined;
  // metadata.articleNumberを使用していない
```

**修正後**：
```typescript
return processedItems.map((item, index) => {
  const isArticle = item.isArticle;
  // metadata.articleNumberを使用してフィードごとにリセット
  const articleIndex = isArticle && item.metadata?.articleNumber 
    ? item.metadata.articleNumber - 1 
    : undefined;
  return (
    <ContentCard 
      key={index} 
      item={item} 
      darkMode={darkMode} 
      index={articleIndex} 
    />
  );
});
```

### 2. Business News番号付けロジック修正（L843-856）

**現在の問題**：
```typescript
let articleCount = 0;
return processedItems.map((item, index) => {
  const isArticle = item.isArticle;
  const articleIndex = isArticle ? articleCount++ : undefined;
  // metadata.articleNumberを使用していない
```

**修正後**：
```typescript
return processedItems.map((item, index) => {
  const isArticle = item.isArticle;
  // metadata.articleNumberを使用してフィードごとにリセット
  const articleIndex = isArticle && item.metadata?.articleNumber 
    ? item.metadata.articleNumber - 1 
    : undefined;
  return (
    <ContentCard 
      key={index} 
      item={item} 
      darkMode={darkMode} 
      index={articleIndex} 
    />
  );
});
```

### 3. 修正内容の詳細

#### 変更理由
- parseTechNewsMarkdown/parseBusinessNewsMarkdownで既にフィードごとにarticleNumberがリセットされている
- しかし、レンダリング時にその値を使用せず、全体通しの番号を使用していた
- これにより、フィードが変わっても番号がリセットされない問題が発生

#### 実装のポイント
- `item.metadata?.articleNumber`を使用（既にパース時に設定済み）
- articleNumberは1から始まるため、表示用には-1する（0から表示）
- metadataがない場合はundefinedを返す（安全性確保）

### 4. 動作確認手順

1. Tech Newsページ（http://localhost:5173/?source=tech-news）にアクセス
2. 各フィード（カテゴリ）の最初の記事が「1.」から始まることを確認
3. 異なるフィードに移ったときに番号が「1.」にリセットされることを確認

4. Business Newsページ（http://localhost:5173/?source=business-news）にアクセス
5. 同様に各フィードで番号がリセットされることを確認

### 5. 期待される表示例

```
Tech_blogs
1. 記事タイトル1
2. 記事タイトル2

Hatena
1. 記事タイトル1  ← ここで番号がリセット
2. 記事タイトル2

Publickey
1. 記事タイトル1  ← ここで番号がリセット
```

## 期待される効果
- Tech News/Business Newsでフィードごとに番号が1からリセットされる
- ユーザーが各フィード内での記事数を把握しやすくなる
- パース時に設定したメタデータが正しく活用される

## 注意事項
- 他のソース（GitHub、Reddit等）の番号付けロジックには影響しない
- metadata.articleNumberが存在しない場合の安全性を確保
- パフォーマンスへの影響は最小限（既存のデータを活用するだけ）