"""JuejinExplorerサービスのテスト.

このモジュールは、TrendRadar MCPサーバーを経由して
掘金のホットトピックを取得するJuejinExplorerクラスのテストを行います。
"""

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.explorers.trendradar.juejin_explorer import JuejinExplorer


class TestJuejinExplorerInitialization:
    """JuejinExplorerの初期化テスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> JuejinExplorer:
        """テスト用のJuejinExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return JuejinExplorer(storage_dir=str(tmp_path))

    def test_explorer_initialization(self, explorer: JuejinExplorer) -> None:
        """
        Given: デフォルトの初期化パラメータ。
        When: JuejinExplorer がインスタンス化されたとき。
        Then: explorer は正しいサービス名と TrendRadarClient を持つ。
        """
        assert explorer.service_name == "trendradar-juejin"
        assert explorer.client is not None

    def test_explorer_with_custom_storage_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """
        Given: カスタムストレージディレクトリ。
        When: JuejinExplorer がインスタンス化されたとき。
        Then: ストレージパスが正しく設定される。
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = JuejinExplorer(storage_dir=str(tmp_path / "custom_data"))
        assert "custom_data" in str(explorer.storage.base_dir)


class TestJuejinExplorerTransform:
    """TrendRadarからArticleへの変換テスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> JuejinExplorer:
        """テスト用のJuejinExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return JuejinExplorer(storage_dir=str(tmp_path))

    def test_transform_trendradar_to_article(self, explorer: JuejinExplorer) -> None:
        """
        Given: TrendRadar のニュース項目辞書。
        When: _transform_to_article が呼ばれたとき。
        Then: 正しい属性を持つ Article オブジェクトが返される。
        """
        trendradar_item = {
            "title": "Vue 3.4 新特性详解",
            "url": "https://juejin.cn/post/123456",
            "hot": 1500000,
        }

        article = explorer._transform_to_article(trendradar_item)

        assert article.title == "Vue 3.4 新特性详解"
        assert article.url == "https://juejin.cn/post/123456"
        assert article.popularity_score == 1500000
        assert article.feed_name == "juejin"
        assert article.category == "hot"

    def test_transform_handles_missing_hot(self, explorer: JuejinExplorer) -> None:
        """
        Given: hot フィールドがない TrendRadar 項目。
        When: _transform_to_article が呼ばれたとき。
        Then: popularity_score はデフォルトで 0 になる。
        """
        trendradar_item = {
            "title": "话题没有热度",
            "url": "https://juejin.cn/post/789",
        }

        article = explorer._transform_to_article(trendradar_item)

        assert article.popularity_score == 0

    def test_transform_parses_published_at(self, explorer: JuejinExplorer) -> None:
        """
        Given: タイムスタンプを持つ TrendRadar 項目。
        When: _transform_to_article が呼ばれたとき。
        Then: published_at が正しく解析される。
        """
        # Test with ISO string
        item_iso = {
            "title": "Article",
            "url": "http://test",
            "published_at": "2023-01-01T12:00:00",
        }
        article_iso = explorer._transform_to_article(item_iso)
        assert article_iso.published_at.year == 2023
        assert article_iso.published_at.month == 1

        # Test with timestamp (epoch)
        item_epoch = {
            "title": "Article Epoch",
            "url": "http://test-epoch",
            "timestamp": 1672531200,  # 2023-01-01 00:00:00 UTC
        }
        article_epoch = explorer._transform_to_article(item_epoch)
        assert article_epoch.published_at.year == 2023

    def test_transform_handles_malformed_hot(self, explorer: JuejinExplorer) -> None:
        """
        Given: 不正な形式の hot フィールドを持つ TrendRadar 項目。
        When: _transform_to_article が呼ばれたとき。
        Then: 例外を発生させずに popularity_score はデフォルトで 0.0 になる。
        """
        item = {
            "title": "Malformed Hot",
            "url": "http://test-malformed",
            "hot": "N/A",
        }
        article = explorer._transform_to_article(item)
        assert article.popularity_score == 0.0


class TestJuejinExplorerCollect:
    """JuejinExplorer.collectメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> JuejinExplorer:
        """テスト用のJuejinExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = JuejinExplorer(storage_dir=str(tmp_path))
        # Mock storage to prevent disk I/O
        explorer.storage = AsyncMock()

        # Mock save methods to return dummy paths containing filename
        async def save_side_effect(data, filename):
            return Path("mock") / filename

        explorer.storage.save.side_effect = save_side_effect
        return explorer

    @pytest.mark.asyncio
    async def test_collect_returns_file_paths(self, explorer: JuejinExplorer) -> None:
        """
        Given: ニュース項目を返すモック化された TrendRadarClient。
        When: collect が呼ばれたとき。
        Then: (json_path, md_path) タプルのリストを返す。
        """
        mock_news = [
            {
                "title": "Vue 3.4 新特性",
                "url": "https://juejin.cn/post/1",
                "hot": 1000000,
            },
            {
                "title": "React 19 详解",
                "url": "https://juejin.cn/post/2",
                "hot": 500000,
            },
        ]

        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            # Mock GPT client to avoid actual API calls
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(
                return_value=(
                    "この技術記事は中国の開発者コミュニティで活発に議論されており、"
                    "多くのエンジニアが関心を寄せています。"
                )
            )

            result = await explorer.collect(days=1, limit=10)

            mock_get.assert_called_once_with(platform="juejin", limit=10)
            # Result should be non-empty list of 2-tuples
            assert result
            assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
            # ファイルサフィックスの確認（回帰検知用）
            assert all(p[0].endswith(".json") and p[1].endswith(".md") for p in result)

    @pytest.mark.asyncio
    async def test_collect_handles_null_fields_from_trendradar(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: TrendRadar が null フィールド (例: desc/title/url) を含む項目を返す。
        When: collect が呼ばれたとき。
        Then: プロンプト構築中にクラッシュせず、正常に完了する。
        """
        mock_news = [
            {
                "title": None,
                "url": None,
                "desc": None,
                "hot": 100,
            }
        ]

        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(return_value="要約テキスト")

            result = await explorer.collect(days=1, limit=10)

            assert isinstance(result, list)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_collect_propagates_errors(self, explorer: JuejinExplorer) -> None:
        """
        Given: TrendRadarClient が例外を発生させる。
        When: collect が呼ばれたとき。
        Then: 例外が伝播される。
        """
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = Exception("API Error")

            with pytest.raises(Exception, match="API Error"):
                await explorer.collect(days=1, limit=10)

    @pytest.mark.asyncio
    async def test_collect_raises_error_for_multi_day_with_days_param(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: days パラメータ != 1 かつ target_dates が None。
        When: collect が呼ばれたとき。
        Then: 明確なメッセージとともに ValueError を発生させる。
        """
        with pytest.raises(ValueError, match="複数日の収集"):
            await explorer.collect(days=2)

    @pytest.mark.asyncio
    async def test_collect_validates_limit(self, explorer: JuejinExplorer) -> None:
        """
        Given: 無効な limit 値。
        When: collect が呼ばれたとき。
        Then: ValueError を発生させる。
        """
        with pytest.raises(ValueError, match="limit は 1 から 100 の整数"):
            await explorer.collect(days=1, limit=0)
        with pytest.raises(ValueError, match="limit は 1 から 100 の整数"):
            await explorer.collect(days=1, limit=101)
        with pytest.raises(ValueError, match="limit は 1 から 100 の整数"):
            await explorer.collect(days=1, limit=-5)

    @pytest.mark.asyncio
    async def test_collect_rejects_bool_limit(self, explorer: JuejinExplorer) -> None:
        """
        Given: limit パラメータに対するブール値。
        When: collect が呼ばれたとき。
        Then: ValueError を発生させる (Pythonではboolはintのサブクラス)。
        """
        with pytest.raises(ValueError, match="limit は 1 から 100 の整数"):
            await explorer.collect(days=1, limit=True)
        with pytest.raises(ValueError, match="limit は 1 から 100 の整数"):
            await explorer.collect(days=1, limit=False)

    @pytest.mark.asyncio
    async def test_collect_with_single_target_date(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: target_dates パラメータ内の単一の日付。
        When: collect が呼ばれたとき。
        Then: 日付を受け入れ、ファイル名に使用する。
        """
        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(return_value="要約テキスト")

            target_date = date(2024, 1, 15)
            result = await explorer.collect(target_dates=[target_date])

            assert len(result) == 1
            json_path, md_path = result[0]
            assert "2024-01-15" in json_path
            assert "2024-01-15" in md_path

    @pytest.mark.asyncio
    async def test_collect_rejects_empty_target_dates(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: 空の target_dates リスト。
        When: collect が呼ばれたとき。
        Then: ValueError を発生させる。
        """
        with pytest.raises(ValueError, match="target_dates には少なくとも1つの日付"):
            await explorer.collect(target_dates=[])

    @pytest.mark.asyncio
    async def test_collect_with_multiple_target_dates(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: target_dates パラメータ内の複数の日付。
        When: collect が呼ばれたとき。
        Then: NotImplementedError を発生させる。
        """
        target_dates = [date(2024, 1, 15), date(2024, 1, 16)]
        with pytest.raises(NotImplementedError, match="複数日の収集"):
            await explorer.collect(target_dates=target_dates)

    @pytest.mark.asyncio
    async def test_collect_returns_empty_for_no_news(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: TrendRadarClient が空のリストを返す。
        When: collect が呼ばれたとき。
        Then: 空のリストを返す。
        """
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            result = await explorer.collect(days=1, limit=10)

            assert result == []

    @pytest.mark.asyncio
    async def test_collect_handles_gpt_error(self, explorer: JuejinExplorer) -> None:
        """
        Given: 要約中に GPT クライアントが例外を発生させる。
        When: collect が呼ばれたとき。
        Then: 記事の要約にエラーメッセージが含まれ、collect が正常に完了する。
        """
        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            # Mock gpt_client.generate_async to raise exception
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(
                side_effect=Exception("GPT Error")
            )

            # Patch _store_articles to capture articles without real I/O
            captured_articles = []

            async def capture_store(articles, date_str):
                captured_articles.extend(articles)
                # Return mock paths without calling real storage
                return [(f"mock/{date_str}.json", f"mock/{date_str}.md")]

            with patch.object(explorer, "_store_articles", side_effect=capture_store):
                result = await explorer.collect(days=1, limit=10)

            # Should complete and return file paths
            assert isinstance(result, list)
            # Verify error message is set in article summary (fixed message, no exception details)
            assert len(captured_articles) == 1
            assert (
                captured_articles[0].summary
                == JuejinExplorer.ERROR_MSG_GENERATION_FAILED
            )
            # Ensure no exception details are leaked
            assert "GPT Error" not in captured_articles[0].summary


class TestJuejinExplorerRun:
    """JuejinExplorer.runメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> JuejinExplorer:
        """テスト用のJuejinExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = JuejinExplorer(storage_dir=str(tmp_path))
        # Mock storage to prevent disk I/O (though run() mocks collect, it's safer)
        explorer.storage = AsyncMock()
        return explorer

    def test_run_calls_run_with_cleanup(self, explorer: JuejinExplorer) -> None:
        """
        Given: JuejinExplorer インスタンス。
        When: run が呼ばれたとき。
        Then: asyncio.run 経由で _run_with_cleanup が呼び出される。
        """
        with patch.object(
            explorer, "_run_with_cleanup", new_callable=AsyncMock
        ) as mock_cleanup:
            explorer.run(days=1, limit=20)

            mock_cleanup.assert_called_once_with(days=1, limit=20)

    @pytest.mark.asyncio
    async def test_run_with_cleanup_calls_collect_and_close(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: JuejinExplorer インスタンス。
        When: _run_with_cleanup が呼ばれたとき。
        Then: collect が呼ばれ、client.close() が確実に実行される。
        """
        with patch.object(explorer, "collect", new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = []
            with patch.object(
                explorer.client, "close", new_callable=AsyncMock
            ) as mock_close:
                await explorer._run_with_cleanup(days=1, limit=20)

                mock_collect.assert_called_once_with(days=1, limit=20)
                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_base_service_cleanup_on_error(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: collect が例外を発生させる。
        When: _run_with_cleanup が呼ばれたとき。
        Then: close がそれでも呼ばれる。
        """
        with patch.object(
            explorer, "collect", new_callable=AsyncMock, side_effect=ValueError("Test")
        ):
            with patch.object(
                explorer.client, "close", new_callable=AsyncMock
            ) as mock_close:
                with pytest.raises(ValueError):
                    await explorer._run_with_cleanup()
                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_raises_error_from_running_loop(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: アクティブな asyncio イベントループ。
        When: ループ内から run() が呼ばれたとき。
        Then: RuntimeError を発生させる。
        """
        with pytest.raises(
            RuntimeError, match="イベントループ実行中には使用できません"
        ):
            explorer.run(days=1, limit=10)


class TestJuejinExplorerContextManager:
    """JuejinExplorerのコンテキストマネージャーメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> JuejinExplorer:
        """テスト用のJuejinExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return JuejinExplorer(storage_dir=str(tmp_path))

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, explorer: JuejinExplorer) -> None:
        """
        Given: async with ステートメントで使用される JuejinExplorer。
        When: ブロックに入り、出るとき。
        Then: 終了時に close() が呼ばれる。
        """
        with patch.object(
            explorer.client, "close", new_callable=AsyncMock
        ) as mock_close:
            async with explorer as e:
                assert e is explorer
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_error(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: async with ブロック内で例外が発生する。
        When: ブロックが終了するとき。
        Then: close() がそれでも呼ばれる。
        """
        with patch.object(
            explorer.client, "close", new_callable=AsyncMock
        ) as mock_close:
            with pytest.raises(ValueError):
                async with explorer:
                    raise ValueError("Test Error")
            mock_close.assert_awaited_once()


class TestJuejinExplorerMarkdownRendering:
    """Markdownレンダリングのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> JuejinExplorer:
        """テスト用のJuejinExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return JuejinExplorer(storage_dir=str(tmp_path))

    def test_render_markdown_with_valid_records(self, explorer: JuejinExplorer) -> None:
        """
        Given: 有効な記録のリスト。
        When: _render_markdown が呼ばれたとき。
        Then: 正しい見出しとフォーマットで Markdown が生成される。
        """
        records = [
            {
                "title": "Vue 3.4 新特性",
                "url": "https://juejin.cn/post/123",
                "summary": "Vue 3.4の新機能について解説",
                "popularity_score": 10000,
            }
        ]

        result = explorer._render_markdown(records, "2024-01-15")

        assert "# 掘金ホットトピック (2024-01-15)" in result
        assert "## 1. [Vue 3.4 新特性](https://juejin.cn/post/123)" in result
        assert "**人気度**: 10,000" in result
        assert "Vue 3.4の新機能について解説" in result

    def test_render_markdown_escapes_special_characters(
        self, explorer: JuejinExplorer
    ) -> None:
        """
        Given: 特殊文字を含む記録。
        When: _render_markdown が呼ばれたとき。
        Then: タイトルとURLの特殊文字はエスケープされ、要約はマークダウンが保持される。
        """
        records = [
            {
                "title": "[Test] Article (with brackets)",
                "url": "https://example.com/path?q=(test)",
                "summary": "Summary with **bold** and [link](http://example.com)",
                "popularity_score": 100,
            }
        ]

        result = explorer._render_markdown(records, "2024-01-15")

        # Title should have escaped brackets
        assert "\\[Test\\]" in result

        # Summary should PRESERVE markdown (not escaped)
        assert "**bold**" in result
        assert "[link](http://example.com)" in result


class TestJuejinExplorerUtils:
    """内部ユーティリティメソッドのテスト。"""

    @pytest.fixture
    def explorer(self, tmp_path: Path) -> JuejinExplorer:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            return JuejinExplorer(storage_dir=str(tmp_path))

    def test_sanitize_prompt_input(self, explorer: JuejinExplorer) -> None:
        """_sanitize_prompt_input のテスト。"""
        # 制御文字の除去 (NULL, BEL)
        assert explorer._sanitize_prompt_input("Hello\x00\x07World") == "HelloWorld"
        # 改行・タブは保持
        assert explorer._sanitize_prompt_input("Line\nTab\t") == "Line\nTab"
        # 連続改行の正規化
        assert explorer._sanitize_prompt_input("A\n\n\nB") == "A\n\nB"
        # 日本語と全角スペース (Zenkaku Space \u3000) は保持
        assert explorer._sanitize_prompt_input("日本\u3000語") == "日本\u3000語"
        # 絵文字は保持 (So category)
        assert explorer._sanitize_prompt_input("Hello 🌍") == "Hello 🌍"
        # 長さ制限
        long_text = "a" * 600
        result = explorer._sanitize_prompt_input(long_text, max_length=10)
        assert len(result) <= 13  # 10 + "..."
        assert result.endswith("...")

    def test_parse_popularity_score(self, explorer: JuejinExplorer) -> None:
        """_parse_popularity_score のテスト。"""
        assert explorer._parse_popularity_score(None) == 0.0
        assert explorer._parse_popularity_score(100) == 100.0
        assert explorer._parse_popularity_score("1,000") == 1000.0
        assert explorer._parse_popularity_score("+500") == 500.0
        assert explorer._parse_popularity_score("invalid") == 0.0
        assert explorer._parse_popularity_score(float("nan")) == 0.0
        assert explorer._parse_popularity_score(float("inf")) == 0.0

    def test_escape_markdown_text(self, explorer: JuejinExplorer) -> None:
        """_escape_markdown_text のテスト。"""
        # HTMLエンティティ
        assert explorer._escape_markdown_text("<script>") == "&lt;script&gt;"
        # 角括弧
        assert explorer._escape_markdown_text("[link]") == "\\[link\\]"
        # 複合
        assert (
            explorer._escape_markdown_text("<b>[B]</b>") == "&lt;b&gt;\\[B\\]&lt;/b&gt;"
        )

    def test_escape_markdown_url(self, explorer: JuejinExplorer) -> None:
        """_escape_markdown_url のテスト。"""
        assert (
            explorer._escape_markdown_url("http://e.com/(1)") == "http://e.com/\\(1\\)"
        )
        assert (
            explorer._escape_markdown_url("http://e.com/[1]") == "http://e.com/\\[1\\]"
        )
