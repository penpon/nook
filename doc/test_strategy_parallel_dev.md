# Nook テスト戦略 & 並列開発ガイド（git worktree + Windsurf プロンプト集）

## 1. 目的と前提条件

このドキュメントは、今後予定されている大規模リファクタリングに備えて、

- 実装コードを一切変更せずに
- pytest ベースの自動テストを段階的に整備し
- 並列開発（すべて git worktree 前提）で効率よくカバレッジ 90%以上（目標 95%）

を達成するためのガイドです。

前提となるルール:

- **テスト実行:** `uv run pytest -n auto`（pytest-xdist 並列）
- **Python コマンド:** すべて `uv run ...` 経由で実行
- **OpenAI 実 API:** テストからは一切叩かない（GPTClient / openai はモック・スタブで扱う）
- **git 運用:** 並列開発時はいずれも **git worktree** を利用する
- **実装コード:** 既存の `nook/` 配下の Python ファイルは編集しない（テストコードのみ追加）

---

## 2. テスト戦略の概要

### 2.1 レイヤー別のカバレッジ目標

- **common レイヤー (`nook/common/*`)**
  - 目標: 95〜100%
  - ロジック中心でテストしやすい。ここでカバレッジを稼ぐ。

- **API レイヤー (`nook/api/*`)**
  - 目標: 90〜95%
  - FastAPI ルーター、ミドルウェア、例外ハンドラを `TestClient` でカバー。

- **サービス / Runner レイヤー (`nook/services/*`)**
  - 目標: 85〜90%
  - 外部 API / I/O はモックしつつ、「どのデータをどう変換・保存するか」をテスト。

- **GPT / HTTP クライアント (`gpt_client.py`, `http_client.py`)**
  - 目標: 80〜90%
  - ネットワーク呼び出しはすべてモック。トークン数・料金計算・レスポンス解析などローカルロジックを重点的にカバー。

全体として **90%以上必達 / 95% をストレッチゴール**とします。

### 2.2 tests/ ディレクトリ構成案

今後の追加テストは、概ね次のような構成で整理します。

```text
tests/
  api/
    test_main.py
    test_error_handler.py
    test_chat_router.py
    test_content_router.py
  common/
    test_daily_snapshot.py        # 既存
    test_daily_merge.py
    test_date_utils.py
    test_async_utils.py
    test_storage.py
    test_http_client.py
    test_gpt_client_unit.py
    test_exceptions.py
    test_error_metrics.py
    test_rate_limiter.py
    test_logging_utils.py
  services/
    test_base_service.py
    test_run_services.py
    test_run_services_test.py
    arxiv_summarizer/
      test_arxiv_helpers.py
      test_arxiv_collect_flow.py
    github_trending/
      test_github_trending.py
    ... 各サービスごとに 1 ファイル程度
  integration/
    test_content_pipeline_stubbed.py  # 任意: Runner 〜 content API までの通しテスト
```

- `common` と `api` を厚めにテストし、`services` で補完する構成です。
- すべてのテストで **OpenAI や外部 HTTP はモック / スタブ** することを原則にします。

---

## 3. git worktree 前提の並列開発ガイド

### 3.1 基本方針

- メインの開発ブランチ（例: `develop`）から、テスト追加用の feature ブランチを切り、
  **各ブランチを git worktree としてチェックアウト**して並列開発します。
- 原則として **1 worktree = 1 テストストリーム** とし、衝突を最小化します。

### 3.2 典型的な worktree 運用例

例として、次の 5 ストリームに分割するとします（詳細は後述の §4）。

- Stream A: `tests-common`（`nook/common/*` のテスト）
- Stream B: `tests-api`（`nook/api/*` のテスト）
- Stream C: `tests-gpt-http`（`gpt_client.py` と `http_client.py`）
- Stream D: `tests-services-core`（BaseService / Runner）
- Stream E: `tests-services-domain`（各サービス固有のロジック）

ブランチ・worktree 命名の一例:

```bash
# ベース: develop ブランチ
# worktree ルートを ./feature/ 以下にまとめる例

# Stream A (common)
git worktree add feature/tests-common develop
cd feature/tests-common
git switch -c feature/tests-common

# Stream B (api)
git worktree add feature/tests-api develop
cd feature/tests-api
git switch -c feature/tests-api

# ... 以下同様にストリームごとに worktree + ブランチを作成
```

