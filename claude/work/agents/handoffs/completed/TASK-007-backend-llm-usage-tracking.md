# TASK-007: LLM API使用量追跡機能の実装

## Worktree情報
- Worktree: `worktrees/TASK-007-backend`
- Branch: `feature/llm-api-usage-tracking`

## タスク概要
GPT-4.1-nano APIの使用量とコストを追跡するシステムを実装する。

## 実装要件

### 1. GPTClientクラスの拡張
- `nook/common/gpt_client.py` を修正
- トークン数カウント機能を追加
- 料金計算機能を追加
- ログ出力機能を追加

### 2. トークン数の計算
- tiktoken ライブラリを使用（`uv pip install tiktoken`）
- gpt-4.1-nano用のエンコーディングを使用
- 入力トークン数と出力トークン数を正確に計算

### 3. 料金計算
```python
# 料金体系（USD per 1M tokens）
PRICING = {
    "input": 0.20,
    "cached_input": 0.05,  # 今回は通常入力として計算
    "output": 0.80
}
```

### 4. ログ出力
- ログファイル: `data/api_usage/llm_usage_log.jsonl`
- JSON Lines形式で1行1レコード
- 各レコードに含める情報：
  - timestamp（ISO 8601形式）
  - service（呼び出し元サービス名）
  - model（使用モデル名）
  - input_tokens（入力トークン数）
  - output_tokens（出力トークン数）
  - cost_usd（今回の呼び出しコスト）
  - cumulative_cost_usd（累計コスト）

### 5. 実装詳細

#### generate_content メソッドの修正
1. 呼び出し元サービスを特定（スタックトレースから取得）
2. プロンプトのトークン数を計算
3. API呼び出し実行
4. レスポンスのトークン数を計算
5. 料金を計算
6. ログに記録

#### ユーティリティメソッドの追加
- `_count_tokens(text: str) -> int`: トークン数計算
- `_calculate_cost(input_tokens: int, output_tokens: int) -> float`: 料金計算
- `_log_usage(service: str, input_tokens: int, output_tokens: int, cost: float)`: ログ記録

### 6. エラーハンドリング
- ログ記録の失敗がAPI呼び出しを妨げないようにする
- ログディレクトリが存在しない場合は自動作成

### 7. テスト
- 手動でいくつかのサービスを実行してログが正しく記録されることを確認
- トークン数と料金計算の妥当性を検証

## 完了条件
- [ ] GPTClientクラスにトークン追跡機能を実装
- [ ] ログファイルが正しく生成される
- [ ] 各サービスからの呼び出しでログが記録される
- [ ] エラーハンドリングが適切に実装されている