# TASK-021: Business Newsセクションでフィード名をタイトルとして表示

## タスク概要
Business Newsセクションで現在「Business」と表示されているカテゴリヘッダーを、各記事のフィード名（例：「日経ビジネス電子版　最新記事」）に変更する。Zenn、Qiita、Noteセクションと同様の表示形式に統一する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
なし

## worktree名
`worktrees/TASK-021-business-news-feed-title`

## 作業内容

### 1. parseBusinessNewsMarkdown関数の修正

現在の実装では「## Business」というカテゴリヘッダーをそのまま表示していますが、これを各記事のフィード名でグループ化して表示するように変更します。

#### 現在の処理フロー
1. `## Business` を検出してカテゴリヘッダーとして追加
2. 各記事を順番に処理

#### 新しい処理フロー
1. すべての記事を読み込み、フィード名でグループ化
2. 各フィードグループごとにヘッダーと記事を追加

### 2. 具体的な実装

`parseBusinessNewsMarkdown`関数を以下のように修正：

```typescript
function parseBusinessNewsMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  const feedGroups = new Map<string, { title: string; url: string; content: string }[]>();
  
  // まず全ての記事を解析してフィード別にグループ化
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 日付付きタイトルは無視
    if (line.startsWith('# ビジネスニュース記事')) {
      continue;
    }
    
    // カテゴリセクション（## Business）は無視
    if (line.startsWith('## ') && line.length > 3) {
      continue;
    }
    
    // 記事を検出
    if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const articleTitle = linkMatch[1];
        const articleUrl = linkMatch[2];
        
        // フィード情報と要約を取得
        let feedName = '';
        let summary = '';
        
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.startsWith('**フィード**:')) {
            feedName = nextLine.replace('**フィード**:', '').trim();
          } else if (nextLine.startsWith('**要約**:')) {
            summary = nextLine.replace('**要約**:', '').trim();
            
            for (let k = j + 1; k < lines.length; k++) {
              const summaryLine = lines[k].trim();
              
              if (summaryLine.startsWith('#') || summaryLine === '---' || summaryLine.startsWith('**')) {
                break;
              }
              
              if (summaryLine) {
                summary += '\n\n' + summaryLine;
              }
            }
          }
        }
        
        // フィード名でグループ化
        if (feedName) {
          if (!feedGroups.has(feedName)) {
            feedGroups.set(feedName, []);
          }
          
          let content = '';
          if (summary) {
            content = `**要約**:\n${summary}`;
          }
          
          feedGroups.get(feedName)!.push({
            title: articleTitle,
            url: articleUrl,
            content: content
          });
        }
      }
    }
  }
  
  // フィードグループごとにコンテンツアイテムを作成
  let globalArticleNumber = 1;
  
  for (const [feedName, articles] of feedGroups) {
    // フィード名をカテゴリヘッダーとして追加
    contentItems.push({
      title: feedName,
      content: '',
      source: 'business news',
      isCategoryHeader: true
    });
    
    // 各記事を追加
    articles.forEach((article) => {
      contentItems.push({
        title: article.title,
        content: article.content,
        url: article.url,
        source: 'business news',
        isArticle: true,
        metadata: {
          source: 'business news',
          articleNumber: globalArticleNumber++,
          feedName: feedName
        }
      });
    });
  }
  
  return contentItems;
}
```

### 3. Tech Newsへの同様の対応

Business Newsと同様にTech Newsセクションも存在する場合は、同じようにフィード名をタイトルとして表示するよう修正する必要があります。

Tech News用のパース関数が存在する場合は、同様の修正を適用します。

### 4. テスト手順

1. 開発サーバーを起動
2. Business Newsセクションにアクセス
3. 「Business」というヘッダーの代わりに「日経ビジネス電子版　最新記事」のようなフィード名が表示されることを確認
4. 複数のフィードがある場合、それぞれが独立したセクションとして表示されることを確認
5. Zenn、Qiita、Noteセクションと同様の表示形式になっていることを確認

## 完了条件

- [ ] parseBusinessNewsMarkdown関数を修正し、フィード名でグループ化
- [ ] カテゴリヘッダーとしてフィード名を表示
- [ ] Tech Newsセクションも同様に修正（存在する場合）
- [ ] ビルドエラーがない
- [ ] 実装したコードに警告がない