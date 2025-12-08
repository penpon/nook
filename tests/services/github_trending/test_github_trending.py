"""Tests for github_trending service logic.

This module tests the pure logic functions in github_trending.py:
- Repository dataclass
- _repository_sort_key
- _render_markdown
- _parse_markdown
- _serialize_repositories
"""

from datetime import date, datetime, timezone

import pytest

from nook.services.github_trending.github_trending import GithubTrending, Repository


@pytest.fixture
def trending(monkeypatch: pytest.MonkeyPatch) -> GithubTrending:
    """
    Create a GithubTrending instance for testing.

    Given: Environment variable OPENAI_API_KEY is set to a dummy value.
    When: GithubTrending is instantiated.
    Then: A valid trending instance is returned.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
    return GithubTrending()


class TestRepositoryDataclass:
    """Tests for Repository dataclass."""

    def test_repository_creation(self) -> None:
        """
        Given: Valid repository information.
        When: Repository is created.
        Then: All fields are correctly set.
        """
        # 前提 / When
        repo = Repository(
            name="owner/repo-name",
            description="A test repository",
            link="https://github.com/owner/repo-name",
            stars=1000,
        )

        # 確認
        assert repo.name == "owner/repo-name"
        assert repo.description == "A test repository"
        assert repo.link == "https://github.com/owner/repo-name"
        assert repo.stars == 1000

    def test_repository_with_none_description(self) -> None:
        """
        Given: Repository with no description.
        When: Repository is created with description=None.
        Then: Description is None.
        """
        # 前提 / When
        repo = Repository(
            name="owner/repo-name",
            description=None,
            link="https://github.com/owner/repo-name",
            stars=500,
        )

        # 確認
        assert repo.description is None

    def test_repository_with_zero_stars(self) -> None:
        """
        Given: Repository with zero stars.
        When: Repository is created with stars=0.
        Then: Stars is 0.
        """
        # 前提 / When
        repo = Repository(
            name="owner/new-repo",
            description="Brand new repository",
            link="https://github.com/owner/new-repo",
            stars=0,
        )

        # 確認
        assert repo.stars == 0


class TestRepositorySortKey:
    """Tests for GithubTrending._repository_sort_key method."""

    def test_sort_key_returns_stars_and_published(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: A repository record with stars and published_at.
        When: _repository_sort_key is called.
        Then: A tuple of (stars, published_at) is returned.
        """
        # 前提
        record = {
            "name": "owner/repo",
            "stars": 1000,
            "published_at": "2024-01-15T00:00:00+00:00",
        }

        # 操作
        result = trending._repository_sort_key(record)

        # 確認
        assert result[0] == 1000
        assert result[1] == datetime(2024, 1, 15, tzinfo=timezone.utc)

    def test_sort_key_handles_missing_stars(self, trending: GithubTrending) -> None:
        """
        Given: A repository record without stars.
        When: _repository_sort_key is called.
        Then: Stars defaults to 0.
        """
        # 前提
        record = {
            "name": "owner/repo",
            "published_at": "2024-01-15T00:00:00+00:00",
        }

        # 操作
        result = trending._repository_sort_key(record)

        # 確認
        assert result[0] == 0

    def test_sort_key_handles_none_stars(self, trending: GithubTrending) -> None:
        """
        Given: A repository record with stars=None.
        When: _repository_sort_key is called.
        Then: Stars defaults to 0.
        """
        # 前提
        record = {
            "name": "owner/repo",
            "stars": None,
            "published_at": "2024-01-15T00:00:00+00:00",
        }

        # 操作
        result = trending._repository_sort_key(record)

        # 確認
        assert result[0] == 0

    def test_sort_key_handles_missing_published_at(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: A repository record without published_at.
        When: _repository_sort_key is called.
        Then: published_at defaults to datetime.min.
        """
        # 前提
        record = {
            "name": "owner/repo",
            "stars": 500,
        }

        # 操作
        result = trending._repository_sort_key(record)

        # 確認
        assert result[1] == datetime.min.replace(tzinfo=timezone.utc)

    def test_sort_key_handles_invalid_published_at(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: A repository record with invalid published_at format.
        When: _repository_sort_key is called.
        Then: published_at defaults to datetime.min.
        """
        # 前提
        record = {
            "name": "owner/repo",
            "stars": 500,
            "published_at": "invalid-date",
        }

        # 操作
        result = trending._repository_sort_key(record)

        # 確認
        assert result[1] == datetime.min.replace(tzinfo=timezone.utc)

    def test_sort_key_orders_multiple_repositories(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Multiple repository records with various stars/published_at.
        When: Records are sorted using _repository_sort_key.
        Then: Records are ordered by stars descending then published_at descending.
        """
        # 前提
        now = datetime(2024, 1, 15, tzinfo=timezone.utc)
        later = datetime(2024, 1, 16, tzinfo=timezone.utc)
        records = [
            {
                "name": "owner/repo-low-stars",
                "stars": 50,
                "published_at": now.isoformat(),
            },
            {
                "name": "owner/repo-high-stars-old",
                "stars": 200,
                "published_at": now.isoformat(),
            },
            {
                "name": "owner/repo-high-stars-new",
                "stars": 200,
                "published_at": later.isoformat(),
            },
        ]

        # 操作
        sorted_records = sorted(
            records,
            key=trending._repository_sort_key,
            reverse=True,
        )

        # 確認
        assert [record["name"] for record in sorted_records] == [
            "owner/repo-high-stars-new",
            "owner/repo-high-stars-old",
            "owner/repo-low-stars",
        ]

    def test_sort_key_with_equal_stars_compares_published_at(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Records with identical stars but different published_at values.
        When: Sorting by _repository_sort_key.
        Then: Newer published_at ranks ahead of older ones.
        """
        # 前提
        now = datetime(2024, 1, 15, tzinfo=timezone.utc)
        later = datetime(2024, 1, 17, tzinfo=timezone.utc)
        records = [
            {"stars": 300, "published_at": later.isoformat(), "name": "newer"},
            {"stars": 300, "published_at": now.isoformat(), "name": "older"},
        ]

        # 操作
        sorted_records = sorted(
            records,
            key=trending._repository_sort_key,
            reverse=True,
        )

        # 確認
        assert [record["name"] for record in sorted_records] == ["newer", "older"]

    def test_sort_key_with_different_stars_prioritizes_stars(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Records with different stars counts.
        When: Sorting by _repository_sort_key.
        Then: Higher stars rank ahead regardless of published_at.
        """
        # 前提
        older = datetime(2024, 1, 10, tzinfo=timezone.utc)
        newer = datetime(2024, 1, 20, tzinfo=timezone.utc)
        records = [
            {"stars": 100, "published_at": newer.isoformat(), "name": "few-stars"},
            {"stars": 500, "published_at": older.isoformat(), "name": "many-stars"},
        ]

        # 操作
        sorted_records = sorted(
            records,
            key=trending._repository_sort_key,
            reverse=True,
        )

        # 確認
        assert [record["name"] for record in sorted_records] == [
            "many-stars",
            "few-stars",
        ]


class TestRenderMarkdown:
    """Tests for GithubTrending._render_markdown method."""

    def test_render_markdown_basic(self, trending: GithubTrending) -> None:
        """
        Given: A list of repository records.
        When: _render_markdown is called.
        Then: Properly formatted markdown is returned.
        """
        # 前提
        records = [
            {
                "language": "python",
                "name": "owner/python-repo",
                "description": "A Python repository",
                "link": "https://github.com/owner/python-repo",
                "stars": 1000,
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        # 操作
        result = trending._render_markdown(records, today)

        # 確認
        assert "# GitHub トレンドリポジトリ (2024-01-15)" in result
        assert "## Python" in result
        assert "### [owner/python-repo](https://github.com/owner/python-repo)" in result
        assert "A Python repository" in result
        assert "⭐ スター数: 1000" in result

    def test_render_markdown_multiple_languages(self, trending: GithubTrending) -> None:
        """
        Given: Records from multiple languages.
        When: _render_markdown is called.
        Then: Each language has its own section.
        """
        # 前提
        records = [
            {
                "language": "python",
                "name": "owner/python-repo",
                "description": "Python repo",
                "link": "https://github.com/owner/python-repo",
                "stars": 1000,
            },
            {
                "language": "javascript",
                "name": "owner/js-repo",
                "description": "JavaScript repo",
                "link": "https://github.com/owner/js-repo",
                "stars": 2000,
            },
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        # 操作
        result = trending._render_markdown(records, today)

        # 確認
        assert "## Python" in result
        assert "## Javascript" in result

    def test_render_markdown_all_language_display(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Records with language='all'.
        When: _render_markdown is called.
        Then: Language is displayed as 'すべての言語'.
        """
        # 前提
        records = [
            {
                "language": "all",
                "name": "owner/repo",
                "description": "A repository",
                "link": "https://github.com/owner/repo",
                "stars": 500,
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        # 操作
        result = trending._render_markdown(records, today)

        # 確認
        assert "## すべての言語" in result

    def test_render_markdown_no_description(self, trending: GithubTrending) -> None:
        """
        Given: A record without description.
        When: _render_markdown is called.
        Then: No description line is added.
        """
        # 前提
        records = [
            {
                "language": "python",
                "name": "owner/repo",
                "description": None,
                "link": "https://github.com/owner/repo",
                "stars": 100,
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        # 操作
        result = trending._render_markdown(records, today)

        # 確認
        assert "### [owner/repo]" in result
        assert "⭐ スター数: 100" in result

    def test_render_markdown_empty_records_returns_header_only(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: No records.
        When: _render_markdown is called.
        Then: Only the header is returned.
        """
        # 前提
        records: list[dict[str, object]] = []
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        # 操作
        result = trending._render_markdown(records, today)

        # 確認
        assert "# GitHub トレンドリポジトリ (2024-01-15)" in result
        assert "##" not in result  # 言語セクションなし

    def test_render_markdown_missing_name_field_raises_key_error(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Record missing the 'name' field.
        When: _render_markdown is called.
        Then: KeyError is raised when accessing repo['name'].
        """
        # 前提
        records = [
            {
                "language": "python",
                "description": "Missing name",
                "link": "https://github.com/owner/repo",
                "stars": 10,
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        # 操作 / 確認
        with pytest.raises(KeyError, match="name"):
            trending._render_markdown(records, today)

    def test_render_markdown_missing_link_field_raises_key_error(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Record missing the 'link' field.
        When: _render_markdown is called.
        Then: KeyError is raised.
        """
        records = [
            {
                "language": "python",
                "name": "owner/repo",
                "description": "Missing link",
                "stars": 10,
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        with pytest.raises(KeyError, match="link"):
            trending._render_markdown(records, today)

    def test_render_markdown_missing_stars_field_raises_key_error(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Record missing the 'stars' field.
        When: _render_markdown is called.
        Then: KeyError is raised.
        """
        records = [
            {
                "language": "python",
                "name": "owner/repo",
                "description": "Missing stars",
                "link": "https://github.com/owner/repo",
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        with pytest.raises(KeyError, match="stars"):
            trending._render_markdown(records, today)

    def test_render_markdown_string_stars_raises_type_error(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Record with string stars (invalid type).
        When: _render_markdown is called.
        Then: TypeError is raised.
        """
        records = [
            {
                "language": "python",
                "name": "owner/repo",
                "description": "String stars type",
                "link": "https://github.com/owner/repo",
                "stars": "1000",
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        with pytest.raises(TypeError, match="must be numeric"):
            trending._render_markdown(records, today)

    def test_render_markdown_language_none_raises_value_error(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Record with language=None.
        When: _render_markdown is called.
        Then: ValueError is raised for missing language.
        """
        records = [
            {
                "language": None,
                "name": "owner/repo",
                "description": "Language none",
                "link": "https://github.com/owner/repo",
                "stars": 100,
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="must not be None"):
            trending._render_markdown(records, today)

    def test_render_markdown_language_non_string_raises_type_error(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Record with non-string language value.
        When: _render_markdown is called.
        Then: TypeError is raised.
        """
        records = [
            {
                "language": 123,
                "name": "owner/repo",
                "description": "Language not string",
                "link": "https://github.com/owner/repo",
                "stars": 100,
            }
        ]
        today = datetime(2024, 1, 15, tzinfo=timezone.utc)

        with pytest.raises(TypeError, match="must be a string"):
            trending._render_markdown(records, today)


class TestParseMarkdown:
    """Tests for GithubTrending._parse_markdown method."""

    def test_parse_markdown_basic(self, trending: GithubTrending) -> None:
        """
        Given: A markdown string with repository information.
        When: _parse_markdown is called.
        Then: A list of repository records is returned.
        """
        # 前提
        content = """# GitHub トレンドリポジトリ (2024-01-15)

## Python

### [owner/python-repo](https://github.com/owner/python-repo)

A Python repository

⭐ スター数: 1,000

---

"""

        # 操作
        result = trending._parse_markdown(content)

        # 確認
        assert len(result) == 1
        assert result[0]["name"] == "owner/python-repo"
        assert result[0]["link"] == "https://github.com/owner/python-repo"
        assert result[0]["description"] == "A Python repository"
        assert result[0]["stars"] == 1000
        assert result[0]["language"] == "python"

    def test_parse_markdown_all_language(self, trending: GithubTrending) -> None:
        """
        Given: A markdown string with 'すべての言語' section.
        When: _parse_markdown is called.
        Then: Language is parsed as 'all'.
        """
        # 前提
        content = """# GitHub トレンドリポジトリ (2024-01-15)

## すべての言語

### [owner/repo](https://github.com/owner/repo)

A repository

⭐ スター数: 500

---

"""

        # 操作
        result = trending._parse_markdown(content)

        # 確認
        assert len(result) == 1
        assert result[0]["language"] == "all"

    def test_parse_markdown_multiple_repos(self, trending: GithubTrending) -> None:
        """
        Given: A markdown string with multiple repositories.
        When: _parse_markdown is called.
        Then: All repositories are parsed.
        """
        # 前提
        content = """# GitHub トレンドリポジトリ (2024-01-15)

## Python

### [owner/repo1](https://github.com/owner/repo1)

First repo

⭐ スター数: 1,000

---

### [owner/repo2](https://github.com/owner/repo2)

Second repo

⭐ スター数: 2,000

---

"""

        # 操作
        result = trending._parse_markdown(content)

        # 確認
        assert len(result) == 2
        assert result[0]["name"] == "owner/repo1"
        assert result[1]["name"] == "owner/repo2"


class TestSerializeRepositories:
    """Tests for GithubTrending._serialize_repositories method."""

    def test_serialize_repositories_basic(self, trending: GithubTrending) -> None:
        """
        Given: A list of repositories by language.
        When: _serialize_repositories is called.
        Then: A list of serialized records is returned.
        """
        # 前提
        repo = Repository(
            name="owner/repo",
            description="A repository",
            link="https://github.com/owner/repo",
            stars=1000,
        )
        repositories_by_language = [("python", [repo])]
        default_date = date(2024, 1, 15)

        # 操作
        result = trending._serialize_repositories(
            repositories_by_language, default_date
        )

        # 確認
        assert len(result) == 1
        assert result[0]["language"] == "python"
        assert result[0]["name"] == "owner/repo"
        assert result[0]["description"] == "A repository"
        assert result[0]["link"] == "https://github.com/owner/repo"
        assert result[0]["stars"] == 1000
        assert "published_at" in result[0]

    def test_serialize_repositories_multiple_languages(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: Repositories from multiple languages.
        When: _serialize_repositories is called.
        Then: All repositories are serialized with correct language.
        """
        # 前提
        python_repo = Repository(
            name="owner/python-repo",
            description="Python repo",
            link="https://github.com/owner/python-repo",
            stars=1000,
        )
        js_repo = Repository(
            name="owner/js-repo",
            description="JS repo",
            link="https://github.com/owner/js-repo",
            stars=2000,
        )
        repositories_by_language = [
            ("python", [python_repo]),
            ("javascript", [js_repo]),
        ]
        default_date = date(2024, 1, 15)

        # 操作
        result = trending._serialize_repositories(
            repositories_by_language, default_date
        )

        # 確認
        assert len(result) == 2
        python_record = next(r for r in result if r["language"] == "python")
        js_record = next(r for r in result if r["language"] == "javascript")
        assert python_record["name"] == "owner/python-repo"
        assert js_record["name"] == "owner/js-repo"

    def test_serialize_repositories_published_at_format(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: A repository to serialize.
        When: _serialize_repositories is called.
        Then: published_at is in ISO format with UTC timezone.
        """
        # 前提
        repo = Repository(
            name="owner/repo",
            description="A repository",
            link="https://github.com/owner/repo",
            stars=100,
        )
        repositories_by_language = [("python", [repo])]
        default_date = date(2024, 1, 15)

        # 操作
        result = trending._serialize_repositories(
            repositories_by_language, default_date
        )

        # 確認
        published_at = result[0]["published_at"]
        assert "2024-01-15" in published_at
        assert "+00:00" in published_at

    def test_serialize_repositories_empty_list(self, trending: GithubTrending) -> None:
        """
        Given: An empty list of repositories.
        When: _serialize_repositories is called.
        Then: An empty list is returned.
        """
        # 前提
        repositories_by_language: list[tuple[str, list[Repository]]] = []
        default_date = date(2024, 1, 15)

        # 操作
        result = trending._serialize_repositories(
            repositories_by_language, default_date
        )

        # 確認
        assert result == []

    def test_serialize_repositories_with_none_description(
        self, trending: GithubTrending
    ) -> None:
        """
        Given: A repository with None description.
        When: _serialize_repositories is called.
        Then: Description is None in the serialized record.
        """
        # 前提
        repo = Repository(
            name="owner/repo",
            description=None,
            link="https://github.com/owner/repo",
            stars=100,
        )
        repositories_by_language = [("python", [repo])]
        default_date = date(2024, 1, 15)

        # 操作
        result = trending._serialize_repositories(
            repositories_by_language, default_date
        )

        # 確認
        assert result[0]["description"] is None
