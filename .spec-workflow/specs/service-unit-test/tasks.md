# Tasks Document - Service Unit Test Implementation

## Overview
このタスクドキュメントは、nookプロジェクトの11サービスに対する包括的なユニットテスト実装を定義します。
- **Phase 2**: BaseFeedService継承サービス（5サービス、75-100ケース）
- **Phase 3**: 非BaseFeedServiceサービス（6サービス、120-180ケース）
- **総テストケース数**: 195-280ケース
- **目標カバレッジ**: 各サービス95%以上

## Phase 2: BaseFeedService継承サービス（5サービス）

### 2.1 business_feed ユニットテスト実装

- [x] 2.1. business_feed ユニットテスト実装（15-18テストケース）
  - File: tests/services/test_business_feed.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（6-8ケース）**:
       - フィード設定（feed.toml）読み込み成功/失敗
       - 複数カテゴリ（business）のフィード処理ループ
       - 日付フィルタリング（指定範囲内/範囲外）
       - 重複チェック（DedupTracker有効時の除外）
       - 日本語判定分岐（_needs_japanese_check=True時）
       - HTTP取得失敗時のリトライ/スキップ
       - GPT要約失敗時のデフォルト値設定
       - ストレージ保存成功/失敗
    2. **_retrieve_article詳細テスト（5-7ケース）**:
       - entry.linkがNone時はNone返却
       - HTTP GET成功（200）、記事情報抽出
       - HTTP GET タイムアウト処理
       - HTTP GET 404/500エラー処理
       - BeautifulSoup解析成功/空HTML/不正HTML
       - 日本語判定True時のフィルタリング（日本語記事→保持、英語記事→None）
       - 人気スコア（_extract_popularity）抽出成功/デフォルト値0.0
    3. **_extract_popularity詳細テスト（3-5ケース）**:
       - メタタグ検出（article:reaction_count, og:likes等）
       - data-reaction-count属性検出
       - ボタンテキストから数値抽出（正規表現）
       - 複数候補から最大値選択
       - すべて失敗時0.0返却
  - Purpose: business_feedサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_feedparser_result, mock_feed_entry, mock_html_japanese_article, mock_dedup_tracker, respx_mock), tests/services/test_base_feed_service.py (Given-When-Thenパターン)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: business_feed.py（nook/services/business_feed/business_feed.py）の内部メソッド単体テストを実装。collect()のフィード処理ループ、日本語判定分岐、_retrieve_article()のHTTPエラー・BeautifulSoup解析・日本語フィルタリング、_extract_popularity()のメタタグ/data属性/テキスト抽出を網羅。既存のtest_business_feed.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: test_base_feed_service.pyのGiven-When-Then構造を厳守、conftest.pyのフィクスチャを最大活用、モック多用でHTTP呼び出しゼロ、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、カバレッジ95%以上（内部メソッド）、既存テストも引き続きパス。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

### 2.2 tech_feed ユニットテスト実装

- [x] 2.2. tech_feed ユニットテスト実装（15-18テストケース）
  - File: tests/services/test_tech_feed.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（6-8ケース）**:
       - フィード設定（feed.toml）読み込み成功/失敗
       - 複数カテゴリ（tech）のフィード処理ループ
       - 日付フィルタリング（指定範囲内/範囲外）
       - 重複チェック（DedupTracker有効時の除外）
       - 日本語判定分岐（_needs_japanese_check=True時）
       - HTTP取得失敗時のリトライ/スキップ
       - GPT要約失敗時のデフォルト値設定
       - ストレージ保存成功/失敗
    2. **_retrieve_article詳細テスト（5-7ケース）**:
       - entry.linkがNone時はNone返却
       - HTTP GET成功（200）、記事情報抽出
       - HTTP GET タイムアウト処理
       - HTTP GET 404/500エラー処理
       - BeautifulSoup解析成功/空HTML/不正HTML
       - 日本語判定True時のフィルタリング（日本語記事→保持、英語記事→None）
       - 人気スコア（_extract_popularity）抽出成功/デフォルト値0.0
    3. **_extract_popularity詳細テスト（3-5ケース）**:
       - メタタグ検出（article:reaction_count, og:likes等）
       - data-reaction-count属性検出
       - ボタンテキストから数値抽出（正規表現）
       - 複数候補から最大値選択
       - すべて失敗時0.0返却
  - Purpose: tech_feedサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_feedparser_result, mock_feed_entry, mock_html_japanese_article, mock_dedup_tracker, respx_mock), tests/services/test_base_feed_service.py (Given-When-Thenパターン)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: tech_feed.py（nook/services/tech_feed/tech_feed.py）の内部メソッド単体テストを実装。collect()のフィード処理ループ、日本語判定分岐、_retrieve_article()のHTTPエラー・BeautifulSoup解析・日本語フィルタリング、_extract_popularity()のメタタグ/data属性/テキスト抽出を網羅。既存のtest_tech_feed.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: test_base_feed_service.pyのGiven-When-Then構造を厳守、conftest.pyのフィクスチャを最大活用、モック多用でHTTP呼び出しゼロ、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、カバレッジ95%以上（内部メソッド）、既存テストも引き続きパス。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

