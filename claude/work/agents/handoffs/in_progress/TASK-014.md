# TASK-014: React Query設定強化

## タスク概要
React Query のエラーハンドリングとリトライロジックを強化し、フロントエンドの安定性を向上

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/QueryClient.ts`（新規作成の可能性）
- `/Users/nana/workspace/nook/nook/frontend/src/main.tsx`（QueryClient設定適用）

## 前提タスク
TASK-012（型定義修正完了後）

## worktree名
worktrees/TASK-014-react-query-config

## 作業内容

### 1. 現状分析
- 現在のReact Query設定を確認（main.tsx またはApp.tsx）
- QueryClient の設定状況を調査
- useSourceData フックでのReact Query使用方法を確認

### 2. QueryClient設定ファイル作成
- カスタムQueryClient設定ファイルの作成
- デフォルト設定のオーバーライド
- 開発環境と本番環境での設定分岐

### 3. エラーハンドリング設定
- グローバルエラーハンドリングの実装
- エラータイプ別の処理ロジック
- エラー状態の管理とユーザー通知

### 4. リトライロジック設定
- ネットワークエラー時の自動リトライ
- リトライ回数と間隔の最適化
- サーバーエラー時のリトライ戦略

### 5. キャッシュ戦略最適化
- データの有効期限設定
- バックグラウンド更新の設定
- ステイル時間の調整

### 6. パフォーマンス最適化
- 同時リクエスト数の制限
- 重複リクエストの防止
- メモリ使用量の最適化

### 7. 開発体験向上
- React Query Devtools の設定（開発環境のみ）
- デバッグ情報の充実
- ログ出力の最適化

### 8. 動作確認
- 正常なデータ取得での動作確認
- エラー時の自動リトライ動作確認
- キャッシュ機能の動作確認
- パフォーマンスの検証

### 品質管理
- [ ] ビルドが成功する
- [ ] 既存テストが成功する
- [ ] useSourceData フックが正常動作する
- [ ] エラー時のリトライが適切に実行される
- [ ] React Query Devtools が開発環境で利用可能

### 技術的注意事項
- 既存のuseQuery呼び出しとの互換性を保持
- React 18のConcurrent Features との互換性確保
- TypeScript型安全性の維持
- バンドルサイズへの影響を最小化

### 設定例
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // カスタムリトライロジック
      },
      staleTime: 5 * 60 * 1000, // 5分
      cacheTime: 10 * 60 * 1000, // 10分
      refetchOnWindowFocus: false,
      onError: (error) => {
        // グローバルエラーハンドリング
      }
    }
  }
});
```

### 期待される結果
- React Query関連のエラーが大幅に減少
- データ取得の安定性向上
- ユーザー体験の向上（ローディング状態の改善）
- 開発時のデバッグ効率向上