# TASK-066: useSourceData.tsをシンプルバージョンに復元（緊急）

## タスク概要
全サービスで番号が表示されない根本原因を特定しました。useSourceData.tsが美しいUI時代の50行から335行の複雑なコードに変化し、この過程でパーサーからの重要なデータ（metadata.articleNumber等）が失われています。美しいUI時代のシンプルなバージョンに復元します。

## 変更予定ファイル
- nook/frontend/src/hooks/useSourceData.ts

## 前提タスク
TASK-063、TASK-064、TASK-065（失敗したContainer Queriesアプローチ）

## worktree名
worktrees/TASK-066-restore-simple-usesourcedata

## 作業内容

### 1. 問題確認
現在のuseSourceData.ts（335行）と美しいUI時代（50行）の比較：

**美しいUI時代（コミット18b6230）:**
- シンプルなuseQuery
- 基本的なパーサー呼び出し
- データフローが明確
- 番号表示が正常に動作

**現在の問題:**
- 過度に複雑なパフォーマンス監視
- 詳細なエラーハンドリング
- メトリクス計算
- データフローが複雑化し、metadata.articleNumber等が失われている

### 2. useSourceData.ts復元

コミット18b6230の美しいUI時代のuseSourceData.tsに完全復元：

```typescript
import { useQuery } from 'react-query';
import { useMemo } from 'react';
import { format } from 'date-fns';
import { getContent } from '../api';
import { getParserForSource } from '../utils/parsers';
import { ContentItem } from '../types';

export function useSourceData(selectedSource: string, selectedDate: Date, enabled: boolean = true) {
  const { data, isLoading, isError, error, refetch } = useQuery(
    ['content', selectedSource, format(selectedDate, 'yyyy-MM-dd')],
    () => getContent(selectedSource, format(selectedDate, 'yyyy-MM-dd')),
    {
      retry: 2,
      enabled,
    }
  );

  const processedItems = useMemo((): ContentItem[] => {
    if (!data?.items || data.items.length === 0) {
      return [];
    }

    const parser = getParserForSource(selectedSource);
    
    if (parser && data.items[0]?.content) {
      try {
        // Hacker Newsの場合は特殊処理
        if (selectedSource === 'hacker-news') {
          return parser(data.items);
        }
        // 他のソースはMarkdownをパース
        return parser(data.items[0].content);
      } catch (error) {
        console.error(`${selectedSource} parsing error:`, error);
        return data.items;
      }
    }

    return data.items;
  }, [data, selectedSource]);

  return {
    data,
    processedItems,
    isLoading,
    isError,
    error,
    refetch,
  };
}
```

### 3. 動作確認

#### 番号表示確認
各サービスで番号が正しく表示されることを確認：

1. **Hacker News**: 「1」「2」「3」等の番号付き記事表示
2. **Tech News**: フィード別に「1」「2」等の番号表示
3. **Zenn**: 記事に番号表示
4. **Qiita**: 記事に番号表示
5. **Note**: 記事に番号表示
6. **Reddit**: 投稿に番号表示
7. **Business News**: 記事に番号表示

#### データフロー確認
```bash
# 開発コンソールでパーサー出力を確認
# 各パーサーがmetadata.articleNumberを正しく設定していることを確認
```

### 4. UI確認

確認項目：
- [ ] 全サービスで記事番号「1」「2」「3」等が表示される
- [ ] カードレイアウトが美しく表示される（shadow-md, p-6等）
- [ ] レスポンシブ動作が正常
- [ ] Image #1, #3のような美しいレイアウトが復元される

### 5. パフォーマンス影響確認

シンプル化による影響：
- [ ] データ取得速度が向上または同等
- [ ] メモリ使用量の削減
- [ ] コンソールエラー・警告の確認
- [ ] 基本機能（データ取得、エラーハンドリング）が正常

### 6. 品質確認
- [ ] ビルドが成功する（`npm run build`）
- [ ] 全テストが成功する（存在する場合）
- [ ] 基本的なエラーハンドリングが機能する
- [ ] レスポンシブ動作が正常

### 7. コミットメッセージ
```
TASK-066: useSourceData.tsをシンプルバージョンに復元（緊急）

実装内容：
- useSourceData.tsをコミット18b6230の50行シンプル版に復元
- 過度に複雑化されたパフォーマンス監視・メトリクス計算を削除
- パーサーからのデータフロー（metadata.articleNumber等）を確実に保持
- 全サービスの番号表示問題を根本解決

技術的な判断事項：
- 複雑さよりもデータフローの確実性を優先
- パーサーからContentCard.tsxまでのデータ受け渡しを単純化
- 335行の複雑なコードを50行のシンプルなコードに復元
- 番号表示に必要な基本機能のみに集中

プロンプト: 他のサービスも同様です。
hacker-newsやtech-newsに限った話ではありません
ultrathink
改めてコミットログからファイルを見比べてください
```

## 重要注意事項
- **緊急修復**: 全サービスの番号表示問題のため最優先
- **シンプル化**: 複雑なパフォーマンス監視よりもデータフローの確実性
- **確実な復元**: 動作確認済みのコミット18b6230のコードを使用
- **全サービス検証**: hacker-news, tech-news, zenn, qiita, note, reddit等すべて確認

## 期待される結果
- 全サービスで記事番号「1」「2」「3」等が正常に表示される
- Image #1, #3のような美しいカードレイアウトが復元される
- データフローが単純化され、保守しやすいコードになる
- パーサーからContentCard.tsxまでのデータが確実に伝達される