# Nook - セットアップガイド

## 環境構築

### 1. Python仮想環境の作成

```bash
# uv を使用した仮想環境作成
uv venv

# 仮想環境を有効化
source .venv/bin/activate
```

### 2. 依存関係のインストール

```bash
# uvを使用してパッケージをインストール
uv pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env.example`を参考に`.env`ファイルを作成し、必要なAPIキーを設定してください。

```bash
cp .env.example .env
```

最低限必要な設定：
- `OPENAI_API_KEY`: Hacker News記事の要約に使用

### 4. Hacker Newsサービスのテスト

```bash
# テスト実行
python -c "
import asyncio
from nook.services.hacker_news.hacker_news import HackerNewsRetriever

async def test():
    retriever = HackerNewsRetriever()
    await retriever.collect(limit=5)  # 5記事でテスト
    print('Test completed successfully!')

asyncio.run(test())
"
```

## トラブルシューティング

### よくある問題

1. **HTTP/2 エラー**: `httpx[http2]`パッケージが不足している場合
   ```bash
   uv pip install "httpx[http2]"
   ```

2. **環境変数エラー**: `.env`ファイルにOPENAI_API_KEYが設定されていない場合
   ```bash
   echo "OPENAI_API_KEY=your_api_key_here" >> .env
   ```

3. **403アクセス拒否エラー**: 一部のサイトでアクセスが制限される場合がありますが、これは正常な動作です。

### ログの確認

詳細なログは以下のレベルで出力されます：
- `INFO`: 正常な処理の進行状況
- `WARNING`: アクセス拒否などの軽微な問題  
- `ERROR`: 重大なエラー

## データの保存場所

収集されたデータは以下に保存されます：
- JSON形式: `data/hacker_news/YYYY-MM-DD.json`
- Markdown形式: `data/hacker_news/YYYY-MM-DD.md`