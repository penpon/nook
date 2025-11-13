# TASK-035: Reddit サブレディット直接カテゴリ化

## タスク概要
Reddit PostsのTechカテゴリを削除し、サブレディット（r/StableDiffusion、r/artificial等）を直接カテゴリヘッダーとして表示する

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/services/reddit_explorer.py`
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
- TASK-028（Reddit Posts形式統一）の置き換え

## worktree名
`worktrees/TASK-035-reddit-subreddit-categorization`

## 作業内容

### 1. 現状分析

#### 現在の4階層構造（TASK-028）
```
Reddit Posts (2025年06月30日)

Tech                           ← カテゴリヘッダー（削除対象）
├─ r/StableDiffusion          ← サブレディットヘッダー
│  ├─ 投稿1: AIアート生成術
│  └─ 投稿2: プロンプト最適化
└─ r/artificial               ← サブレディットヘッダー
   ├─ 投稿3: AGI最新動向
   └─ 投稿4: 機械学習倫理
```

#### 変更後の3階層構造（TASK-035）
```
Reddit Posts (2025年06月30日)

r/StableDiffusion             ← サブレディットを直接カテゴリヘッダーに
├─ 投稿1: AIアート生成術
└─ 投稿2: プロンプト最適化

r/artificial                  ← サブレディットを直接カテゴリヘッダーに
├─ 投稿3: AGI最新動向
└─ 投稿4: 機械学習倫理
```

### 2. バックエンド変更（reddit_explorer.py）

#### A. マークダウン生成ロジックの修正
```python
# 現在のロジック（修正前）
for category, subreddits in categories.items():
    content += f"## {category.capitalize()}\n\n"        # ← 削除
    
    for subreddit, subreddit_posts in subreddits.items():
        content += f"### r/{subreddit}\n\n"             # ← ## に変更
        
        for post in subreddit_posts:
            content += f"#### [{post.title}]({post.url})\n\n"  # ← ### に変更

# 修正後のロジック
for category, subreddits in categories.items():
    # カテゴリ行を削除
    
    for subreddit, subreddit_posts in subreddits.items():
        content += f"## r/{subreddit}\n\n"             # ### から ## に変更
        
        for post in subreddit_posts:
            content += f"### [{post.title}]({post.url})\n\n"   # #### から ### に変更
            content += f"アップボート数: {post.score}\n\n"
            content += f"**要約**:\n{post.summary}\n\n"
            content += "---\n\n"
```

### 3. フロントエンド変更（App.tsx）

#### A. parseRedditPostsMarkdown関数の修正
```typescript
function parseRedditPostsMarkdown(markdown: string): ContentItem[] {
  const items: ContentItem[] = [];
  const lines = markdown.split('\n');
  let articleNumber = 1;
  let currentSubreddit = '';
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // サブレディットを直接カテゴリヘッダーとして検出（## r/xxx）
    if (line.startsWith('## r/')) {
      currentSubreddit = line.substring(5).trim(); // "## r/" を除去
      articleNumber = 1; // カテゴリごとに番号をリセット
      
      items.push({
        title: currentSubreddit,
        url: '',
        content: '',
        isLanguageHeader: false,
        isCategoryHeader: true,    // サブレディットを直接カテゴリヘッダーに
        isArticle: false,
        metadata: {
          source: 'reddit',
          subreddit: currentSubreddit
        }
      });
    }
    
    // 投稿タイトル行を検出（### [タイトル](URL)）
    else if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const titleMatch = line.match(/^###\s*\[([^\]]+)\]\(([^)]+)\)$/);
      if (titleMatch && currentSubreddit) {
        const title = titleMatch[1];
        const url = titleMatch[2];
        
        // アップボート数と要約を取得
        const { score, summary } = extractRedditPostData(lines, i);
        
        items.push({
          title,
          url,
          content: summary,
          isLanguageHeader: false,
          isCategoryHeader: false,
          isArticle: true,
          metadata: {
            source: 'reddit',
            subreddit: currentSubreddit,
            score: score,
            articleNumber: articleNumber++
          }
        });
      }
    }
  }
  
  return items;
}
```

### 4. 表示形式の変更

#### 変更前（TASK-028）：
```
Reddit Posts (2025年06月30日)

Tech
├─ r/StableDiffusion
│  ├─ 1. AIアート生成術 ⬆️ 1,234
│  └─ 2. プロンプト最適化 ⬆️ 892
└─ r/artificial
   ├─ 3. AGI最新動向 ⬆️ 567
   └─ 4. 機械学習倫理 ⬆️ 443
```

#### 変更後（TASK-035）：
```
Reddit Posts (2025年06月30日)

r/StableDiffusion
├─ 1. AIアート生成術 ⬆️ 1,234
└─ 2. プロンプト最適化 ⬆️ 892

r/artificial
├─ 1. AGI最新動向 ⬆️ 567        // 番号が1にリセット
└─ 2. 機械学習倫理 ⬆️ 443
```

### 5. Tech Newsとの統一性

#### Tech News（参考）
```
Tech News (2025年06月30日)

Tech Blogs
├─ 記事1
└─ 記事2

Hatena
├─ 記事3
└─ 記事4
```

#### Reddit Posts（TASK-035後）
```
Reddit Posts (2025年06月30日)

r/StableDiffusion
├─ 投稿1
└─ 投稿2

r/artificial
├─ 投稿3
└─ 投稿4
```

### 6. UI表示の考慮事項
- **カテゴリヘッダー**: サブレディット名をそのまま表示（r/StableDiffusion）
- **記事番号**: カテゴリヘッダー（サブレディット）ごとに1からリセット
- **アップボート表示**: 既存の⬆️アイコンを維持
- **ソースタグ**: 「reddit」タグで統一

### 7. 期待される効果
- Reddit投稿の直感的な分類表示
- サブレディット別の効率的なアクセス
- Tech Newsと統一したマルチカテゴリ体験
- 4階層から3階層への簡素化

### 8. テスト確認項目
- サブレディット名の正確な抽出
- カテゴリヘッダーの適切な表示
- 投稿の連番付与
- アップボート情報の表示
- 既存のReddit特有機能の維持

### 9. 注意事項
- 既存のReddit投稿取得ロジック（categories構造）は維持
- バックエンドでのカテゴリ情報を除去しつつ、サブレディット情報は保持
- フロントエンドでisSubredditHeaderは不要（isCategoryHeaderで代用）
- 既存のContentCardコンポーネントでサブレディット表示に対応
- レスポンシブデザインの維持