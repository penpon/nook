# TASK-069-A: DAT取得メソッドのCookie・ヘッダー強化

## タスク概要
5chan DAT取得時の403エラーを解決するため、Cookie設定と完全なヘッダーセットを実装する。

## 変更予定ファイル
- `/home/ubuntu/nook/nook/services/fivechan_explorer/fivechan_explorer.py`

## 前提タスク
なし（緊急対応）

## worktree名
`worktrees/TASK-069-A-dat-cookie-headers`

## 作業内容

### 1. _get_thread_posts_from_datメソッドの改修

現在の実装（604-676行）を以下のように改修：

```python
async def _get_thread_posts_from_dat(self, dat_url: str, board_id: str = None) -> List[Dict[str, Any]]:
    """
    dat形式でスレッドの投稿を取得（403エラー対策強化版）
    """
    # 板サーバーの取得（Referer設定用）
    if board_id:
        board_server = self._get_board_server(board_id)
    else:
        # URLから板サーバーを抽出
        import re
        match = re.match(r'https://([^/]+)\.5ch\.net/([^/]+)/', dat_url)
        if match:
            board_server = match.group(1)
            board_id = match.group(2)
        else:
            board_server = 'medaka'
            board_id = 'prog'
    
    # 完全なブラウザヘッダー
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': f'https://{board_server}.5ch.net/{board_id}/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    # 必須Cookie設定
    cookies = {
        'READJS': 'on',  # 最重要: JavaScriptの読み込み許可
        'PON': '',       # 板設定（空でも設定する）
    }
    
    try:
        self.logger.info(f"dat取得開始（Cookie対応版）: {dat_url}")
        self.logger.debug(f"使用Cookie: {cookies}")
        self.logger.debug(f"Referer: {headers['Referer']}")
        
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                dat_url, 
                headers=headers, 
                cookies=cookies,
                timeout=30.0,
                follow_redirects=True
            )
        
        self.logger.info(f"dat取得レスポンス: {response.status_code}")
        
        # 詳細なログ出力（デバッグ用）
        if response.status_code != 200:
            self.logger.debug(f"レスポンスヘッダー: {dict(response.headers)}")
            self.logger.debug(f"レスポンス内容（最初の500文字）: {response.text[:500]}")
        
        if response.status_code == 200:
            # 既存の成功処理（変更なし）
            # ... (既存のコード)
        elif response.status_code == 403:
            # 403エラーの詳細分析
            is_cloudflare = "cloudflare" in response.text.lower() or "just a moment" in response.text.lower()
            if is_cloudflare:
                self.logger.error("Cloudflare保護検出: より高度な対策が必要")
            else:
                self.logger.error(f"403エラー: Cookie/ヘッダー対策でも失敗")
            return []
        else:
            self.logger.error(f"dat取得HTTP error: {response.status_code}")
            return []
            
    except Exception as e:
        self.logger.error(f"dat取得エラー {dat_url}: {e}")
        import traceback
        self.logger.debug(f"エラー詳細: {traceback.format_exc()}")
    
    return []
```

### 2. _retrieve_ai_threadsメソッドの修正

board_idをDAT取得メソッドに渡すように修正（724行付近）：

```python
# 変更前
posts = await self._get_thread_posts_from_dat(dat_url)

# 変更後
posts = await self._get_thread_posts_from_dat(dat_url, board_id)
```

### 3. テスト手順

1. 実装完了後、以下のコマンドでテスト：
   ```bash
   python -m nook.services.run_services --service 5chan
   ```

2. ログを確認して403エラーが解消されたか確認

3. 成功した場合はTASK-069-Cで詳細な検証を実施

## 注意事項

- エンコーディング処理は既存のコードを維持
- ログ出力を詳細にして問題分析を容易にする
- Cookie設定が重要（特にREADJS='on'）