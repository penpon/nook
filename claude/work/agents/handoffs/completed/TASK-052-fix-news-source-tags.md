# TASK-052: ニュースソースタグ表示修正
## タスク概要: Zenn, Qiita, Note, Reddit, ArxivのContentCardでソースタグが表示されない問題を修正
## 変更予定ファイル: nook/frontend/src/App.tsx
## 前提タスク: なし
## worktree名: worktrees/TASK-052-fix-news-source-tags
## 作業内容:

### 1. 問題の詳細
- GitHub TrendingとHacker Newsではソースタグ（青い丸いタグ）が表示される
- Zenn, Qiita, Note, Reddit, Arxivではソースタグが表示されない
- 原因: これらのソースのパース関数で`source`フィールドが`metadata`オブジェクト内にのみ設定されており、トップレベルに設定されていない

### 2. 修正内容
以下のパース関数で、ContentItemに`source`フィールドをトップレベルに追加する：

#### parseZennArticlesMarkdown (404-416行目)
```typescript
contentItems.push({
  title: article.title,
  url: article.url,
  content: content,
  source: 'zenn',  // この行を追加
  isLanguageHeader: false,
  // ... 以下既存のフィールド
});
```

#### parseQiitaArticlesMarkdown (535-547行目)
```typescript
contentItems.push({
  title: article.title,
  url: article.url,
  content: content,
  source: 'qiita',  // この行を追加
  isLanguageHeader: false,
  // ... 以下既存のフィールド
});
```

#### parseNoteArticlesMarkdown (673-685行目)
```typescript
items.push({
  title: article.title,
  url: article.url,
  content: article.content,
  source: 'note',  // この行を追加
  isLanguageHeader: false,
  // ... 以下既存のフィールド
});
```

#### parseRedditPostsMarkdown (888-901行目)
```typescript
contentItems.push({
  title,
  url,
  content: content,
  source: 'reddit',  // この行を追加
  isLanguageHeader: false,
  // ... 以下既存のフィールド
});
```

#### parseAcademicPapersMarkdown (774-785行目)
```typescript
items.push({
  title: title,
  url: url,
  content: content,
  source: 'arxiv',  // この行を追加
  isLanguageHeader: false,
  // ... 以下既存のフィールド
});
```

### 3. テスト手順
1. フロントエンドを起動
2. 各ニュースソース（Zenn, Qiita, Note, Reddit, Arxiv）に切り替え
3. 各記事のContentCardに青いソースタグが表示されることを確認
4. タグ内にソース名（zenn, qiita, note, reddit, arxiv）が表示されることを確認

### 4. 注意事項
- 4chanと5chanは既に正しく設定されているため修正不要
- GitHub TrendingとHacker Newsも既に正しく設定されているため修正不要
- `metadata`オブジェクト内の`source`フィールドは削除せず、そのまま残す（他の用途で使用されている可能性があるため）