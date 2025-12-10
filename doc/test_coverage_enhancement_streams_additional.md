# テストカバレッジ強化ストリーム（追加）

## 概要

このドキュメントは、`test_coverage_enhancement_streams.md` の Stream F〜N 完了後も目標未達だった4ファイルに対する追加テストタスクを定義します。

**現状と目標:**

| ファイル | 現状 | 目標 | 差分 | 未カバー行数 |
|----------|------|------|------|-------------|
| `nook/common/rate_limiter.py` | 74% | 95% | +21% | 15行 |
| `nook/services/run_services.py` | 52% | 85% | +33% | 86行 |
| `nook/services/arxiv_summarizer/arxiv_summarizer.py` | 79% | 85% | +6% | 87行 |
| `nook/services/fivechan_explorer/fivechan_explorer.py` | 39% | 50% | +11% | 309行 |

**前提:**
- 実装コード（nook/配下の .py）は一切編集しない
- OpenAI や外部 HTTP API を実際に叩くテストは書かない（必ずモック・スタブで対応）

---

## Stream O: rate_limiter.py 強化

### 目的

common レイヤーの `rate_limiter.py` を目標（95%）に到達させる。

### 対象

- `nook/common/rate_limiter.py` (74% → 95%)

### 未カバー行の詳細

```
72-76: RateLimitedHTTPClient.__init__ のデフォルト rate_limit 生成
86:    add_domain_rate_limit メソッド
90-92: _get_domain メソッド（urlparse処理）
96-103: _acquire_rate_limit メソッド（ドメイン別レート制限取得）
107-108: get メソッド（レート制限付きGET）
112-113: post メソッド（レート制限付きPOST）
```

### 完了基準

- `rate_limiter.py` のカバレッジが 95% 以上になること
- `RateLimitedHTTPClient` クラスの全メソッドがテストされていること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、rate_limiter.py のカバレッジを 95% 以上にしたいです。

対象と現状:
- nook/common/rate_limiter.py (現状 74%)

未カバー行:
- 72-76行: RateLimitedHTTPClient.__init__ のデフォルト rate_limit 生成
- 86行: add_domain_rate_limit メソッド
- 90-92行: _get_domain メソッド（urlparse処理）
- 96-103行: _acquire_rate_limit メソッド（ドメイン別レート制限取得）
- 107-108行: get メソッド（レート制限付きGET）
- 112-113行: post メソッド（レート制限付きPOST）

やってほしいこと:
1. tests/common/test_rate_limiter.py を確認し（存在しない場合は新規作成）、RateLimitedHTTPClient クラスのテストを追加してください。
2. 以下をテストしてください:
   - RateLimitedHTTPClient の初期化（デフォルト rate_limit 使用）
   - add_domain_rate_limit でドメイン固有のレート制限を追加
   - _get_domain でURLからドメインを正しく抽出
   - _acquire_rate_limit でドメイン別/デフォルトのレート制限を正しく適用
   - get/post メソッドがレート制限を適用してからリクエストを実行
3. HTTP リクエストは httpx.MockTransport を使ってモックしてください。
4. asyncio.sleep はモックして実際の待機を回避してください。

