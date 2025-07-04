# TASK-069-B: 403対策メソッドのDAT取得への統合

## タスク概要
既存の`_get_with_403_tolerance`メソッドの高度な戦略をDAT取得に適用し、403エラーを徹底的に回避する。

## 変更予定ファイル
- `/home/ubuntu/nook/nook/services/fivechan_explorer/fivechan_explorer.py`

## 前提タスク
- TASK-069-A（Cookie・ヘッダー強化が完了していること）

## worktree名
`worktrees/TASK-069-B-dat-403-tolerance`

## 作業内容

### 1. 新メソッド: _get_dat_with_403_tolerance の実装

`_get_thread_posts_from_dat`メソッドの後に新しいメソッドを追加：

```python
async def _get_dat_with_403_tolerance(self, dat_url: str, board_id: str) -> Optional[httpx.Response]:
    """
    DAT取得専用の403エラー耐性リクエスト
    複数のUser-Agent戦略とCookie組み合わせを試行
    """
    # 板サーバーの取得
    board_server = self._get_board_server(board_id) if board_id else 'medaka'
    
    # DAT取得用のUser-Agent戦略（より控えめなものから開始）
    user_agent_strategies = [
        # 戦略1: 古典的な専用ブラウザ風
        "Monazilla/1.00 (JaneStyle/4.10)",
        # 戦略2: 古いIE（互換性重視）
        "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)",
        # 戦略3: 古いモバイルブラウザ
        "Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25",
        # 戦略4: 現代的なブラウザ（完全版）
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # 戦略5: curl風（最小限）
        "curl/7.68.0"
    ]
    
    # Cookie戦略の組み合わせ
    cookie_strategies = [
        {'READJS': 'on'},
        {'READJS': 'on', 'PON': ''},
        {'READJS': '1'},
        {},  # Cookieなし
    ]
    
    attempt = 0
    for ua_idx, user_agent in enumerate(user_agent_strategies):
        for cookie_idx, cookies in enumerate(cookie_strategies):
            attempt += 1
            try:
                self.logger.info(f"DAT取得戦略 {attempt}: UA戦略{ua_idx+1} + Cookie戦略{cookie_idx+1}")
                
                # ヘッダー構築（戦略に応じて調整）
                headers = {
                    'User-Agent': user_agent,
                }
                
                # UA戦略に応じてヘッダーを調整
                if ua_idx >= 3:  # 現代的なブラウザの場合
                    headers.update({
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate',
                        'Referer': f'https://{board_server}.5ch.net/{board_id}/',
                        'Connection': 'keep-alive',
                    })
                else:  # 簡素なヘッダー
                    headers.update({
                        'Accept': 'text/plain',
                        'Connection': 'close'
                    })
                
                # アクセス間隔（戦略が進むほど長く）
                wait_time = 2 + (attempt * 1.5)
                if attempt > 1:
                    self.logger.info(f"待機時間: {wait_time}秒")
                    await asyncio.sleep(wait_time)
                
                # リクエスト実行
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        dat_url,
                        headers=headers,
                        cookies=cookies if cookies else None,
                        timeout=30.0,
                        follow_redirects=True
                    )
                
                self.logger.info(f"レスポンス: {response.status_code}")
                
                if response.status_code == 200:
                    # 有効なDATデータか確認
                    if response.content and len(response.content) > 100:
                        self.logger.info(f"成功: 戦略{attempt}で正常取得")
                        return response
                    else:
                        self.logger.warning(f"200だが内容が不十分: {len(response.content)}バイト")
                        
                elif response.status_code == 403:
                    # 詳細分析
                    if "cloudflare" in response.text.lower():
                        self.logger.warning(f"Cloudflare検出: 長時間待機（30秒）")
                        if attempt < 5:  # 最初の5回まで
                            await asyncio.sleep(30)
                    else:
                        self.logger.warning(f"通常の403エラー")
                        
            except Exception as e:
                self.logger.warning(f"戦略{attempt}エラー: {str(e)}")
                continue
    
    self.logger.error("全DAT取得戦略が失敗")
    return None
```

### 2. _get_thread_posts_from_datメソッドの改修

TASK-069-Aの実装に以下を追加：

```python
async def _get_thread_posts_from_dat(self, dat_url: str, board_id: str = None) -> List[Dict[str, Any]]:
    """dat形式でスレッドの投稿を取得（403エラー対策強化版）"""
    
    # まずTASK-069-Aの実装を試行
    # ... (既存のCookie/ヘッダー実装)
    
    # 403エラーの場合、高度な戦略を適用
    if response.status_code == 403:
        self.logger.warning("通常のDAT取得失敗、高度な403対策を適用")
        
        # 403対策メソッドを呼び出し
        tolerance_response = await self._get_dat_with_403_tolerance(dat_url, board_id)
        
        if tolerance_response and tolerance_response.status_code == 200:
            # 成功した場合、既存の解析処理を実行
            response = tolerance_response
            # ... (既存の成功処理に続く)
```

### 3. 代替DAT URLの試行

`_get_dat_with_403_tolerance`の最後に以下を追加：

```python
# 最終手段: 代替URLパターン
self.logger.info("代替DATエンドポイントを試行")

# URLパターンの変換
alternative_urls = []

# パターン1: 旧形式URL
if 'medaka' in dat_url:
    old_url = dat_url.replace('medaka.5ch.net', 'mevius.5ch.net')
    alternative_urls.append(old_url)

# パターン2: bbspink系の場合
if any(x in dat_url for x in ['mercury', 'venus']):
    pink_url = dat_url.replace('.5ch.net', '.bbspink.com')
    alternative_urls.append(pink_url)

for alt_url in alternative_urls:
    self.logger.info(f"代替URL試行: {alt_url}")
    # 簡素なリクエストで試行
    # ... (実装)
```

## テスト手順

1. TASK-069-Aの実装が完了していることを確認
2. 新しい403対策を実装
3. 実際のDAT取得でテスト
4. ログを詳細に確認し、どの戦略で成功したかを記録

## 注意事項

- アクセス間隔を適切に設定（サーバー負荷を避ける）
- ログを詳細に出力（成功戦略の分析用）
- 既存の成功処理は変更しない