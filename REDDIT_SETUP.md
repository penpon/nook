# Reddit データ生成の設定と実行

## 問題の解決

RedditのAPIデータが生成されない問題は、必要なPython依存関係がインストールされていないことが原因でした。

## 解決方法

### 1. 仮想環境のセットアップ
```bash
# プロジェクトルートで実行
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. 環境変数の確認
`.env`ファイルにReddit APIの認証情報が設定されていることを確認：
```
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT="python:nook:v1.0 (by /u/username)"
```

### 3. 手動実行
```bash
source .venv/bin/activate
PYTHONPATH=. python nook/services/run_services_sync.py --service reddit
```

### 4. 自動実行の設定
crontabに以下のエントリを追加して毎日実行：
```bash
# 毎日午前9時にRedditデータを収集
0 9 * * * cd /Users/nana/workspace/nook && source .venv/bin/activate && PYTHONPATH=. python nook/services/run_services_sync.py --service reddit
```

## 確認事項

- ✅ Reddit API認証情報が設定されている
- ✅ Python依存関係がインストールされている
- ✅ データファイル（2025-07-01.md）が正常に生成される
- ✅ フロントエンドでRedditの記事が表示される

## 生成されるファイル

- `data/reddit_explorer/YYYY-MM-DD.md`: 日次のReddit人気投稿データ
- 各投稿には要約、スコア、URL、コメントの傾向が含まれる

## 注意事項

- Reddit APIには利用制限があるため、過度なリクエストは避ける
- GPT APIを使用して要約を生成するため、APIキーが必要
- 初回実行時は時間がかかる場合がある（要約生成のため）