# TASK-022: HTTP/1.1フォールバック機能の実装

## タスク概要: HTTP/2接続でStreamResetエラーが発生するサイトに対して、HTTP/1.1にフォールバックする機能を実装

## 変更予定ファイル:
- nook/common/http_client.py
- nook/services/hacker_news/hacker_news.py

## 前提タスク: なし（独立して実装可能）

## worktree名: worktrees/TASK-022-http-fallback

## 作業内容:

### 1. AsyncHTTPClientクラスの拡張
以下の機能を追加：
- `get()`メソッドに`force_http1`パラメータを追加
- StreamResetエラーをキャッチしてHTTP/1.1で自動リトライ
- HTTP/1.1専用のクライアントインスタンスを保持

```python
async def get(self, url: str, headers: Optional[Dict[str, str]] = None, 
              params: Optional[Dict[str, Any]] = None, 
              force_http1: bool = False, **kwargs) -> httpx.Response:
    # force_http1がTrueの場合、HTTP/1.1クライアントを使用
    # StreamResetエラーの場合、自動的にHTTP/1.1でリトライ
```

### 2. 問題のあるドメインリストの管理
`blocked_domains.json`に追加フィールド：
```json
{
  "http1_required_domains": [
    "htmlrev.com",
    "example-site.com"
  ]
}
```

### 3. HackerNewsRetrieverの修正
- ドメインチェックを追加
- 特定のドメインに対してはforce_http1=Trueを設定

### 4. エラーハンドリングの改善
- StreamResetエラーの詳細なログ
- フォールバック成功時の情報ログ

## 期待される効果:
- HTTP/2非対応サイトへのアクセス成功率向上
- 自動フォールバックによる透過的な処理
- 将来的な互換性問題への対応力向上