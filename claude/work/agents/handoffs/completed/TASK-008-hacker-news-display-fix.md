# TASK-008: Hacker News記事表示修正

## タスク概要
Hacker Newsで記事内容が表示されない問題を修正。
根本原因：フロントエンドが構造化JSONデータをMarkdownとしてパースしようとしているため、記事が表示されない。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx` (1255-1264行目のHacker News処理部分)

## 前提タスク
なし（独立タスク）

## worktree名
worktrees/TASK-008-hacker-news-display-fix

## 作業内容

### 1. 問題の根本原因

**判明した問題**:
- APIレスポンス: 構造化されたJSONデータ（各記事がオブジェクトとして返される）
- フロントエンド期待値: `## [タイトル](URL)`形式のMarkdownテキスト
- 現在の処理: `parseHackerNewsMarkdown(data.items[0].content)`でMarkdownパースを試行
- 結果: パース失敗により記事が表示されない

### 2. APIレスポンス構造（確認済み）

```json
{
  "items": [
    {
      "title": "記事タイトル",
      "content": "**要約**:\n記事の要約内容...\n\nスコア: 392",
      "url": "https://example.com",
      "source": "hacker news"
    },
    // ... 他の記事
  ]
}
```

### 3. 修正方針

Hacker Newsの処理部分（1255-1264行目）を修正し、JSONレスポンスを適切に処理：

#### 修正前（1255-1264行目）
```typescript
// Hacker Newsの場合は特別な処理
if (selectedSource === 'hacker news' && data.items[0]?.content) {
  try {
    return parseHackerNewsMarkdown(data.items[0].content);
  } catch (error) {
    console.error('Hacker News Markdown parsing error:', error);
    // フォールバック: 元のアイテムをそのまま返す
    return data.items;
  }
}
```

#### 修正後
```typescript
// Hacker Newsの場合は構造化データをそのまま処理
if (selectedSource === 'hacker news' && data.items && data.items.length > 0) {
  // カテゴリヘッダーを追加
  const items: ContentItem[] = [{
    title: 'Hacker News',
    url: '',
    content: '',
    isLanguageHeader: false,
    isCategoryHeader: true,
    isArticle: false
  }];
  
  // 各記事を適切な形式に変換
  data.items.forEach((item, index) => {
    items.push({
      title: item.title,
      url: item.url,
      content: item.content,
      isLanguageHeader: false,
      isCategoryHeader: false,
      isArticle: true,
      metadata: {
        source: 'hackernews',
        articleNumber: index + 1
      }
    });
  });
  
  return items;
}
```

### 4. 修正の詳細

#### 新しい処理フロー
1. **構造化データ確認**: `data.items`が存在することを確認
2. **カテゴリヘッダー追加**: 他のソースと同様の「Hacker News」ヘッダーを追加
3. **記事変換**: 各JSONオブジェクトを`ContentItem`形式に変換
4. **メタデータ設定**: `source`と`articleNumber`を適切に設定

#### 期待される結果
- Hacker Newsの記事一覧が正常に表示される
- 各記事にタイトル、URL、要約内容が表示される
- 番号付けが正しく動作する（1から開始）
- 他のソースと同様のUI表示になる

### 5. 検証方法

#### 動作確認
1. **フロントエンド確認**: Hacker Newsを選択して記事一覧が表示されることを確認
2. **データ表示**: 各記事のタイトル、URL、要約が正常に表示されることを確認
3. **番号付け**: 記事番号が1から開始されることを確認
4. **レスポンシブ**: ダークモード切り替えなど他の機能に影響しないことを確認

#### 他ソースとの比較
- ArXivと同様の表示レイアウトになることを確認
- カテゴリヘッダーが適切に表示されることを確認

### 6. 技術的注意点

#### 削除する処理
- `parseHackerNewsMarkdown`関数の呼び出し（不要になる）
- Markdownパース関連のエラーハンドリング

#### 保持する処理
- エラーハンドリングの基本構造
- フォールバック処理（`data.items`をそのまま返す）
- 他のソースの処理には影響しない

#### データ型の整合性
- 既存の`ContentItem`インターフェースとの互換性を維持
- `metadata.source`を'hackernews'に設定（他のソースとの一貫性）

## 期待される効果

- Hacker News記事の正常表示
- ユーザーエクスペリエンスの向上
- バックエンド・フロントエンド間のデータフロー最適化