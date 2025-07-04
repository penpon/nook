# TASK-080: モバイルレイアウト基盤整備

## タスク概要
モバイルレイアウト最適化のための基盤整備を行う。Container Queriesクラスの修正、BottomNavigationの統合、MobileHeaderの活用を実施し、モバイルファーストアプローチを実現する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/components/layout/Sidebar.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/components/mobile/BottomNavigation.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/components/mobile/MobileHeader.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/components/weather/WeatherWidget.tsx`

## 前提タスク
なし

## worktree名
worktrees/TASK-080-mobile-layout-foundation

## 作業内容

### 1. Container Queriesクラスの修正
- `Sidebar.tsx`の`cq-xs:` `cq-md:`クラスを通常のレスポンシブクラスに変更
- Container Queriesプラグインが削除されているため、標準のTailwind CSSクラスを使用

### 2. BottomNavigationの統合
- `App.tsx`にBottomNavigationコンポーネントを追加
- モバイル（768px未満）でのみ表示するよう設定
- 現在のモバイルナビゲーションと連携

### 3. MobileHeaderの活用
- `App.tsx`にMobileHeaderコンポーネントを追加
- モバイル（768px未満）でのみ表示するよう設定
- ハンバーガーメニューボタンとの連携

### 4. **重要: UI重複問題の修正**
- **ハンバーガーメニューボタンとDashboardテキストの重複修正**
  - z-indexの調整（メニュー: z-30、ボタン: z-20）
  - App.tsx 95-103行のz-indexを修正
- **WeatherWidgetのダークモード対応**
  - WeatherWidget.tsx 24行・34行の`bg-white`を`bg-white dark:bg-gray-800`に変更
  - テキストカラーも`text-gray-500`を`text-gray-500 dark:text-gray-400`に変更

### 5. レスポンシブデザインの調整
- モバイルファーストアプローチの実装
- タッチサイズの最適化維持
- ダークモード対応の維持

### 6. TDD開発手順
- **Red段階**: 既存のテストが通ることを確認
- **Green段階**: 最小限の変更で機能を実装
- **Refactor段階**: コードの品質向上
- **Commit段階**: 各段階でコミット

### 7. 品質チェック
- [ ] ビルドが成功する
- [ ] 全テストが成功する
- [ ] `npx biome check --apply .`が通過する
- [ ] 新規追加コードの警告を解消
- [ ] テストコードを変更していない

### 8. 完了条件
- BottomNavigationがモバイルで正しく表示される
- MobileHeaderがモバイルで正しく表示される
- Container Queriesエラーが解消される
- **ハンバーガーメニューボタンとDashboardテキストの重複が解消される**
- **Weatherがモバイルで正しく表示される（ダークモード対応）**
- レスポンシブデザインが適切に機能する