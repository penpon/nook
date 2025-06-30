# TASK-007: APIレスポンス形式の統一

## タスク概要: content.pyを修正してGitHub TrendingもHacker Newsと同じ個別アイテム形式で返すように変更（言語別セクション維持）

## 変更予定ファイル: 
- nook/api/routers/content.py

## 前提タスク: TASK-006（GitHub TrendingのJSON保存実装が完了していること）

## worktree名: worktrees/TASK-007-api-response-unification

## 作業内容:

1. **GitHub Trending用の処理を追加**
   - HackerNewsと同様に、sourceが"github"の場合の個別処理を実装
   - JSONファイルから言語別リポジトリデータを読み込む

2. **ContentItem生成の実装**
   - 言語別にセクションを維持しながら、各リポジトリを個別のContentItemとして生成
   - 言語セクションの開始を示すために、言語名だけのContentItemを挿入
   - フォーマット:
     ```python
     # 言語セクションヘッダー
     ContentItem(
         title="Python",  # または "Go", "Rust"
         content="",  # 空のコンテンツ
         url=None,
         source="github-section"  # セクションを識別するための特別なソース
     )
     
     # リポジトリアイテム
     ContentItem(
         title=repository["name"],  # "owner/repo"形式
         content=f"{repository['description']}\n\n⭐ スター数: {repository['stars']}",
         url=repository["link"],
         source="github"
     )
     ```

3. **ソート順の実装**
   - 各言語セクション内でスター数で降順ソート
   - 言語の順序は維持（Python → Go → Rust）

4. **日付ヘッダーの削除**
   - "GitHub Trending - 2025-06-23"のような日付付きタイトルは生成しない
   - "GitHub トレンドリポジトリ (2025-06-23)"も削除

5. **"all"ソースでの処理**
   - GitHub Trendingも言語別セクション付きの個別アイテムとして含める

## 期待される成果:
- GitHub Trendingが言語別セクションを維持しながら、番号付きの個別カードとして表示される
- 各リポジトリ名がクリック可能なリンクになる
- 日付ヘッダーが表示されない
- Hacker Newsと統一されたインターフェースを実現