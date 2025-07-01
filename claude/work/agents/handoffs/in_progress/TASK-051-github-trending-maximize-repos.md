# TASK-051: GitHub Trending取得数調整と全言語リポジトリ追加

## タスク概要
GitHub Trendingの取得数を調整し、言語指定なし（any）のリポジトリも追加で取得するように変更。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/services/github_trending/github_trending.py`

## 前提タスク
なし

## worktree名
`worktrees/TASK-051-github-trending-maximize-repos`

## 作業内容

### 1. collectメソッドの修正（L69-96）

**変更内容**: 
- デフォルトlimit値は10のまま維持
- specific言語もlimitと同じ数を取得
- 言語指定なし（any）のリポジトリを追加

```python
async def collect(self, limit: int = 10) -> None:
    """
    GitHubのトレンドリポジトリを収集して保存します。
    
    Parameters
    ----------
    limit : int, default=10
        各言語から取得するリポジトリ数。
    """
    all_repositories = []
    
    # 言語指定なしのリポジトリを取得（新規追加）
    repositories = await self._retrieve_repositories("", limit)
    all_repositories.append(("all", repositories))
    await self.rate_limit()  # レート制限を遵守
    
    # 一般的な言語のリポジトリを取得
    for language in self.languages_config["general"]:
        repositories = await self._retrieve_repositories(language, limit)
        all_repositories.append((language, repositories))
        await self.rate_limit()  # レート制限を遵守
    
    # 特定の言語のリポジトリを取得（limitと同じ数に変更）
    for language in self.languages_config["specific"]:
        repositories = await self._retrieve_repositories(language, limit)  # limit // 2 → limit
        all_repositories.append((language, repositories))
        await self.rate_limit()  # レート制限を遵守
    
    # 翻訳処理
    all_repositories = await self._translate_repositories(all_repositories)
    
    # 保存
    await self._store_summaries(all_repositories)
```

### 3. 実際の取得処理の確認

`_retrieve_repositories`メソッド（L124）で以下を確認：
```python
repo_elements = soup.select("article.Box-row")[:limit]
```
この処理により、指定されたlimit数まで取得されることを確認。

### 2. _retrieve_repositoriesメソッドの動作確認

言語パラメータが空文字列の場合の処理（L115-117）:
```python
url = self.base_url
if language:
    url += f"/{language}"
```
空文字列の場合は`https://github.com/trending`のまま（全言語対象）となることを確認。

### 3. 動作確認手順

1. 修正後、GitHub Trendingサービスを実行：
   ```bash
   python -m nook.services.run_services_sync --service github_trending
   ```

2. 生成されたMarkdownファイルを確認：
   ```bash
   # リポジトリ数をカウント
   grep -c "^### \[" data/github_trending/$(date +%Y-%m-%d).md
   ```
   期待値: 40件（All 10 + Python 10 + Go 10 + Rust 10）

3. 各言語セクションのリポジトリ数を確認：
   ```bash
   # 全言語セクション
   sed -n '/^## すべての言語/,/^## Python/p' data/github_trending/$(date +%Y-%m-%d).md | grep -c "^### \["
   # → 10件
   
   # Pythonセクション
   sed -n '/^## Python/,/^## Go/p' data/github_trending/$(date +%Y-%m-%d).md | grep -c "^### \["
   # → 10件
   
   # Goセクション  
   sed -n '/^## Go/,/^## Rust/p' data/github_trending/$(date +%Y-%m-%d).md | grep -c "^### \["
   # → 10件
   
   # Rustセクション
   sed -n '/^## Rust/,$ p' data/github_trending/$(date +%Y-%m-%d).md | grep -c "^### \["
   # → 10件
   ```

## 期待される効果
- 言語指定なし（全言語）: 10リポジトリ
- Python: 10リポジトリ  
- Go: 10リポジトリ
- Rust: 10リポジトリ
- 合計40リポジトリを取得（現在の20リポジトリから2倍に増加）
- 言語を問わない人気リポジトリも確認可能

## 注意事項
- GitHubへのアクセス頻度が増えるため、レート制限に注意
- 翻訳処理も2倍になるため、実行時間が長くなる可能性  
- GPT APIの使用量も増加するため、コストに注意
- 言語指定なしのリポジトリは多言語混在のため、翻訳品質に注意

## パフォーマンスへの影響
- 取得時間: 約2倍（20→40リポジトリ）
- API呼び出し: 40回の翻訳処理
- ストレージ: Markdownファイルサイズが約2倍に増加

## 将来的な改善案
- 言語の追加（languages.tomlでコメントアウトされている言語の有効化）
- 並行処理による高速化
- キャッシュ機能の実装（同じリポジトリの翻訳を再利用）