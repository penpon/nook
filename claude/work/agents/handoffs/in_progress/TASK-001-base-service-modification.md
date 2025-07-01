# TASK-001: グローバルHTTPクライアント移行のベースサービスクラス修正

## タスク概要
BaseServiceクラスを修正して、グローバルHTTPクライアントの使用をサポートする基盤を作成する

## 変更予定ファイル
- nook/common/base_service.py

## 前提タスク
なし

## worktree名
worktrees/TASK-001-global-http-client-base

## 作業内容

### 1. BaseServiceクラスの拡張
```python
# 以下のメソッドを追加
async def setup_http_client(self):
    """グローバルHTTPクライアントをセットアップ"""
    from nook.common.http_client import get_http_client
    self.http_client = await get_http_client()

async def cleanup(self):
    """クリーンアップ処理（オーバーライド可能）"""
    # グローバルクライアントの場合はクローズ不要
    pass
```

### 2. 非同期初期化パターンのサポート
- `async def initialize(self)` メソッドの追加を検討
- サービスの非同期初期化をサポート

### 3. 後方互換性の維持
- 既存のサービスが壊れないように注意
- 段階的な移行を可能にする設計

## 注意事項
- 既存のサービスとの互換性を保つ
- エラーハンドリングを適切に実装
- ドキュメントコメントを追加