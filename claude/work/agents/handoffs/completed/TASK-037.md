# TASK-037: Qiita Articles フィード直接カテゴリ化

## タスク概要
Qiita Articlesの独自分類を廃止し、タグ名をそのまま使用してカテゴリヘッダーとして表示する

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
- TASK-033（Qiita Articles フィード分類実装）の置き換え

## worktree名
`worktrees/TASK-037-qiita-feed-direct-categorization`

## 作業内容

### 1. 現状分析

#### TASK-033での分類方式（廃止対象）
```
Qiita Articles (2025年06月30日)

Web開発                      ← 独自カテゴリ（廃止）
├─ 1. Vue.js 3の新機能
└─ 2. React最新動向

AI・機械学習                  ← 独自カテゴリ（廃止）
└─ 3. ChatGPT API活用法
```

#### 変更後の表示（TASK-037）
```
Qiita Articles (2025年06月30日)

Vue.js                       ← タグ名をそのまま使用
├─ 1. Vue.js 3の新機能
└─ 2. Vue.jsコンポーネント設計

ChatGPT                      ← タグ名をそのまま使用
└─ 1. ChatGPT API活用法      // 番号が1にリセット

React                        ← タグ名をそのまま使用
└─ 1. React最新動向          // 番号が1にリセット
```

### 2. フィード情報の分析

Qiitaのフィード情報形式：
- `ChatGPTタグが付けられた新着記事 - Qiita`
- `Vue.jsタグが付けられた新着記事 - Qiita`
- `Reactタグが付けられた新着記事 - Qiita`
- `Qiita - 人気の記事`（特殊ケース）

抽出すべきタグ名：`タグが付けられた`の前の文字列

### 3. parseQiitaArticlesMarkdown関数の修正

```typescript
function parseQiitaArticlesMarkdown(markdown: string): ContentItem[] {
  const items: ContentItem[] = [];
  const lines = markdown.split('\n');
  const tagGroups = new Map<string, any[]>();
  
  // 記事の解析とタグ別グループ化
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 記事タイトル行を検出（### [タイトル](URL)）
    const titleMatch = line.match(/^###\s*\[([^\]]+)\]\(([^)]+)\)$/);
    if (titleMatch) {
      const title = titleMatch[1];
      const url = titleMatch[2];
      
      // フィード情報を抽出
      const feedInfo = extractFeedInfo(lines, i);
      const tagName = extractQiitaTagName(feedInfo);
      
      // タグ名でグループ化
      if (!tagGroups.has(tagName)) {
        tagGroups.set(tagName, []);
      }
      
      tagGroups.get(tagName)!.push({
        title,
        url,
        content: extractSummary(lines, i),
        feedInfo
      });
    }
  }
  
  // タグ名をカテゴリヘッダーとして生成
  for (const [tagName, articles] of tagGroups) {
    // タグ名をそのままカテゴリヘッダーに
    items.push({
      title: tagName,
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
          source: 'qiita',
          feed: tagName,
          articleNumber: articleNumber++
        }
      });
    }
  }
  
  return items;
}

// Qiitaタグ名を抽出
function extractQiitaTagName(feedInfo: string): string {
  // 例: 'ChatGPTタグが付けられた新着記事 - Qiita' → 'ChatGPT'
  const tagMatch = feedInfo.match(/^(.+?)タグが付けられた/);
  if (tagMatch) {
    return tagMatch[1];
  }
  
  // 人気記事の場合
  if (feedInfo.includes('Qiita - 人気の記事')) {
    return '人気の記事';
  }
  
  // マッチしない場合はフィード情報から推測
  return feedInfo.replace(' - Qiita', '').trim();
}
```

### 4. UI表示の考慮事項
- **カテゴリヘッダー**: タグ名をそのまま表示（ChatGPT、Vue.js、React等）
- **記事番号**: カテゴリヘッダー（タグ）ごとに1からリセット
- **タグ表示**: 記事詳細にQiitaタグ情報を表示
- **ソースタグ**: 「qiita」タグで統一

### 5. 期待される効果
- Qiitaタグによる直感的な分類
- 独自カテゴリ分類の廃止によるシンプル化
- 実際のQiitaタグとの一致
- 新しいタグへの自動対応

### 6. テスト確認項目
- タグ名の正確な抽出
- 特殊ケース（人気の記事）の処理
- カテゴリヘッダーの適切な表示
- 記事の連番付与
- タグ情報の正しい抽出

### 7. 注意事項
- 既存のQiita記事取得ロジック（services/）は変更しない
- フロントエンド側でのパース処理のみで実現
- タグ名の抽出ロジックを確実に実装
- 新しいタグが追加されても自動的に対応
- 「人気の記事」などの特殊フィードへの対応