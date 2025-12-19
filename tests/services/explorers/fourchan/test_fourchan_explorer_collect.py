from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.services.explorers.fourchan.fourchan_explorer import FourChanExplorer, Thread


@pytest.fixture
def fourchan_explorer(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    explorer = FourChanExplorer(test_mode=True)
    explorer.http_client = AsyncMock()
    explorer.storage = AsyncMock()
    explorer.logger = MagicMock()
    explorer.target_boards = ["g"]
    return explorer


class TestHelpers:
    def test_extract_thread_id_from_url(self, fourchan_explorer):
        assert fourchan_explorer._extract_thread_id_from_url("https://boards.4chan.org/g/thread/12345") == 12345
        assert fourchan_explorer._extract_thread_id_from_url("https://boards.4chan.org/g/thread/12345#p123") == 12345
        assert fourchan_explorer._extract_thread_id_from_url("https://boards.4chan.org/g/thread/12345/") == 12345
        assert fourchan_explorer._extract_thread_id_from_url("invalid") == 0

    def test_calculate_popularity(self, fourchan_explorer):
        meta = {"replies": 10, "images": 2, "bumps": 5}
        posts = [{}, {}, {}]  # 3 posts
        # popularity = 10 + 2*2 + 5 + 3 + recency
        # recency: last_modified or time.
        # If missing, recency = 0
        pop = fourchan_explorer._calculate_popularity(meta, posts)
        assert pop >= 22.0

    def test_thread_sort_key(self, fourchan_explorer):
        item = {"popularity_score": 10.0, "published_at": "2023-01-01T12:00:00+00:00"}
        key = fourchan_explorer._thread_sort_key(item)
        assert key[0] == 10.0
        assert key[1].year == 2023


class TestRetrieveAIThreads:
    @pytest.mark.asyncio
    async def test_retrieve_ai_threads_success(self, fourchan_explorer):
        # Explicit mock response
        mock_response = MagicMock()
        mock_response.json.side_effect = [
            [
                {
                    "threads": [
                        {
                            "no": 1,
                            "sub": "AI thread using GPT",
                            "com": "comment",
                            "time": 1672531200,  # 2023-01-01 00:00:00 UTC
                            "last_modified": 1672534800,
                        },
                        {"no": 2, "sub": "Not related", "com": "foo"},
                    ]
                }
            ],  # catalog
            {"posts": [{"no": 1, "com": "OP"}]},  # thread posts
        ]
        fourchan_explorer.http_client.get.return_value = mock_response

        mock_dedup = MagicMock()
        mock_dedup.is_duplicate.return_value = (False, "title")

        with patch(
            "nook.services.explorers.fourchan.fourchan_explorer.is_within_target_dates",
            return_value=True,
        ):
            threads = await fourchan_explorer._retrieve_ai_threads("g", None, mock_dedup, [date(2023, 1, 1)])

            assert len(threads) == 1
            assert threads[0].thread_id == 1

    @pytest.mark.asyncio
    async def test_retrieve_ai_threads_filtering(self, fourchan_explorer):
        mock_response = MagicMock()
        mock_response.json.side_effect = [
            [
                {
                    "threads": [
                        {"no": 1, "sub": "AI", "time": 100},
                        {"no": 2, "sub": "AI 2", "time": 100, "last_modified": 200},
                        {"no": 3, "sub": "AI 3", "time": 100, "last_modified": 100},
                    ]
                }
            ],
            {"posts": []},  # thread 3
        ]
        fourchan_explorer.http_client.get.return_value = mock_response

        mock_dedup = MagicMock()

        def is_dup(title):
            return (True, title) if title == "AI" else (False, title)

        mock_dedup.is_duplicate.side_effect = is_dup
        mock_dedup.get_original_title.return_value = "orig"

        with patch("nook.services.explorers.fourchan.fourchan_explorer.is_within_target_dates") as mock_date:
            # 1 (Dup) -> skipped before date check?
            # Logic: is_dup checked first.
            # 2 (Date skip) -> last_modified checked -> returns False
            # 3 (No posts) -> last_modified checked -> returns True -> _retrieve_thread_posts (empty) -> skipped
            mock_date.side_effect = [False, True]

            threads = await fourchan_explorer._retrieve_ai_threads("g", None, mock_dedup, [date(2023, 1, 1)])

            assert len(threads) == 0


class TestCollect:
    @pytest.mark.asyncio
    async def test_collect_flow(self, fourchan_explorer):
        fourchan_explorer.setup_http_client = AsyncMock()
        fourchan_explorer._load_existing_titles = MagicMock()
        fourchan_explorer._store_summaries = AsyncMock(return_value=[("path.json", "path.md")])
        fourchan_explorer._summarize_thread = AsyncMock()

        # Timestamp must match target date (today/yesterday usually)
        # We can pass explicit target_dates to collect
        now_ts = int(datetime.now().timestamp())
        t1 = Thread(
            thread_id=1,
            title="AI",
            url="u",
            board="g",
            posts=[],
            timestamp=now_ts,
            popularity_score=10,
        )

        fourchan_explorer._retrieve_ai_threads = AsyncMock(return_value=[t1])

        saved = await fourchan_explorer.collect(thread_limit=1, target_dates=[datetime.now().date()])

        assert len(saved) == 1
        assert saved[0] == ("path.json", "path.md")
        fourchan_explorer._store_summaries.assert_awaited()

    @pytest.mark.asyncio
    async def test_collect_no_threads(self, fourchan_explorer):
        fourchan_explorer.setup_http_client = AsyncMock()
        fourchan_explorer._load_existing_titles = MagicMock()
        fourchan_explorer._retrieve_ai_threads = AsyncMock(return_value=[])

        saved = await fourchan_explorer.collect()
        assert len(saved) == 0


class TestStoreSummaries:
    @pytest.mark.asyncio
    async def test_store_summaries_empty(self, fourchan_explorer):
        res = await fourchan_explorer._store_summaries([], [])
        assert res == []

    @pytest.mark.asyncio
    async def test_store_summaries_success(self, fourchan_explorer):
        t1 = Thread(thread_id=1, title="AI", url="u", board="g", posts=[], timestamp=100)

        with (
            patch(
                "nook.services.explorers.fourchan.fourchan_explorer.group_records_by_date",
                return_value={"2023-01-01": []},
            ),
            patch(
                "nook.services.explorers.fourchan.fourchan_explorer.store_daily_snapshots",
                new_callable=AsyncMock,
            ) as mock_store,
        ):
            mock_store.return_value = [("f.json", "f.md")]

            res = await fourchan_explorer._store_summaries([t1], [date(2023, 1, 1)])
            assert res == [("f.json", "f.md")]


class TestComponents:
    @pytest.mark.asyncio
    async def test_summarize_thread(self, fourchan_explorer):
        fourchan_explorer.gpt_client.generate_content = MagicMock(return_value="Summary")
        t = Thread(
            thread_id=1,
            title="T",
            url="u",
            board="g",
            posts=[{"com": "OP"}, {"com": "Rep"}],
            timestamp=100,
        )

        await fourchan_explorer._summarize_thread(t)

        assert t.summary == "Summary"
        assert "OP" in fourchan_explorer.gpt_client.generate_content.call_args[1]["prompt"]

    @pytest.mark.asyncio
    async def test_summarize_thread_error(self, fourchan_explorer):
        fourchan_explorer.gpt_client.generate_content = MagicMock(side_effect=Exception("Error"))
        t = Thread(thread_id=1, title="T", url="u", board="g", posts=[], timestamp=100)

        await fourchan_explorer._summarize_thread(t)
        assert "エラー" in t.summary

    def test_render_markdown(self, fourchan_explorer):
        records = [
            {
                "board": "g",
                "title": "Title",
                "url": "http://u",
                "timestamp": 1234567890,
                "summary": "Sum",
                "published_at": datetime(2009, 2, 13, 23, 31, 30, tzinfo=timezone.utc).isoformat(),
            }
        ]
        md = fourchan_explorer._render_markdown(records, datetime(2023, 1, 1))
        assert "## /g/" in md
        assert "[Title](http://u)" in md

    def test_parse_markdown(self, fourchan_explorer):
        md = """
## /g/

### [Title](http://u)

作成日時: <t:1234567890:F>

**要約**:
Sum

---
        """
        records = fourchan_explorer._parse_markdown(md)
        assert len(records) == 1
        assert records[0]["title"] == "Title"
        assert records[0]["timestamp"] == 1234567890
        assert records[0]["board"] == "g"

    @pytest.mark.asyncio
    async def test_retrieve_thread_posts_error(self, fourchan_explorer):
        fourchan_explorer.http_client.get.side_effect = Exception("Err")
        posts = await fourchan_explorer._retrieve_thread_posts("g", 1)
        assert posts == []

    @pytest.mark.asyncio
    async def test_load_existing_threads(self, fourchan_explorer):
        # JSON path
        fourchan_explorer.load_json = AsyncMock(return_value={"g": [{"thread_id": 1}]})
        res = await fourchan_explorer._load_existing_threads(datetime(2023, 1, 1))
        assert len(res) == 1
        assert res[0]["board"] == "g"

        # Markdown path
        fourchan_explorer.load_json = AsyncMock(return_value=None)
        fourchan_explorer.storage.load = AsyncMock(
            return_value="## /g/\n\n### [T](u)\n\n作成日時: <t:1:F>\n\n**要約**:\nS\n\n---"
        )
        res = await fourchan_explorer._load_existing_threads(datetime(2023, 1, 1))
        assert len(res) == 1
        assert res[0]["title"] == "T"

    def test_load_existing_titles(self, fourchan_explorer):
        fourchan_explorer.storage.load_markdown = MagicMock(return_value="### [Title](u)")
        tracker = fourchan_explorer._load_existing_titles()
        assert tracker.is_duplicate("Title")[0] is True

    def test_select_top_threads(self, fourchan_explorer):
        # Testing the helper method specifically
        t1 = Thread(
            thread_id=1,
            title="A",
            url="",
            board="",
            posts=[],
            timestamp=100,
            popularity_score=10,
        )
        t2 = Thread(
            thread_id=2,
            title="B",
            url="",
            board="",
            posts=[],
            timestamp=100,
            popularity_score=20,
        )

        res = fourchan_explorer._select_top_threads([t1, t2], limit=1)
        assert len(res) == 1
        assert res[0].popularity_score == 20
