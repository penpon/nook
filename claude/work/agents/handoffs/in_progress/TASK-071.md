# TASK-071: 下部ナビゲーション削除とモバイル天気表示統一

## タスク概要
下部ナビゲーション（「ホーム」「トレンド」「検索」「ダッシュボード」「設定」）を削除し、モバイルでもPC版と同じレイアウトで天気情報を表示する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/components/BottomNavigation.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/components/layout/Sidebar.tsx`
- 関連するCSS/スタイルファイル

## 前提タスク
なし（独立して実行可能）

## worktree名
worktrees/TASK-071-remove-bottom-nav-unified-weather

## 作業内容

### 1. 下部ナビゲーションの削除
- App.tsxから`<BottomNavigation>`コンポーネントの呼び出しを削除
- BottomNavigationコンポーネントを無効化またはコメントアウト
- 下部ナビゲーション関連のstate管理ロジックを削除

### 2. モバイルレイアウトの統一
- `hidden md:flex`を`flex`に変更してモバイルでもサイドバーを常時表示
- モバイル用のオーバーレイサイドバーロジックを削除
- サイドバーの幅やレスポンシブ調整

### 3. レイアウト調整
- メインコンテンツエリアのマージン調整
- モバイル画面でのサイドバー幅の最適化
- 天気ウィジェットの表示確認

### 4. 品質チェック
- PC版とモバイル版で天気情報が同じように表示されることを確認
- ナビゲーション機能が正常に動作することを確認
- レスポンシブデザインの動作確認

## 期待される結果
- モバイルとPC版で統一されたレイアウト
- 天気情報がモバイルでも常時表示される
- 下部ナビゲーションが完全に削除される
- サイドバーナビゲーションのみでアプリケーションが動作する