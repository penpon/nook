# TASK-011: Business NewsとTech Newsのフィード記事数を5に制限

## タスク概要
Business NewsとTech Newsの各フィードから取得する記事数を5つに制限する

## 変更予定ファイル
- nook/services/business_feed/business_feed.py
- nook/services/tech_feed/tech_feed.py

## 前提タスク
なし

## worktree名
worktrees/TASK-011-limit-feed-articles

## 作業内容
1. business_feed.pyの修正
   - runメソッドのlimitパラメータのデフォルト値を30から5に変更
   - collectメソッドのlimitパラメータのデフォルト値を30から5に変更
   - docstringのlimitパラメータの説明を更新

2. tech_feed.pyの修正
   - runメソッドのlimitパラメータのデフォルト値を30から5に変更
   - collectメソッドのlimitパラメータのデフォルト値を30から5に変更
   - docstringのlimitパラメータの説明を更新

3. 変更後の動作確認
   - 各フィードから5記事ずつ取得されることを確認