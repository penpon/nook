# TASK-070: 高度な403エラー回避機能の実装
## タスク概要: TASK-069で解決できない厳格なサイト（NYTimes等）に対する高度な回避機能を実装
## 変更予定ファイル: nook/common/advanced_http_client.py（新規）, nook/services/hacker_news/hacker_news.py
## 前提タスク: TASK-069
## worktree名: worktrees/TASK-070-advanced-403-bypass
## 作業内容:

### 1. 背景
- TASK-069実装後も、NYTimes、Cell.com、journals.aps.org等の約50%のサイトは403エラー
- これらのサイトは最新のCloudflare保護や高度なBot検出を使用
- ヘッドレスブラウザ（Playwright）を使用することで確実にアクセス可能

### 2. 実装内容

#### 2.1 advanced_http_client.pyの新規作成
1. **Playwrightベースのブラウザクライアント**
   - ヘッドレスChromiumを使用
   - JavaScriptレンダリング対応
   - Cloudflareチャレンジの自動解決

2. **段階的アプローチ**
   - Level 1: 通常のHTTPクライアント（TASK-069）
   - Level 2: cloudscraper（TASK-069）
   - Level 3: Playwright（本タスク）

3. **パフォーマンス最適化**
   - ブラウザインスタンスの再利用
   - 必要な場合のみ起動
   - タイムアウト設定

#### 2.2 実装コード（参考）

```python
# advanced_http_client.py
from playwright.async_api import async_playwright
import asyncio
from typing import Optional

class AdvancedHTTPClient:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        
    async def start(self):
        """ブラウザを起動"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
    
    async def get_with_browser(self, url: str, timeout: int = 30000) -> tuple[int, str]:
        """ブラウザを使用してコンテンツを取得"""
        if not self.browser:
            await self.start()
            
        page = await self.context.new_page()
        try:
            # ページに移動
            response = await page.goto(url, wait_until='networkidle', timeout=timeout)
            
            # JavaScriptが完全に実行されるまで待機
            await page.wait_for_load_state('networkidle')
            
            # Cloudflareチャレンジの待機（必要な場合）
            try:
                await page.wait_for_selector('body', timeout=5000)
            except:
                pass
            
            # コンテンツを取得
            content = await page.content()
            status = response.status if response else 200
            
            return status, content
            
        finally:
            await page.close()
    
    async def close(self):
        """ブラウザを閉じる"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
```

#### 2.3 hacker_news.pyの改善
- 厳格な403エラーサイトに対してadvanced_http_clientを使用
- 設定で有効/無効を切り替え可能

### 3. 段階的実装戦略

```python
async def fetch_with_fallback(url: str) -> str:
    """段階的フォールバック戦略"""
    
    # Level 1: 通常のHTTPクライアント（TASK-069実装）
    try:
        response = await http_client.get(url)
        if response.status_code == 200:
            return response.text
    except:
        pass
    
    # Level 2: すでにTASK-069でcloudscraperフォールバック実装済み
    
    # Level 3: Playwrightベースのブラウザ（最終手段）
    if url_requires_browser(url):  # NYTimes等の特定ドメイン
        status, content = await advanced_client.get_with_browser(url)
        if status == 200:
            return content
    
    raise Exception("All methods failed")
```

### 4. 依存関係
- playwright（すでにインストール済み）
- ブラウザドライバー（playwright install chromium）

### 5. 注意事項
- ブラウザ起動は重い処理なので、必要な場合のみ使用
- メモリ使用量に注意（ブラウザインスタンスの適切な管理）
- 並列処理時のリソース制限を考慮

### 6. 期待される結果
- 現在失敗している50%のサイト（NYTimes等）からもコンテンツ取得可能
- 全体的な成功率を90%以上に向上