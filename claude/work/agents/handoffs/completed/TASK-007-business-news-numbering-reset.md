# TASK-007: Business Newsの番号リセット実装

## タスク概要: Business Newsサービスでフィードごとに記事番号をリセットする機能を実装

## 変更予定ファイル: src/App.tsx

## 前提タスク: TASK-006（コードの一貫性のため）

## worktree名: worktrees/TASK-007-business-news-numbering-reset

## 作業内容:

1. **現状確認**
   - `parseBusinessNewsMarkdown`関数（273-301行目付近）で`globalArticleNumber`が使用されている
   - すべてのフィードをまたいで番号が連続している

2. **実装内容**
   - `globalArticleNumber`変数を削除
   - フィードループ内に`let articleNumber = 1;`を追加
   - TASK-006のTech Newsと同じパターンで実装

3. **変更例**
   ```typescript
   // 現在のコード
   let globalArticleNumber = 1;
   for (const [feedName, articles] of feedGroups) {
     // ...
     for (const article of articles) {
       contentItems.push({
         metadata: {
           articleNumber: globalArticleNumber++
         }
       });
     }
   }

   // 修正後のコード
   for (const [feedName, articles] of feedGroups) {
     let articleNumber = 1; // フィードごとにリセット
     // ...
     for (const article of articles) {
       contentItems.push({
         metadata: {
           articleNumber: articleNumber++
         }
       });
     }
   }
   ```

4. **動作確認**
   - Business Newsを選択
   - 複数のフィード（Bloomberg、Financial Timesなど）が表示されることを確認
   - 各フィードの最初の記事が「1」から始まることを確認
   - フィード内で番号が連続することを確認

5. **注意事項**
   - Tech News（TASK-006）と同じ実装パターンを使用すること
   - ContentCardコンポーネントは変更不要
   - 表示ロジック（1489-1518行目）も変更不要
   - テストコードは変更しない