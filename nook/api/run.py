"""APIサーバーを起動するためのスクリプト。"""

import argparse

import uvicorn
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()


def main():
    """APIサーバーを起動します。
    コマンドライン引数でホストとポートを指定できます。
    """
    parser = argparse.ArgumentParser(description="Nook APIサーバーを起動します")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",  # nosec B104 - API server intentionally binds to all interfaces
        help="ホストアドレス (デフォルト: 0.0.0.0)",
    )
    parser.add_argument("--port", type=int, default=8000, help="ポート番号 (デフォルト: 8000)")
    parser.add_argument("--reload", action="store_true", help="コード変更時に自動リロードする")

    args = parser.parse_args()

    print(f"Nook APIサーバーを起動しています... http://{args.host}:{args.port}")

    uvicorn.run("nook.api.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