まずファイルを確認し、テストを実装してください。
```

---

## Stream P: run_services.py 強化

### 目的

サービスランナーの `run_services.py` を目標（85%）に到達させる。

### 対象

- `nook/services/run_services.py` (52% → 85%)

### 未カバー行の詳細

```
31-62: ServiceRunner.__init__ 内のサービスクラスimport群
84-86: _run_sync_service 内の日付表示ロジック（複数日の場合）
126-133: _run_sync_service 内の保存ファイルサマリー表示
151: run_all 内のサービス遅延読み込み
188-195: run_all 内のエラー詳細ログ出力
208: run_service 内のサービス遅延読み込み
223-225: run_service 内のエラーハンドリング
236-237: run_continuous 内のエラーハンドリング
245-246: stop メソッド
251-260: run_service_sync 関数
265-324: main 関数（argparse処理）
329-378: 後方互換性関数群（run_github_trending等）
```

### 完了基準

- `run_services.py` のカバレッジが 85% 以上になること
- ServiceRunner の主要メソッドと後方互換性関数がテストされていること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、run_services.py のカバレッジを 85% 以上にしたいです。

対象と現状:
- nook/services/run_services.py (現状 52%)
- 既存テスト: tests/services/test_run_services.py

未カバー行:
- 31-62行: ServiceRunner.__init__ 内のサービスクラスimport群
- 84-86行: _run_sync_service 内の日付表示ロジック（複数日の場合）
- 126-133行: _run_sync_service 内の保存ファイルサマリー表示
- 151行: run_all 内のサービス遅延読み込み
- 188-195行: run_all 内のエラー詳細ログ出力
- 208行: run_service 内のサービス遅延読み込み
- 223-225行: run_service 内のエラーハンドリング
- 236-237行: run_continuous 内のエラーハンドリング
- 245-246行: stop メソッド
- 251-260行: run_service_sync 関数
- 265-324行: main 関数（argparse処理）
- 329-378行: 後方互換性関数群

やってほしいこと:
1. tests/services/test_run_services.py を確認し、未カバー行をテストするケースを追加してください。
2. 以下を重点的にテストしてください:
   - ServiceRunner.__init__ の実パス（サービスクラスのimport）
     - 注意: import自体はコードを実行すれば通るため、`ServiceRunner()` を直接インスタンス化するテストを追加
   - _run_sync_service で複数日を処理した場合の日付表示（len(sorted_dates) > 1）
   - _run_sync_service で saved_files がある場合のサマリー表示
   - run_all/run_service でエラーが発生した場合のログ出力
   - run_continuous でエラーが発生した場合の継続動作
   - stop メソッド
   - run_service_sync 関数（同期版ラッパー）
   - 後方互換性関数（run_github_trending, run_all_services 等）
3. 実サービスクラスはモック/ダミーに差し替えてテストしてください。

まずカバレッジレポートで未カバー行を確認し、そこを埋めるテストを追加してください。
```

---

## Stream Q: arxiv_summarizer.py 強化

### 目的

arXiv サービスの `arxiv_summarizer.py` を目標（85%）に到達させる。

### 対象

- `nook/services/arxiv_summarizer/arxiv_summarizer.py` (79% → 85%)

### 未カバー行の詳細

```
138-139: collect 内の「対象日なし」早期リターン
292, 297, 301, 305: _get_curated_paper_ids 内の条件分岐
321-327: _get_curated_paper_ids 内の例外ハンドリング（非404エラー）
344, 348, 352: フォールバック処理内の条件分岐
380: _get_processed_ids 内の None 日付処理
405-439: _save_processed_ids_by_date 内のループ処理
459: _load_ids_from_file 内の空コンテンツ処理
488, 494: _get_paper_date 内のエラーハンドリングと None リターン
526, 532, 541-543: _retrieve_paper_info 内の条件分岐
635-647: _download_html_without_retry 内のエラーハンドリング
680, 683: _extract_from_html 内の body 処理
708-710: _extract_from_html 内の例外ハンドリング
726-729: _download_pdf_without_retry
785-789, 795-799, 803-807: _extract_from_pdf 内のページ抽出エラー処理
```

### 完了基準

- `arxiv_summarizer.py` のカバレッジが 85% 以上になること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、arxiv_summarizer.py のカバレッジを 85% 以上にしたいです。

対象と現状:
- nook/services/arxiv_summarizer/arxiv_summarizer.py (現状 79%)

未カバー行（主要なもの）:
- 138-139行: collect 内の「対象日なし」早期リターン
- 321-327行: _get_curated_paper_ids 内の例外ハンドリング（非404エラー）
- 405-439行: _save_processed_ids_by_date 内のループ処理
- 635-647行: _download_html_without_retry 内のエラーハンドリング
- 708-710行: _extract_from_html 内の例外ハンドリング
- 785-807行: _extract_from_pdf 内のページ抽出エラー処理

やってほしいこと:
1. tests/services/arxiv_summarizer/ 配下の既存テストを確認してください。
2. 以下を重点的にテストしてください:
   - collect で空の target_dates を渡した場合の早期リターン
   - _get_curated_paper_ids で非404エラー（500等）が発生した場合
   - _save_processed_ids_by_date で日付ごとにIDを正しくグループ化
   - _download_html_without_retry で404エラーの場合（空文字列を返す）
   - _download_html_without_retry でその他のHTTPエラーの場合（例外を再発生）
   - _extract_from_html で例外が発生した場合（空文字列を返す）
   - _extract_from_pdf でページ抽出エラーが発生した場合（スキップして続行）
