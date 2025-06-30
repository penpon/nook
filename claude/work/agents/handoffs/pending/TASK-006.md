# TASK-006: GitHub Trendingデータ構造の変更

## タスク概要: GitHub TrendingをHacker Newsと同じJSON形式で保存できるように変更（言語別セクションは維持）

## 変更予定ファイル: 
- nook/services/github_trending/github_trending.py

## 前提タスク: なし

## worktree名: worktrees/TASK-006-github-json-format

## 作業内容:

1. **データ構造の定義**
   - Repositoryクラスにto_dict()メソッドを追加
   - 各リポジトリの情報を辞書形式に変換できるようにする

2. **JSON保存の実装**
   - _store_summaries()メソッドを修正
   - リポジトリ情報をJSON形式で保存
   - 構造: 
     ```json
     {
       "Python": [
         {
           "name": "owner/repo",
           "link": "https://github.com/owner/repo",
           "description": "日本語での説明",
           "stars": 12345
         }
       ],
       "Go": [...],
       "Rust": [...]
     }
     ```

3. **互換性の維持**
   - 既存のMarkdown保存も残す（後方互換性のため）
   - JSONファイルとMarkdownファイルの両方を生成

4. **実装の注意点**
   - 言語別のグループ構造を維持
   - HackerNewsと同様のオブジェクト構造にする
   - save_json()メソッドを使用してJSON保存

## 期待される成果:
- GitHub Trendingのデータが言語別にグループ化されたJSON形式で保存される
- 各リポジトリは個別のオブジェクトとして保存される
- 既存のMarkdown形式も維持される