運用上のポイント:

- **既存 worktree の削除は慎重に**行う（他の作業中ブランチと衝突する恐れがある）。
- 1つの worktree では **1つのタスクに集中** し、別タスクに着手するときは新しい worktree を作る方針にすると安全です。
- テストコード変更のみとはいえ、PR はストリームごとに分けてレビューしやすくします。

### 3.3 テスト実行の基本ルール

各 worktree 内でのテスト実行例:

```bash
# 全テストを並列実行
uv run pytest -n auto

# カバレッジを確認
uv run pytest -n auto --cov=nook --cov-report=term-missing

# 対象ディレクトリを絞る（例: common のみ）
uv run pytest -n auto tests/common
```

---

## 4. テストストリーム定義と担当範囲

ここでは、並列開発しやすいようにテストタスクを 5 つのストリームに分割します。

### Stream A: common 基盤テスト

- 対象
  - `nook/common/daily_snapshot.py`
  - `nook/common/daily_merge.py`
  - `nook/common/date_utils.py`
  - `nook/common/async_utils.py`
  - `nook/common/storage.py`
  - `nook/common/exceptions.py`, `service_errors.py`, `error_metrics.py`, `rate_limiter.py`, `logging_utils.py` など
- 目的
  - ロジック中心のユーティリティ層で、95%以上のカバレッジを確保し、他レイヤーの安心感を高める。

### Stream B: API レイヤーテスト

- 対象
  - `nook/api/main.py`
  - `nook/api/middleware/error_handler.py`
  - `nook/api/exceptions.py`
  - `nook/api/routers/chat.py`
  - `nook/api/routers/content.py`
- 目的
  - FastAPI のエンドポイントとエラーハンドリングの挙動を固定し、
    リファクタリング時に API コントラクトが崩れないようにする。

### Stream C: GPT / HTTP クライアント

- 対象
  - `nook/common/gpt_client.py`
  - `nook/common/http_client.py`
- 目的
  - OpenAI や HTTP 通信の実呼び出しはモックしつつ、
    トークン数計算・料金計算・レスポンス解析・HTTP フォールバック等のロジックをテストする。

### Stream D: サービス基盤 (BaseService / Runner)

- 対象
  - `nook/common/base_service.py`
  - `nook/services/base_feed_service.py`
  - `nook/services/run_services.py`
  - `nook/services/run_services_test.py`
- 目的
  - すべてのサービスに共通する挙動（ストレージ操作、rate_limit、Runner ロジック）を固め、
    個別サービス側のテスト負荷を下げる。

### Stream E: 各サービス固有ロジック

- 対象
  - `nook/services/arxiv_summarizer/*`
  - `nook/services/github_trending/*`
  - `nook/services/tech_feed/*`
  - その他、`business_feed`, `zenn_explorer`, `qiita_explorer`, `note_explorer`, `reddit_explorer`, `fourchan_explorer`, `fivechan_explorer` など
- 目的
  - 代表的なサービスから順に、ドメインロジック（フィルタ条件、スコア計算、タイトル生成など）をテスト。
  - 外部 API 呼び出し部はモックし、データ変換ロジックに集中する。

---

## 5. Windsurf（Cascade）向けおすすめプロンプト集

各ストリームを Windsurf（このエージェント）で実装してもらう際の「プロンプト雛形」を示します。

### 5.1 共通の前置きテンプレート

どのタスクでも、最初に次のような前置きを付けると意図が伝わりやすくなります。

```text
このリポジトリでは大規模リファクタリングに備えてテストコードを整備中です。

前提と制約:
- 実装コード（nook/配下の .py）は一切編集しないでください。
- OpenAI や外部 HTTP API を実際に叩くテストは書かないでください。必ずモック・スタブで対応してください。
- pytest は uv 経由で `uv run pytest -n auto` を使います。
- 並列開発時はいずれのタスクも git worktree 上のブランチで作業します。

この前提で、[ここにやりたいことを書く] を進めてください。
```

以下では、各ストリームごとの「やりたいこと」の具体的な書き方を示します。

---

### 5.2 Stream A 向けプロンプト例（common 基盤）

#### 5.2.1 common 全体のテスト強化

