# TASK-038: note Articles フィード直接カテゴリ化

## タスク概要
note Articlesの独自分類を廃止し、ハッシュタグ名をそのまま使用してカテゴリヘッダーとして表示する

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
- TASK-034（note Articles フィード分類実装）の置き換え

## worktree名
`worktrees/TASK-038-note-feed-direct-categorization`

## 作業内容

### 1. 現状分析

#### TASK-034での分類方式（廃止対象）
```
note Articles (2025年06月30日)

AI・開発ツール               ← 独自カテゴリ（廃止）
└─ 1. ClaudeCode実践記

ビジネス・起業               ← 独自カテゴリ（廃止）
└─ 2. スタートアップ体験談
```

#### 変更後の表示（TASK-038）
```
note Articles (2025年06月30日)

#ClaudeCode                  ← ハッシュタグをそのまま使用
├─ 1. ClaudeCode実践記
└─ 2. ClaudeCodeで変わった開発体験

#スタートアップ              ← ハッシュタグをそのまま使用
└─ 1. スタートアップ体験談   // 番号が1にリセット

#デザイン                    ← ハッシュタグをそのまま使用
└─ 1. デザインシステム構築記 // 番号が1にリセット
```

### 2. フィード情報の分析

noteのフィード情報形式：
- `#ClaudeCodeタグ`
- `#Anthropicタグ`
- `#スタートアップタグ`
- `#デザインタグ`

抽出すべきハッシュタグ：`#`を含む全体

### 3. parseNoteArticlesMarkdown関数の修正

```typescript
function parseNoteArticlesMarkdown(markdown: string): ContentItem[] {
  const items: ContentItem[] = [];
  const lines = markdown.split('\n');
  const hashtagGroups = new Map<string, any[]>();
  
  // 記事の解析とハッシュタグ別グループ化
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 記事タイトル行を検出（### [タイトル](URL)）
    const titleMatch = line.match(/^###\s*\[([^\]]+)\]\(([^)]+)\)$/);
    if (titleMatch) {
      const title = titleMatch[1];
      const url = titleMatch[2];
      
      // フィード情報を抽出
      const feedInfo = extractFeedInfo(lines, i);
      const hashtag = extractNoteHashtag(feedInfo);
      
      // ハッシュタグでグループ化
      if (!hashtagGroups.has(hashtag)) {
        hashtagGroups.set(hashtag, []);
      }
      
      hashtagGroups.get(hashtag)!.push({
        title,
        url,
        content: extractSummary(lines, i),
        feedInfo
      });
    }
  }
  
  // ハッシュタグをカテゴリヘッダーとして生成
  for (const [hashtag, articles] of hashtagGroups) {
    // ハッシュタグをそのままカテゴリヘッダーに
    items.push({
      title: hashtag,
      url: '',
      content: '',
      isLanguageHeader: false,
      isCategoryHeader: true,
      isArticle: false
    });
    
    // 記事を追加（カテゴリごとに番号をリセット）
    let articleNumber = 1;
    for (const article of articles) {
      items.push({
        title: article.title,
        url: article.url,
        content: article.content,
        isLanguageHeader: false,
        isCategoryHeader: false,
        isArticle: true,
        metadata: {
          source: 'note',
          feed: hashtag,
          articleNumber: articleNumber++
        }
      });
    }
  }
  
  return items;
}

// noteハッシュタグを抽出
function extractNoteHashtag(feedInfo: string): string {
  // 例: '#ClaudeCodeタグ' → '#ClaudeCode'
  const hashtagMatch = feedInfo.match(/^(#.+?)タグ$/);
  if (hashtagMatch) {
    return hashtagMatch[1];
  }
  
  // マッチしない場合はフィード情報全体を返す
  return feedInfo;
}
```

### 4. UI表示の考慮事項
- **カテゴリヘッダー**: ハッシュタグをそのまま表示（#ClaudeCode、#スタートアップ等）
- **記事番号**: カテゴリヘッダー（ハッシュタグ）ごとに1からリセット
- **ハッシュタグ表示**: 記事詳細にnoteハッシュタグ情報を表示
- **ソースタグ**: 「note」タグで統一

### 5. 期待される効果
- noteハッシュタグによる直感的な分類
- 独自カテゴリ分類の廃止によるシンプル化
- 実際のnoteハッシュタグとの一致
- 新しいハッシュタグへの自動対応

### 6. テスト確認項目
- ハッシュタグの正確な抽出（#記号を含む）
- 日本語ハッシュタグの適切な処理
- カテゴリヘッダーの適切な表示
- 記事の連番付与
- ハッシュタグ情報の正しい抽出

### 7. 注意事項
- 既存のnote記事取得ロジック（services/）は変更しない
- フロントエンド側でのパース処理のみで実現
- ハッシュタグの#記号を保持
- 新しいハッシュタグが追加されても自動的に対応
- 日本語ハッシュタグの適切な処理