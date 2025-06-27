# TASK-002: HackerNewsタイトル表示の詳細実装

## タスク概要
HackerNewsの表示において、汎用的なタイトル表示から理想的な専用フォーマットに変更する。

**現在の表示：**
```
Hacker news Feed
June 27, 2025
```

**理想的な表示：**
```
hacker news - 2025-06-27
Hacker News トップ記事 (2025-06-27)
```

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`（177-182行目）

## 前提タスク
- TASK-001（既存タスクの完了を確認後実行）

## worktree名
worktrees/TASK-002-hacker-news-title-display-detailed

## 作業内容

### 1. 実装詳細
App.tsx の177-182行目を以下のように修正：

**現在のコード：**
```tsx
<h1 className="text-2xl font-bold text-gray-900 dark:text-white">
  {selectedSource.charAt(0).toUpperCase() + selectedSource.slice(1)} Feed
</h1>
<p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
  {format(selectedDate, 'MMMM d, yyyy')}
</p>
```

**修正後：**
```tsx
<h1 className="text-2xl font-bold text-gray-900 dark:text-white">
  {selectedSource === 'hacker news' 
    ? `hacker news - ${format(selectedDate, 'yyyy-MM-dd')}`
    : `${selectedSource.charAt(0).toUpperCase() + selectedSource.slice(1)} Feed`}
</h1>
<p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
  {selectedSource === 'hacker news'
    ? `Hacker News トップ記事 (${format(selectedDate, 'yyyy-MM-dd')})`
    : format(selectedDate, 'MMMM d, yyyy')}
</p>
```

### 2. 実装手順
1. **developブランチでの準備作業**
   - TASK-001のcompletedへの移動を確認
   - 本タスクをin_progressに移動してコミット

2. **worktree作成と移動**
   ```bash
   git worktree add -b feature/TASK-002-hacker-news-title-display-detailed worktrees/TASK-002-hacker-news-title-display-detailed
   cd worktrees/TASK-002-hacker-news-title-display-detailed
   pwd && git branch --show-current
   ```

3. **実装**
   - App.tsx の177-182行目を上記の通り修正
   - 条件分岐で`selectedSource === 'hacker news'`を正確に判定
   - 日付フォーマットを`yyyy-MM-dd`に変更（HackerNewsのみ）

4. **品質保証**
   - フロントエンドビルド: `npm run build`
   - 他ソースの表示が変更されていないことを確認
   - HackerNewsソースで理想の表示になることを確認

5. **context7レビュー**
   - 実装の技術的妥当性確認
   - React/TypeScriptベストプラクティス確認

6. **完了処理**
   - developブランチにマージ
   - タスクファイルをcompletedに移動
   - worktree削除

### 3. 技術的注意事項
- 既存の`date-fns`ライブラリを活用
- 他ソースに一切影響を与えない実装
- ダークモード対応も含めた完全な実装
- TypeScriptの型安全性を維持

### 4. 検証項目
- [ ] HackerNewsで理想の表示になる
- [ ] 他ソース（paper, github等）の表示が変更されない
- [ ] 日付選択時の動作が正常
- [ ] ダークモード切り替えで問題なし
- [ ] ビルドエラーなし
- [ ] TypeScript警告なし

## 期待される成果物
- 条件分岐による適切なタイトル表示実装
- HackerNews専用の日英併記フォーマット
- 他ソースへの影響ゼロの実装