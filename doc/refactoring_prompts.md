# 大規模リファクタリング プロンプト集

## 概要

このドキュメントは、Nook プロジェクトのフル版リファクタリングを段階的に実施するためのプロンプト集です。
本リファクタリングは、**developブランチ** 上で段階的に実行します。

**目標:**
- `nook/common/` → `nook/core/` へ再編成（サブパッケージ化）
- `nook/services/` を domain ごとに分類（explorers/feeds/analyzers）
- 後方互換性を維持しながら段階的移行

**前提:**
- 作業は全て `develop` ブランチで行います。
- 各フェーズ完了時にテスト全パスを確認してください。

## Set 1: Core Refactoring (Phase A - E)

**Branch:** `develop`

このセットでは、`nook/common` から `nook/core` への構造変更とファイル移動を一気通貫で行います。
外部インターフェース（importパス）の互換性を維持することが最重要です。

### プロンプト: Core層リファクタリングの実行

```text
現在、develop ブランチで作業中と認識してください。
このフェーズでは、nook/common から nook/core への移行（Phase A〜E）を一括して行います。

前提と制約:
- テストカバレッジ 93% を維持すること
- 既存の import パス（nook.common.xxx）が引き続き動作すること（互換性レイヤーの作成）
- 実装コードの機能的変更は行わない（構造変更のみ）
- **重要:** `nook/core/` 以下の新規ファイル内では、**絶対に `nook/common` からの import を行わないでください**（循環参照によりプロセスがクラッシュする危険性が高いため）。必要なユーティリティは `nook/core` 内のものを使用してください。

以下の手順でタスクを実行してください。ステップごとに確認は不要です。一気に進めてください。

### Step 1: 互換性レイヤー設計とCore構造作成 (Phase A, B)
1. `doc/refactoring_compatibility_layer.md` を参照し、設計を理解する。
2. `nook/core/` ディレクトリとサブパッケージ（clients, utils, storage, errors, logging）を作成する。
3. 各ディレクトリに空の `__init__.py` を作成する。

### Step 2: モジュール移動 (Phase C, D)
以下の配置ルールに従って `git mv` を実行し、各ファイルの相対importを修正してください。

- **logging/**: logging.py, logging_utils.py
- **clients/**: gpt_client.py, http_client.py, rate_limiter.py
- **utils/**: async_utils.py, date_utils.py, decorators.py, dedup.py
- **storage/**: storage.py, daily_merge.py, daily_snapshot.py
- **errors/**: exceptions.py, service_errors.py, error_metrics.py
- **root(nook/core)**: config.py (common/config.pyから移動)

### Step 3: Services基盤の予備移動 (Phase Eの一部)
以下のファイルは services 層に属するため、一時的な配置または services/base への先行移動を行います。
- nook/common/base_service.py → nook/services/base/base_service.py (ディレクトリ作成含む)
- nook/common/feed_utils.py → nook/services/base/feed_utils.py

### Step 4: 互換性レイヤーの実装 (Phase E)
1. 各新サブパッケージの `__init__.py` でシンボルを適切に export する。
2. `nook/common/__init__.py` を編集し、旧パスからの import が新パスへ転送されるように re-export を実装する。（※ `git mv` でフォルダが消えている・`__init__.py` が移動されている場合は、`nook/common/` ディレクトリを再作成し、新規に `__init__.py` を作成してください）
3. `nook/core/__init__.py` を整備する。

### Step 5: テスト実行と検証
1. `tests/common/` 内のテストを実行し、パスすることを確認する。
2. `grep "from nook.common" nook/` で内部利用箇所を確認し、可能な範囲で `nook.core` に置換する（必須ではないが推奨）。

完了後、変更内容のサマリーを報告してください。
```

---

## Set 2: Services Base Refactoring (Phase F)

**Branch:** `develop`

※ Set 1 がマージされた後に実行してください。

### プロンプト: Services基盤の整理

```text
現在、develop ブランチで作業中と認識してください。
Set 1 (Core Refactoring) が完了し、`nook/core` が存在している状態です。

目標:
Services層の基盤（runner, base）を明確に分離・整理します。

実行手順:

1. **runner パッケージ作成**
   - `nook/services/runner/` ディレクトリを作成。
   - `nook/services/run_services.py` → `nook/services/runner/run_services.py` へ移動。
   - `nook/services/runner/__init__.py` を作成。

2. **base パッケージ確認**
   - `nook/services/base/` に `base_service.py` と `feed_utils.py` が存在することを確認。
   - `nook/services/base_feed_service.py` → `nook/services/base/base_feed_service.py` へ移動。
   - `nook/services/base/__init__.py` を整備。

3. **Import修正 & 互換性**
   - `nook.services.run_services` 等の旧パス利用箇所を修正、または `nook/services/__init__.py` で re-export して互換性を維持する。

4. **検証**
   - `uv run pytest -n auto tests/services/test_base*.py tests/services/test_run_services*.py` を実行。
```

---

## Set 3: Services Domains Refactoring (Phase G)

**Branch:** `develop`

※ Set 2 がマージされた後に実行してください。

### プロンプト: サービスのドメイン分類

