# TASK-011: Hacker News表示修正

## タスク概要
Hacker Newsの表示における番号付けとコンテンツ表示の問題を修正する。ArXivと同様の問題が発生しており、統一的な表示品質の向上を図る。

## 変更予定ファイル
- `/nook/frontend/src/App.tsx` （番号付けロジックの修正）
- `/nook/api/content.py` （コンテンツ切り詰め制限の調整）

## 前提タスク
- TASK-010 (ArXiv表示修正) の完了を参考
- TASK-001 (Hacker Newsタイトル表示) の状況確認

## worktree名
worktrees/TASK-011-fix-hacker-news-display

## 作業内容

### 1. 番号付けロジックの修正（優先度：高）

**問題**: Hacker Newsが「他のソース」として扱われているため、カテゴリヘッダーにも番号が付与される可能性がある。

**修正箇所**: App.tsx (1642-1653行目)

**修正内容**:
ArXivと同様の専用番号付けロジックを追加：
```typescript
// Hacker Newsの場合も特別な番号付けロジック
else if (selectedSource === 'hacker news') {
  let articleCount = 0;
  return processedItems.map((item, index) => {
    const isArticle = item.isArticle;
    const articleIndex = isArticle ? articleCount++ : undefined;
    return (
      <ContentCard 
        key={index} 
        item={item} 
        darkMode={darkMode} 
        index={articleIndex} 
      />
    );
  });
}
```

### 2. コンテンツ表示制限の調整（優先度：中）

**問題**: content.py でテキストが500文字で切り詰められ、「...」が表示される。

**修正箇所**: `/nook/api/content.py` (84-90行目)

**修正内容**:
- 切り詰め制限を拡張（500文字 → 1000文字以上）
- または、フロントエンドでの表示制御に変更
- 省略表示の改善

### 3. 進行中タスクとの整合性確認（優先度：低）

**確認事項**:
- TASK-001 (Hacker Newsタイトル表示) の現在の状況
- 重複する修正内容がないかの確認
- 必要に応じてTASK-001との統合

## 検証方法

### 修正前の確認
1. Hacker Newsページでの番号表示の確認
2. 記事内容の切り詰め状況の確認

### 修正後の検証
1. カテゴリヘッダーに番号が付かないことの確認
2. 記事番号が1から順番に表示されることの確認
3. 記事内容が適切に表示されることの確認（切り詰めの改善）
4. ビルドエラーがないことの確認
5. 他のソース（ArXiv、5chan等）に影響がないことの確認

## 完了条件
- [ ] Hacker Newsの記事番号が1から正しく表示される
- [ ] カテゴリヘッダーに番号が表示されない
- [ ] 記事内容の表示が改善される（切り詰め制限の調整）
- [ ] ビルドが成功する
- [ ] 他のソースの表示に影響がない
- [ ] フロントエンドのリント警告を増加させない

## 注意事項
- TASK-010のArXiv修正と同様のアプローチを採用する
- 進行中のTASK-001との競合を避ける
- 変更は最小限に留め、他の機能に影響を与えない
- テストは必ずブラウザでの実際の表示確認を行う

## 技術的参考情報

### Hacker Newsのデータフロー
1. `/nook/services/hacker_news/` でデータ収集
2. `/nook/api/content.py` でAPIレスポンス生成
3. フロントエンドのApp.tsx でパース・表示

### 既存の番号付けロジック（参考）
- **ArXiv**: `selectedSource === 'paper'` で専用処理
- **5chan**: `selectedSource === '5chan'` で専用処理
- **Hacker News**: 現在は「他のソース」として通常処理

### 関連する既完了タスク
- TASK-008: Hacker News構造化JSONデータ処理
- TASK-009: Hacker Newsスコア降順ソート
- TASK-010: ArXiv表示修正（参考実装）