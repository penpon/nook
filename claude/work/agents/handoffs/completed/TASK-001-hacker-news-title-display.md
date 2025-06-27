# TASK-001: HackerNewsの特別なタイトル表示を実装する

## タスク概要
HackerNewsの表示において、現在の汎用的なタイトルから理想的な形式に変更する。

現在の表示：
```
Hacker news Feed
June 27, 2025
```

理想的な表示：
```
hacker news - 2025-06-27
Hacker News トップ記事 (2025-06-27)
```

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
なし

## worktree名
worktrees/TASK-001-hacker-news-title-display

## 作業内容
1. App.tsxの177-182行目付近のタイトル表示部分を修正
2. `selectedSource === 'hacker news'`の条件分岐を追加
3. HackerNewsの場合：
   - 1行目：`hacker news - YYYY-MM-DD`形式
   - 2行目：`Hacker News トップ記事 (YYYY-MM-DD)`形式
4. 他のソースには影響を与えないよう実装
5. 実装後、フロントエンドをビルドして動作確認

## 実装の詳細
- 英語の日付形式と日本語の表示を併用
- タイトル表示のCSS/スタイリングも適切に調整
- レスポンシブデザインも考慮

## 実装結果
✅ **実装完了** (feature/TASK-001-hacker-news-title-display ブランチ)

### 実装内容
- React三項演算子による条件分岐を実装
- Fragment(`<>`)を使用した適切なJSX構造
- TailwindCSSクラスの適切な適用
- Reactベストプラクティスに準拠

### 品質確認
- ✅ フロントエンドビルド成功
- ✅ TypeScript型チェック通過
- ✅ Context7によるコードレビュー完了
- ✅ 条件付きレンダリングのベストプラクティス準拠

### 次の手順
手動でのマージが必要：
```bash
cd /Users/nana/workspace/nook
git merge feature/TASK-001-hacker-news-title-display --no-ff
git branch -d feature/TASK-001-hacker-news-title-display
```