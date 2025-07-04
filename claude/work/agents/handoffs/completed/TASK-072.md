# TASK-072: モバイル版レイアウト修正 - 天気情報ヘッダー配置とオーバーレイサイドバー

## タスク概要
モバイル版のレイアウト問題を修正し、上部ヘッダーに天気情報を配置してサイドバーをオーバーレイ式に戻す。また、モバイル版で天気情報が正しく取得できることを確認する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/components/MobileHeader.tsx`（新規作成）
- `/Users/nana/workspace/nook/nook/frontend/src/components/weather/WeatherWidget.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/components/layout/Sidebar.tsx`

## 前提タスク
TASK-071（下部ナビゲーション削除）の完了

## worktree名
worktrees/TASK-072-mobile-weather-header

## 作業内容

### 1. MobileHeaderコンポーネント作成
- `/components/MobileHeader.tsx`を新規作成
- 天気情報（WeatherWidget）を含むヘッダーコンポーネント
- ハンバーガーメニューボタンを配置
- レスポンシブ対応（md:hidden）

### 2. App.tsxレイアウト修正
- サイドバーを`hidden md:flex`に戻す（オーバーレイ式）
- MobileHeaderを追加
- モバイル版でのメインコンテンツエリア調整
- オーバーレイサイドバーの状態管理を復活

### 3. 天気情報取得の確認・修正
- WeatherWidgetの取得ロジックを確認
- モバイル版での天気データ取得テスト
- APIエラーハンドリングの確認
- 必要に応じてWeatherWidgetの修正

### 4. オーバーレイサイドバーの復活
- `isMobileMenuOpen`状態管理を復活
- ハンバーガーメニューの動作確認
- オーバーレイ表示時の背景タップで閉じる機能

### 5. レスポンシブ対応の確認
- デスクトップ版の動作確認（既存レイアウト維持）
- モバイル版の動作確認（ヘッダー + オーバーレイ）
- 天気情報の両方での表示確認

## 品質チェック項目
- [ ] モバイル版でコンテンツが正常に閲覧できる
- [ ] モバイル版で天気情報が取得・表示される
- [ ] デスクトップ版の既存レイアウトが維持される
- [ ] オーバーレイサイドバーが正常に動作する
- [ ] レスポンシブ対応が正しく機能する

## 期待される結果
- モバイル版：上部ヘッダーに天気情報、コンテンツエリア最大化
- デスクトップ版：サイドバーに天気情報（既存維持）
- 天気情報がモバイル版で正しく取得・表示される
- オーバーレイサイドバーでナビゲーション機能が正常に動作する