# TASK-069: HTTPクライアント403エラー対策実装
## タスク概要: http_client.pyに403エラー対策機能を追加し、より多くのサイトからコンテンツを取得可能にする
## 変更予定ファイル: nook/common/http_client.py, nook/services/hacker_news/requirements.txt
## 前提タスク: なし
## worktree名: worktrees/TASK-069-http-403-fix
## 作業内容:

### 1. 背景
- 多数のサイト（NYTimes、Cell.com等）が403エラーを返している
- 現在のhttp_client.pyにはUser-Agent設定やBot検出回避機能がない
- テストにより、適切なヘッダー設定で約50%のサイトが正常にアクセス可能になることを確認済み

### 2. 実装内容

#### 2.1 http_client.pyの改善
1. **ブラウザヘッダーの追加**
   - デフォルトで最新のChromeブラウザヘッダーを設定
   - User-Agent、Accept、Sec-Fetch-*等の完全なヘッダーセット

2. **cloudscraperフォールバック機能**
   - 403エラー時に自動的にcloudscraperを使用
   - cloudscraperの結果をhttpx互換形式で返す

3. **既存機能との互換性維持**
   - 既存のget/postメソッドのインターフェースを変更しない
   - オプションでBot回避機能を無効化できるようにする

#### 2.2 依存関係の追加
- requirements.txtにcloudscraperを追加

### 3. 実装コード（参考）

```python
# http_client.pyの改善例
import cloudscraper

class AsyncHTTPClient:
    @staticmethod
    def get_browser_headers() -> Dict[str, str]:
        """最新のブラウザヘッダーを返す"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    
    async def get(self, url: str, headers: Optional[Dict[str, str]] = None, 
                  params: Optional[Dict[str, Any]] = None,
                  force_http1: bool = False,
                  use_browser_headers: bool = True,
                  **kwargs) -> httpx.Response:
        """改善されたGETメソッド"""
        
        # ブラウザヘッダーを使用
        if use_browser_headers and headers is None:
            headers = self.get_browser_headers()
        elif use_browser_headers and headers:
            # ユーザー指定のヘッダーとマージ
            browser_headers = self.get_browser_headers()
            browser_headers.update(headers)
            headers = browser_headers
            
        # 既存の処理...
        try:
            # 通常のhttpxリクエスト
            response = await client.get(url, headers=headers, params=params, **kwargs)
            response.raise_for_status()
            return response
            
        except httpx.HTTPStatusError as e:
            # 403エラーの場合、cloudscraperでリトライ
            if e.response.status_code == 403:
                logger.info(f"403 error for {url}, trying cloudscraper")
                return await self._cloudscraper_fallback(url, params, **kwargs)
            else:
                # 既存のエラー処理
                raise
    
    async def _cloudscraper_fallback(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> httpx.Response:
        """cloudscraperを使用したフォールバック処理"""
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )
            
            # 同期処理を非同期で実行
            response = await asyncio.to_thread(
                scraper.get,
                url,
                params=params,
                timeout=self.timeout.timeout
            )
            
            # httpx互換のレスポンスに変換
            return self._convert_to_httpx_response(response)
            
        except Exception as e:
            logger.error(f"Cloudscraper failed for {url}: {e}")
            # 元の403エラーを再発生
            raise APIException(
                f"HTTP 403 error (cloudscraper also failed)",
                status_code=403
            ) from e
```

### 4. テスト手順
1. 実装後、test_final_solution.pyのテストケースを実行
2. 成功率が50%以上になることを確認
3. 既存の機能が正常に動作することを確認

### 5. 注意事項
- cloudscraperは同期ライブラリなので、asyncio.to_threadで非同期化する
- 既存のエラーハンドリングと互換性を保つ
- パフォーマンスへの影響を最小限にする（403エラー時のみcloudscraper使用）