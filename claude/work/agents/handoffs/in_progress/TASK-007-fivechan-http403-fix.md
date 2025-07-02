# TASK-007: 5chanサービスのHTTP 403エラー修正

## タスク概要
5chanサービスがmenu.5ch.net/bbsmenu.htmlにアクセスする際にHTTP 403 Forbiddenエラーが発生する問題を修正する。HTTP/1.1フォールバック機能の有効化と適切なブラウザヘッダーの設定を行う。

## 変更予定ファイル
- nook/services/fivechan_explorer/fivechan_explorer.py

## 前提タスク
なし

## worktree名
worktrees/TASK-007-fivechan-http403-fix

## 作業内容

### 1. 問題の詳細
- 5ch.netのmenu.5ch.net/bbsmenu.htmlへのアクセスが403 Forbiddenで拒否される
- すべての板からのスレッド取得が失敗し、0件の結果となる
- 原因：HTTP/2互換性問題、User-Agent設定不足、レート制限の可能性

### 2. 修正内容

#### 2.1 HTTP/1.1の強制使用
fivechan_explorer.pyの以下の箇所でHTTPクライアント呼び出しにforce_http1=Trueパラメータを追加：
- 195-197行目付近：板一覧ページ取得
- 221-223行目付近：板のスレッド一覧取得
- その他のHTTPリクエスト箇所

#### 2.2 ブラウザヘッダーの完全設定
現在のheaders辞書に以下を追加：
```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Referer": "https://5ch.net/"
}
```

#### 2.3 エラーハンドリングの強化
403エラーを特別に処理し、詳細なログを出力：
- HTTPステータスコードを確認
- 403の場合は具体的なエラー内容をログに記録
- リトライ間隔の調整（必要に応じて）

### 3. テスト方法
1. 修正後、`python -m nook.services.run_services --service 5chan`を実行
2. 403エラーが発生せず、スレッドが正常に取得されることを確認
3. ログでHTTP/1.1が使用されていることを確認

### 4. 注意事項
- レート制限を考慮し、request_delayは現在の2秒を維持（必要に応じて調整）
- 他のサービスには影響しないよう、5chanサービス固有の設定として実装
- HTTPクライアントの既存機能（force_http1）を活用

### 5. 期待される結果
- 403エラーが解消され、5ch.netへのアクセスが成功
- 各板からAI関連スレッドが正常に取得される
- 取得したスレッドがJSONファイルに保存される