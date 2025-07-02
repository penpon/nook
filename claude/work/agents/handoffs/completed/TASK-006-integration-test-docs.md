# TASK-006: 統合テストの実施とドキュメント更新

## タスク概要
グローバルHTTPクライアント移行後の統合テストを実施し、関連ドキュメントを更新する

## 変更予定ファイル
- scripts/crawl_all.sh（必要に応じて）
- README.md（HTTPクライアントに関する説明を追加）
- CLAUDE.md（開発ガイドラインを更新）
- 各種テストスクリプト

## 前提タスク
- TASK-001～TASK-005のすべて

## worktree名
worktrees/TASK-006-integration-test

## 作業内容

### 1. 統合テストの実施

#### 1.1 個別サービステスト
```bash
# 各サービスを個別に実行
python -m nook.services.run_services --service hacker_news
python -m nook.services.run_services --service github_trending
# ... 全11サービスをテスト
```

#### 1.2 並行実行テスト
```bash
# crawl_all.shを実行
./scripts/crawl_all.sh
```

#### 1.3 リソースリークテスト
```bash
# 複数回実行してメモリ使用量を監視
for i in {1..5}; do
    python -m nook.services.run_services --service all
    echo "Run $i completed"
    sleep 5
done
```

### 2. エラーログの確認
- 「Unclosed client session」エラーが出ないことを確認
- HTTPクライアント関連のエラーがないことを確認
- 各サービスのデータ収集が正常に完了していることを確認

### 3. パフォーマンステスト
- 移行前後の実行時間を比較
- メモリ使用量の改善を確認
- HTTP接続数の削減を確認

### 4. ドキュメントの更新

#### 4.1 README.mdに追加
```markdown
## HTTPクライアント管理

本プロジェクトでは、効率的なリソース管理のためグローバルHTTPクライアントを使用しています。

- すべてのサービスが共通のコネクションプールを使用
- HTTP/2による効率的な通信
- 自動的なリソース管理
```

#### 4.2 CLAUDE.mdの更新
```markdown
### HTTPクライアントの使用方法

新しいサービスを作成する際は、以下のパターンに従ってください：

1. __init__でhttp_clientをNoneに初期化
2. collect/runメソッドでsetup_http_client()を呼び出し
3. サービス側でのclose処理は不要（グローバル管理）
```

### 5. トラブルシューティングガイドの作成
- よくある問題と解決方法
- HTTPクライアント関連のデバッグ方法
- パフォーマンスチューニングのヒント

## 完了基準
1. 全サービスが正常に動作する
2. リソースリークが発生しない
3. パフォーマンスが改善または維持されている
4. ドキュメントが最新の状態に更新されている

## 注意事項
- 本番環境での動作を想定したテスト
- エッジケースの考慮
- 後方互換性の確認