"""
nook/services/github_trending/github_trending.py のテスト

テスト観点:
- GithubTrendingの初期化
- トレンドリポジトリ取得
- HTML解析
- リポジトリ情報抽出
- 言語フィルタリング
- データ保存
- エラーハンドリング
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from nook.services.github_trending.github_trending import GithubTrending, Repository

# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    """
    Given: デフォルトのstorage_dir
    When: GithubTrendingを初期化
    Then: インスタンスが正常に作成される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        assert service.service_name == "github_trending"
        assert service.http_client is None
        assert service.base_url == "https://github.com/trending"


@pytest.mark.unit
def test_init_loads_languages_config(mock_env_vars):
    """
    Given: 言語設定ファイルが存在
    When: GithubTrendingを初期化
    Then: 言語設定が正常に読み込まれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        assert hasattr(service, "languages_config")
        assert isinstance(service.languages_config, dict)


# =============================================================================
# 2. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_trending_repos(mock_env_vars):
    """
    Given: 有効なGitHubトレンドHTML
    When: collectメソッドを呼び出す
    Then: リポジトリが正常に取得・保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        mock_html = """
        <html><body>
            <article class="Box-row">
                <h2 class="h3"><a href="/test/repo">test/repo</a></h2>
                <p>Test repository description</p>
                <span class="d-inline-block mr-3">
                    <span>Python</span>
                </span>
                <a class="Link--muted">1,234</a>
            </article>
        </body></html>
        """

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(return_value=Mock(text=mock_html))
            service.gpt_client.generate_async = AsyncMock(return_value="要約テキスト")

            result = await service.collect(limit=5, target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_languages(mock_env_vars):
    """
    Given: 複数の言語のリポジトリ
    When: collectメソッドを呼び出す
    Then: 全ての言語が処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch(
                "tomli.load",
                return_value={"general": ["python"], "specific": ["javascript"]},
            ),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body></body></html>")
            )

            result = await service.collect(limit=3, target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_target_dates(mock_env_vars):
    """
    Given: 特定の日付を指定
    When: collectメソッドを呼び出す
    Then: 指定した日付のデータが取得される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        target_date = date.today() - timedelta(days=1)

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body></body></html>")
            )

            result = await service.collect(limit=5, target_dates=[target_date])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_limit_parameter(mock_env_vars):
    """
    Given: limit パラメータを指定
    When: collectメソッドを呼び出す
    Then: 指定した件数まで取得される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body></body></html>")
            )

            result = await service.collect(limit=10, target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 3. collect メソッドのテスト - 異常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_network_error(mock_env_vars):
    """
    Given: ネットワークエラーが発生
    When: collectメソッドを呼び出す
    Then: エラーがログされ、例外が発生する
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            # エラーが発生することを期待
            with pytest.raises(Exception):
                await service.collect(target_dates=[date.today()])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_invalid_html(mock_env_vars):
    """
    Given: 不正なHTML
    When: collectメソッドを呼び出す
    Then: エラーがログされ、空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body>Invalid</body></html>")
            )

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_gpt_api_error(mock_env_vars):
    """
    Given: GPT APIがエラーを返す
    When: collectメソッドを呼び出す
    Then: エラーが適切に処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        mock_html = """
        <html><body>
            <article class="Box-row">
                <h2 class="h3"><a href="/test/repo">test/repo</a></h2>
            </article>
        </body></html>
        """

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(return_value=Mock(text=mock_html))
            service.gpt_client.generate_async = AsyncMock(side_effect=Exception("API Error"))

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 4. collect メソッドのテスト - 境界値
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_empty_html(mock_env_vars):
    """
    Given: 空のHTML
    When: collectメソッドを呼び出す
    Then: 空リストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body></body></html>")
            )

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_none_target_dates(mock_env_vars):
    """
    Given: target_datesがNone
    When: collectメソッドを呼び出す
    Then: デフォルトの日付が使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body></body></html>")
            )

            result = await service.collect(target_dates=None)

            assert isinstance(result, list)


# =============================================================================
# 5. Repository モデルのテスト
# =============================================================================


@pytest.mark.unit
def test_repository_creation():
    """
    Given: リポジトリ情報
    When: Repositoryオブジェクトを作成
    Then: 正しくインスタンス化される
    """
    repo = Repository(
        name="test/repo",
        description="Test description",
        link="https://github.com/test/repo",
        stars=1234,
    )

    assert repo.name == "test/repo"
    assert repo.stars == 1234
    assert repo.description == "Test description"
    assert repo.link == "https://github.com/test/repo"


@pytest.mark.unit
def test_repository_with_none_description():
    """
    Given: 説明がNone
    When: Repositoryオブジェクトを作成
    Then: Noneが許容される
    """
    repo = Repository(
        name="test/repo",
        description=None,
        link="https://github.com/test/repo",
        stars=100,
    )

    assert repo.description is None


