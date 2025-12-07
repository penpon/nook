# テストカバレッジ強化ストリーム（90%達成に向けて）

## 概要

このドキュメントは、現状のカバレッジ38%から目標の90%以上を達成するための追加タスクを定義します。

**前提:**
- 既存の Stream A〜E は実行済み
- 実装コードは一切編集せず、テストコードのみ追加

**現状と目標のギャップ:**

| レイヤー | 目標 | 現状 | 必要な改善 |
|---------|------|------|-----------|
| common | 95-100% | ~80% | +15-20% |
| API | 90-95% | ~85% | +5-10% |
| GPT/HTTP | 80-90% | 63-66% | +15-25% |
| services | 85-90% | ~25% | **+60-65%** |

---

## Stream F: 0%カバレッジ解消（最優先）

### 目的

テストが一切存在しないファイルを解消し、最低限のリグレッション検知を可能にする。

### 対象

- `nook/services/fivechan_explorer/fivechan_explorer.py` (510行, 0%)
- `nook/services/reddit_explorer/reddit_explorer.py` (293行, 0%)
- `nook/services/run_services_sync.py` (137行, 0%)
- `nook/services/run_services_test.py` (119行, 0%)
- `nook/api/run.py` (14行, 0%)

### 完了基準

- 各ファイルのカバレッジが 50% 以上になること
- 主要な public 関数/メソッドに対する正常系テストが存在すること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、現在 0% カバレッジのファイル群にテストを追加したいです。

対象:
- nook/services/fivechan_explorer/fivechan_explorer.py
- nook/services/reddit_explorer/reddit_explorer.py
- nook/services/run_services_sync.py
- nook/services/run_services_test.py
- nook/api/run.py

やってほしいこと:
1. 各ファイルの主要な public 関数/クラス/メソッドを洗い出してください。
2. 外部 API 呼び出しはすべてモックし、データ変換・フィルタリング・保存ロジックを重点的にテストしてください。
3. tests/ 以下に適切なテストファイルを作成し、各ファイルが 50% 以上のカバレッジになるようテストを実装してください。
4. 特に fivechan_explorer と reddit_explorer は行数が多いため、ヘルパー関数やデータ変換ロジックから優先してください。

ファイルごとに順番に進めてください。
```

---

## Stream G: common 未達モジュール強化

### 目的

common レイヤーで目標（95-100%）に未達のモジュールを強化する。

### 対象

- `nook/common/decorators.py` (48% → 95%)
- `nook/common/dedup.py` (20% → 95%)
- `nook/common/feed_utils.py` (70% → 95%)
- `nook/common/base_service.py` (69% → 95%)

### 完了基準

- 各ファイルのカバレッジが 95% 以上になること
- 全ての分岐パス（正常系・異常系・境界値）がテストされていること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、common レイヤーの未達モジュールを 95% 以上にしたいです。

対象と現状:
- nook/common/decorators.py (現状 48%)
- nook/common/dedup.py (現状 20%)
- nook/common/feed_utils.py (現状 70%)
- nook/common/base_service.py (現状 69%)

やってほしいこと:
1. 各モジュールの既存テストを確認し、カバーされていない行・分岐を特定してください。
2. decorators.py: リトライ、タイムアウト、キャッシュなどのデコレータの全分岐をテストしてください。
3. dedup.py: 重複検出ロジックの全パターン（完全一致、類似度、閾値境界）をテストしてください。
4. feed_utils.py: フィード処理ユーティリティの全関数をテストしてください。
5. base_service.py: BaseService の全メソッド（save_data, save_markdown, save_json, load_json, save_with_backup, rate_limit）を tmp_path を使ってテストしてください。

各モジュールについて、不足しているテストケースを特定してから実装に進んでください。
```

---

## Stream H: GPT/HTTP クライアント強化

### 目的

GPT/HTTP クライアントを目標（80-90%）に到達させる。

### 対象

- `nook/common/gpt_client.py` (63% → 85%)
- `nook/common/http_client.py` (66% → 85%)

### 完了基準

- 各ファイルのカバレッジが 85% 以上になること
- ネットワーク I/O は完全にモック化されていること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、GPT/HTTP クライアントのカバレッジを 85% 以上にしたいです。

対象と現状:
- nook/common/gpt_client.py (現状 63%)
- nook/common/http_client.py (現状 66%)

やってほしいこと:

【gpt_client.py】
1. 既存の tests/common/test_gpt_client_unit.py を確認し、カバーされていない行を特定してください。
2. 以下の未テスト領域を重点的にカバーしてください:
   - generate_content, chat, chat_with_search, send_message のメソッド
   - エラーハンドリングパス（APIException, RateLimitError など）
   - レスポンス解析ロジック
3. OpenAI SDK は一切呼び出さず、ダミーオブジェクトで完結させてください。

