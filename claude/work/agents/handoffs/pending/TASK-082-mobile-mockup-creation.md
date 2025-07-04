# TASK-082: モバイルモックアップ作成

## タスク概要
改善されたモバイルレイアウトをPlaywrightを使用してモックアップ作成し、Before/After比較画像を生成する。ユーザーが提供したスクリーンショットとの比較を含む。

## 変更予定ファイル
- `/Users/nana/workspace/nook/mockups/mobile-before.png`
- `/Users/nana/workspace/nook/mockups/mobile-after.png`
- `/Users/nana/workspace/nook/mockups/mobile-comparison.html`

## 前提タスク
TASK-081 (モバイルUI改善)

## worktree名
worktrees/TASK-082-mobile-mockup-creation

## 作業内容

### 1. Playwright環境の準備
- ローカル開発サーバーの起動確認
- ブラウザの設定（モバイルビューポート）
- スクリーンショット撮影の設定

### 2. Before画像の作成
- 改善前の状態を再現（TASK-080実行前の状態）
- モバイルビューポート（375x667）での撮影
- ハンバーガーメニュー開閉状態の撮影

### 3. After画像の作成
- 改善後の状態を撮影（TASK-081完了後）
- 同じモバイルビューポートでの撮影
- 新しいBottomNavigationの撮影
- 改善されたハンバーガーメニューの撮影

### 4. 比較画像の作成
- Before/After並列表示のHTML作成
- 主要な改善点の視覚的ハイライト
- ユーザー提供のスクリーンショットとの比較

### 5. モックアップの詳細
- **解像度**: 375x667 (iPhone SE)
- **テーマ**: ライトモード/ダークモード両方
- **状態**: メニュー開閉、ナビゲーション操作
- **フォーカス**: BottomNavigation、MobileHeader、Sidebar

### 6. 撮影シナリオ
1. ホーム画面（デフォルト状態）
2. ハンバーガーメニュー開状態
3. BottomNavigation操作状態
4. 各ソース選択状態
5. ダークモード切り替え状態

### 7. 品質チェック
- [ ] 高解像度での撮影（2x）
- [ ] 異なるデバイスサイズでの確認
- [ ] ライト/ダークモード両方での撮影
- [ ] 画像の最適化とファイルサイズ管理

### 8. 完了条件
- Before/After比較画像が作成される
- 改善点が視覚的に明確に分かる
- ユーザーが提供したスクリーンショットとの比較が可能
- HTMLベースの比較ページが完成する

### 9. 成果物
- `mockups/mobile-before.png`: 改善前の状態
- `mockups/mobile-after.png`: 改善後の状態
- `mockups/mobile-comparison.html`: 比較ページ
- `mockups/README.md`: 改善点の説明