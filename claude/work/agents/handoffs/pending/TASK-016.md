# TASK-016: useSourceDataフック強化

## タスク概要
useSourceDataフック内のエラーハンドリングを強化し、詳細なログ出力機能を追加してデバッグ効率を向上

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/hooks/useSourceData.ts`

## 前提タスク
TASK-012（型定義修正完了後）

## worktree名
worktrees/TASK-016-use-source-data-enhancement

## 作業内容

### 1. 現状分析
- useSourceData フックの現在の実装を詳細確認
- React Query の使用方法と設定を調査
- エラーハンドリングの現状と問題点を特定

### 2. エラーハンドリング強化
- try-catch ブロックでの例外処理追加
- 詳細なエラーログ出力機能
- エラータイプ別の処理ロジック実装

### 3. ログ機能拡充
- フック呼び出し時のパラメータログ
- API呼び出し前後の状態ログ
- エラー発生時のコンテキスト情報記録

### 4. 状態管理改善
- ローディング状態の詳細化
- エラー状態の構造化
- リトライ状態の追加

### 5. パフォーマンス最適化
- 不要な再レンダリングの防止
- メモ化の適切な活用
- 依存配列の最適化

### 6. 型安全性強化
- 戻り値の型定義精密化
- エラーオブジェクトの型定義
- ジェネリクスの活用

### 7. デバッグ支援機能
- 開発環境での詳細ログ
- React DevTools との連携情報
- パフォーマンス測定機能

### 8. 動作確認
- 正常なデータ取得での動作確認
- 各種エラーシナリオでの動作確認
- ログ出力内容の確認
- パフォーマンス影響の確認

### 品質管理
- [ ] ビルドが成功する
- [ ] 既存テストが成功する
- [ ] useSourceData の呼び出し元が正常動作する
- [ ] エラー時に詳細ログが出力される
- [ ] パフォーマンスが維持される

### 技術的注意事項
- 既存の使用箇所（App.tsx:38:47）との互換性保持
- React Query のベストプラクティスに従った実装
- React 18 の新機能との互換性確保
- TypeScript strict モードでの型安全性確保

### 実装方針
```typescript
export function useSourceData(
  selectedSource: string,
  selectedDate: string,
  enabled: boolean
) {
  // 詳細ログ出力
  useEffect(() => {
    console.log('useSourceData called with:', {
      selectedSource,
      selectedDate,
      enabled,
      timestamp: new Date().toISOString()
    });
  }, [selectedSource, selectedDate, enabled]);

  // React Query with enhanced error handling
  const queryResult = useQuery({
    queryKey: ['sourceData', selectedSource, selectedDate],
    queryFn: async () => {
      try {
        // API呼び出しログ
        console.log('API call started:', { selectedSource, selectedDate });
        
        const result = await apiCall();
        
        console.log('API call completed:', result);
        return result;
      } catch (error) {
        // 詳細エラーログ
        console.error('useSourceData API error:', {
          error,
          selectedSource,
          selectedDate,
          timestamp: new Date().toISOString()
        });
        throw error;
      }
    },
    enabled,
    onError: (error) => {
      // React Query エラーハンドリング
    }
  });

  return {
    ...queryResult,
    // 追加の状態やヘルパー関数
  };
}
```

### ログ出力設計
- 開発環境: 詳細ログ + パフォーマンス情報
- 本番環境: エラーログのみ
- 構造化ログ: JSON形式での出力
- タイムスタンプ: ISO 8601形式

### 期待される結果
- useSourceData関連のエラーの原因特定が容易になる
- API呼び出しの状況が詳細に把握できる
- パフォーマンス問題の早期発見
- 開発効率の大幅向上