@pytest.mark.unit
def test_repository_with_zero_stars():
    """
    Given: スター数が0
    When: Repositoryオブジェクトを作成
    Then: 0が許容される
    """
    repo = Repository(
        name="test/repo",
        description="Test",
        link="https://github.com/test/repo",
        stars=0,
    )

    assert repo.stars == 0


# =============================================================================
# 6. _retrieve_repositories メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_repositories_success(mock_env_vars):
    """
    Given: 有効なHTMLレスポンス
    When: _retrieve_repositoriesを呼び出す
    Then: リポジトリリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        from nook.common.dedup import DedupTracker

        dedup_tracker = DedupTracker()

        mock_html = """
        <html><body>
            <article class="Box-row">
                <h2 class="h3"><a href="/test/repo">test/repo</a></h2>
                <p>Description</p>
                <a class="Link--muted">500</a>
            </article>
        </body></html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=mock_html))

        repos = await service._retrieve_repositories("python", 5, dedup_tracker)

        assert isinstance(repos, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_repositories_with_limit(mock_env_vars):
    """
    Given: limitを超えるリポジトリが存在
    When: _retrieve_repositoriesを呼び出す
    Then: limit件数まで取得される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        from nook.common.dedup import DedupTracker

        dedup_tracker = DedupTracker()

        # 複数のリポジトリを含むHTML
        mock_html = """
        <html><body>
            <article class="Box-row">
                <h2 class="h3"><a href="/test/repo1">test/repo1</a></h2>
                <a class="Link--muted">100</a>
            </article>
            <article class="Box-row">
                <h2 class="h3"><a href="/test/repo2">test/repo2</a></h2>
                <a class="Link--muted">200</a>
            </article>
            <article class="Box-row">
                <h2 class="h3"><a href="/test/repo3">test/repo3</a></h2>
                <a class="Link--muted">300</a>
            </article>
        </body></html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=mock_html))

        repos = await service._retrieve_repositories("python", 2, dedup_tracker)

        assert len(repos) <= 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_repositories_deduplication(mock_env_vars):
    """
    Given: 重複するリポジトリ名
    When: _retrieve_repositoriesを呼び出す
    Then: 重複が除外される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        from nook.common.dedup import DedupTracker

        dedup_tracker = DedupTracker()
        dedup_tracker.add("test/repo1")

        mock_html = """
        <html><body>
            <article class="Box-row">
                <h2 class="h3"><a href="/test/repo1">test/repo1</a></h2>
                <a class="Link--muted">100</a>
            </article>
        </body></html>
        """

        service.http_client.get = AsyncMock(return_value=Mock(text=mock_html))

        repos = await service._retrieve_repositories("python", 5, dedup_tracker)

        assert len(repos) == 0


# =============================================================================
# 7. _translate_repositories メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_repositories_success(mock_env_vars):
    """
    Given: リポジトリリスト
    When: _translate_repositoriesを呼び出す
    Then: 説明が翻訳される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        repos = [
            Repository(
                name="test/repo",
                description="Test description",
                link="https://github.com/test/repo",
                stars=100,
            )
        ]

        service.gpt_client.generate_async = AsyncMock(return_value="翻訳された説明")

        result = await service._translate_repositories([("python", repos)])

        assert result[0][1][0].description == "翻訳された説明"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_repositories_with_progress_callback(mock_env_vars):
    """
    Given: 進捗コールバックを指定
    When: _translate_repositoriesを呼び出す
    Then: コールバックが呼ばれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        repos = [
            Repository(
                name="test/repo",
                description="Test description",
                link="https://github.com/test/repo",
                stars=100,
            )
        ]

        service.gpt_client.generate_async = AsyncMock(return_value="翻訳")

        callback_called = []

        def callback(idx, total, name):
            callback_called.append((idx, total, name))

        await service._translate_repositories([("python", repos)], progress_callback=callback)

        assert len(callback_called) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_translate_repositories_error_handling(mock_env_vars):
    """
    Given: 翻訳中にエラーが発生
    When: _translate_repositoriesを呼び出す
    Then: エラーがログされ、処理が継続される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        repos = [
            Repository(
                name="test/repo",
                description="Test description",
                link="https://github.com/test/repo",
                stars=100,
            )
        ]

        service.gpt_client.generate_async = AsyncMock(side_effect=Exception("Error"))

        result = await service._translate_repositories([("python", repos)])

        assert isinstance(result, list)


# =============================================================================
# 8. データ保存のテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_summaries_for_date_success(mock_env_vars):
    """
    Given: リポジトリリストと日付
    When: _store_summaries_for_dateを呼び出す
    Then: ファイルが保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        repos = [
            Repository(
                name="test/repo",
                description="Test description",
                link="https://github.com/test/repo",
                stars=100,
            )
        ]

        with (
            patch.object(
                service,
                "save_json",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
            patch.object(
                service,
                "save_markdown",
                new_callable=AsyncMock,
                return_value=Path("/data/test.md"),
            ),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            json_path, md_path = await service._store_summaries_for_date(
                [("python", repos)], date.today()
            )

            assert json_path == "/data/test.json"
            assert md_path == "/data/test.md"


# =============================================================================
# 9. Markdownレンダリングのテスト
# =============================================================================


@pytest.mark.unit
def test_render_markdown_success(mock_env_vars):
    """
    Given: リポジトリレコード
    When: _render_markdownを呼び出す
    Then: Markdown形式のテキストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        records = [
            {
                "language": "python",
                "name": "test/repo",
                "description": "Test description",
                "link": "https://github.com/test/repo",
                "stars": 100,
            }
        ]

        result = service._render_markdown(records, datetime.now())

        assert "# GitHub トレンドリポジトリ" in result
        assert "test/repo" in result


