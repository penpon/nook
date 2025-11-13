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