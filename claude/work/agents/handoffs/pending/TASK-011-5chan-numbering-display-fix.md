# TASK-011: 5chan表示ロジックの番号リセット修正

## タスク概要: 5chanサービスの表示ロジックでmetadata.articleNumberを使用するように修正

## 変更予定ファイル: src/App.tsx

## 前提タスク: TASK-009、TASK-010（コードの一貫性のため）

## worktree名: worktrees/TASK-011-5chan-numbering-display-fix

## 作業内容:

1. **問題の確認**
   - parseFivechanThreadsMarkdown関数（1008-1125行目）では正しくカテゴリ（板）ごとに番号をリセット
   - しかし表示ロジック（1597-1611行目）では独自のグローバルカウンタを使用
   - 結果：プログラム技術板の後のニュー速板が連続した番号から開始してしまう

2. **修正内容**
   ```typescript
   // 現在のコード（1597-1611行目付近）
   else if (selectedSource === '5chan') {
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
   else if (selectedSource === '5chan') {
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
   - 5chを選択
   - 複数の板（プログラム技術、ニュー速等）が表示されることを確認
   - 各板の最初のスレッドが「1」から始まることを確認
   - 板内で番号が連続することを確認

4. **注意事項**
   - metadata.articleNumberは1から始まるため、表示時は`-1`して0ベースに変換
   - TASK-009、TASK-010と同じ実装パターンを使用
   - テストコードは変更しない