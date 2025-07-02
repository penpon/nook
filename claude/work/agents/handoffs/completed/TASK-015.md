# TASK-015: Error Boundary実装

## タスク概要
React アプリケーション全体の安定性向上のため、Error Boundary を実装してコンポーネントエラーの適切なキャッチと表示機能を追加

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/components/ErrorBoundary.tsx`（新規作成）
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`（Error Boundary導入）

## 前提タスク
TASK-012（型定義修正完了後）

## worktree名
worktrees/TASK-015-error-boundary

## 作業内容

### 1. Error Boundary設計
- React Error Boundary の仕様調査
- エラー情報の収集とログ出力設計
- ユーザーフレンドリーなエラー表示UI設計

### 2. ErrorBoundary コンポーネント実装
- クラスコンポーネントでのError Boundary実装
- エラー状態の管理とリセット機能
- 詳細なエラー情報の記録

### 3. エラー表示UI実装
- ユーザー向けの分かりやすいエラーメッセージ
- エラー回復のためのアクション（リロード、リトライ等）
- 開発環境での詳細エラー情報表示

### 4. App.tsx への統合
- Error Boundary でメインアプリケーションをラップ
- 適切な階層での Error Boundary 配置
- パフォーマンスへの影響を最小化

### 5. エラーログ機能
- エラー発生時の詳細情報収集
- スタックトレースの記録
- ユーザー操作履歴の収集（可能な範囲で）

### 6. 回復機能実装
- エラー状態からの回復方法提供
- 部分的なリセット機能
- 安全な状態への復帰

### 7. 動作確認
- 意図的なエラー発生でのError Boundary動作確認
- エラー表示UIの確認
- エラー回復機能の確認

### 品質管理
- [ ] ビルドが成功する
- [ ] 既存テストが成功する
- [ ] Error Boundary が適切にエラーをキャッチする
- [ ] ユーザーフレンドリーなエラー画面が表示される
- [ ] エラー回復機能が正常動作する

### 技術的注意事項
- Error Boundary は非同期エラーをキャッチできない点を考慮
- React 18 の Concurrent Features との互換性確保
- 過度なエラーキャッチによるデバッグ困難化を避ける
- アクセシビリティを考慮したエラー表示

### 実装例（参考）
```typescript
interface Props {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; resetError: () => void }>;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // エラーログ記録
  }

  render() {
    if (this.state.hasError) {
      // エラーUI表示
    }
    return this.props.children;
  }
}
```

### Error Boundary 配置戦略
- App.tsx のトップレベルでの全体エラーキャッチ
- 重要なコンポーネント単位での部分的エラーキャッチ
- 段階的なエラー処理（詳細 → 簡潔）

### 期待される結果
- React コンポーネントエラーによるアプリケーションクラッシュの防止
- ユーザーにとって分かりやすいエラー情報の提供
- エラー発生時の適切な回復手段の提供
- 開発時のエラー原因特定の効率化