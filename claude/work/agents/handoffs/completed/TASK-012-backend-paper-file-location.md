# TASK-012: Paperサービスのファイル保存先とファイル名形式の修正

## 概要
Paperサービスがスクレイピングしたデータを間違った場所に間違った名前で保存している問題を修正する。

## 問題詳細
1. **保存場所の不整合**
   - 現在: `paper_summarizer/`
   - 期待: `data/paper_summarizer/`

2. **ファイル名の不整合**
   - 現在: `paper_summarizer_2025-06-24.md`
   - 期待: `2025-06-24.md`

## 変更予定ファイル
- nook/common/base_service.py
- nook/services/paper_summarizer.py

## 前提タスク
- なし（即座に実行可能）

## 作業内容
1. base_service.pyのsave_dataメソッドで保存先パスを修正
   - 現在: `output_dir = Path(self.name)` 
   - 修正後: `output_dir = Path("data") / self.name`

2. paper_summarizer.pyでファイル名形式を修正
   - 現在: `{self.name}_{date_str}.md`
   - 修正後: `{date_str}.md`

3. 既存のdataディレクトリ構造を確認し、必要に応じてディレクトリを作成

## 完了条件
- Paperサービスを実行すると`data/paper_summarizer/2025-06-24.md`にファイルが保存される
- APIエンドポイント（/api/content/paper）が正しくデータを返す
- ダッシュボードで最新の論文データが表示される