# TASK-068: 5chan Explorer 403エラー修正

## タスク概要
5chan Explorerでdat形式のスレッド取得時に403エラー（Cloudflareチャレンジ）が発生する問題を修正する。cloudscraperライブラリを使用してCloudflareを回避する。

## 変更予定ファイル
- nook/pyproject.toml（依存関係追加）
- nook/services/fivechan_explorer/fivechan_explorer.py

## 前提タスク
なし

## worktree名
worktrees/TASK-068-fivechan-cloudscraper-fix

## 作業内容

### 1. 依存関係の追加
pyproject.tomlに`cloudscraper`を追加：
```
cloudscraper = "^1.2.71"
```

### 2. fivechan_explorer.pyの修正

#### 2.1 importの追加
```python
import cloudscraper
```

#### 2.2 _get_thread_posts_from_datメソッドの修正
現在のhttpxベースの実装をcloudscraperベースに変更する。

修正後のメソッド（参考実装）：
```python
async def _get_thread_posts_from_dat(self, dat_url: str) -> List[Dict[str, Any]]:
    """
    dat形式でスレッドの投稿を取得（cloudscraper使用版）
    """
    try:
        self.logger.info(f"dat取得開始: {dat_url}")
        
        # cloudscraper セッションを作成
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        
        # Monazilla形式のヘッダーを設定
        scraper.headers.update({
            'User-Agent': 'Monazilla/1.00 (NookCrawler/1.0)',
            'Accept-Encoding': 'gzip',
            'Referer': dat_url.replace('/dat/', '/test/read.cgi/').replace('.dat', '/')
        })
        
        # 同期的にリクエスト（cloudscraperは同期ライブラリ）
        response = scraper.get(dat_url, timeout=30)
        self.logger.info(f"dat取得レスポンス: {response.status_code}")
        
        if response.status_code == 200:
            # 文字化け対策（Shift_JIS + フォールバック）
            try:
                content = response.content.decode('shift_jis', errors='ignore')
            except:
                try:
                    content = response.content.decode('cp932', errors='ignore')
                except:
                    content = response.text
            
            posts = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if line.strip():
                    # dat形式: name<>mail<>date ID<>message<>title(1行目のみ)
                    parts = line.split('<>')
                    if len(parts) >= 4:
                        post_data = {
                            'no': i + 1,
                            'name': parts[0],
                            'mail': parts[1], 
                            'date': parts[2],
                            'com': parts[3],
                            'time': parts[2]  # 互換性のため
                        }
                        
                        # 1行目の場合はタイトルも含まれる
                        if i == 0 and len(parts) >= 5:
                            post_data['title'] = parts[4]
                        
                        posts.append(post_data)
            
            self.logger.info(f"dat解析完了: 総行数{len(lines)}, 有効投稿{len(posts)}件")
            if posts:
                self.logger.info(f"dat取得成功: {len(posts)}投稿")
                return posts[:10]  # 最初の10投稿
            else:
                self.logger.warning(f"dat内容は取得したが投稿データなし")
                return []
        else:
            self.logger.error(f"dat取得HTTP error: {response.status_code}")
            if "Just a moment" in response.text:
                self.logger.error("Cloudflareチャレンジページが検出されました")
            return []
            
    except Exception as e:
        self.logger.error(f"dat取得エラー {dat_url}: {e}")
        import traceback
        self.logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
    
    return []
```

#### 2.3 非同期処理の調整
cloudscraperは同期ライブラリなので、非同期メソッド内で使用する場合は`asyncio.to_thread`を使用することを検討：

```python
# 同期処理を別スレッドで実行
response = await asyncio.to_thread(scraper.get, dat_url, timeout=30)
```

### 3. テストの実施
修正後、以下のコマンドでテストを実行：
```bash
python -m nook.services.run_services --service 5chan
```

成功基準：
- dat取得時に403エラーが発生しない
- スレッドの投稿内容が正常に取得できる
- ログに「dat取得成功」が表示される

### 4. 品質チェック
- ビルドが成功することを確認
- 自動品質チェック（Biome）を実行
- 既存のテストが通ることを確認