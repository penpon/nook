# TASK-045: ArXivサービス名完全統一（paper_summarizer → arxiv_summarizer）

## タスク概要
paper_summarizerをarxiv_summarizerに完全統一し、ディレクトリ・ファイル・コード全体を変更。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/services/paper_summarizer/` → `arxiv_summarizer/`（ディレクトリ全体）
- `/Users/nana/workspace/nook/nook/services/run_services.py`
- `/Users/nana/workspace/nook/nook/services/run_services_sync.py`
- `/Users/nana/workspace/nook/nook/api/routers/content.py`
- `/Users/nana/workspace/nook/test_paper.py`
- `/Users/nana/workspace/nook/README.md`
- ドキュメントファイル群
- データディレクトリの移行

## 前提タスク
TASK-042, TASK-043, TASK-044（すべて完了後）

## worktree名
`worktrees/TASK-045-arxiv-service-rename`

## 作業内容

### 1. ディレクトリ・ファイル構造変更
**ディレクトリ名変更**:
- `nook/services/paper_summarizer/` → `arxiv_summarizer/`
- `data/paper_summarizer/` → `arxiv_summarizer/`

**ファイル名変更**:
- `paper_summarizer.py` → `arxiv_summarizer.py`
- ログファイル: `logs/paper_summarizer.log` → `arxiv_summarizer.log`

### 2. Pythonコード修正

#### run_services.py
- L38: `from nook.services.paper_summarizer.paper_summarizer import PaperSummarizer` → `from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer`
- L52: `"paper": PaperSummarizer(),` → `"arxiv": ArxivSummarizer(),`
- L244: `def run_paper_summarizer():` → `def run_arxiv_summarizer():`
- L245: `run_service_sync("paper")` → `run_service_sync("arxiv")`

#### run_services_sync.py
- L25: `from nook.services.paper_summarizer.paper_summarizer import PaperSummarizer` → `from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer`
- L153: `def run_paper_summarizer():` → `def run_arxiv_summarizer():`
- L165: `paper_summarizer = PaperSummarizer()` → `arxiv_summarizer = ArxivSummarizer()`
- L166: `paper_summarizer.run()` → `arxiv_summarizer.run()`

#### arxiv_summarizer.py（旧paper_summarizer.py）
- クラス名: `class PaperSummarizer` → `class ArxivSummarizer`
- L97: `super().__init__("paper_summarizer")` → `super().__init__("arxiv_summarizer")`

#### content.py
- L42: `"arxiv": "paper_summarizer"` → `"arxiv": "arxiv_summarizer"`

#### test_paper.py
- L3: インポート文の修正
- ファイル名も`test_arxiv.py`に変更検討

### 3. ドキュメント更新

#### README.md
- L26: `3. **Paper Summarizer** - arXiv論文の要約` → `3. **ArXiv Summarizer** - arXiv論文の要約`
- L132: `python -m nook.services.run_services --service paper_summarizer` → `--service arxiv_summarizer`
- L148: `├── paper_summarizer/    # arXiv論文` → `├── arxiv_summarizer/    # arXiv論文`

#### 設計ドキュメント
- `/Users/nana/workspace/nook/doc/detail_software_design.md`: paper_summarizerの記述を更新
- `/Users/nana/workspace/nook/doc/new_detail_software.design.md`: 複数箇所の更新

### 4. データ移行
- `data/paper_summarizer/` → `data/arxiv_summarizer/`
- 既存データファイルの移行
- ログファイルの移行または処理方針決定

### 5. スクリプト更新
#### crawl_all.sh
- L43: `python -m nook.services.run_services --service paper` → `--service arxiv`

### 6. キャッシュクリア
- `__pycache__`ディレクトリの削除
- 既存のワークツリー内の同期

## 期待される効果
- paper/arxivの完全な統一
- 一貫した命名規則の確立
- 保守性の向上

## 注意事項
- データ移行は慎重に実行（バックアップ必須）
- 既存のログファイルの処理方針を事前決定
- 変更後の動作確認を徹底実施
- 外部依存関係がないことを確認済み

## 実行順序
1. ディレクトリ・ファイル構造変更
2. Pythonコード修正
3. ドキュメント更新
4. データ移行
5. 動作確認・テスト実行