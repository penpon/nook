# TASK-040: Academic Papers カテゴリヘッダー追加

## タスク概要
Academic Papersの表示形式を変更し、「ArXiv」をカテゴリヘッダーとして追加して、その下に論文を表示する

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
- なし（Academic Papers関連の既存タスク）

## worktree名
`worktrees/TASK-040-academic-papers-category-header`

## 作業内容

### 1. 現状分析

#### 現在の表示形式
```
Academic Papers (2025年06月30日)

1. 大規模言語モデルの効率的な学習手法
2. 量子コンピューティングにおける誤り訂正
3. 自動運転車のための深層強化学習
```

#### 希望の表示形式
```
Academic Papers (2025年06月30日)

ArXiv
├─ 1. 大規模言語モデルの効率的な学習手法
├─ 2. 量子コンピューティングにおける誤り訂正
└─ 3. 自動運転車のための深層強化学習
```

### 2. parseAcademicPapersMarkdown関数の実装

```typescript
function parseAcademicPapersMarkdown(markdown: string): ContentItem[] {
  const items: ContentItem[] = [];
  const lines = markdown.split('\n');
  
  // 最初に「ArXiv」カテゴリヘッダーを追加
  items.push({
    title: 'ArXiv',
    url: '',
    content: '',
    isLanguageHeader: false,
    isCategoryHeader: true,
    isArticle: false
  });
  
  let articleNumber = 1;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 論文タイトル行を検出（### [タイトル](URL)）
    const titleMatch = line.match(/^###\s*\[([^\]]+)\]\(([^)]+)\)$/);
    if (titleMatch) {
      const title = titleMatch[1];
      const url = titleMatch[2];
      
      items.push({
        title: title,
        url: url,
        content: extractSummary(lines, i),
        isLanguageHeader: false,
        isCategoryHeader: false,
        isArticle: true,
        metadata: {
          source: 'arxiv',
          articleNumber: articleNumber++
        }
      });
    }
  }
  
  return items;
}
```

### 3. UI表示の考慮事項

- **カテゴリヘッダー**: 「ArXiv」を固定で表示
- **記事番号**: カテゴリごとにリセット（1から開始）
- **インデント**: カテゴリヘッダー下の論文を視覚的にインデント
- **ツリー構造**: ├─、└─ を使用して階層を表現

### 4. 番号付けの重要な変更

**カテゴリヘッダーごとに番号をリセット**する必要があります。これは他のすべてのニュースソースにも適用されます：

```
Tech News
├─ Tech Blogs
│  ├─ 1. 記事A
│  └─ 2. 記事B
└─ Hatena
   ├─ 1. 記事C  // 番号がリセットされる
   └─ 2. 記事D
```

### 5. 他のニュースソースとの統一性

この変更により、Academic Papersも他のニュースソースと同様のレイアウトになります：

- **Hacker News**: 「Hacker News」カテゴリ下に投稿（TASK-039）
- **Tech News**: 複数カテゴリ（Tech Blogs、Hatena等）
- **Reddit Posts**: 複数サブレディット（r/StableDiffusion等）
- **Academic Papers**: 「ArXiv」カテゴリ下に論文

### 6. 期待される効果

- 統一されたUI体験
- 他のニュースソースとの一貫性
- 将来的に複数の論文ソース（ArXiv以外）を追加する場合の拡張性

### 7. テスト確認項目

- カテゴリヘッダー「ArXiv」の表示
- 論文のインデント表示
- 記事番号の正しい表示（1から開始）
- ContentCardコンポーネントでの適切なレンダリング

### 8. 注意事項

- 既存のAcademic Papers記事取得ロジック（services/）は変更しない
- フロントエンド側でのパース処理のみで実現
- 他のニュースソースとの表示一貫性を保つ
- カテゴリごとの番号リセットを実装