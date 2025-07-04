# TASK-071: モバイルハンバーガーメニューの修正と不要UI要素の削除

## タスク概要
モバイル版でハンバーガーメニューが機能しない問題の修正と、不要なUI要素（虫眼鏡、縦3つの黒い点）の削除、天気情報のモバイル版での無効化を行う。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/hooks/useMobileMenu.ts`
- `/Users/nana/workspace/nook/nook/frontend/src/components/mobile/MobileHeader.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
なし

## worktree名
worktrees/TASK-071-mobile-menu-fix

## 作業内容

### 1. useMobileMenuフックの修正
- 現在の問題：`toggleMobileMenu`と`closeMobileMenu`関数が存在しない
- App.tsxで呼び出されているが、フックが提供していない
- 追加する関数：
  - `toggleMobileMenu`: メニューの開閉を切り替え
  - `closeMobileMenu`: メニューを閉じる
  - `openMobileMenu`: メニューを開く

### 2. MobileHeaderの修正
- 不要なUI要素の削除：
  - 虫眼鏡（Search）アイコン：`showSearchButton`をデフォルトで`false`に変更
  - 縦3つの黒い点（MoreVertical）アイコン：条件付きで非表示
- 天気情報の制御：
  - `showWeather`プロパティの適切な制御

### 3. App.tsxの修正
- 天気情報の無効化：`showWeather={false}`に変更
- 不要なアイコンの非表示化：`showSearchButton={false}`を追加

### 4. 動作確認
- mcp-playwrightを使用してモバイル版での動作確認
- ハンバーガーメニューの開閉テスト
- 不要なUI要素が削除されていることを確認
- 天気情報がモバイルで表示されないことを確認

## 品質チェック項目
- [ ] ビルドが成功する
- [ ] 全テストが成功する（該当する場合）
- [ ] 自動品質チェック（Biome）が通過する
- [ ] ハンバーガーメニューが正常に動作する
- [ ] 不要なUI要素が削除されている
- [ ] 天気情報がモバイルで非表示になっている

## 完了条件
- ハンバーガーメニューがモバイル版で正常に機能する
- 虫眼鏡アイコンと縦3つの黒い点が表示されない
- 天気情報がモバイル版で非表示になっている
- mcp-playwrightでモバイル版での動作が確認できる