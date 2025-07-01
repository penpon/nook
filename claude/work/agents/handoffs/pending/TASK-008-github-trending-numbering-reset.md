# TASK-008: GitHub Trendingの番号リセット実装

## タスク概要: GitHub Trendingサービスで言語ごとにリポジトリ番号をリセットする機能を実装

## 変更予定ファイル: src/App.tsx

## 前提タスク: TASK-006、TASK-007（コードの一貫性のため）

## worktree名: worktrees/TASK-008-github-trending-numbering-reset

## 作業内容:

1. **現状確認**
   - 表示ロジック（1472-1487行目）で単一の`repositoryCount`カウンターを使用
   - すべての言語をまたいでリポジトリ番号が連続している
   - 言語ヘッダー（`isLanguageHeader: true`）とリポジトリ（`isRepository: true`）の区別がある

2. **実装方針**
   - 言語ヘッダーを検出するたびにカウンターをリセット
   - 各言語内でリポジトリ番号を1から開始

3. **実装内容**
   ```typescript
   // 現在のコード（1472-1487行目付近）
   if (selectedSource === 'github') {
     let repositoryCount = 0;
     return processedItems.map((item, index) => {
       const isRepository = item.isRepository;
       const repositoryIndex = isRepository ? repositoryCount++ : undefined;
       return (
         <ContentCard 
           key={index} 
           item={item} 
           darkMode={darkMode} 
           index={repositoryIndex} 
         />
       );
     });
   }

   // 修正後のコード
   if (selectedSource === 'github') {
     let repositoryCount = 0;
     return processedItems.map((item, index) => {
       // 言語ヘッダーを検出したらカウンターをリセット
       if (item.isLanguageHeader) {
         repositoryCount = 0;
       }
       
       const isRepository = item.isRepository;
       const repositoryIndex = isRepository ? repositoryCount++ : undefined;
       return (
         <ContentCard 
           key={index} 
           item={item} 
           darkMode={darkMode} 
           index={repositoryIndex} 
         />
       );
     });
   }
   ```

4. **動作確認**
   - GitHub Trendingを選択
   - 複数の言語（Python、Go、Rustなど）が表示されることを確認
   - 各言語の最初のリポジトリが「1」から始まることを確認
   - 言語内でリポジトリ番号が連続することを確認
   - 言語ヘッダーには番号が付かないことを確認

5. **エッジケース確認**
   - 単一言語のみの場合も番号が1から開始
   - リポジトリがない言語がある場合も正常動作

6. **注意事項**
   - `parseGitHubTrendingMarkdown`関数は変更不要
   - ContentCardコンポーネントは変更不要（`index + 1`で表示）
   - テストコードは変更しない