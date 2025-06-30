# TASK-006: ニュースフィード投稿からフィード情報行を削除

## タスク概要
Zenn、Qiita、noteの投稿表示において、記事リストに含まれている「フィード: Zennの「Claude Code」のフィード」などのフィード情報行を削除する。タイトルで既に何のフィードか明らかなため、投稿内容にこの情報は不要。

## 変更予定ファイル
- nook/frontend/src/App.tsx

## 前提タスク
なし

## worktree名
worktrees/TASK-006-remove-feed-info-from-articles

## 作業内容

### 1. parseZennArticlesMarkdown関数の修正（App.tsx 286-402行目）
- 記事リストを生成する際に、`**フィード**:`で始まる行をスキップする処理を追加
- フィード情報の抽出は現状通り維持（カテゴリ名として使用するため）

### 2. parseQiitaArticlesMarkdown関数の修正（App.tsx 417-532行目）
- 同様に`**フィード**:`で始まる行を記事リストから除外

### 3. parseNoteArticlesMarkdown関数の修正（App.tsx 564-669行目）
- 同様に`**フィード**:`で始まる行を記事リストから除外

### 実装方針
各パース関数で、articlesListに行を追加する前に以下のチェックを追加：
```typescript
// フィード情報行はスキップ
if (line.trim().startsWith('**フィード**:')) {
  continue;
}
```

### テスト確認事項
- Zenn、Qiita、noteの各フィードで記事が正しく表示されること
- カテゴリ名（フィード名）は引き続き正しく表示されること
- フィード情報行が記事リストに含まれていないこと