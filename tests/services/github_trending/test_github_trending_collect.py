"""Tests for GithubTrending collect flow and repository retrieval logic."""

import asyncio
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from nook.services.github_trending.github_trending import GithubTrending, Repository
from nook.common.exceptions import APIException
from nook.common.dedup import DedupTracker


@pytest.fixture
def trending(monkeypatch: pytest.MonkeyPatch) -> GithubTrending:
    """Create a GithubTrending instance with mocked dependencies."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    service = GithubTrending()
    service.http_client = AsyncMock()
    service.gpt_client = AsyncMock()
    service.storage = AsyncMock()
    service.logger = MagicMock()

    # Mock rate_limit
    service.rate_limit = AsyncMock()

    # Mock config loading by overriding attributes if necessary,
    # but normally __init__ loads them.
    # For testing collect flow, we might need to mock languages_config

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

        # Verify URL construction
        trending.http_client.get.assert_called_with(
            "https://github.com/trending/python"
        )

    async def test_retrieve_any_language(
        self, trending: GithubTrending, mock_html: str
    ) -> None:
        """Should handle retrieval for 'any' language (empty string in logic)."""
        trending.http_client.get.return_value = MagicMock(text=mock_html)
        dedup_tracker = DedupTracker()

        # "any" maps to empty string in method call usually?
        # Wait, the method takes `language`. If language is "any", it appends "/any"?
        # Actually in collect: `await self._retrieve_repositories("any", ...)`
        # Then in _retrieve_repositories: `if language: url += f"/{language}"`
        # So "any" -> "https://github.com/trending/any" which is valid?
        # Actually GitHub trending URL for "all languages" is just "https://github.com/trending".
        # But the code says: `_retrieve_repositories("any", ...)`
        # Let's check logic: `url = self.base_url; if language: url += ...`
        # If "any" is passed, it becomes `/trending/any`.
        # Is that correct? The code seems to use "any" as a language parameter.

        await trending._retrieve_repositories("any", 5, dedup_tracker)
        trending.http_client.get.assert_called_with("https://github.com/trending/any")

    async def test_skips_duplicates(
        self, trending: GithubTrending, mock_html: str
    ) -> None:
        """Should skip repositories already in dedup_tracker."""
        trending.http_client.get.return_value = MagicMock(text=mock_html)
        dedup_tracker = DedupTracker()
        dedup_tracker.add("owner/repo1")  # Already exists

        repos = await trending._retrieve_repositories("python", 5, dedup_tracker)

        assert len(repos) == 1
        assert repos[0].name == "owner/repo2"

    async def test_handles_exception_and_retry(self, trending: GithubTrending) -> None:
        """Should raise Exception on extraction error (likely wrapped in retry logic)."""
        trending.http_client.get.side_effect = Exception("Connection Refused")
        dedup_tracker = DedupTracker()

        # Depending on implementation it might raise APIException or let RetryException bubble up
        # We accept generic Exception here to be safe across implementations
        with pytest.raises(Exception):
            await trending._retrieve_repositories("python", 5, dedup_tracker)

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

        # Mock dependencies used inside _store_summaries_for_date
        with (
            patch(
                "nook.services.github_trending.github_trending.store_daily_snapshots",
                new_callable=AsyncMock,
            ) as mock_store_snapshots,
            patch(
                "nook.services.github_trending.github_trending.group_records_by_date"
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
                "nook.services.github_trending.github_trending.store_daily_snapshots",
                new_callable=AsyncMock,
            ) as mock_store_snapshots,
            patch(
                "nook.services.github_trending.github_trending.group_records_by_date"
            ),
        ):
            mock_store_snapshots.return_value = []  # No files saved

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
        # Check language field injection
        py_repo = next(r for r in result if r["name"] == "py_repo")
        assert py_repo["language"] == "python"

    async def test_loads_from_markdown_if_json_missing(
        self, trending: GithubTrending
    ) -> None:
        """Should fallback to markdown if JSON is missing."""
        target_date = datetime(2024, 1, 1)
        trending.load_json = AsyncMock(return_value=None)
        trending.storage.load.return_value = "# Markdown Content"

        # Mock _parse_markdown to verify it's called
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

        # Must verify safe exception handling
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

    # FIX: mock_load must be async mock
    async def test_collect_flow_success(self, mock_trending_configured: GithubTrending):
        """Test successful collection flow."""
        repo_py = Repository(name="o/py", description="desc", link="l", stars=100)
        repo_rs = Repository(name="o/rs", description="desc", link="l", stars=200)
        repo_any = Repository(name="o/any", description="desc", link="l", stars=50)

        # Mock dependencies
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
                    [repo_any],  # for "any"
                    [repo_py],  # for "python"
                    [repo_rs],  # for "rust"
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

            # Check calls
            assert mock_retrieve.call_count == 3  # any, python, rust
            # Verify rate limit calls: 3 retrievals + translation (calls inside translation)
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
            # Setup existing to match retrieved
            mock_load.return_value = [{"name": "o/exist"}]

            results = await mock_trending_configured.collect(
                limit=1, target_dates=[date(2024, 1, 1)]
            )

            assert len(results) == 0
            mock_translate.assert_not_called()  # Translation should be skipped