### 2.3 note_explorer ユニットテスト実装

- [x] 2.3. note_explorer ユニットテスト実装（15-18テストケース）
  - File: tests/services/test_note_explorer.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（6-8ケース）**:
       - フィード設定（feed.toml）読み込み成功/失敗
       - 複数カテゴリのフィード処理ループ
       - 日付フィルタリング（指定範囲内/範囲外）
       - 重複チェック（DedupTracker有効時の除外）
       - HTTP取得失敗時のリトライ/スキップ
       - GPT要約失敗時のデフォルト値設定
       - ストレージ保存成功/失敗
    2. **_retrieve_article詳細テスト（5-7ケース）**:
       - entry.linkがNone時はNone返却
       - HTTP GET成功（200）、記事情報抽出
       - HTTP GET タイムアウト処理
       - HTTP GET 404/500エラー処理
       - BeautifulSoup解析成功/空HTML/不正HTML
       - 人気スコア（_extract_popularity）抽出成功/デフォルト値0.0
    3. **_extract_popularity詳細テスト（3-5ケース）**:
       - メタタグ検出（note:likes, article:reaction_count等）
       - data-like-count属性検出
       - ボタンテキストから数値抽出（正規表現）
       - 複数候補から最大値選択
       - すべて失敗時0.0返却
  - Purpose: note_explorerサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_feedparser_result, mock_feed_entry, mock_html_note_article, mock_dedup_tracker, respx_mock), tests/services/test_base_feed_service.py (Given-When-Thenパターン)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: note_explorer.py（nook/services/note_explorer/note_explorer.py）の内部メソッド単体テストを実装。collect()のフィード処理ループ、_retrieve_article()のHTTPエラー・BeautifulSoup解析、_extract_popularity()のnote特有のメタタグ（note:likes等）/data属性/テキスト抽出を網羅。既存のtest_note_explorer.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: test_base_feed_service.pyのGiven-When-Then構造を厳守、conftest.pyのフィクスチャを最大活用、モック多用でHTTP呼び出しゼロ、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、カバレッジ95%以上（内部メソッド）、既存テストも引き続きパス。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

### 2.4 qiita_explorer ユニットテスト実装

- [x] 2.4. qiita_explorer ユニットテスト実装（15-18テストケース）
  - File: tests/services/test_qiita_explorer.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（6-8ケース）**:
       - フィード設定（feed.toml）読み込み成功/失敗
       - 複数カテゴリのフィード処理ループ
       - 日付フィルタリング（指定範囲内/範囲外）
       - 重複チェック（DedupTracker有効時の除外）
       - HTTP取得失敗時のリトライ/スキップ
       - GPT要約失敗時のデフォルト値設定
       - ストレージ保存成功/失敗
    2. **_retrieve_article詳細テスト（5-7ケース）**:
       - entry.linkがNone時はNone返却
       - HTTP GET成功（200）、記事情報抽出
       - HTTP GET タイムアウト処理
       - HTTP GET 404/500エラー処理
       - BeautifulSoup解析成功/空HTML/不正HTML
       - 人気スコア（_extract_popularity）抽出成功/デフォルト値0.0
    3. **_extract_popularity詳細テスト（3-5ケース）**:
       - メタタグ検出（qiita:likes, article:like_count等）
       - data-like-count属性検出
       - ボタンテキストから数値抽出（正規表現、「いいね」表記）
       - 複数候補から最大値選択
       - すべて失敗時0.0返却
  - Purpose: qiita_explorerサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_feedparser_result, mock_feed_entry, mock_html_qiita_article, mock_dedup_tracker, respx_mock), tests/services/test_base_feed_service.py (Given-When-Thenパターン)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: qiita_explorer.py（nook/services/qiita_explorer/qiita_explorer.py）の内部メソッド単体テストを実装。collect()のフィード処理ループ、_retrieve_article()のHTTPエラー・BeautifulSoup解析、_extract_popularity()のQiita特有のメタタグ（qiita:likes等）/data属性/テキスト抽出（「いいね」表記）を網羅。既存のtest_qiita_explorer.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: test_base_feed_service.pyのGiven-When-Then構造を厳守、conftest.pyのフィクスチャを最大活用、モック多用でHTTP呼び出しゼロ、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、カバレッジ95%以上（内部メソッド）、既存テストも引き続きパス。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

