# TASK-039: Hacker News カテゴリヘッダー追加

## タスク概要
Hacker Newsの表示形式を変更し、「Hacker News」をカテゴリヘッダーとして追加して、その下に投稿を表示する

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
- TASK-031（Hacker News GitHub Trending形式対応）の追加修正

## worktree名
`worktrees/TASK-039-hacker-news-category-header`

## 作業内容

### 1. 現状分析

#### 現在の表示形式
```
Hacker News (2025年06月30日)

1. AIの未来について考える ⬆️ 1,234
2. 新しいプログラミング言語の設計 ⬆️ 892
3. スタートアップの成功法則 ⬆️ 567
```

#### 希望の表示形式
```
Hacker News (2025年06月30日)

Hacker News
├─ 1. AIの未来について考える ⬆️ 1,234
├─ 2. 新しいプログラミング言語の設計 ⬆️ 892
└─ 3. スタートアップの成功法則 ⬆️ 567
```

### 2. parseHackerNewsMarkdown関数の修正

```typescript
function parseHackerNewsMarkdown(markdown: string): ContentItem[] {
  const items: ContentItem[] = [];
  const lines = markdown.split('\n');
  
  // 最初に「Hacker News」カテゴリヘッダーを追加
  items.push({
    title: 'Hacker News',
    url: '',
    content: '',
    isLanguageHeader: false,
    isCategoryHeader: true,
    isArticle: false
  });
  
  let articleNumber = 1;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 記事タイトル行を検出（### [タイトル](URL)）
    const titleMatch = line.match(/^###\s*\[([^\]]+)\]\(([^)]+)\)$/);
    if (titleMatch) {
      const title = titleMatch[1];
      const url = titleMatch[2];
      
      // スコア情報を次の行から抽出
      const scoreInfo = extractScoreInfo(lines, i);
      
      items.push({
        title: title,
        url: url,
        content: extractSummary(lines, i),
        isLanguageHeader: false,
        isCategoryHeader: false,
        isArticle: true,
        metadata: {
          source: 'hackernews',
          score: scoreInfo.score,
          articleNumber: articleNumber++
        }
      });
    }
  }
  
  return items;
}
```

### 3. UI表示の考慮事項

- **カテゴリヘッダー**: 「Hacker News」を固定で表示
- **記事番号**: カテゴリヘッダーごとに1からリセット（Hacker Newsは単一カテゴリなので実質1から連番）
- **スコア表示**: 各記事のスコアを表示（⬆️形式）
- **インデント**: カテゴリヘッダー下の記事を視覚的にインデント

### 4. 他のニュースソースとの統一性

この変更により、Hacker Newsも他のニュースソースと同様のレイアウトになります：

- **Tech News**: Tech Blogs、Hatenaなどのカテゴリ下に記事
- **Reddit Posts**: r/StableDiffusion、r/artificialなどのサブレディット下に投稿
- **Zenn/Qiita/note**: フィード名/タグ名/ハッシュタグ下に記事
- **Hacker News**: 「Hacker News」カテゴリ下に投稿

### 5. 期待される効果

- 統一されたUI体験
- 他のニュースソースとの一貫性
- 将来的に複数のHacker Newsフィードを追加する場合の拡張性

### 6. テスト確認項目

- カテゴリヘッダー「Hacker News」の表示
- 記事のインデント表示
- 記事番号の正しい表示
- スコア情報の維持
- ContentCardコンポーネントでの適切なレンダリング

### 7. 注意事項

- 既存のHacker News記事取得ロジック（services/）は変更しない
- フロントエンド側でのパース処理のみで実現
- 他のニュースソースとの表示一貫性を保つ