# TASK-010: 4chan表示ロジックの番号リセット修正

## タスク概要: 4chanサービスの表示ロジックでmetadata.articleNumberを使用するように修正

## 変更予定ファイル: src/App.tsx

## 前提タスク: TASK-009（コードの一貫性のため）

## worktree名: worktrees/TASK-010-4chan-numbering-display-fix

## 作業内容:

1. **問題の確認**
   - parseFourchanThreadsMarkdown関数（909-1006行目）では正しくカテゴリ（ボード）ごとに番号をリセット
   - しかし表示ロジック（1581-1595行目）では独自のグローバルカウンタを使用
   - 結果：/g/の後の/sci/が連続した番号から開始してしまう

2. **修正内容**
   ```typescript
   // 現在のコード（1581-1595行目付近）
   else if (selectedSource === '4chan') {
     let threadCount = 0; // グローバルカウンタ
     return processedItems.map((item, index) => {
       const isArticle = item.isArticle;
       const threadIndex = isArticle ? threadCount++ : undefined;
       return (
         <ContentCard 
           key={index} 
           item={item} 
           darkMode={darkMode} 
           index={threadIndex} 
         />
       );
     });
   }

   // 修正後のコード（metadata.articleNumberを使用）
   else if (selectedSource === '4chan') {
     return processedItems.map((item, index) => {
       const isArticle = item.isArticle;
       const threadIndex = isArticle && item.metadata?.articleNumber 
         ? item.metadata.articleNumber - 1 
         : undefined;
       return (
         <ContentCard 
           key={index} 
           item={item} 
           darkMode={darkMode} 
           index={threadIndex} 
         />
       );
     });
   }
   ```

3. **動作確認**
   - 4chを選択
   - 複数のボード（/g/、/sci/等）が表示されることを確認
   - 各ボードの最初のスレッドが「1」から始まることを確認
   - ボード内で番号が連続することを確認

4. **注意事項**
   - metadata.articleNumberは1から始まるため、表示時は`-1`して0ベースに変換
   - TASK-009のNoteと同じ実装パターンを使用
   - テストコードは変更しない