### 2.5 zenn_explorer ユニットテスト実装

- [-] 2.5. zenn_explorer ユニットテスト実装（15-18テストケース）
  - File: tests/services/test_zenn_explorer.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（6-8ケース）**:
       - フィード設定（feed.toml）読み込み成功/失敗
       - 複数カテゴリのフィード処理ループ
       - 日付フィルタリング（指定範囲内/範囲外）
       - 重複チェック（DedupTracker有効時の除外）
       - HTTP取得失敗時のリトライ/スキップ
       - GPT要約失敗時のデフォルト値設定
       - ストレージ保存成功/失敗
    2. **_retrieve_article詳細テスト（5-7ケース）**:
       - entry.linkがNone時はNone返却
       - HTTP GET成功（200）、記事情報抽出
       - HTTP GET タイムアウト処理
       - HTTP GET 404/500エラー処理
       - BeautifulSoup解析成功/空HTML/不正HTML
       - 人気スコア（_extract_popularity）抽出成功/デフォルト値0.0
    3. **_extract_popularity詳細テスト（3-5ケース）**:
       - メタタグ検出（zenn:likes, article:like_count等）
       - data-like-count属性検出
       - ボタンテキストから数値抽出（正規表現）
       - 複数候補から最大値選択
       - すべて失敗時0.0返却
  - Purpose: zenn_explorerサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_feedparser_result, mock_feed_entry, mock_html_zenn_article, mock_dedup_tracker, respx_mock), tests/services/test_base_feed_service.py (Given-When-Thenパターン)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: zenn_explorer.py（nook/services/zenn_explorer/zenn_explorer.py）の内部メソッド単体テストを実装。collect()のフィード処理ループ、_retrieve_article()のHTTPエラー・BeautifulSoup解析、_extract_popularity()のZenn特有のメタタグ（zenn:likes等）/data属性/テキスト抽出を網羅。既存のtest_zenn_explorer.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: test_base_feed_service.pyのGiven-When-Then構造を厳守、conftest.pyのフィクスチャを最大活用、モック多用でHTTP呼び出しゼロ、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、カバレッジ95%以上（内部メソッド）、既存テストも引き続きパス。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

---

## Phase 3: 非BaseFeedServiceサービス（6サービス）

### 3.1 arxiv_summarizer ユニットテスト実装

- [-] 3.1. arxiv_summarizer ユニットテスト実装（20-25テストケース）
  - File: tests/services/test_arxiv_summarizer.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（6-8ケース）**:
       - arxiv.Search成功/失敗/空結果
       - 日付フィルタリング（指定範囲内/範囲外）
       - 重複チェック（処理済みID管理）
       - PDF取得成功/失敗分岐
       - GPT要約成功/失敗
       - ストレージ保存成功/失敗
    2. **_search_arxiv テスト（3-4ケース）**:
       - クエリ生成、カテゴリ指定（cs.AI等）
       - max_results制限適用
       - arxiv API例外ハンドリング
    3. **_download_pdf テスト（4-5ケース）**:
       - PDF URL抽出成功/失敗
       - HTTP GET成功/タイムアウト/404
       - BytesIO変換成功
    4. **_extract_text_from_pdf テスト（4-5ケース）**:
       - pdfplumber.open成功/失敗
       - ページ抽出、テキスト結合
       - 破損PDFハンドリング
    5. **_clean_text テスト（3-4ケース）**:
       - LaTeX記号除去（$、\、{、}等）
       - 空白正規化（連続空白→単一）
       - 特殊文字除去
  - Purpose: arxiv_summarizerサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_arxiv_entry_xml, respx_mock, mock_gpt_client), nook/services/arxiv_summarizer/arxiv_summarizer.py (remove_tex_backticks, remove_outer_markdown_markers等のユーティリティ)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: arxiv_summarizer.py（nook/services/arxiv_summarizer/arxiv_summarizer.py）の内部メソッド単体テストを実装。arxiv.Search API、PDF取得、テキスト抽出、整形（LaTeX記号除去）を網羅。エラーハンドリング（API失敗、PDF破損、タイムアウト）を網羅。既存のtest_arxiv_summarizer.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: arxiv.Searchはモック化（実際のAPI呼び出しなし）、PDF取得はrespx_mock使用、pdfplumberはMagicMockで置換、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、外部API呼び出しゼロ、カバレッジ95%以上。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

