"""Tests for GithubTrending collect flow and repository retrieval logic."""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.core.errors.exceptions import RetryException
from nook.core.utils.dedup import DedupTracker
from nook.services.analyzers.github_trending.github_trending import (
    GithubTrending,
    Repository,
)


@pytest.fixture
def trending(monkeypatch: pytest.MonkeyPatch) -> GithubTrending:
    """Create a GithubTrending instance with mocked dependencies."""
    # モック化された依存関係を持つGithubTrendingインスタンスを作成
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    service = GithubTrending()
    service.http_client = AsyncMock()
    service.gpt_client = AsyncMock()
    service.storage = AsyncMock()
    service.logger = MagicMock()

    # rate_limitをモック化
    service.rate_limit = AsyncMock()

    # 必要に応じて設定の属性をオーバーライド
    # 通常は__init__で読み込まれる
    # collectフローをテストする場合、languages_configをモック化する必要がある場合がある

    return service


@pytest.mark.asyncio
class TestRetrieveRepositories:
    """Tests for _retrieve_repositories method."""

    @pytest.fixture
    def mock_html(self) -> str:
        return """
        <html>
            <body>
                <article class="Box-row">
                    <h2><a href="/owner/repo1">owner / repo1</a></h2>
                    <p>Description 1</p>
                    <div class="f6 color-fg-muted mt-2">
                        <a class="Link--muted" href="/owner/repo1/stargazers">1,000</a>
                    </div>
                </article>
                <article class="Box-row">
                    <h2><a href="/owner/repo2">owner / repo2</a></h2>
                    <!-- No description -->
                    <div class="f6 color-fg-muted mt-2">
                        <a class="Link--muted" href="/owner/repo2/stargazers">500</a>
                    </div>
                </article>
            </body>
        </html>
        """

    async def test_retrieve_success(
        self, trending: GithubTrending, mock_html: str
    ) -> None:
        """Should retrieve and parse repositories successfully."""
        trending.http_client.get.return_value = MagicMock(text=mock_html)
        dedup_tracker = DedupTracker()

        repos = await trending._retrieve_repositories("python", 5, dedup_tracker)

        assert len(repos) == 2

        assert repos[0].name == "owner/repo1"
        assert repos[0].link == "https://github.com/owner/repo1"
        assert repos[0].description == "Description 1"
        assert repos[0].stars == 1000

        assert repos[1].name == "owner/repo2"
        assert repos[1].description is None
        assert repos[1].stars == 500

        # URL構築の検証
        trending.http_client.get.assert_called_with(
            "https://github.com/trending/python"
        )

    async def test_retrieve_any_language(
        self, trending: GithubTrending, mock_html: str
    ) -> None:
        """Should handle retrieval for 'any' language (empty string in logic)."""
        trending.http_client.get.return_value = MagicMock(text=mock_html)
        dedup_tracker = DedupTracker()

        # "any"の場合、正しいURLが呼ばれるか確認

        await trending._retrieve_repositories("any", 5, dedup_tracker)
        trending.http_client.get.assert_called_with("https://github.com/trending")

    async def test_skips_duplicates(
        self, trending: GithubTrending, mock_html: str
    ) -> None:
        """Should skip repositories already in dedup_tracker."""
        trending.http_client.get.return_value = MagicMock(text=mock_html)
        dedup_tracker = DedupTracker()
        dedup_tracker.add("owner/repo1")  # 既に存在

        repos = await trending._retrieve_repositories("python", 5, dedup_tracker)

        assert len(repos) == 1
        assert repos[0].name == "owner/repo2"

    async def test_handles_exception_and_retry(self, trending: GithubTrending) -> None:
        """Should raise RetryException on extraction error."""
        trending.http_client.get.side_effect = Exception("Connection Refused")
        dedup_tracker = DedupTracker()

        with pytest.raises(RetryException) as exc_info:
            await trending._retrieve_repositories("python", 5, dedup_tracker)

        assert "Failed to retrieve repositories" in str(exc_info.value)

    async def test_handles_invalid_star_count(self, trending: GithubTrending) -> None:
        """Should handle invalid star count gracefully (default to 0)."""
        mock_html = """
        <html>
            <article class="Box-row">
                <h2><a href="/o/r">o/r</a></h2>
                <div class="f6 color-fg-muted mt-2">
                    <a class="Link--muted">invalid</a>
                </div>
            </article>
        </html>
        """
        trending.http_client.get.return_value = MagicMock(text=mock_html)
        dedup_tracker = DedupTracker()

        repos = await trending._retrieve_repositories("python", 5, dedup_tracker)

        assert len(repos) == 1
        assert repos[0].stars == 0


