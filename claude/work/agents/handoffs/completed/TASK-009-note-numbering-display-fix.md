# TASK-009: Note表示ロジックの番号リセット修正

## タスク概要: Noteサービスの表示ロジックでmetadata.articleNumberを使用するように修正

## 変更予定ファイル: src/App.tsx

## 前提タスク: なし

## worktree名: worktrees/TASK-009-note-numbering-display-fix

## 作業内容:

1. **問題の確認**
   - parseNoteArticlesMarkdown関数（584-690行目）では正しくカテゴリごとに番号をリセット
   - しかし表示ロジック（1550-1564行目）では独自のグローバルカウンタを使用
   - 結果：#Anthropicの後の#OpenAIが「3」から開始してしまう

2. **修正内容**
   ```typescript
   // 現在のコード（1550-1564行目付近）
   else if (selectedSource === 'note') {
     let articleCount = 0; // グローバルカウンタ
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

   // 修正後のコード（Zennと同じパターン）
   else if (selectedSource === 'note') {
     return processedItems.map((item, index) => {
       const isArticle = item.isArticle;
       const articleIndex = isArticle && item.metadata?.articleNumber 
         ? item.metadata.articleNumber - 1 
         : undefined;
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

3. **動作確認**
   - Noteを選択
   - 複数のハッシュタグ（#Anthropic、#OpenAI等）が表示されることを確認
   - 各ハッシュタグの最初の記事が「1」から始まることを確認
   - ハッシュタグ内で番号が連続することを確認

4. **注意事項**
   - metadata.articleNumberは1から始まるため、表示時は`-1`して0ベースに変換
   - Zenn（1521-1533行目）の実装パターンを参考にする
   - テストコードは変更しない