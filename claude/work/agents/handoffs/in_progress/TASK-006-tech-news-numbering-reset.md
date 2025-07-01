# TASK-006: Tech Newsの番号リセット実装

## タスク概要: Tech Newsサービスでフィードごとに記事番号をリセットする機能を実装

## 変更予定ファイル: src/App.tsx

## 前提タスク: なし

## worktree名: worktrees/TASK-006-tech-news-numbering-reset

## 作業内容:

1. **現状確認**
   - `parseTechNewsMarkdown`関数（163-189行目付近）で`globalArticleNumber`が使用されている
   - すべてのフィードをまたいで番号が連続している

2. **実装内容**
   - `globalArticleNumber`変数を削除
   - フィードループ内に`let articleNumber = 1;`を追加
   - Zennサービスの実装パターンを参考にする（304-421行目）

3. **変更例**
   ```typescript
   // 現在のコード
   let globalArticleNumber = 1;
   for (const [feedName, articles] of feedGroups) {
     // ...
     articles.forEach((article) => {
       contentItems.push({
         metadata: {
           articleNumber: globalArticleNumber++
         }
       });
     });
   }

   // 修正後のコード
   for (const [feedName, articles] of feedGroups) {
     let articleNumber = 1; // フィードごとにリセット
     // ...
     articles.forEach((article) => {
       contentItems.push({
         metadata: {
           articleNumber: articleNumber++
         }
       });
     });
   }
   ```

4. **動作確認**
   - Tech Newsを選択
   - 複数のフィード（TechCrunch、The Vergeなど）が表示されることを確認
   - 各フィードの最初の記事が「1」から始まることを確認
   - フィード内で番号が連続することを確認

5. **注意事項**
   - ContentCardコンポーネントは変更不要
   - 表示ロジック（1489-1518行目）も変更不要
   - テストコードは変更しない