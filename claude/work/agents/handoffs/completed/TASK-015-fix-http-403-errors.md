# TASK-015: HTTP 403エラーの修正

## タスク概要
HTTPクライアントにUser-Agentヘッダーが設定されていないため、多くのWebサイトで403 Forbiddenエラーが発生しています。

## 問題の詳細
- axios.com、kleinbottle.com、codeforces.com、washingtonpost.comなどで403エラー
- HTTPクライアント（nook/common/http_client.py）にデフォルトヘッダーが設定されていない

## 変更予定ファイル
- nook/common/http_client.py

## 前提タスク
- なし（独立したタスク）

## 実装内容

1. AsyncHTTPClientクラスのコンストラクタでデフォルトヘッダーを設定
2. User-Agentに一般的なブラウザの値を設定
3. その他の必要なヘッダー（Accept、Accept-Language等）も追加

## 実装例

```python
def __init__(self, config: BaseConfig = None):
    self.config = config or BaseConfig()
    self.default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    # ... 既存のコード
```

4. get()とpost()メソッドでデフォルトヘッダーをマージ

```python
async def get(self, url: str, headers: Optional[Dict[str, str]] = None, ...):
    # デフォルトヘッダーとユーザー指定のヘッダーをマージ
    merged_headers = {**self.default_headers, **(headers or {})}
    
    response = await self._client.get(
        url,
        headers=merged_headers,
        ...
    )
```

## テスト方法
1. 修正後、crawl_all.shを再実行
2. 403エラーが減少することを確認
3. 特にaxios.com、washingtonpost.comなどの主要サイトでのアクセスを確認

## 注意事項
- User-Agentは定期的に更新が必要
- 一部のサイトは追加の認証やCookie が必要な場合がある
- robots.txtの遵守も考慮すること