```text
上記の前提に加えて、common レイヤーのテストを集中的に整備したいです。

対象:
- nook/common/daily_snapshot.py
- nook/common/daily_merge.py
- nook/common/date_utils.py
- nook/common/async_utils.py
- nook/common/storage.py
- nook/common/exceptions.py, service_errors.py, error_metrics.py, rate_limiter.py, logging_utils.py

やってほしいこと:
1. 各モジュールの責務と主要な public 関数/クラスを洗い出してください。
2. 既存の tests/common/test_daily_snapshot.py を参考に、tests/common/ 以下に追加すべきテストファイルとテストケース一覧を提案してください。
3. そのうえで、優先度の高い関数から順に pytest テストコードを実装してください。
4. I/O を伴う箇所（LocalStorage など）は tmp_path を使ってテストし、グローバルな data ディレクトリは汚さないようにしてください。

まずは計画とテストケースの一覧を出してから、個別テストの実装に進んでください。
```

#### 5.2.2 単一モジュールに絞った詳細依頼（例: async_utils）

```text
common レイヤーのうち、nook/common/async_utils.py だけを対象にテストを追加したいです。

- gather_with_errors, run_with_semaphore, batch_process, AsyncTaskManager の全ての分岐パスをカバーできるような pytest テストを tests/common/test_async_utils.py に追加してください。
- 実装コードは変更禁止です。
- テストは async 関数に対して pytest.mark.asyncio を使ってください。

テストケース設計 → 実装 → 想定される失敗パターンの洗い出し、の順で進めてください。
```

---

### 5.3 Stream B 向けプロンプト例（API レイヤー）

#### 5.3.1 API 全体のテスト整備

