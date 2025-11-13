# TASK-036: Zenn Articles フィード直接カテゴリ化

## タスク概要
Zenn Articlesの独自分類を廃止し、フィード情報をそのまま使用してカテゴリヘッダーとして表示する

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
- TASK-032（Zenn Articles フィード分類実装）の置き換え

## worktree名
`worktrees/TASK-036-zenn-feed-direct-categorization`

## 作業内容

### 1. 現状分析

#### TASK-032での分類方式（廃止対象）
```
Zenn Articles (2025年06月30日)

AI駆動開発ツール              ← 独自カテゴリ（廃止）
├─ 1. Claude Code実践ガイド
└─ 2. Cursor活用術

画像生成AI                    ← 独自カテゴリ（廃止）
└─ 3. Stable Diffusion最新情報
```

#### 変更後の表示（TASK-036）
```
Zenn Articles (2025年06月30日)

Claude Code                   ← フィード名をそのまま使用
├─ 1. Claude Code実践ガイド
└─ 2. もう一つのClaude Code記事

Cursor                        ← フィード名をそのまま使用
└─ 1. Cursor活用術           // 番号が1にリセット

Stable Diffusion             ← フィード名をそのまま使用
└─ 1. Stable Diffusion最新情報 // 番号が1にリセット
```

### 2. フィード情報の分析

Zennのフィード情報形式：
- `Zennの「Claude Code」のフィード`
- `Zennの「Cursor」のフィード`
- `Zennの「Stable Diffusion」のフィード`
- `Zennの「生成AI」のフィード`

抽出すべきフィード名：`「」`内の文字列

### 3. parseZennArticlesMarkdown関数の修正

```typescript
function parseZennArticlesMarkdown(markdown: string): ContentItem[] {
  const items: ContentItem[] = [];
  const lines = markdown.split('\n');
  const feedGroups = new Map<string, any[]>();
  
  // 記事の解析とフィード別グループ化
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 記事タイトル行を検出（### [タイトル](URL)）
    const titleMatch = line.match(/^###\s*\[([^\]]+)\]\(([^)]+)\)$/);
    if (titleMatch) {
      const title = titleMatch[1];
      const url = titleMatch[2];
      
      // フィード情報を抽出
      const feedInfo = extractFeedInfo(lines, i);
      const feedName = extractZennFeedName(feedInfo);
      
      // フィード名でグループ化
      if (!feedGroups.has(feedName)) {
        feedGroups.set(feedName, []);
      }
      
      feedGroups.get(feedName)!.push({
        title,
        url,
        content: extractSummary(lines, i),
        feedInfo
      });
    }
  }
  
  // フィード名をカテゴリヘッダーとして生成
  for (const [feedName, articles] of feedGroups) {
    // フィード名をそのままカテゴリヘッダーに
    items.push({
      title: feedName,
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
          source: 'zenn',
          feed: feedName,
          articleNumber: articleNumber++
        }
      });
    }
  }
  
  return items;
}

// Zennフィード名を抽出
function extractZennFeedName(feedInfo: string): string {
  // 例: 'Zennの「Claude Code」のフィード' → 'Claude Code'
  const match = feedInfo.match(/Zennの「(.+?)」のフィード/);
  if (match) {
    return match[1];
  }
  
  // マッチしない場合はフィード情報全体を返す
  return feedInfo;
}
```

### 4. UI表示の考慮事項
- **カテゴリヘッダー**: フィード名をそのまま表示（Claude Code、Cursor等）
- **記事番号**: カテゴリヘッダー（フィード）ごとに1からリセット
- **フィード表示**: 記事詳細にフィード情報を表示
- **ソースタグ**: 「zenn」タグで統一

### 5. 期待される効果
- フィード名による直感的な分類
- 独自カテゴリ分類の廃止によるシンプル化
- 実際のZennトピックとの一致
- 新しいフィードへの自動対応

### 6. テスト確認項目
- フィード名の正確な抽出
- 日本語フィード名の適切な処理
- カテゴリヘッダーの適切な表示
- 記事の連番付与
- フィード情報の正しい抽出

### 7. 注意事項
- 既存のZenn記事取得ロジック（services/）は変更しない
- フロントエンド側でのパース処理のみで実現
- フィード名の抽出ロジックを確実に実装
- 新しいフィードが追加されても自動的に対応