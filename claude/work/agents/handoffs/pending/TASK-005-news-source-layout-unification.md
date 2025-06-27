# TASK-005: ニュースソース別レイアウト統一

## タスク概要
各ニュースソース（Hacker News、Tech News、Business News等）の表示を統一し、それぞれに適した日本語タイトルと表示形式を実装する。現在のHacker News特化の条件分岐を全ソースに拡張する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/components/NewsHeader.tsx`（TASK-004で作成されたファイル）

## 前提タスク
TASK-004（独立タイトルコンポーネント実装が完了してから実施）

## worktree名
worktrees/TASK-005-news-source-layout-unification

## 作業内容

### 1. ニュースソース表示仕様の定義
```typescript
// 各ソースの表示情報を定義
const sourceDisplayInfo = {
  'hacker news': {
    title: 'Hacker News',
    subtitle: 'ハッカーニューストップ記事',
    dateFormat: 'yyyy-MM-dd'
  },
  'tech news': {
    title: 'Tech News',
    subtitle: '技術ニュース記事',
    dateFormat: 'yyyy年MM月dd日'
  },
  'business news': {
    title: 'Business News', 
    subtitle: 'ビジネスニュース記事',
    dateFormat: 'yyyy年MM月dd日'
  },
  // 他のソースも同様に定義
};
```

### 2. NewsHeaderコンポーネントの拡張
- 各ソース向けの表示ロジック実装
- 日本語サブタイトルの実装
- 統一されたデザインでの差別化

### 3. App.tsxの条件分岐改善
- 現在のHacker News専用条件分岐を全ソース対応に拡張
- 保守性の高いソース情報管理の実装

### 4. 統一デザイン要件
- すべてのソースで一貫したタイトル枠サイズ
- 日本語タイトル・サブタイトルの実装
- 各ソース特有の色・アイコンでの差別化検討

### 5. 完了条件
- [ ] 全ニュースソースで統一されたタイトル表示が実装される
- [ ] 各ソースに適した日本語タイトル・サブタイトルが表示される
- [ ] 日付フォーマットがソースごとに適切に設定される
- [ ] ビルドが成功する
- [ ] 全テストが成功する
- [ ] すべてのニュースソースで表示確認が完了する

## 設計考慮事項
- 新しいニュースソース追加時の拡張性
- 国際化（i18n）への将来対応
- 保守性の高いコード構造

## 注意事項
- 既存の機能に影響を与えない
- TypeScript型安全性を保持
- レスポンシブデザインを維持
- ダークモード対応を継続