@pytest.mark.asyncio
class TestStoreSummaries:
    """Tests for _store_summaries_for_date method."""

    async def test_store_success(self, trending: GithubTrending) -> None:
        """Should process records and call store_daily_snapshots."""
        repo = Repository(name="o/r", description="d", link="l", stars=10)
        repos_by_lang = [("python", [repo])]
        target_date = date(2024, 1, 1)

        # _store_summaries_for_date内で使用される依存関係をモック化
        with (
            patch(
                "nook.services.analyzers.github_trending.github_trending.store_daily_snapshots",
                new_callable=AsyncMock,
            ) as mock_store_snapshots,
            patch(
                "nook.services.analyzers.github_trending.github_trending.group_records_by_date"
            ) as mock_group,
        ):
            mock_group.return_value = {target_date: [{"name": "o/r"}]}
            mock_store_snapshots.return_value = [("json", "md")]

            json_path, md_path = await trending._store_summaries_for_date(
                repos_by_lang, target_date
            )

            assert json_path == "json"
            assert md_path == "md"
            mock_store_snapshots.assert_awaited_once()

    async def test_raises_if_no_repos(self, trending: GithubTrending) -> None:
        """Should raise ValueError if empty list passed."""
        with pytest.raises(ValueError, match="保存するリポジトリがありません"):
            await trending._store_summaries_for_date([], date(2024, 1, 1))

    async def test_raises_if_save_failed(self, trending: GithubTrending) -> None:
        """Should raise ValueError if no files saved."""
        repo = Repository(name="o/r", description="d", link="l", stars=10)
        repos_by_lang = [("python", [repo])]

        with (
            patch(
                "nook.services.analyzers.github_trending.github_trending.store_daily_snapshots",
                new_callable=AsyncMock,
            ) as mock_store_snapshots,
            patch(
                "nook.services.analyzers.github_trending.github_trending.group_records_by_date"
            ),
        ):
            mock_store_snapshots.return_value = []  # ファイルが保存されなかった

            with pytest.raises(ValueError, match="保存に失敗しました"):
                await trending._store_summaries_for_date(
                    repos_by_lang, date(2024, 1, 1)
                )


@pytest.mark.asyncio
class TestLoadExistingRepositoriesByDate:
    """Tests for _load_existing_repositories_by_date method."""

    async def test_loads_from_json_list(self, trending: GithubTrending) -> None:
        """Should return list from JSON if it's already a list."""
        target_date = datetime(2024, 1, 1)
        expected = [{"name": "repo1"}]

        trending.load_json = AsyncMock(return_value=expected)

        result = await trending._load_existing_repositories_by_date(target_date)
        assert result == expected
        trending.load_json.assert_called_with("2024-01-01.json")

    async def test_loads_from_json_dict_and_flattens(
        self, trending: GithubTrending
    ) -> None:
        """Should flatten dict structure from JSON."""
        target_date = datetime(2024, 1, 1)
        json_data = {"python": [{"name": "py_repo"}], "rust": [{"name": "rs_repo"}]}

        trending.load_json = AsyncMock(return_value=json_data)

        result = await trending._load_existing_repositories_by_date(target_date)

        assert len(result) == 2
        names = {r["name"] for r in result}
        assert "py_repo" in names
        assert "rs_repo" in names
        # languageフィールドの注入を確認
        py_repo = next(r for r in result if r["name"] == "py_repo")
        assert py_repo["language"] == "python"

    async def test_loads_from_markdown_if_json_missing(
        self, trending: GithubTrending
    ) -> None:
        """Should fallback to markdown if JSON is missing."""
        target_date = datetime(2024, 1, 1)
        trending.load_json = AsyncMock(return_value=None)
        trending.storage.load.return_value = "# Markdown Content"

        # _parse_markdownが呼ばれることを検証するためモック化
        with patch.object(
            trending, "_parse_markdown", return_value=[{"name": "md_repo"}]
        ) as mock_parse:
            result = await trending._load_existing_repositories_by_date(target_date)

            assert result == [{"name": "md_repo"}]
            trending.storage.load.assert_called_with("2024-01-01.md")
            mock_parse.assert_called_with("# Markdown Content")

    async def test_returns_empty_if_nothing_found(
        self, trending: GithubTrending
    ) -> None:
        """Should return empty list if neither JSON nor MD exists."""
        target_date = datetime(2024, 1, 1)
        trending.load_json = AsyncMock(return_value=None)
        trending.storage.load.return_value = None

        result = await trending._load_existing_repositories_by_date(target_date)
        assert result == []