### 3.2 fivechan_explorer ユニットテスト実装

- [ ] 3.2. fivechan_explorer ユニットテスト実装（30-35テストケース）
  - File: tests/services/test_fivechan_explorer.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（8-10ケース）**:
       - 板設定（boards.toml）読み込み成功/失敗
       - 複数サブドメイン試行ループ（egg.5ch.net, lavender.5ch.net等）
       - subject.txt取得成功/失敗
       - dat取得成功/失敗
       - 人気スコア計算（レス数、レス間隔）
       - 日付フィルタリング
       - GPT要約成功/失敗
       - ストレージ保存成功/失敗
    2. **_fetch_subject_txt テスト（6-8ケース）**:
       - 各サブドメイン試行（成功するまで）
       - Shift_JIS解析成功/失敗/文字化け対応
       - HTTPエラー（404、500）/タイムアウト
       - cloudscraper使用（User-Agent設定）
    3. **_parse_subject_txt テスト（5-6ケース）**:
       - <> 区切り解析成功
       - スレッドID、タイトル、レス数抽出
       - 不正フォーマット処理（<>が1つしかない等）
       - 文字化け対応（errors='ignore'）
    4. **_fetch_dat_file テスト（4-5ケース）**:
       - Shift_JIS解析成功/失敗
       - HTTP GET成功/タイムアウト/404
       - リトライロジック（複数サブドメイン試行）
    5. **_parse_dat_file テスト（4-5ケース）**:
       - <> 区切り解析（名前、メール、日時、本文）
       - 不正行スキップ（<>が4つ未満等）
       - 空レス処理
    6. **_calculate_popularity テスト（3-4ケース）**:
       - レス数加点（多レス→高スコア）
       - レス間隔加点（短い間隔→高スコア）
       - 古いスレッド減点
  - Purpose: fivechan_explorerサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_5chan_subject_txt, mock_5chan_dat, respx_mock, thread_factory)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: fivechan_explorer.py（nook/services/fivechan_explorer/fivechan_explorer.py）の内部メソッド単体テストを実装。Shift_JIS解析、複数サブドメインリトライ、dat解析（<>区切り）を網羅。不正フォーマット、文字化け、HTTPエラーを網羅。既存のtest_fivechan_explorer.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: cloudscraper.create_scraperをモック化、Shift_JISバイト列をbytes.decode('shift_jis', errors='ignore')で処理、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、文字化けケースも正常処理、カバレッジ95%以上。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

### 3.3 fourchan_explorer ユニットテスト実装

- [ ] 3.3. fourchan_explorer ユニットテスト実装（25-30テストケース）
  - File: tests/services/test_fourchan_explorer.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（6-8ケース）**:
       - カタログAPI取得成功/失敗/空結果
       - スレッド取得成功/失敗
       - 日付フィルタリング
       - 人気スコア計算
       - GPT要約成功/失敗
       - ストレージ保存成功/失敗
    2. **_fetch_catalog テスト（5-6ケース）**:
       - 4chan catalog.json API成功/失敗
       - JSON解析成功/不正JSON
       - HTTPエラー（404、500）/タイムアウト
    3. **_fetch_thread テスト（5-6ケース）**:
       - スレッド詳細JSON API成功/失敗/404
       - JSON解析成功/不正JSON
       - タイムアウト処理
    4. **_parse_thread テスト（4-5ケース）**:
       - JSON解析成功、投稿リスト抽出
       - 空スレッド処理
       - 不正フォーマット処理
    5. **_calculate_popularity テスト（3-4ケース）**:
       - レス数、bumps、images数からスコア計算
       - 各要素の重み付け検証
    6. **_summarize_thread テスト（2-3ケース）**:
       - GPT要約成功/失敗
  - Purpose: fourchan_explorerサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_4chan_catalog, mock_4chan_thread, respx_mock)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: fourchan_explorer.py（nook/services/fourchan_explorer/fourchan_explorer.py）の内部メソッド単体テストを実装。4chan catalog.json/スレッドJSON API、JSON解析、人気スコア計算を網羅。HTTPエラー、タイムアウト、不正JSONを網羅。既存のtest_fourchan_explorer.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: 4chan APIはrespx_mockでモック化、実際のAPI呼び出しなし、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、カバレッジ95%以上。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

