"""Pytest共通設定ファイル（全テストで自動ロードされる）.

このファイルはpytestが自動的に読み込み、すべてのテストに適用される。
"""

import os

# 全テスト共通設定:
# BaseConfigのロード時に検証エラーが発生しないように、
# テスト実行時はダミーのAPIキーを設定する。
# 特定のテストでのみ必要な設定はフィクスチャで定義すること。
os.environ.setdefault("OPENAI_API_KEY", "dummy")
