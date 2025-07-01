# TASK-021: エラーログレベルの最適化

## タスク概要: 想定内のHTTPエラー（401, 403, 404）のログレベルを調整し、ログの可読性を向上させる

## 変更予定ファイル:
- nook/services/hacker_news/hacker_news.py
- nook/common/decorators.py

## 前提タスク: TASK-020（ブロックリスト実装後の方が効果的）

## worktree名: worktrees/TASK-021-log-levels

## 作業内容:

### 1. hacker_news.pyの修正
`_fetch_story_content()`メソッドで：
- 401, 403エラーは`logger.debug()`に変更
- 404エラーも`logger.info()`に変更
- それ以外のエラーは`logger.error()`のまま
- エラーメッセージをより簡潔に

### 2. 新しいログ出力フォーマット
```python
# 401/403の場合
logger.debug(f"Expected access restriction for {story.url}: {response.status_code}")

# 404の場合
logger.info(f"Content not found for {story.url}: 404")

# その他のエラー
logger.error(f"Unexpected error fetching {story.url}: {str(e)}")
```

### 3. 要約レベルのログ追加
`_get_top_stories()`の最後に、エラーの要約を1行で出力：
```python
logger.info(f"Content fetch summary: {success_count} succeeded, {blocked_count} blocked, {error_count} failed")
```

### 4. デコレータの改善
`handle_errors`デコレータで、特定の例外タイプに応じてログレベルを変更する機能を追加（オプション）

## 期待される効果:
- コンソール出力がクリーンになる
- 重要なエラーが見つけやすくなる
- デバッグ時は`--log-level debug`で詳細を確認可能
- 運用時のログ監視が容易に