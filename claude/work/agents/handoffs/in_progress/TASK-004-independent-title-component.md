# TASK-004: 独立タイトルコンポーネント実装

## タスク概要
現在の小さなタイトル表示（text-2xl + text-sm）を、大きな独立したタイトル枠に変更。Tech News/Business Newsのレイアウトを参考に、視覚的インパクトのある専用タイトルコンポーネントを実装する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/components/NewsHeader.tsx`（新規作成）
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
TASK-003（データ修正が完了してから実施）

## worktree名
worktrees/TASK-004-independent-title-component

## 作業内容

### 1. NewsHeaderコンポーネント設計・実装
- 独立したヘッダーコンポーネントの新規作成
- 大きなタイトル表示（text-3xl以上）
- 背景色・境界線・パディングによる独立した枠の実装
- レスポンシブデザイン対応

### 2. コンポーネント仕様
```typescript
interface NewsHeaderProps {
  selectedSource: string;
  selectedDate: Date;
  darkMode: boolean;
}
```

### 3. デザイン要件
- 独立した視覚的な枠組み（背景色、境界線、シャドウ）
- 大きなタイトルサイズ（現在のtext-2xlより大きく）
- ダークモード対応
- モバイル・デスクトップ両対応

### 4. App.tsx統合
- 現在のタイトル部分（177-187行目）をNewsHeaderコンポーネントに置き換え
- 適切なpropsの受け渡し
- 既存のレイアウトとの調和

### 5. 完了条件
- [ ] NewsHeader.tsxが正常に作成される
- [ ] App.tsxにNewsHeaderが統合される
- [ ] ビルドが成功する
- [ ] すべてのニュースソースで大きなタイトル表示が確認される
- [ ] ダークモード切り替えが正常に動作する
- [ ] レスポンシブ表示が正常に動作する

## 注意事項
- 既存のContentCardコンポーネントとの互換性を維持
- パフォーマンスへの影響を最小化
- アクセシビリティを考慮した実装