# TASK-010: APIレスポンスのタイトル修正

## タスク概要: GitHub Trendingの日付ヘッダーを削除

## 変更予定ファイル: 
- nook/api/routers/content.py

## 前提タスク: なし

## worktree名: worktrees/TASK-010-remove-date-header

## 作業内容:

1. **_get_source_display_name関数の確認**
   - 現在の実装を確認

2. **GitHub Trendingのタイトル変更**
   - 行105と行139のタイトル生成部分を修正
   - GitHub Trendingの場合は日付を含めない
   
   ```python
   # 修正前
   title=f"{_get_source_display_name(source)} - {target_date.strftime('%Y-%m-%d')}"
   
   # 修正後（GitHub Trendingの場合）
   title="" if source == "github" else f"{_get_source_display_name(source)} - {target_date.strftime('%Y-%m-%d')}"
   ```

3. **動作確認**
   - APIレスポンスにタイトルが含まれないことを確認
   - 他のソースには影響がないことを確認

## 期待される成果:
- GitHub Trendingの不要な日付ヘッダーが削除される
- フロントエンドで「GitHub Trending - 2025-06-23」のような表示がなくなる