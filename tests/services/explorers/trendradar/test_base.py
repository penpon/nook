"""BaseTrendRadarExplorer基底クラスのテスト.

このモジュールは、TrendRadar系Explorerの基底クラスのテストを行います。
"""

from pathlib import Path

import pytest

from nook.services.base.base_feed_service import Article
from nook.services.explorers.trendradar.base import BaseTrendRadarExplorer
from nook.services.explorers.trendradar.utils import create_empty_soup


class ConcreteTrendRadarExplorer(BaseTrendRadarExplorer):
    """テスト用の具象Explorerクラス。"""

    PLATFORM_NAME = "test-platform"
    FEED_NAME = "test-feed"
    MARKDOWN_HEADER = "Test Header"

    def _get_summary_prompt(self, article: Article) -> str:
        return f"Summarize: {article.title}"

    def _get_system_instruction(self) -> str:
        return "You are a summarizer."


class TestBaseTrendRadarExplorerInitialization:
    """BaseTrendRadarExplorerの初期化テスト。"""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ConcreteTrendRadarExplorer:
        """テスト用のConcreteTrendRadarExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ConcreteTrendRadarExplorer(
            service_name="test-trendradar",
            storage_dir=str(tmp_path),
        )

    def test_initialization_with_required_attributes(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: 必須属性が設定された具象クラス。
        When: インスタンス化されたとき。
        Then: 正しく初期化される。
        """
        assert explorer.service_name == "test-trendradar"
        assert explorer.PLATFORM_NAME == "test-platform"
        assert explorer.FEED_NAME == "test-feed"
        assert explorer.MARKDOWN_HEADER == "Test Header"
        assert explorer.client is not None

    def test_initialization_raises_error_without_platform_name(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """
        Given: PLATFORM_NAMEが未設定の具象クラス。
        When: インスタンス化されたとき。
        Then: ValueErrorを発生させる。
        """

        class MissingPlatformExplorer(BaseTrendRadarExplorer):
            PLATFORM_NAME = ""  # Empty
            FEED_NAME = "test"
            MARKDOWN_HEADER = "Test"

            def _get_summary_prompt(self, article: Article) -> str:
                return ""

            def _get_system_instruction(self) -> str:
                return ""

        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        with pytest.raises(ValueError, match="PLATFORM_NAME"):
            MissingPlatformExplorer(service_name="test", storage_dir=str(tmp_path))

    def test_initialization_raises_error_without_feed_name(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """
        Given: FEED_NAMEが未設定の具象クラス。
        When: インスタンス化されたとき。
        Then: ValueErrorを発生させる。
        """

        class MissingFeedExplorer(BaseTrendRadarExplorer):
            PLATFORM_NAME = "test"
            FEED_NAME = ""  # Empty
            MARKDOWN_HEADER = "Test"

            def _get_summary_prompt(self, article: Article) -> str:
                return ""

            def _get_system_instruction(self) -> str:
                return ""

        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        with pytest.raises(ValueError, match="FEED_NAME"):
            MissingFeedExplorer(service_name="test", storage_dir=str(tmp_path))

    def test_initialization_raises_error_without_markdown_header(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """
        Given: MARKDOWN_HEADERが未設定の具象クラス。
        When: インスタンス化されたとき。
        Then: ValueErrorを発生させる。
        """

        class MissingHeaderExplorer(BaseTrendRadarExplorer):
            PLATFORM_NAME = "test"
            FEED_NAME = "test"
            MARKDOWN_HEADER = ""  # Empty

            def _get_summary_prompt(self, article: Article) -> str:
                return ""

            def _get_system_instruction(self) -> str:
                return ""

        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        with pytest.raises(ValueError, match="MARKDOWN_HEADER"):
            MissingHeaderExplorer(service_name="test", storage_dir=str(tmp_path))


class TestBaseTrendRadarExplorerTransform:
    """BaseTrendRadarExplorerの変換メソッドのテスト。"""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ConcreteTrendRadarExplorer:
        """テスト用のConcreteTrendRadarExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ConcreteTrendRadarExplorer(
            service_name="test-trendradar",
            storage_dir=str(tmp_path),
        )

    def test_transform_to_article_basic(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: 基本的なTrendRadarアイテム。
        When: _transform_to_article が呼ばれたとき。
        Then: 正しいArticleオブジェクトを返す。
        """
        item = {
            "title": "Test Title",
            "url": "https://example.com",
            "hot": 1000,
        }
        article = explorer._transform_to_article(item)

        assert article.title == "Test Title"
        assert article.url == "https://example.com"
        assert article.popularity_score == 1000.0
        assert article.feed_name == "test-feed"
        assert article.category == "hot"

    def test_transform_to_article_with_desc(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: descフィールドを持つアイテム。
        When: _transform_to_article が呼ばれたとき。
        Then: descがtextに設定される。
        """
        item = {
            "title": "Test",
            "url": "https://example.com",
            "desc": "This is a description",
        }
        article = explorer._transform_to_article(item)
        assert article.text == "This is a description"

    def test_transform_to_article_with_description(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: descriptionフィールドを持つアイテム。
        When: _transform_to_article が呼ばれたとき。
        Then: descriptionがtextに設定される。
        """
        item = {
            "title": "Test",
            "url": "https://example.com",
            "description": "This is a description",
        }
        article = explorer._transform_to_article(item)
        assert article.text == "This is a description"

    def test_transform_to_article_fallback_to_rank(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: hotの代わりにrankを持つアイテム。
        When: _transform_to_article が呼ばれたとき。
        Then: rankがpopularity_scoreに使用される。
        """
        item = {
            "title": "Test",
            "url": "https://example.com",
            "rank": 5,
        }
        article = explorer._transform_to_article(item)
        assert article.popularity_score == 5.0

    def test_transform_to_article_handles_none_values(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: Noneフィールドを持つアイテム。
        When: _transform_to_article が呼ばれたとき。
        Then: デフォルト値が使用される。
        """
        item = {
            "title": None,
            "url": None,
            "desc": None,
            "hot": None,
        }
        article = explorer._transform_to_article(item)
        assert article.title == ""
        assert article.url == ""
        assert article.text == ""
        assert article.popularity_score == 0.0


class TestBaseTrendRadarExplorerGetDefaultSummaryPrompt:
    """BaseTrendRadarExplorerの_get_default_summary_promptメソッドのテスト。"""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ConcreteTrendRadarExplorer:
        """テスト用のConcreteTrendRadarExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ConcreteTrendRadarExplorer(
            service_name="test-trendradar",
            storage_dir=str(tmp_path),
        )

    def test_generates_prompt_with_all_sections(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: Articleと各種パラメータ。
        When: _get_default_summary_prompt が呼ばれたとき。
        Then: 全セクションを含むプロンプトが生成される。
        """
        article = Article(
            feed_name="test",
            title="Test Article",
            url="https://example.com/article",
            text="Article description",
            soup=create_empty_soup(),
        )
        sections = ["セクション1", "セクション2", "セクション3"]

        prompt = explorer._get_default_summary_prompt(
            article=article,
            platform_label="テストプラットフォーム",
            content_label="ホットトピック",
            sections=sections,
        )

        assert "テストプラットフォーム" in prompt
        assert "ホットトピック" in prompt
        assert "Test Article" in prompt
        assert "https://example.com/article" in prompt
        assert "Article description" in prompt
        assert "1. セクション1" in prompt
        assert "2. セクション2" in prompt
        assert "3. セクション3" in prompt

    def test_sanitizes_input_values(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: 長いタイトルを持つArticle。
        When: _get_default_summary_prompt が呼ばれたとき。
        Then: 入力値がサニタイズされる。
        """
        # 非常に長いタイトル
        long_title = "A" * 500
        article = Article(
            feed_name="test",
            title=long_title,
            url="https://example.com",
            text="",
            soup=create_empty_soup(),
        )

        prompt = explorer._get_default_summary_prompt(
            article=article,
            platform_label="Test",
            content_label="Topic",
            sections=["Section"],
        )

        # タイトルは200文字で切り捨て
        assert len(long_title) > 200
        # プロンプト内では切り捨てられている
        assert "A" * 200 in prompt
        assert "..." in prompt


class TestBaseTrendRadarExplorerRenderMarkdown:
    """BaseTrendRadarExplorerの_render_markdownメソッドのテスト。"""

    @pytest.fixture
    def explorer(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ConcreteTrendRadarExplorer:
        """テスト用のConcreteTrendRadarExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ConcreteTrendRadarExplorer(
            service_name="test-trendradar",
            storage_dir=str(tmp_path),
        )

    def test_renders_markdown_with_header(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: レコードリストと日付。
        When: _render_markdown が呼ばれたとき。
        Then: ヘッダーを含むMarkdownが生成される。
        """
        records = [
            {
                "title": "Test Article",
                "url": "https://example.com",
                "summary": "Test summary",
                "popularity_score": 1000,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        assert "# Test Header (2024-01-15)" in result
        assert "[Test Article](https://example.com)" in result
        assert "**人気度**: 1,000" in result
        assert "**要約**:" in result
        assert "Test summary" in result

    def test_renders_multiple_records(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: 複数のレコード。
        When: _render_markdown が呼ばれたとき。
        Then: 全レコードが番号付きで出力される。
        """
        records = [
            {"title": "Article 1", "url": "https://example.com/1", "summary": "Summary 1", "popularity_score": 100},
            {"title": "Article 2", "url": "https://example.com/2", "summary": "Summary 2", "popularity_score": 200},
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        assert "## 1. [Article 1]" in result
        assert "## 2. [Article 2]" in result

    def test_escapes_special_characters_in_title(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: 特殊文字を含むタイトル。
        When: _render_markdown が呼ばれたとき。
        Then: タイトルがエスケープされる。
        """
        records = [
            {
                "title": "[Important] <Alert>",
                "url": "https://example.com",
                "summary": "Summary",
                "popularity_score": 100,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        assert "\\[Important\\]" in result
        assert "&lt;Alert&gt;" in result

    def test_escapes_special_characters_in_url(self, explorer: ConcreteTrendRadarExplorer) -> None:
        """
        Given: 括弧を含むURL。
        When: _render_markdown が呼ばれたとき。
        Then: URLがエスケープされる。
        """
        records = [
            {
                "title": "Test",
                "url": "https://example.com/path(with)parens",
                "summary": "Summary",
                "popularity_score": 100,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        assert "\\(with\\)parens" in result