【http_client.py】
1. 既存の tests/common/test_http_client.py を確認し、カバーされていない行を特定してください。
2. 以下の未テスト分岐を重点的にカバーしてください:
   - HTTP/2 → HTTP/1.1 フォールバック（422, StreamError）
   - 403 エラー時の cloudscraper フォールバック
   - 各種エラーパス（タイムアウト、接続エラーなど）
3. httpx.MockTransport を使い、実ネットワークには接続しないでください。

まずカバレッジレポートで未カバー行を確認し、そこを埋めるテストを追加してください。
```

---

## Stream I: サービス基盤強化

### 目的

サービス層の基盤となるモジュールを強化し、個別サービステストの土台を固める。

### 対象

- `nook/services/base_feed_service.py` (58% → 85%)
- `nook/services/run_services.py` (33% → 85%)

### 完了基準

- 各ファイルのカバレッジが 85% 以上になること
- Runner ロジックと BaseFeedService の全メソッドがテストされていること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、サービス基盤レイヤーのカバレッジを 85% 以上にしたいです。

対象と現状:
- nook/services/base_feed_service.py (現状 58%)
- nook/services/run_services.py (現状 33%)

やってほしいこと:

【base_feed_service.py】
1. 既存の tests/services/test_base_feed_service.py を確認し、カバーされていない行を特定してください。
2. 以下を重点的にテストしてください:
   - _summarize_article の正常系・例外系
   - _fetch_articles, _filter_articles, _process_articles などのフロー
   - collect メソッドの全分岐
3. gpt_client と http_client はモックしてください。

【run_services.py】
1. 既存のテストを確認し、カバーされていない行を特定してください。
2. ServiceRunner の以下を重点的にテストしてください:
   - run_all, run_service メソッド
   - 各サービスへのパラメータ（limit, days, target_dates）の受け渡し
   - エラーハンドリング
3. 実サービスクラスはダミーに差し替えてテストしてください。

まずカバレッジレポートで未カバー行を確認し、そこを埋めるテストを追加してください。
```

---

## Stream J: 個別サービス強化（arxiv, hacker_news）

### 目的

代表的なサービスのカバレッジを強化する。

### 対象

- `nook/services/arxiv_summarizer/arxiv_summarizer.py` (31% → 85%)
- `nook/services/hacker_news/hacker_news.py` (29% → 85%)

### 完了基準

- 各ファイルのカバレッジが 85% 以上になること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、arxiv_summarizer と hacker_news のカバレッジを 85% 以上にしたいです。

対象と現状:
- nook/services/arxiv_summarizer/arxiv_summarizer.py (現状 31%)
- nook/services/hacker_news/hacker_news.py (現状 29%)

やってほしいこと:

【arxiv_summarizer】
1. 既存のテストを確認し、カバーされていない行を特定してください。
2. 以下を重点的にテストしてください:
   - ヘルパー関数（remove_tex_backticks, remove_outer_markdown_markers など）
   - _get_curated_paper_ids, _retrieve_paper_info, _summarize_paper_info
   - collect メソッドの全フロー
3. arxiv API と OpenAI はすべてモックしてください。

【hacker_news】
1. 既存のテストを確認し、カバーされていない行を特定してください。
2. 以下を重点的にテストしてください:
   - 記事フィルタリングロジック
   - スコア計算、ソート順
   - collect メソッドの全フロー
3. HTTP 呼び出しと OpenAI はすべてモックしてください。

まずカバレッジレポートで未カバー行を確認し、そこを埋めるテストを追加してください。
```

---

## Stream K: 個別サービス強化（tech_feed, business_feed, github_trending）

### 目的

フィード系サービスのカバレッジを強化する。

### 対象

- `nook/services/tech_feed/tech_feed.py` (39% → 85%)
- `nook/services/business_feed/business_feed.py` (39% → 85%)
- `nook/services/github_trending/github_trending.py` (42% → 85%)

### 完了基準

- 各ファイルのカバレッジが 85% 以上になること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、tech_feed, business_feed, github_trending のカバレッジを 85% 以上にしたいです。

対象と現状:
- nook/services/tech_feed/tech_feed.py (現状 39%)
- nook/services/business_feed/business_feed.py (現状 39%)
- nook/services/github_trending/github_trending.py (現状 42%)

やってほしいこと:

【共通アプローチ】
1. 各ファイルの既存テストを確認し、カバーされていない行を特定してください。
2. 以下を重点的にテストしてください:
   - フィード取得・パースロジック
   - 記事フィルタリング条件
   - スコア計算、ソート順
   - collect メソッドの全フロー
3. HTTP 呼び出しと OpenAI はすべてモックしてください。

【github_trending 固有】
- GitHub API のレスポンス構造をモックデータとして用意
- popularity_score 計算ロジックのテスト

1 ファイルずつ順番に進めてください。
```

---

## Stream L: 個別サービス強化（explorer 系）

### 目的

Explorer 系サービスのカバレッジを強化する。

### 対象