### 3.4 github_trending ユニットテスト実装

- [ ] 3.4. github_trending ユニットテスト実装（20-25テストケース）
  - File: tests/services/test_github_trending.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（5-7ケース）**:
       - GitHub Trending HTMLスクレイピング成功/失敗
       - 言語フィルタリング（languages.toml）
       - 人気スコア計算
       - GPT要約成功/失敗
       - ストレージ保存成功/失敗
    2. **_fetch_trending_html テスト（4-5ケース）**:
       - HTML取得成功/タイムアウト/404
       - HTTPエラー処理
    3. **_parse_repositories テスト（6-8ケース）**:
       - BeautifulSoupセレクタ解析成功
       - リポジトリ名、説明、スター数抽出
       - スター数フォーマット（カンマ付き、k/M表記）
       - 空ページ処理
       - 不正HTML処理
    4. **_calculate_popularity テスト（2-3ケース）**:
       - スター数ベーススコア計算
    5. **_summarize_repository テスト（3-4ケース）**:
       - GPT要約成功/失敗/空説明
  - Purpose: github_trendingサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_github_trending_html, respx_mock)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: github_trending.py（nook/services/github_trending/github_trending.py）の内部メソッド単体テストを実装。HTMLスクレイピング、BeautifulSoup解析、スター数抽出（カンマ/k/M表記）、GPT要約を網羅。HTTPエラー、不正HTML、タイムアウトを網羅。既存のtest_github_trending.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: GitHub APIはrespx_mockでモック化、実際のHTTP呼び出しなし、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、カバレッジ95%以上。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

### 3.5 hacker_news ユニットテスト実装

- [ ] 3.5. hacker_news ユニットテスト実装（25-30テストケース）
  - File: tests/services/test_hacker_news.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（6-8ケース）**:
       - HN topstories API取得成功/失敗/空結果
       - ストーリー詳細取得成功/失敗
       - コンテンツ取得成功/失敗
       - スコアフィルタリング（≥20）
       - テキスト長フィルタリング（100-10000）
       - GPT要約成功/失敗
       - ストレージ保存成功/失敗
    2. **_fetch_top_stories テスト（4-5ケース）**:
       - topstories.json API成功/失敗
       - JSON解析成功/不正JSON
       - HTTPエラー/タイムアウト
    3. **_fetch_story テスト（5-6ケース）**:
       - item/{id}.json API成功/失敗/削除済みストーリー
       - JSON解析成功/不正JSON
       - タイムアウト処理
    4. **_fetch_story_content テスト（5-6ケース）**:
       - URL先コンテンツ取得成功/タイムアウト/404
       - メタディスクリプション抽出成功
       - 段落抽出フォールバック
       - blocked_domains.json判定（401/403エラー時自動追加）
    5. **_calculate_popularity テスト（2-3ケース）**:
       - score、descendants（コメント数）ベーススコア
    6. **_summarize_story テスト（3-4ケース）**:
       - GPT要約成功/失敗
  - Purpose: hacker_newsサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_hn_story, mock_hn_api, respx_mock)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: hacker_news.py（nook/services/hacker_news/hacker_news.py）の内部メソッド単体テストを実装。HN API（topstories、item）、コンテンツ取得、フィルタリング（スコア≥20、テキスト長100-10000）、blocked_domains.json管理を網羅。HTTPエラー、タイムアウト、削除済みストーリーを網羅。既存のtest_hacker_news.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: HN APIはrespx_mockでモック化、実際のAPI呼び出しなし、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、カバレッジ95%以上。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

### 3.6 reddit_explorer ユニットテスト実装