```text
FastAPI ベースの API レイヤー (`nook/api/*`) のテストを追加したいです。

対象:
- nook/api/main.py
- nook/api/middleware/error_handler.py
- nook/api/exceptions.py
- nook/api/routers/chat.py
- nook/api/routers/content.py

制約:
- 実装コードは一切編集せず、tests/api/ 以下にテストコードを追加してください。
- Chat API では GPTClient をモックし、OpenAI 実 API には絶対に接続しないでください。
- Content API では LocalStorage を tmp_path ベースに差し替えて、実際の data ディレクトリを汚さないようにしてください。

やってほしいこと:
1. FastAPI の TestClient を使って、各エンドポイントの正常系と代表的な異常系をテストする計画を立ててください。
2. tests/api/test_main.py, test_error_handler.py, test_chat_router.py, test_content_router.py の構成案と中身を順に提案・実装してください。
3. error_handler_middleware と handle_exception の全ての例外分岐をテストで通るようにしてください。
```

#### 5.3.2 Chat ルーターだけを集中的にテスト

```text
nook/api/routers/chat.py のみを対象に、Chat API のテストを追加したいです。

- tests/api/test_chat_router.py を新規作成し、以下のパスをテストしてください:
  - OPENAI_API_KEY が未設定の場合に、ダミーメッセージで応答するパス
  - OPENAI_API_KEY が設定されている場合に、GPTClient をモックして正しい system プロンプトと chat_history が渡されること
  - GPTClient 側で例外が発生したときに HTTP 500 が返ること

pytest と monkeypatch を使ったモック戦略を明示しながら実装してください。
```

---

### 5.4 Stream C 向けプロンプト例（GPT / HTTP クライアント）

#### 5.4.1 gpt_client.py のユニットテスト

```text
nook/common/gpt_client.py を対象に、OpenAI 実 API に触れないユニットテストを追加したいです。

- tests/common/test_gpt_client_unit.py を新規作成し、次をカバーしてください:
  - _count_tokens, _calculate_cost, _messages_to_responses_input, _supports_max_completion_tokens, _is_gpt5_model, _get_calling_service などの純粋ロジック部分
  - generate_content, chat, chat_with_search, send_message について、GPTClient.client をダミーオブジェクトに差し替えた上で、渡されるパラメータとレスポンス処理のロジックを確認
- OpenAI SDK 自体は一切呼び出さないようにしてください（モックで完結させる）。

内部ロジックのテストに集中し、ネットワーク I/O は完全にスタブ化する方針でお願いします。
```

#### 5.4.2 http_client.AsyncHTTPClient のテスト

```text
nook/common/http_client.py を対象に、AsyncHTTPClient の挙動をテストしたいです。

- tests/common/test_http_client.py を追加し、MockTransport を使って httpx の通信を完全にモックしてください。
- GET/POST の正常系に加えて、
  - HTTP/2 から HTTP/1.1 へのフォールバック（422, StreamError）
  - 403 エラー時の cloudscraper フォールバック
  - APIException に変換されるエラーパス
 など、主な分岐がすべてテストで通るようにしてください。

実ネットワークには絶対に接続しないでください。
```

---

### 5.5 Stream D 向けプロンプト例（サービス基盤）

#### 5.5.1 BaseService / BaseFeedService / Runner のテスト

```text
サービス基盤レイヤーのテストを追加したいです。

対象:
- nook/common/base_service.py
- nook/services/base_feed_service.py
- nook/services/run_services.py
- nook/services/run_services_test.py

要望:
1. BaseService を継承したダミーサービスクラスをテスト内で定義し、save_data/save_markdown/save_json/load_json/save_with_backup/rate_limit の挙動を tests/services/test_base_service.py にまとめてください。
2. BaseFeedService._summarize_article について、gpt_client をモックして正常系・例外系ともに article.summary が期待どおりになることを tests/services/test_base_feed_service.py として実装してください。
3. ServiceRunner / ServiceRunnerTest では、実サービスクラスをダミーに差し替え、各サービス名に対して想定どおりの limit / days / target_dates が渡されることを tests/services/test_run_services*.py で確認してください。

実装コードは変更せず、テストコードのみで完結するようにしてください。
```

---

### 5.6 Stream E 向けプロンプト例（各サービス固有ロジック）

#### 5.6.1 arxiv_summarizer の代表テスト

```text
nook/services/arxiv_summarizer/arxiv_summarizer.py を対象に、代表的なロジック部分のテストを追加したいです。

- tests/services/arxiv_summarizer/test_arxiv_helpers.py を新規追加し、
  - remove_tex_backticks
  - remove_outer_markdown_markers
  - remove_outer_singlequotes
  - _is_valid_body_line
 などのヘルパー関数を入力パターン別にテストしてください。

- tests/services/arxiv_summarizer/test_arxiv_collect_flow.py を新規追加し、
  - _get_curated_paper_ids, _retrieve_paper_info, _summarize_paper_info, _store_summaries, _save_processed_ids_by_date をモックして、collect の全体フローが正しく動くことだけを検証してください。

外部の arxiv API や HTTP 通信、OpenAI は一切呼び出さないでください。
```

#### 5.6.2 その他サービス（github_trending など）のテスト雛形

```text
nook/services/github_trending 以下のサービスコードを対象に、
外部 API をモックした上で、記事フィルタリングや Markdown 生成ロジックをテストしたいです。

- tests/services/github_trending/test_github_trending.py を追加し、
  - フィードから取得したダミーデータをもとに、どのレコードが採用されるか
  - popularity_score やソート順
  - daily_snapshot への渡し方
 などを重点的にテストしてください。

テストでは HTTP や OpenAI をすべてスタブ化し、純粋にデータ変換部分のロジックを確認する方針でお願いします。
```

---

## 6. タスク粒度ガイドラインと小さめプロンプト例

タスクを細かく分割しすぎるとコンテキストウィンドウを圧迫し、大きすぎると 1 回の対話で扱う情報量が増えて品質が落ちやすくなります。
ここでは、各 Stream ごとに「ほどよい」タスク粒度と、それに対応するコンパクトなプロンプト例を示します。

### 6.1 共通ルール

- **1タスクあたり対象モジュールは最大 1〜2 個** を目安にする。
- 各タスクでは「テストケース設計 → 実装」の両方を依頼するが、
  - まずテストケース一覧を出してから、
  - 優先度の高いものから実装してもらう。
- プロンプトでは **すでに存在する tests/ ファイル** や **このドキュメント** への参照は最小限にし、
  現時点で対象とするモジュール名・関数名を明示する。

特に迷ったら、以下の粒度テンプレートをそのまま使ってください。

### 6.2 Stream A（common）のおすすめタスク粒度

#### A1: daily_snapshot / daily_merge だけを対象にする

```text
上記の共通前提に加えて、次のモジュールだけを対象にテストを追加してください。
対象:
- nook/common/daily_snapshot.py
- nook/common/daily_merge.py

やってほしいこと:
1. 各モジュールの主要な関数（group_records_by_date, store_daily_snapshots, merge_records など）を整理してください。
2. tests/common/ 以下に必要なテストケース一覧を箇条書きで提案してください。
3. 優先度の高いケースから順に pytest テストコードを実装してください。

I/O は tmp_path を使い、グローバルな data ディレクトリは変更しないでください。
```

#### A2: date_utils / async_utils に絞ったテスト

```text
common レイヤーのうち、次の 2 モジュールだけを対象にテストを追加したいです。

対象:
- nook/common/date_utils.py
- nook/common/async_utils.py

やってほしいこと:
1. 日付・タイムゾーン変換系の関数と、並行実行ユーティリティ（gather_with_errors, run_with_semaphore など）のテストケースを設計してください。
2. tests/common/test_date_utils.py と tests/common/test_async_utils.py を作成し、代表的な正常系と異常系・境界値をカバーするテストを実装してください。
3. Async な関数は pytest.mark.asyncio を使ってテストしてください。
```

#### A3: storage / 例外・メトリクス系のテスト

```text
次のモジュールに対してテストを追加したいです。

対象:
- nook/common/storage.py
- nook/common/exceptions.py
- nook/common/service_errors.py
- nook/common/error_metrics.py
- nook/common/rate_limiter.py
- nook/common/logging_utils.py

やってほしいこと:
1. LocalStorage のファイル操作まわりを tmp_path を使ってテストしてください。
2. 各種例外クラスとエラーメトリクス／レートリミッタ／ログユーティリティについて、落ちないこと・基本的なフィールド値が正しいことを確認するテストを追加してください。
3. tests/common/ 配下にテストファイルを作成し、1 テストファイルあたり 1〜2 モジュールを担当する形で整理してください。
```

### 6.3 Stream B（API）のおすすめタスク粒度

#### B1: main.py / exceptions.py の最小テスト

```text
API レイヤーのうち、次の 2 モジュールだけを対象にテストを追加したいです。

対象:
- nook/api/main.py
- nook/api/exceptions.py

やってほしいこと:
1. FastAPI TestClient を使って `/` エンドポイントのレスポンス内容をテストしてください。
2. NookHTTPException およびそのサブクラス（NotFoundError など）のステータスコード・エラーフィールドが期待どおりであることを確認するユニットテストを tests/api/test_main.py と tests/api/test_exceptions.py に追加してください。
```

#### B2: error_handler ミドルウェア単体

```text
nook/api/middleware/error_handler.py のみを対象に、error_handler_middleware と handle_exception のテストを追加したいです。

- RequestValidationError, StarletteHTTPException, APIException など主要な例外タイプごとに、
  返される JSON の error.type / status_code / error_id が期待どおりかを tests/api/test_error_handler.py に実装してください。
- 実装コードは変更せず、最小限の Request オブジェクトとダミーの call_next を使ってください。
```

#### B3: chat ルーターのみ

```text
nook/api/routers/chat.py だけを対象にテストを追加します。

- OPENAI_API_KEY 未設定時のダミーレスポンスパス
- OPENAI_API_KEY 設定時に、GPTClient をモックして正しい system プロンプトと chat_history が渡されること
- GPTClient 側の例外時に HTTP 500 が返ること

を tests/api/test_chat_router.py にテストとして実装してください。
```

#### B4: content ルーターのみ

```text
nook/api/routers/content.py のみを対象にテストを追加します。

- invalid source で 404 になるパス
- hacker-news / arxiv / all の代表的なパスについて、LocalStorage を tmp_path ベースのインスタンスにモックした上で、戻り値の items 構造を確認するテスト
を tests/api/test_content_router.py に実装してください。
```

### 6.4 Stream C（GPT / HTTP）のおすすめタスク粒度

#### C1: GPTClient の純粋ロジックのみ

```text
nook/common/gpt_client.py のうち、外部 API に依存しない純粋ロジック部分だけを対象にテストを追加したいです。

対象関数の例:
- _count_tokens
- _calculate_cost
- _messages_to_responses_input
- _supports_max_completion_tokens
- _is_gpt5_model
- _get_calling_service

tests/common/test_gpt_client_unit.py に、これらの関数の入力パターンと期待結果を網羅するテストを追加してください。
```

#### C2: GPTClient の generate/chat 系をダミークライアントでテスト

```text
GPTClient.client をダミーオブジェクトに差し替えたうえで、
- generate_content
- chat
- chat_with_search
- send_message

のメソッドが正しいパラメータを組み立て、ダミーレスポンスから期待どおりのテキストを取り出せるかを tests/common/test_gpt_client_unit.py に追加でテストしてください。
OpenAI 実 API には絶対に接続しないようにしてください。
```

#### C3: AsyncHTTPClient の代表的な分岐

```text
nook/common/http_client.py を対象に、AsyncHTTPClient の主な分岐パスだけをテストしたいです。

- GET/POST の正常系
- HTTP/2 → HTTP/1.1 フォールバック（422 / StreamError）
- 403 エラー時の cloudscraper フォールバック（モックベース）
- APIException に変換されるエラーパス

を httpx.MockTransport などを用いて、tests/common/test_http_client.py に実装してください。
実ネットワークには接続しないでください。
```

### 6.5 Stream D（サービス基盤）のおすすめタスク粒度

#### D1: BaseService だけ

```text
nook/common/base_service.py を対象に、DummyService をテスト内で定義して挙動を確認したいです。

- save_data/save_markdown/save_json/load_json/save_with_backup/rate_limit

これらのメソッドが、LocalStorage を通じて正しく動作することを tmp_path を使って tests/services/test_base_service.py にテストとして実装してください。
```

#### D2: BaseFeedService のみ

```text
nook/services/base_feed_service.py を対象に、_summarize_article だけをテストしたいです。

- gpt_client.generate_content をモックして、summary が正常に設定されるケース
- 例外発生時にロギングされつつ、article.summary にエラーメッセージが入るケース

を tests/services/test_base_feed_service.py に実装してください。
```

#### D3: Runner 類（run_services / run_services_test）

```text
nook/services/run_services.py と run_services_test.py を対象に、ServiceRunner / ServiceRunnerTest の挙動をテストしたいです。

- service_classes をダミーサービスクラスに差し替え、collect に渡されるパラメータ（limit, days, target_dates）が期待どおりか確認するテストを tests/services/test_run_services.py / test_run_services_test.py に追加してください。

外部 API や実際のサービスクラスには触れず、ダミーサービスのみを使ってください。
```

### 6.6 Stream E（各サービス）のおすすめタスク粒度

#### E1: arxiv_summarizer のヘルパー関数だけ

```text
nook/services/arxiv_summarizer/arxiv_summarizer.py のうち、ヘルパー関数だけを対象にテストしたいです。

対象:
- remove_tex_backticks
- remove_outer_markdown_markers
- remove_outer_singlequotes
- _is_valid_body_line

tests/services/arxiv_summarizer/test_arxiv_helpers.py に、これらの関数の入力パターンと期待結果をカバーするテストを追加してください。
```

#### E2: arxiv_summarizer.collect のフローのみ

```text
arxiv_summarizer の collect メソッドのフローだけをテストしたいです。

- _get_curated_paper_ids
- _retrieve_paper_info
- _summarize_paper_info
- _store_summaries
- _save_processed_ids_by_date

をモックしたうえで、collect が対象日付リストをもとに正しくフローを進め、saved_files の戻り値構造が期待どおりになることだけを tests/services/arxiv_summarizer/test_arxiv_collect_flow.py に実装してください。
外部の arxiv API や OpenAI には触れないでください。
```

#### E3: 任意の 1 サービス（例: github_trending）のロジック

```text
nook/services/github_trending 以下のコードを対象に、外部 API をモックして記事フィルタリングと Markdown 生成ロジックをテストしたいです。

- フィードから取得したダミーデータをもとに、どのレコードが採用されるか
- popularity_score やソート順
- daily_snapshot への渡し方

を tests/services/github_trending/test_github_trending.py に実装してください。
HTTP や OpenAI への実アクセスはすべてスタブ化してください。
```

---

## 7. 実行と運用のメモ

- 日常的な実行コマンドの例:
  - `uv run pytest -n auto`
  - `uv run pytest -n auto tests/common`
  - `uv run pytest -n auto --cov=nook --cov-report=term-missing`
- git worktree で作業中のディレクトリが増えすぎた場合は、
  - 手動で整理する前に、どの worktree がまだ使用中かをチーム内で確認すること
- 何か大きな設計変更を伴うテスト追加やリファクタリング案を検討する場合は、
  - Serena（sanity_check）などに相談してから実装に入ると安全です。

以上が、現時点でのテスト戦略・worktree 前提の並列開発ガイド・Windsurf プロンプト集のまとめです。将来的な仕様変更やサービス追加にあわせて、このドキュメントを更新してください。
