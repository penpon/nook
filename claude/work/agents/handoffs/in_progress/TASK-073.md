# TASK-073: APIネットワークエラーテスト失敗の修正

## タスク概要
テスト環境でのAPIネットワークエラーを修正し、/api/weather と /api/content/hacker-news のテスト失敗を解決する。テスト環境でのAPIリクエストモック化と必要なセットアップの改善を実施。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/test/setup.ts`
- `/Users/nana/workspace/nook/nook/frontend/src/test/idealUIState.test.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/test/mocks/handlers.ts`（新規作成）
- `/Users/nana/workspace/nook/nook/frontend/src/test/mocks/mockData.ts`（新規作成）

## 前提タスク
なし（独立して実行可能）

## worktree名
worktrees/TASK-073-fix-api-test-failures

## 作業内容

### 1. APIモックの実装
**新規作成**: `/src/test/mocks/mockData.ts`
- weather APIのモックデータ: `{"temperature":24.48,"icon":"01n"}`
- hacker-news APIのモックデータ: 15記事のデータ（実際のAPIレスポンスを基に）

**新規作成**: `/src/test/mocks/handlers.ts`
- MSW（Mock Service Worker）またはaxiosのモック設定
- GET `/api/weather` のモックレスポンス
- GET `/api/content/hacker-news` のモックレスポンス

### 2. テストセットアップの改善
**修正**: `/src/test/setup.ts`
- `window.scrollTo`のモック実装
- `fetch`/`axios`のモック設定
- テスト環境でのURL操作制限の回避
- APIモックの初期化

### 3. テスト環境の最適化
**修正**: `/src/test/idealUIState.test.tsx`
- テスト専用のQueryClientの設定
- APIリクエストの待機処理改善
- エラーハンドリングテストの追加

### 4. JSDOM環境の拡張
**追加**: テスト環境でのブラウザAPI模擬
- `window.scrollTo`の実装
- URL操作（`window.history.replaceState`）の制限回避
- 必要なDOM APIの補完

### 5. テスト戦略の見直し
- 統合テストとユニットテストの分離考慮
- APIリクエストを伴わないコンポーネントテストの確認
- テストの安定性と信頼性の向上

## 技術的詳細

### APIモックの実装方針
```typescript
// Weather APIモック
const mockWeatherResponse = {
  temperature: 24.48,
  icon: "01n"
};

// Hacker News APIモック
const mockHackerNewsResponse = {
  items: [
    // 15記事のデータ（実際のAPIレスポンスより）
  ]
};
```

### テストセットアップの改善
```typescript
// window.scrollToのモック
Object.defineProperty(window, 'scrollTo', {
  value: jest.fn(),
  writable: true
});

// URL操作の制限回避
delete window.location;
window.location = { href: 'http://localhost:3000/' };
```

## 品質チェック項目
- [ ] `/api/weather` テストが成功する
- [ ] `/api/content/hacker-news` テストが成功する
- [ ] 理想UI状態テストが安定して通過する
- [ ] テストカバレッジが維持される
- [ ] 実際のAPIとのモックデータの整合性確認
- [ ] テスト実行時間の改善確認

## 期待される結果
- テスト環境でのAPIネットワークエラーが解決される
- 理想UI状態テストが安定して成功する
- テストの実行速度と信頼性が向上する
- 実際のAPIレスポンスと一致するモックデータの実装
- テスト環境の堅牢性が改善される

## 注意事項
- テストデータに依存した実装は避ける（CLAUDE.md 3.2参照）
- テストコードの変更は最小限に抑える
- 実際のAPIの動作を正確に模擬する
- テスト環境固有の問題のみを対象とする