@pytest.mark.asyncio
class TestTranslateRepositories:
    """Tests for _translate_repositories method."""

    async def test_translate_success(self, trending: GithubTrending) -> None:
        """Should translate descriptions using GPT."""
        repo = Repository(name="r", description="Original", link="l", stars=1)
        repos_by_lang = [("python", [repo])]

        trending.gpt_client.generate_async.return_value = "翻訳済み概要"

        result = await trending._translate_repositories(repos_by_lang)

        assert result[0][1][0].description == "翻訳済み概要"
        trending.gpt_client.generate_async.assert_called_once()
        trending.rate_limit.assert_awaited()

    async def test_handles_translation_error(self, trending: GithubTrending) -> None:
        """Should keep original description on translation error."""
        repo = Repository(name="r", description="Original", link="l", stars=1)
        repos_by_lang = [("python", [repo])]

        trending.gpt_client.generate_async.side_effect = Exception("GPT Error")

        # 安全な例外処理を検証
        result = await trending._translate_repositories(repos_by_lang)

        assert result[0][1][0].description == "Original"
        trending.logger.error.assert_called()


@pytest.mark.asyncio
class TestCollect:
    """Tests for collect method."""

    @pytest.fixture
    def mock_trending_configured(self, trending: GithubTrending) -> GithubTrending:
        trending.languages_config = {"general": ["python"], "specific": ["rust"]}
        return trending

    # 修正: mock_loadはasync mockである必要がある
    async def test_collect_flow_success(self, mock_trending_configured: GithubTrending):
        """Test successful collection flow."""
        repo_py = Repository(name="o/py", description="desc", link="l", stars=100)
        repo_rs = Repository(name="o/rs", description="desc", link="l", stars=200)
        repo_any = Repository(name="o/any", description="desc", link="l", stars=50)

        # 依存関係をモック化
        with (
            patch.object(
                mock_trending_configured,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(
                mock_trending_configured,
                "_retrieve_repositories",
                side_effect=[
                    [repo_any],  # "any"用
                    [repo_py],  # "python"用
                    [repo_rs],  # "rust"用
                ],
            ) as mock_retrieve,
            patch.object(
                mock_trending_configured,
                "_translate_repositories",
                new_callable=AsyncMock,
            ) as mock_translate,
            patch.object(
                mock_trending_configured,
                "_store_summaries_for_date",
                new_callable=AsyncMock,
            ) as mock_store,
        ):
            mock_load.return_value = []
            mock_translate.return_value = [
                ("any", [repo_any]),
                ("python", [repo_py]),
                ("rust", [repo_rs]),
            ]
            mock_store.return_value = ("path/json", "path/md")

            results = await mock_trending_configured.collect(
                limit=1, target_dates=[date(2024, 1, 1)]
            )

            assert len(results) == 1
            assert results[0] == ("path/json", "path/md")

            # 呼び出し確認
            assert mock_retrieve.call_count == 3  # any, python, rustの3回
            # レート制限の呼び出しを確認: 3回の取得 + 翻訳
            assert mock_trending_configured.rate_limit.call_count >= 3

    async def test_no_new_repositories(self, mock_trending_configured: GithubTrending):
        """Test flow when no new repositories are found."""
        repo_existing = Repository(
            name="o/exist", description="desc", link="l", stars=100
        )

        with (
            patch.object(
                mock_trending_configured,
                "_load_existing_repositories_by_date",
                new_callable=AsyncMock,
            ) as mock_load,
            patch.object(
                mock_trending_configured,
                "_retrieve_repositories",
                return_value=[repo_existing],
            ),
            patch.object(
                mock_trending_configured,
                "_translate_repositories",
                new_callable=AsyncMock,
            ) as mock_translate,
        ):
            # 取得したものと一致するように既存のものをセットアップ
            mock_load.return_value = [{"name": "o/exist"}]

            results = await mock_trending_configured.collect(
                limit=1, target_dates=[date(2024, 1, 1)]
            )

            assert len(results) == 0
            mock_translate.assert_not_called()  # 翻訳はスキップされるべき