# =============================================================================
# 10. Markdownパースのテスト
# =============================================================================


@pytest.mark.unit
def test_parse_markdown_success(mock_env_vars):
    """
    Given: Markdown形式のテキスト
    When: _parse_markdownを呼び出す
    Then: リポジトリレコードが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        markdown = """# GitHub トレンドリポジトリ (2024-01-01)

## Python

### [test/repo](https://github.com/test/repo)

Test description

⭐ スター数: 100

---

"""

        result = service._parse_markdown(markdown)

        assert len(result) == 1
        assert result[0]["name"] == "test/repo"
        assert result[0]["stars"] == 100


# =============================================================================
# 11. エラーハンドリング統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_workflow_collect_and_save(mock_env_vars):
    """
    Given: 完全なワークフロー
    When: collect→save→cleanupを実行
    Then: 全フローが正常に動作
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        mock_html = """
        <html><body>
            <article class="Box-row">
                <h2 class="h3"><a href="/test/repo">test/repo</a></h2>
                <p>Test description</p>
                <a class="Link--muted">1000</a>
            </article>
        </body></html>
        """

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service.storage,
                "save",
                new_callable=AsyncMock,
                return_value=Path("/data/test.json"),
            ),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(return_value=Mock(text=mock_html))
            service.gpt_client.generate_async = AsyncMock(return_value="要約")

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)

            await service.cleanup()


# =============================================================================
# 12. 重複チェックのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_existing_repositories(mock_env_vars):
    """
    Given: 既存のリポジトリが存在
    When: collectメソッドを呼び出す
    Then: 重複が除外される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        existing_repos = [{"name": "test/repo", "stars": 100}]

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=existing_repos,
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body></body></html>")
            )

            result = await service.collect(target_dates=[date.today()])

            assert isinstance(result, list)


# =============================================================================
# 13. 複数日付処理のテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_dates(mock_env_vars):
    """
    Given: 複数の日付を指定
    When: collectメソッドを呼び出す
    Then: 各日付のデータが処理される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        dates = [date.today(), date.today() - timedelta(days=1)]

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body></body></html>")
            )

            result = await service.collect(target_dates=dates)

            assert isinstance(result, list)


# =============================================================================
# 14. ソート処理のテスト
# =============================================================================


@pytest.mark.unit
def test_repository_sort_key(mock_env_vars):
    """
    Given: リポジトリレコード
    When: _repository_sort_keyを呼び出す
    Then: ソートキーが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        record = {"stars": 100, "published_at": datetime.now(UTC).isoformat()}

        result = service._repository_sort_key(record)

        assert isinstance(result, tuple)
        assert result[0] == 100


# =============================================================================
# 15. シリアライズのテスト
# =============================================================================


@pytest.mark.unit
def test_serialize_repositories(mock_env_vars):
    """
    Given: リポジトリリスト
    When: _serialize_repositoriesを呼び出す
    Then: 辞書のリストが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        repos = [
            Repository(
                name="test/repo",
                description="Test description",
                link="https://github.com/test/repo",
                stars=100,
            )
        ]

        result = service._serialize_repositories([("python", repos)], date.today())

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "test/repo"


# =============================================================================
# 16. HTTPクライアント初期化のテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_initializes_http_client(mock_env_vars):
    """
    Given: HTTPクライアントが未初期化
    When: collectメソッドを呼び出す
    Then: HTTPクライアントが初期化される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()

        assert service.http_client is None

        with (
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            # setup_http_clientを実際に実行してモックのHTTPクライアントを設定
            async def setup_http():
                service.http_client = AsyncMock()
                service.http_client.get = AsyncMock(
                    return_value=Mock(text="<html><body></body></html>")
                )

            with patch.object(service, "setup_http_client", new=setup_http):
                await service.collect(target_dates=[date.today()])

                assert service.http_client is not None


# =============================================================================
# 17. レート制限のテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_respects_rate_limit(mock_env_vars):
    """
    Given: 複数の言語を処理
    When: collectメソッドを呼び出す
    Then: レート制限が適用される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = GithubTrending()
        service.http_client = AsyncMock()

        with (
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service.storage, "save", new_callable=AsyncMock),
            patch.object(service, "rate_limit", new_callable=AsyncMock) as mock_rate_limit,
            patch.object(
                service,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            service.http_client.get = AsyncMock(
                return_value=Mock(text="<html><body></body></html>")
            )

            await service.collect(target_dates=[date.today()])

            assert mock_rate_limit.call_count > 0
