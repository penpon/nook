"""ZhihuExplorerサービスのテスト.

このモジュールは、TrendRadar MCPサーバーを経由して
知乎のホットトピックを取得するZhihuExplorerクラスのテストを行います。
"""

from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.explorers.trendradar.zhihu_explorer import ZhihuExplorer


class TestZhihuExplorerInitialization:
    """ZhihuExplorerの初期化テスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """テスト用のZhihuExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer(storage_dir=str(tmp_path))

    def test_explorer_initialization(self, explorer: ZhihuExplorer) -> None:
        """
        Given: デフォルトの初期化パラメータ。
        When: ZhihuExplorer がインスタンス化されたとき。
        Then: explorer は正しいサービス名と TrendRadarClient を持つ。
        """
        assert explorer.service_name == "trendradar-zhihu"
        assert explorer.client is not None

    def test_explorer_with_custom_storage_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """
        Given: カスタムストレージディレクトリ。
        When: ZhihuExplorer がインスタンス化されたとき。
        Then: ストレージパスが正しく設定される。
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer(storage_dir=str(tmp_path / "custom_data"))
        assert "custom_data" in str(explorer.storage.base_dir)


class TestZhihuExplorerTransform:
    """TrendRadarからArticleへの変換テスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """テスト用のZhihuExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer(storage_dir=str(tmp_path))

    def test_transform_trendradar_to_article(self, explorer: ZhihuExplorer) -> None:
        """
        Given: TrendRadar のニュース項目辞書。
        When: _transform_to_article が呼ばれたとき。
        Then: 正しい属性を持つ Article オブジェクトが返される。
        """
        trendradar_item = {
            "title": "测试热门话题",
            "url": "https://www.zhihu.com/question/123456",
            "hot": 1500000,
        }

        article = explorer._transform_to_article(trendradar_item)

        assert article.title == "测试热门话题"
        assert article.url == "https://www.zhihu.com/question/123456"
        assert article.popularity_score == 1500000
        assert article.feed_name == "zhihu"
        assert article.category is None

    def test_transform_handles_missing_hot(self, explorer: ZhihuExplorer) -> None:
        """
        Given: hot フィールドがない TrendRadar 項目。
        When: _transform_to_article が呼ばれたとき。
        Then: popularity_score はデフォルトで 0 になる。
        """
        trendradar_item = {
            "title": "话题没有热度",
            "url": "https://www.zhihu.com/question/789",
        }

        article = explorer._transform_to_article(trendradar_item)

        assert article.popularity_score == 0

    def test_transform_parses_published_at(self, explorer: ZhihuExplorer) -> None:
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

    def test_transform_parses_epoch_zero(self, explorer: ZhihuExplorer) -> None:
        """
        Given: エポックタイムスタンプ 0 を持つ TrendRadar 項目。
        When: _transform_to_article が呼ばれたとき。
        Then: published_at は 1970-01-01T00:00:00Z になる。

        Note: epoch=0 は TrendRadar 側でデフォルト値として返されることがあり、
        パーサ回帰防止のためにこのエッジケースをテストしています。
        """
        item = {
            "title": "Epoch Zero Article",
            "url": "http://test-epoch-zero",
            "timestamp": 0,
        }
        article = explorer._transform_to_article(item)
        assert article.published_at.year == 1970
        assert article.published_at.month == 1
        assert article.published_at.day == 1

    def test_transform_handles_malformed_hot(self, explorer: ZhihuExplorer) -> None:
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

    def test_parse_published_at_field_priority(self, explorer: ZhihuExplorer) -> None:
        """
        Given: 複数のタイムスタンプ候補フィールドを持つ項目。
        When: _parse_published_at が呼ばれたとき。
        Then: フィールドは優先順位順にチェックされる (published_at > timestamp > pub_date > created_at)。
        """

        # published_at has highest priority
        item_with_published_at = {
            "published_at": "2023-06-15T10:00:00Z",
            "timestamp": 1672531200,  # 2023-01-01 (should be ignored)
            "pub_date": "2023-03-01T00:00:00Z",  # (should be ignored)
        }
        result = explorer._parse_published_at(item_with_published_at)
        assert result.year == 2023
        assert result.month == 6
        assert result.day == 15

        # timestamp is second priority
        item_with_timestamp = {
            "timestamp": 1672531200,  # 2023-01-01
            "pub_date": "2023-03-01T00:00:00Z",  # (should be ignored)
        }
        result = explorer._parse_published_at(item_with_timestamp)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1

        # pub_date is third priority
        item_with_pub_date = {
            "pub_date": "2023-03-15T00:00:00Z",
            "created_at": "2023-02-01T00:00:00Z",  # (should be ignored)
        }
        result = explorer._parse_published_at(item_with_pub_date)
        assert result.year == 2023
        assert result.month == 3

        # created_at is last priority
        item_with_created_at = {
            "created_at": "2023-02-20T00:00:00Z",
        }
        result = explorer._parse_published_at(item_with_created_at)
        assert result.year == 2023
        assert result.month == 2

    def test_parse_published_at_invalid_epoch_fallback(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: 無効なエポックタイムスタンプ値を持つ項目。
        When: _parse_published_at が呼ばれたとき。
        Then: 次の候補または現在日時にフォールバックする。
        """

        # Very large epoch value (OverflowError)
        item_overflow = {
            "timestamp": 9999999999999,  # Far future, causes OverflowError
            "pub_date": "2023-05-01T00:00:00Z",  # Should fall back to this
        }
        result = explorer._parse_published_at(item_overflow)
        assert result.year == 2023
        assert result.month == 5

    def test_parse_published_at_negative_epoch_forced_fallback(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: 負のエポック値を持ち、datetime.fromtimestampがOSErrorを発生する。
        When: _parse_published_at が呼ばれたとき。
        Then: 確実に created_at にフォールバックする。

        Note: 負のエポック値の処理はOSやPlatformに依存するため、
        datetime.fromtimestamp をモックして確実に例外を発生させ、
        フォールバック動作を検証します。
        """
        item_negative = {
            "timestamp": -999999999,
            "created_at": "2023-04-01T00:00:00Z",  # Should fall back to this
        }

        with patch("nook.services.explorers.trendradar.utils.datetime") as mock_dt:
            # datetimeモジュール全体をモック
            mock_dt.now = MagicMock(
                return_value=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
            )

            # fromtimestamp: 負の値では例外を発生、それ以外は本物を呼ぶ
            def _mock_fromtimestamp(ts, tz=None):
                if ts < 0:
                    raise OSError("Negative epoch not supported (forced for test)")
                return datetime.fromtimestamp(ts, tz=tz)

            mock_dt.fromtimestamp = _mock_fromtimestamp

            result = explorer._parse_published_at(item_negative)

        # Should fall back to created_at
        assert result.year == 2023
        assert result.month == 4
        assert result.day == 1

    def test_parse_published_at_parse_failure_fallback(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: 解析不可能なタイムスタンプ文字列を持つ項目。
        When: _parse_published_at が呼ばれたとき。
        Then: モック化された現在日時にフォールバックする。

        Note: datetime.now をモックして時間を固定し、
        テストのフレーク（月末境界でのタイムラグによる失敗）を防ぎます。
        """
        # 固定の日時を設定（月末境界の影響を受けない日付を選択）
        fixed_now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        # All fields have invalid values
        item_all_invalid = {
            "published_at": "not-a-date",
            "timestamp": "invalid",
            "pub_date": "also-invalid",
        }

        with patch("nook.services.explorers.trendradar.utils.datetime") as mock_dt:
            # datetime.now() と datetime.fromtimestamp() の両方を設定
            mock_dt.now.return_value = fixed_now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            result = explorer._parse_published_at(item_all_invalid)

        # Should return the mocked current datetime
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

        # Empty item (no timestamp fields)
        item_empty = {}
        with patch("nook.services.explorers.trendradar.utils.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            result = explorer._parse_published_at(item_empty)

        # Should return the mocked current datetime
        assert result.year == 2024


class TestZhihuExplorerCollect:
    """ZhihuExplorer.collectメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """テスト用のZhihuExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer(storage_dir=str(tmp_path))
        # Mock storage to prevent disk I/O
        explorer.storage = AsyncMock()

        # Mock save methods to return dummy paths containing filename
        # 本番の LocalStorage.save は Path を返すため、ここでも Path を返す
        async def save_side_effect(data, filename):
            return Path("mock") / filename

        explorer.storage.save.side_effect = save_side_effect
        return explorer

    @pytest.mark.asyncio
    async def test_collect_returns_file_paths(self, explorer: ZhihuExplorer) -> None:
        """
        Given: ニュース項目を返すモック化された TrendRadarClient。
        When: collect が呼ばれたとき。
        Then: (json_path, md_path) タプルのリストを返す。
        """
        mock_news = [
            {"title": "热门话题1", "url": "https://zhihu.com/q/1", "hot": 1000000},
            {"title": "热门话题2", "url": "https://zhihu.com/q/2", "hot": 500000},
        ]

        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            # Mock GPT client to avoid actual API calls
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(
                return_value=(
                    "このトピックは中国の技術コミュニティで活発に議論されており、"
                    "多くのエンジニアが関心を寄せています。"
                )
            )

            result = await explorer.collect(days=1, limit=10)

            mock_get.assert_called_once_with(platform="zhihu", limit=10)
            # Result should be non-empty list of 2-tuples
            assert result
            assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
            # ファイルサフィックスの確認（回帰検知用）
            assert all(p[0].endswith(".json") and p[1].endswith(".md") for p in result)

    @pytest.mark.asyncio
    async def test_collect_handles_null_fields_from_trendradar(
        self, explorer: ZhihuExplorer
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
    async def test_collect_propagates_errors(self, explorer: ZhihuExplorer) -> None:
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
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: days パラメータ != 1 かつ target_dates が None。
        When: collect が呼ばれたとき。
        Then: 明確なメッセージとともに ValueError を発生させる。
        """
        with pytest.raises(ValueError, match="複数日の収集"):
            await explorer.collect(days=2)

    @pytest.mark.asyncio
    async def test_collect_validates_limit(self, explorer: ZhihuExplorer) -> None:
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
    async def test_collect_rejects_bool_limit(self, explorer: ZhihuExplorer) -> None:
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
        self, explorer: ZhihuExplorer
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
        self, explorer: ZhihuExplorer
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
        self, explorer: ZhihuExplorer
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
    async def test_collect_with_none_target_dates(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: target_dates が None。
        When: collect が呼ばれたとき。
        Then: 今日の日付をファイル名に使用する。

        Note: datetime.now をモック固定して日付境界のフレークを完全に排除。
        """
        # 固定の日時を使用（フレーク防止）
        fixed_now = datetime(2024, 6, 15, 23, 59, 59, tzinfo=timezone.utc)
        expected_date_str = "2024-06-15"

        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]

        with patch("nook.services.explorers.trendradar.base.datetime") as mock_dt:
            # now() を固定
            mock_dt.now.return_value = fixed_now
            # fromtimestamp は本物を使用
            mock_dt.fromtimestamp = datetime.fromtimestamp

            with patch.object(
                explorer.client, "get_latest_news", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = mock_news
                explorer.gpt_client = MagicMock()
                explorer.gpt_client.generate_async = AsyncMock(
                    return_value="要約テキスト"
                )

                result = await explorer.collect(target_dates=None)

                assert len(result) == 1
                json_path, md_path = result[0]
                assert expected_date_str in json_path
                assert expected_date_str in md_path

    @pytest.mark.asyncio
    async def test_collect_returns_empty_for_no_news(
        self, explorer: ZhihuExplorer
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
    async def test_collect_handles_gpt_error(self, explorer: ZhihuExplorer) -> None:
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
                == ZhihuExplorer.ERROR_MSG_GENERATION_FAILED
            )
            # Ensure no exception details are leaked
            assert "GPT Error" not in captured_articles[0].summary

    @pytest.mark.asyncio
    async def test_collect_handles_empty_gpt_response(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: GPT クライアントが空または空白のみの応答を返す。
        When: collect が呼ばれたとき。
        Then: 記事の要約に ERROR_MSG_EMPTY_SUMMARY が含まれる。
        """
        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]

        # Test cases: empty string and whitespace-only string
        for empty_response in ["", "   ", "\n\t"]:
            with patch.object(
                explorer.client, "get_latest_news", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = mock_news
                explorer.gpt_client = MagicMock()
                explorer.gpt_client.generate_async = AsyncMock(
                    return_value=empty_response
                )

                captured_articles: list = []

                def create_capture_store(target_list):
                    async def _capture_store(articles, date_str):
                        target_list.extend(articles)
                        return [(f"mock/{date_str}.json", f"mock/{date_str}.md")]

                    return _capture_store

                capture_store = create_capture_store(captured_articles)

                with patch.object(
                    explorer, "_store_articles", side_effect=capture_store
                ):
                    result = await explorer.collect(days=1, limit=10)

                assert isinstance(result, list)
                assert len(captured_articles) >= 1
                assert (
                    captured_articles[-1].summary
                    == ZhihuExplorer.ERROR_MSG_EMPTY_SUMMARY
                ), f"Failed for empty_response: {repr(empty_response)}"

    @pytest.mark.asyncio
    async def test_collect_handles_cancelled_error_in_summary(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: 要約生成中に CancelledError が発生する。
        When: collect が呼ばれたとき。
        Then: 記事は空のsummaryで保存される。

        Note: return_exceptions=True を使用しているため、CancelledError は
        results に含まれる。しかし、CancelledError は BaseException の
        サブクラスであり、isinstance(result, Exception) チェックに該当しない。
        そのため、エラーメッセージが設定されず、空のsummaryのまま処理が継続される。
        """
        import asyncio

        mock_news = [{"title": "Test", "url": "http://test", "hot": 100}]
        with patch.object(
            explorer.client, "get_latest_news", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_news
            # Mock gpt_client.generate_async to raise CancelledError
            explorer.gpt_client = MagicMock()
            explorer.gpt_client.generate_async = AsyncMock(
                side_effect=asyncio.CancelledError()
            )

            # Patch _store_articles to capture articles without real I/O
            captured_articles: list = []

            async def capture_store(articles, date_str):
                captured_articles.extend(articles)
                return [(f"mock/{date_str}.json", f"mock/{date_str}.md")]

            with patch.object(explorer, "_store_articles", side_effect=capture_store):
                # collectは正常に完了する
                result = await explorer.collect(days=1, limit=10)

            # CancelledError は BaseException なので Exception チェックに該当せず、
            # 空のsummaryのまま保存される
            assert isinstance(result, list)
            assert len(captured_articles) == 1
            assert captured_articles[0].summary == ""


class TestZhihuExplorerRun:
    """ZhihuExplorer.runメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """テスト用のZhihuExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer(storage_dir=str(tmp_path))
        # Mock storage to prevent disk I/O (though run() mocks collect, it's safer)
        explorer.storage = AsyncMock()
        return explorer

    def test_run_calls_run_with_cleanup(self, explorer: ZhihuExplorer) -> None:
        """
        Given: ZhihuExplorer インスタンス。
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
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: ZhihuExplorer インスタンス。
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
    async def test_base_service_cleanup_on_error(self, explorer: ZhihuExplorer) -> None:
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
        self, explorer: ZhihuExplorer
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


class TestZhihuExplorerContextManager:
    """ZhihuExplorerのコンテキストマネージャーメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """テスト用のZhihuExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer(storage_dir=str(tmp_path))

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, explorer: ZhihuExplorer) -> None:
        """
        Given: async with ステートメントで使用される ZhihuExplorer。
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
        self, explorer: ZhihuExplorer
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
            mock_close.assert_called_once()


class TestZhihuExplorerRenderMarkdown:
    """ZhihuExplorer._render_markdownメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """テスト用のZhihuExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer(storage_dir=str(tmp_path))

    def test_render_markdown_with_normal_records(self, explorer: ZhihuExplorer) -> None:
        """
        Given: 特殊文字を含まない通常のレコード。
        When: _render_markdown が呼ばれたとき。
        Then: Markdown が正しく生成される。
        """
        records = [
            {
                "title": "Test Title",
                "url": "https://example.com",
                "summary": "Test summary",
                "popularity_score": 1000,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        assert "# 知乎ホットトピック (2024-01-15)" in result
        assert "[Test Title](https://example.com)" in result
        assert "**人気度**: 1,000" in result
        assert "**要約**:" in result
        assert "Test summary" in result

    def test_render_markdown_escapes_title_brackets(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: タイトルに角括弧を含むレコード。
        When: _render_markdown が呼ばれたとき。
        Then: Markdown リンクの破損を防ぐために角括弧がエスケープされる。
        """
        records = [
            {
                "title": "[Important] Test Topic",
                "url": "https://example.com",
                "summary": "Summary",
                "popularity_score": 500,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        # Brackets should be escaped
        assert "\\[Important\\]" in result

    def test_render_markdown_escapes_url_parentheses(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: URL に括弧を含むレコード。
        When: _render_markdown が呼ばれたとき。
        Then: 開き括弧と閉じ括弧の両方がエスケープされる。
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

        # Both opening and closing parentheses should be escaped
        assert "path\\(with\\)parens" in result

    def test_render_markdown_preserves_summary_markdown(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: 要約に Markdown 文字を含むレコード。
        When: _render_markdown が呼ばれたとき。
        Then: 要約は既にMarkdown形式で構造化されているため、エスケープせずそのまま出力する。
        """
        records = [
            {
                "title": "Test",
                "url": "https://example.com",
                "summary": "See [this link](url) for details",
                "popularity_score": 100,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        # Summary should NOT be escaped (markdown is preserved)
        assert "[this link](url)" in result

    def test_render_markdown_escapes_html_characters(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: HTML 特殊文字を含むレコード。
        When: _render_markdown が呼ばれたとき。
        Then: タイトルのHTML文字がエスケープされる（要約はエスケープしない）。
        """
        records = [
            {
                "title": "Test <script>alert('xss')</script>",
                "url": "https://example.com",
                "summary": "<b>Bold</b> text",
                "popularity_score": 100,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        # Title HTML should be escaped
        assert "&lt;script&gt;" in result
        # Summary HTML should NOT be escaped (markdown is preserved)
        assert "<b>Bold</b>" in result

    def test_render_markdown_escapes_url_brackets(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: URL に角括弧を含むレコード。
        When: _render_markdown が呼ばれたとき。
        Then: URL 内の角括弧がエスケープされる。
        """
        records = [
            {
                "title": "Test",
                "url": "https://example.com/path[with]brackets",
                "summary": "Summary",
                "popularity_score": 100,
            }
        ]
        result = explorer._render_markdown(records, "2024-01-15")

        # Brackets in URL should be escaped
        assert "path\\[with\\]brackets" in result

    def test_escape_markdown_url_escapes_all_special_chars(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: Markdown を壊すすべての文字を含む URL。
        When: _escape_markdown_url が呼ばれたとき。
        Then: すべての特殊文字がエスケープされる。
        """
        url = "https://example.com/test[1](2)"
        result = explorer._escape_markdown_url(url)

        assert "\\[" in result
        assert "\\]" in result
        assert "\\(" in result
        assert "\\)" in result
        assert result == "https://example.com/test\\[1\\]\\(2\\)"


class TestZhihuExplorerParsePopularityScore:
    """ZhihuExplorer._parse_popularity_scoreメソッドのテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """テスト用のZhihuExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        return ZhihuExplorer(storage_dir=str(tmp_path))

    def test_parse_popularity_score_with_int(self, explorer: ZhihuExplorer) -> None:
        """
        Given: 整数値。
        When: _parse_popularity_score が呼ばれたとき。
        Then: 値の float を返す。
        """
        assert explorer._parse_popularity_score(1000) == 1000.0

    def test_parse_popularity_score_with_float(self, explorer: ZhihuExplorer) -> None:
        """
        Given: float 値。
        When: _parse_popularity_score が呼ばれたとき。
        Then: float をそのまま返す。
        """
        assert explorer._parse_popularity_score(1234.5) == 1234.5

    def test_parse_popularity_score_with_string_number(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: 数値の文字列表現。
        When: _parse_popularity_score が呼ばれたとき。
        Then: 解析された値の float を返す。
        """
        assert explorer._parse_popularity_score("1500") == 1500.0

    def test_parse_popularity_score_with_none(self, explorer: ZhihuExplorer) -> None:
        """
        Given: None 値。
        When: _parse_popularity_score が呼ばれたとき。
        Then: 0.0 を返す。
        """
        assert explorer._parse_popularity_score(None) == 0.0

    def test_parse_popularity_score_with_invalid_string(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: 数値以外の文字列。
        When: _parse_popularity_score が呼ばれたとき。
        Then: 0.0 を返す。
        """
        assert explorer._parse_popularity_score("N/A") == 0.0
        assert explorer._parse_popularity_score("invalid") == 0.0

    def test_parse_popularity_score_with_negative(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: 負の数。
        When: _parse_popularity_score が呼ばれたとき。
        Then: 負の float を返す (検証なし)。
        """
        assert explorer._parse_popularity_score(-100) == -100.0

    def test_parse_popularity_score_with_zero(self, explorer: ZhihuExplorer) -> None:
        """
        Given: ゼロ値。
        When: _parse_popularity_score が呼ばれたとき。
        Then: 0.0 を返す。
        """
        assert explorer._parse_popularity_score(0) == 0.0

    def test_parse_popularity_score_with_bool(self, explorer: ZhihuExplorer) -> None:
        """
        Given: ブール値。
        When: _parse_popularity_score が呼ばれたとき。
        Then: True の場合は 1.0、False の場合は 0.0 を返す (bool は int のサブクラス)。

        Note: boolはintのサブクラスなので、float(True)=1.0, float(False)=0.0 となる。
        この動作は _parse_published_at の bool 除外とは異なり、popularity_score では
        現状の実装上許容される動作である。
        """
        # bool is subclass of int in Python, so float(True) = 1.0
        assert explorer._parse_popularity_score(True) == 1.0
        assert explorer._parse_popularity_score(False) == 0.0

    def test_parse_popularity_score_with_formatted_string(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: カンマまたはプラス記号を含む文字列値 (例: "1,234" または "+500")。
        When: _parse_popularity_score が呼ばれたとき。
        Then: 書式設定が正規化された解析済みの float 値を返す。
        """
        # カンマ区切りの数値文字列
        assert explorer._parse_popularity_score("1,234") == 1234.0
        assert explorer._parse_popularity_score("1,234,567") == 1234567.0

        # プラス記号付きの数値文字列
        assert explorer._parse_popularity_score("+500") == 500.0
        assert explorer._parse_popularity_score("+1,234") == 1234.0

        # 空白を含む文字列
        assert explorer._parse_popularity_score("  1500  ") == 1500.0
        assert explorer._parse_popularity_score(" +1,000 ") == 1000.0

    def test_parse_popularity_score_with_suffix_notation(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: サフィックス表記を含む文字列値 (例: "12.3k" または "1.5万")。
        When: _parse_popularity_score が呼ばれたとき。
        Then: 現在の実装ではパースできないため 0.0 を返す。

        Note: TrendRadar APIがサフィックス系の値を返す可能性がある場合は、
        将来実装を拡張してこれらをパースできるようにする必要があります。
        そのときはテストの期待値を更新してください。
        """
        # 現在の実装では「k」「万」等のサフィックスはパースできず0.0を返す
        assert explorer._parse_popularity_score("12.3k") == 0.0
        assert explorer._parse_popularity_score("1.5万") == 0.0
        assert explorer._parse_popularity_score("2K") == 0.0
        assert explorer._parse_popularity_score("100万+") == 0.0


class TestZhihuExplorerTargetDatesValidation:
    """target_datesとdaysパラメータのバリデーションテスト。"""

    @pytest.fixture
    def explorer(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> ZhihuExplorer:
        """テスト用のZhihuExplorerインスタンスを作成。"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-testing")
        explorer = ZhihuExplorer(storage_dir=str(tmp_path))
        explorer.storage = AsyncMock()
        return explorer

    @pytest.mark.asyncio
    async def test_collect_rejects_target_dates_with_days_not_one(
        self, explorer: ZhihuExplorer
    ) -> None:
        """
        Given: target_dates が提供され、かつ days != 1。
        When: collect が呼ばれたとき。
        Then: days != 1 の ValueError を発生させる (一貫性のため days チェックが最初に行われる)。
        """
        # days != 1 チェックが最初に実行されるため、「複数日の収集」エラーが発生
        with pytest.raises(ValueError, match="複数日の収集"):
            await explorer.collect(target_dates=[date(2024, 1, 15)], days=2)