- [ ] 3.6. reddit_explorer ユニットテスト実装（20-25テストケース）
  - File: tests/services/test_reddit_explorer.py
  - **実装するテストケース**:
    1. **collect内部分岐テスト（5-7ケース）**:
       - subreddits.toml読み込み成功/失敗
       - asyncpraw OAuth認証成功/失敗
       - subreddit取得成功/失敗/存在しない
       - 投稿取得成功/失敗/空
       - 人気スコア計算
       - GPT要約成功/失敗
       - ストレージ保存成功/失敗
    2. **_get_reddit_instance テスト（4-5ケース）**:
       - asyncpraw.Reddit初期化成功/失敗
       - OAuth認証（client_id、client_secret）成功/失敗
       - コンテキストマネージャー動作
    3. **_fetch_subreddit_posts テスト（5-6ケース）**:
       - subreddit.hot()取得成功/失敗
       - stickied投稿除外
       - 投稿タイプ判定（image、video、text、link等7種）
       - UTC→JST変換
    4. **_calculate_popularity テスト（2-3ケース）**:
       - upvotesベーススコア計算
    5. **_summarize_post テスト（3-4ケース）**:
       - GPT要約成功/失敗/空タイトル
  - Purpose: reddit_explorerサービスの内部メソッド単体テストを実装し、カバレッジ95%以上を達成
  - _Leverage: tests/conftest.py (mock_reddit_post, mock_reddit_api, respx_mock)_
  - _Prompt: Implement the task for spec service-unit-test. Role: Python/pytest ユニットテスト専門家 | Task: reddit_explorer.py（nook/services/reddit_explorer/reddit_explorer.py）の内部メソッド単体テストを実装。asyncpraw OAuth認証、subreddit取得、投稿タイプ判定（7種: image/gallery/video/poll/crosspost/text/link）、UTC→JST変換、GPT要約を網羅。認証失敗、subreddit存在しない、空投稿を網羅。既存のtest_reddit_explorer.pyに追加する形で実装（既存の統合テストは維持）。 | Restrictions: asyncprawはモック化（実際のReddit API呼び出しなし）、既存テストを削除しない | Success: 全テストがpytest -v -m unitでグリーン、カバレッジ95%以上。実装完了後、tasks.mdで本タスクを[-]に変更、log-implementationツールで実装詳細を記録（artifacts必須）、完了後[x]に変更。_

---

## 実装完了基準

### 各タスク完了時の手順
1. **タスク開始時**: tasks.mdで該当タスクを `- [ ]` から `- [-]` に変更
2. **実装実行**: プロンプトに従ってテストコードを実装
3. **テスト実行**: `pytest tests/services/test_{service_name}.py -v -m unit` で全テスト成功確認
4. **カバレッジ測定**: `pytest tests/services/test_{service_name}.py --cov=nook/services/{service_name} --cov-report=term-missing` で95%以上確認
5. **実装ログ記録**: `log-implementation` ツールで実装詳細を記録（**artifacts必須**: apiEndpoints、components、functions、classes、integrations）
6. **タスク完了**: tasks.mdで該当タスクを `- [-]` から `- [x]` に変更

### 全体完了基準
- 全11サービスのタスクが `- [x]` になっている
- 全サービスのカバレッジが95%以上
- 総テストケース数: 195-280ケース
- 全テストが `pytest tests/services/ -v -m unit` でグリーン

---

## 参考リソース

### テストパターン参照
- **Given-When-Then構造**: tests/services/test_base_feed_service.py
- **モック戦略**: tests/conftest.py
- **既存統合テスト**: tests/services/test_{service_name}.py（各サービス）

### フィクスチャ一覧
- 環境変数: `mock_env_vars`
- HTTPクライアント: `respx_mock`, `mock_httpx_client`
- GPTクライアント: `mock_gpt_client`
- 外部API: `mock_hn_api`, `mock_reddit_api`, `mock_arxiv_entry_xml`
- HTML: `mock_html_japanese_article`, `mock_html_english_article`, `mock_github_trending_html`
- 掲示板: `mock_4chan_catalog`, `mock_5chan_subject_txt`
- ファクトリー: `article_factory`, `thread_factory`
- ストレージ: `temp_data_dir`, `mock_storage`
- 重複チェック: `mock_dedup_tracker`
- 時刻固定: `fixed_datetime`

### サービス実装ファイル
- BaseFeedService: nook/services/base_feed_service.py
- business_feed: nook/services/business_feed/business_feed.py
- tech_feed: nook/services/tech_feed/tech_feed.py
- note_explorer: nook/services/note_explorer/note_explorer.py
- qiita_explorer: nook/services/qiita_explorer/qiita_explorer.py
- zenn_explorer: nook/services/zenn_explorer/zenn_explorer.py
- arxiv_summarizer: nook/services/arxiv_summarizer/arxiv_summarizer.py
- fivechan_explorer: nook/services/fivechan_explorer/fivechan_explorer.py
- fourchan_explorer: nook/services/fourchan_explorer/fourchan_explorer.py
- github_trending: nook/services/github_trending/github_trending.py
- hacker_news: nook/services/hacker_news/hacker_news.py
- reddit_explorer: nook/services/reddit_explorer/reddit_explorer.py
