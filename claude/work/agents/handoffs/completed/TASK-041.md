# TASK-041: 全ニュースソース カテゴリヘッダーごとの番号リセット実装

## タスク概要
すべてのニュースソースで、カテゴリヘッダーごとに記事番号を1からリセットする統一仕様を実装する

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`（既存のparseXxxMarkdown関数すべて）

## 前提タスク
- 各ニュースソースの既存タスクの実装と合わせて適用

## worktree名
（各ニュースソースのタスクのworktreeで実装）

## 作業内容

### 1. 統一仕様の定義

#### 現在の番号付け（全体通し番号）
```
Tech News
├─ Tech Blogs
│  ├─ 1. 記事A
│  └─ 2. 記事B
└─ Hatena
   ├─ 3. 記事C  // 通し番号が続く
   └─ 4. 記事D

Reddit Posts
├─ r/StableDiffusion
│  ├─ 5. 投稿E
│  └─ 6. 投稿F
└─ r/artificial
   ├─ 7. 投稿G
   └─ 8. 投稿H
```

#### 新しい番号付け（カテゴリごとにリセット）
```
Tech News
├─ Tech Blogs
│  ├─ 1. 記事A
│  └─ 2. 記事B
└─ Hatena
   ├─ 1. 記事C  // 番号が1にリセット
   └─ 2. 記事D

Reddit Posts
├─ r/StableDiffusion
│  ├─ 1. 投稿E
│  └─ 2. 投稿F
└─ r/artificial
   ├─ 1. 投稿G  // 番号が1にリセット
   └─ 2. 投稿H
```

### 2. 実装パターン

すべてのparseXxxMarkdown関数で以下のパターンを適用：

```typescript
function parseXxxMarkdown(markdown: string): ContentItem[] {
  const items: ContentItem[] = [];
  // ... 

  // カテゴリごとのループ
  for (const [category, articles] of categoryGroups) {
    // カテゴリヘッダーを追加
    items.push({
      title: category,
      isCategoryHeader: true,
      // ...
    });
    
    // カテゴリごとに番号をリセット
    let articleNumber = 1;
    
    // 記事を追加
    for (const article of articles) {
      items.push({
        title: article.title,
        metadata: {
          articleNumber: articleNumber++  // カテゴリ内での番号
        },
        // ...
      });
    }
  }
  
  return items;
}
```

### 3. 適用対象のニュースソース

以下のすべてのニュースソースで番号リセットを実装：

1. **Tech News** (TASK-022)
   - カテゴリ: Tech Blogs, Hatena等

2. **Business News** (TASK-024)
   - カテゴリ: 経済ニュース、ビジネス戦略等

3. **Zenn Articles** (TASK-036)
   - カテゴリ: Claude Code, Cursor等（フィード名）

4. **Qiita Articles** (TASK-037)
   - カテゴリ: ChatGPT, Vue.js等（タグ名）

5. **note Articles** (TASK-038)
   - カテゴリ: #ClaudeCode, #スタートアップ等（ハッシュタグ）

6. **Reddit Posts** (TASK-035)
   - カテゴリ: r/StableDiffusion, r/artificial等（サブレディット）

7. **4chan Threads** (TASK-029)
   - カテゴリ: /g/, /tech/等（ボード）

8. **5ch Threads** (TASK-030)
   - カテゴリ: プログラム技術板、ニュー速VIP等（板）

9. **Hacker News** (TASK-039)
   - カテゴリ: Hacker News（単一カテゴリ）

10. **Academic Papers** (TASK-040)
    - カテゴリ: ArXiv（単一カテゴリ）

### 4. UI表示の統一

- すべてのContentCardコンポーネントで、`metadata.articleNumber`を使用して番号を表示
- カテゴリヘッダーごとに番号がリセットされることを視覚的に明確化
- ツリー構造の表示（├─、└─）も考慮

### 5. 期待される効果

- **視認性向上**: カテゴリ内での記事位置が明確
- **ナビゲーション改善**: 各カテゴリ内での記事数が一目瞭然
- **統一性**: すべてのニュースソースで一貫した番号付け
- **ユーザビリティ**: 記事参照時の混乱を防止

### 6. テスト確認項目

- 各カテゴリの最初の記事が必ず「1」から開始
- カテゴリが変わると番号が「1」にリセット
- 単一カテゴリのソース（Hacker News、Academic Papers）も正常動作
- 既存の機能（ソート、フィルタ等）に影響なし

### 7. 注意事項

- バックエンドのデータ構造は変更しない
- フロントエンドのパース処理のみで実現
- 既存のメタデータ構造を維持しつつ拡張
- パフォーマンスへの影響を最小限に