3. arxiv ライブラリ、httpx、pdfplumber はすべてモックしてください。

まずカバレッジレポートで未カバー行を確認し、そこを埋めるテストを追加してください。
```

---

## Stream R: fivechan_explorer.py 強化

### 目的

5ch サービスの `fivechan_explorer.py` を目標（50%）に到達させる。

### 対象

- `nook/services/fivechan_explorer/fivechan_explorer.py` (39% → 50%)

### 未カバー行の詳細（主要なブロック）

```
513-607: _get_with_403_tolerance（403エラー耐性リクエスト処理）
626-692: _try_alternative_endpoints（代替エンドポイント戦略）
741-750: _get_subject_txt_data 内の文字コード変換
792-885: _get_thread_posts_from_dat（dat形式投稿取得）
912-1018: _retrieve_ai_threads（AI関連スレッド取得メイン処理）
1021-1029, 1034-1043, 1046-1057: スレッド処理のヘルパー部分
1084-1087, 1118-1145, 1148-1289: 要約・保存処理
```

### 完了基準

- `fivechan_explorer.py` のカバレッジが 50% 以上になること
- 主要なメソッド（collect, _retrieve_ai_threads, _get_thread_posts_from_dat）がテストされていること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、fivechan_explorer.py のカバレッジを 50% 以上にしたいです。

対象と現状:
- nook/services/fivechan_explorer/fivechan_explorer.py (現状 39%)

主要な未カバーブロック:
- 513-607行: _get_with_403_tolerance（403エラー耐性リクエスト処理）
- 626-692行: _try_alternative_endpoints（代替エンドポイント戦略）
- 741-750行: _get_subject_txt_data 内の文字コード変換
- 792-885行: _get_thread_posts_from_dat（dat形式投稿取得）
- 912-1018行: _retrieve_ai_threads（AI関連スレッド取得メイン処理）

やってほしいこと:
1. tests/services/fivechan_explorer/ 配下の既存テストを確認してください（存在しない場合は新規作成）。
2. 以下を優先的にテストしてください（行数が多いため、50%達成に最も効果的なもの）:
   - _get_subject_txt_data: subject.txt 形式の解析（モックレスポンスを使用）
   - _get_thread_posts_from_dat: dat 形式の投稿解析（モックレスポンスを使用）
   - _retrieve_ai_threads: AI関連スレッドのフィルタリングと処理
   - collect: メインの収集フロー
3. HTTP リクエストはすべてモックしてください。cloudscraper もモックが必要です。
4. 文字コード変換（Shift_JIS, CP932）のテストには適切なバイト列を用意してください。

注意:
- このファイルは外部サービス（5ch）に強く依存しており、Cloudflare対策のコードが多いです。
- 実際のHTTPリクエストは一切行わず、モックレスポンスでテストしてください。

まずカバレッジレポートで未カバー行を確認し、50%達成に必要な最小限のテストを追加してください。
```

---

## 実行順序と推定工数

| 順序 | Stream | 優先度 | 推定工数 | 累積目標カバレッジ |
|------|--------|--------|---------|-------------------|
| 1 | **O** (rate_limiter) | 最優先 | 小（10分） | 83% |
| 2 | **P** (run_services) | 高 | 中（30分） | 86% |
| 3 | **Q** (arxiv_summarizer) | 中 | 中（30分） | 88% |
| 4 | **R** (fivechan_explorer) | 中 | 大（1時間） | **90%+** |

---

## 完了確認コマンド

各 Stream 完了時に以下を実行してカバレッジを確認:

```bash
uv run pytest -n auto --cov=nook --cov-report=term-missing
```

特定ファイルのみ確認:

```bash
# rate_limiter.py
uv run pytest -n auto --cov=nook/common/rate_limiter.py --cov-report=term-missing tests/common/test_rate_limiter.py

# run_services.py
uv run pytest -n auto --cov=nook/services/run_services.py --cov-report=term-missing tests/services/test_run_services.py

# arxiv_summarizer.py
uv run pytest -n auto --cov=nook/services/arxiv_summarizer --cov-report=term-missing tests/services/arxiv_summarizer/

# fivechan_explorer.py
uv run pytest -n auto --cov=nook/services/fivechan_explorer --cov-report=term-missing tests/services/fivechan_explorer/
```