```text
現在、develop ブランチで作業中と認識してください。

目標:
フラットな `nook/services/xxx_explorer` 等の構成を、ドメイン別（explorers, feeds, analyzers）に再編します。

実行手順:

1. **ディレクトリ構造作成**
   以下の親ディレクトリと `__init__.py` を作成してください。
   - `nook/services/explorers/`
   - `nook/services/feeds/`
   - `nook/services/analyzers/`

2. **サービス移動**
   以下のように移動し、ディレクトリ名からサフィックス（_explorer等）を削除してシンプルにしてください。

   **Explorers:**
   - `fivechan_explorer` → `explorers/fivechan` (ファイルは `fivechan_explorer.py` のまま移動)
   - `reddit_explorer` → `explorers/reddit` (ファイルは `reddit_explorer.py` のまま移動)
   - `note_explorer` → `explorers/note`
   - `qiita_explorer` → `explorers/qiita`
   - `zenn_explorer` → `explorers/zenn`
   - `fourchan_explorer` → `explorers/fourchan`

   **Feeds:**
   - `business_feed` → `feeds/business`
   - `tech_feed` → `feeds/tech`
   - `hacker_news` → `feeds/hacker_news`

   **Analyzers:**
   - `arxiv_summarizer` → `analyzers/arxiv`
   - `github_trending` → `analyzers/github_trending`

3. **Import修正 (実装 & テスト)**
   - 移動した各ファイル内の相対 import を修正してください。
   - `run_services.py` 内でのサービス呼び出しパスを修正してください。
   - **重要:** `tests/` 以下の全てのテストコードについても、移動したサービスへの import パスを検索置換で修正してください。
     - 例: `from nook.services.reddit_explorer` → `from nook.services.explorers.reddit`
     - 例: `nook.services.reddit_explorer.RedditExplorer` → `nook.services.explorers.reddit.reddit_explorer.RedditExplorer`
   - **注意:** `nook/api/` (Routers等) も忘れずに検索・置換対象に含めてください。API層が古い `nook.services` パスを参照している可能性があります。

4. **検証**
   `uv run pytest -n auto tests/services/` を実行し、全サービスのテストがパスすることを確認してください。
   ※この段階ではテストファイルの移動は行いません。
```

---

## Set 4: Services Tests Refactoring (Phase H)

**Branch:** `develop`

※ Set 3 がマージされた後に実行してください。

### プロンプト: Servicesテストの再編

```text
現在、develop ブランチで作業中と認識してください。

目標:
実装コード（Set 3で再編済み）に合わせて、`tests/services/` 以下の構造を同期させます。

実行手順:

1. **テストディレクトリ作成**
   実装側と同様の構造を `tests/services/` 下に作成してください。
   - `tests/services/explorers/`
   - `tests/services/feeds/`
   - `tests/services/analyzers/`
   - `tests/services/base/`
   - `tests/services/runner/`

2. **テストファイル移動**
   `tests/services/` 直下のテストファイルを、対応するサブディレクトリに移動してください。
   例: `test_reddit_explorer.py` → `tests/services/explorers/test_reddit.py` (ファイル名も整理推奨、あるいはそのまま移動)

3. **Import修正**
   テストコード内の `from nook.services.reddit_explorer` といった古い import を、`from nook.services.explorers.reddit` のような新パスに完全に更新してください。

4. **検証**
   `uv run pytest -n auto tests/services/` で全テストがパスすることを確認。
```

---

## Set 5: Final Cleanup (Phase I)

**Branch:** `develop`

※ 全ての実装とテスト再編が完了した後に実行してください。

### プロンプト: 最終クリーンアップ

```text
現在、develop ブランチで作業中と認識してください。

目標:
リファクタリングの仕上げとして、旧互換性レイヤーの削除（可能な場合）または整理、そしてプロジェクト全体の整合性確認を行います。

実行手順:

1. **Importの一斉更新**
   プロジェクト全体（`nook/` および `tests/`）を対象に、旧パス（`nook.common` や `nook.services.xxx_explorer`）を使用している箇所を検索し、全て新パス（`nook.core` 等）に置換してください。
   
   ```bash
   grep -r "nook.common" nook/ tests/ scripts/
   ```
   ※ `scripts/` ディレクトリや `Dockerfile`, `pyproject.toml` など、コード以外の設定ファイル内にも古い記述（例: `nook.services.run_services` の直接指定など）が残っていないか確認してください。

2. **互換性レイヤーの最小化**
   `nook/common/__init__.py` などに残っている互換性定義について、外部ライブラリとして利用されていない限り、削除または Deprecation Warning の強化を行ってください。
   空になった `nook/common` ディレクトリがあれば削除を検討してください（`__init__.py` のみ残す運用も可）。

3. **最終検証**
   - 全テスト実行: `uv run pytest -n auto`
   - カバレッジ確認: `uv run pytest -n auto --cov=nook --cov-report=term-missing`
   - Lintチェック: `uv run ruff check .`

4. **READMEなどの更新**
   ディレクトリ構造の変更に合わせて、開発者向けドキュメントがあれば更新してください。
```