- `nook/services/zenn_explorer/zenn_explorer.py` (33% → 85%)
- `nook/services/qiita_explorer/qiita_explorer.py` (37% → 85%)
- `nook/services/note_explorer/note_explorer.py` (35% → 85%)
- `nook/services/fourchan_explorer/fourchan_explorer.py` (18% → 85%)

### 完了基準

- 各ファイルのカバレッジが 85% 以上になること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、Explorer 系サービスのカバレッジを 85% 以上にしたいです。

対象と現状:
- nook/services/zenn_explorer/zenn_explorer.py (現状 33%)
- nook/services/qiita_explorer/qiita_explorer.py (現状 37%)
- nook/services/note_explorer/note_explorer.py (現状 35%)
- nook/services/fourchan_explorer/fourchan_explorer.py (現状 18%)

やってほしいこと:

【共通アプローチ】
1. 各ファイルの既存テストを確認し、カバーされていない行を特定してください。
2. 以下を重点的にテストしてください:
   - スクレイピング/API レスポンスのパースロジック
   - 記事フィルタリング・スコアリング
   - collect メソッドの全フロー
3. HTTP 呼び出しと OpenAI はすべてモックしてください。

【fourchan_explorer 固有】
- 特にカバレッジが低いため、ヘルパー関数とデータ変換ロジックから優先

1 ファイルずつ順番に進めてください。
```

---

## Stream M: API レイヤー仕上げ

### 目的

API レイヤーを目標（90-95%）に到達させる。

### 対象

- `nook/api/routers/content.py` (77% → 90%)
- `nook/api/routers/weather.py` (38% → 90%)

### 完了基準

- 各ファイルのカバレッジが 90% 以上になること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、API レイヤーのカバレッジを 90% 以上にしたいです。

対象と現状:
- nook/api/routers/content.py (現状 77%)
- nook/api/routers/weather.py (現状 38%)

やってほしいこと:

【content.py】
1. 既存の tests/api/test_content_router.py を確認し、カバーされていない行を特定してください。
2. 以下を重点的にテストしてください:
   - 各 source パラメータのパス（hacker-news, arxiv, all など）
   - エラーケース（invalid source, ファイル不存在など）
3. LocalStorage は tmp_path ベースにモックしてください。

【weather.py】
1. tests/api/test_weather_router.py を新規作成してください。
2. 以下を重点的にテストしてください:
   - 正常系レスポンス
   - 外部 API エラー時のフォールバック
3. 天気 API 呼び出しはモックしてください。

まずカバレッジレポートで未カバー行を確認し、そこを埋めるテストを追加してください。
```

---

## Stream N: common レイヤー仕上げ

### 目的

common レイヤーの残り未達モジュールを目標（95%）に到達させる。

### 対象

- `nook/common/rate_limiter.py` (74% → 95%)
- `nook/common/storage.py` (88% → 95%)
- `nook/common/logging_utils.py` (88% → 95%)
- `nook/common/async_utils.py` (93% → 95%)

### 完了基準

- 各ファイルのカバレッジが 95% 以上になること

### プロンプト

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。

この前提で、common レイヤーの残り未達モジュールを 95% 以上にしたいです。

対象と現状:
- nook/common/rate_limiter.py (現状 74%)
- nook/common/storage.py (現状 88%)
- nook/common/logging_utils.py (現状 88%)
- nook/common/async_utils.py (現状 93%)

やってほしいこと:
1. 各ファイルの既存テストを確認し、カバーされていない行を特定してください。
2. 未カバー行に対するテストケースを追加してください。
3. 特に以下に注意してください:
   - rate_limiter: 待機ロジック、境界値
   - storage: エラーハンドリングパス
   - logging_utils: 各ログレベル、フォーマット
   - async_utils: エラー時の挙動

まずカバレッジレポートで未カバー行を確認し、そこを埋めるテストを追加してください。
```

---

## 実行順序と推定工数

| 順序 | Stream | 優先度 | 推定工数 | 累積目標カバレッジ |
|------|--------|--------|---------|------------------|
| 1 | **F** | 最優先 | 大 | 45% |
| 2 | **G** | 高 | 中 | 55% |
| 3 | **H** | 高 | 中 | 60% |
| 4 | **I** | 高 | 中 | 65% |
| 5 | **J** | 中 | 中 | 72% |
| 6 | **K** | 中 | 中 | 78% |
| 7 | **L** | 中 | 大 | 85% |
| 8 | **M** | 中 | 小 | 88% |
| 9 | **N** | 低 | 小 | **90%+** |

---

## 完了確認コマンド

各 Stream 完了時に以下を実行してカバレッジを確認:

```bash
uv run pytest -n auto --cov=nook --cov-report=term-missing
```

特定レイヤーのみ確認:

```bash
# common レイヤー
uv run pytest -n auto --cov=nook/common --cov-report=term-missing tests/common

# services レイヤー
uv run pytest -n auto --cov=nook/services --cov-report=term-missing tests/services

# API レイヤー
uv run pytest -n auto --cov=nook/api --cov-report=term-missing tests/api
```
