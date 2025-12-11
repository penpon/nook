import os

# BaseConfigのロード時に検証エラーが発生しないように、
# テスト実行時はダミーのAPIキーを設定する
os.environ.setdefault("OPENAI_API_KEY", "dummy")
