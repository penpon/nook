"""Tests for run_services_sync module.

This module tests the service runner functions in run_services_sync.py:
- Individual service runner functions
- Main function with argument parsing
- Error handling and logging
"""

from unittest.mock import MagicMock, patch
import os
import sys

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from nook.services.run_services_sync import (
    run_fivechan_explorer,
    run_reddit_explorer,
    run_github_trending,
    run_hacker_news,
    run_note_explorer,
    run_zenn_explorer,
    run_qiita_explorer,
    run_tech_feed,
    run_business_feed,
    run_arxiv_summarizer,
    run_fourchan_explorer,
    main,
)


class TestRunFiveChanExplorer:
    """Tests for run_fivechan_explorer function."""

    @patch("nook.services.run_services_sync.FiveChanExplorer")
    @patch("builtins.print")
    def test_run_fivechan_explorer_success(
        self, mock_print, mock_explorer_class
    ) -> None:
        """
        Given: A working FiveChanExplorer.
        When: run_fivechan_explorer is called.
        Then: The explorer is instantiated and run() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_fivechan_explorer()

        mock_explorer_class.assert_called_once()
        mock_explorer.run.assert_called_once()
        mock_print.assert_any_call("5chanからAI関連スレッドを収集しています...")
        mock_print.assert_any_call("5chanからのAI関連スレッド収集が完了しました。")

    @patch("nook.services.run_services_sync.FiveChanExplorer")
    @patch("builtins.print")
    def test_run_fivechan_explorer_exception(
        self, mock_print, mock_explorer_class
    ) -> None:
        """
        Given: FiveChanExplorer raises an exception.
        When: run_fivechan_explorer is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.run.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_fivechan_explorer()

        mock_print.assert_any_call("5chanからAI関連スレッドを収集しています...")
        mock_print.assert_any_call(
            "5chanからのAI関連スレッド収集中にエラーが発生しました: Test error"
        )


class TestRunRedditExplorer:
    """Tests for run_reddit_explorer function."""

    @patch.dict(
        os.environ,
        {"REDDIT_CLIENT_ID": "test-id", "REDDIT_CLIENT_SECRET": "test-secret"},
    )
    @patch("nook.services.run_services_sync.RedditExplorer")
    @patch("builtins.print")
    def test_run_reddit_explorer_success(self, mock_print, mock_explorer_class) -> None:
        """
        Given: A working RedditExplorer with credentials.
        When: run_reddit_explorer is called.
        Then: The explorer is instantiated and run() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_reddit_explorer()

        mock_explorer_class.assert_called_once()
        mock_explorer.run.assert_called_once()
        mock_print.assert_any_call("Reddit投稿を収集しています...")
        mock_print.assert_any_call("Reddit投稿の収集が完了しました。")

    @patch.dict(os.environ, {}, clear=True)
    @patch("builtins.print")
    def test_run_reddit_explorer_missing_credentials(self, mock_print) -> None:
        """
        Given: Missing Reddit API credentials.
        When: run_reddit_explorer is called.
        Then: Warning is printed and function returns early.
        """
        run_reddit_explorer()

        mock_print.assert_any_call("Reddit投稿を収集しています...")
        mock_print.assert_any_call(
            "警告: REDDIT_CLIENT_ID または REDDIT_CLIENT_SECRET が設定されていません。"
        )
        mock_print.assert_any_call(
            "Reddit APIを使用するには、これらの環境変数を設定してください。"
        )

    @patch.dict(
        os.environ,
        {"REDDIT_CLIENT_ID": "test-id", "REDDIT_CLIENT_SECRET": "test-secret"},
    )
    @patch("nook.services.run_services_sync.RedditExplorer")
    @patch("builtins.print")
    def test_run_reddit_explorer_exception(
        self, mock_print, mock_explorer_class
    ) -> None:
        """
        Given: RedditExplorer raises an exception.
        When: run_reddit_explorer is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.run.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_reddit_explorer()

        mock_print.assert_any_call("Reddit投稿を収集しています...")
        mock_print.assert_any_call(
            "Reddit投稿の収集中にエラーが発生しました: Test error"
        )


class TestRunGitHubTrending:
    """Tests for run_github_trending function."""

    @patch("nook.services.run_services_sync.GithubTrending")
    @patch("builtins.print")
    def test_run_github_trending_success(self, mock_print, mock_explorer_class) -> None:
        """
        Given: A working GithubTrending.
        When: run_github_trending is called.
        Then: The explorer is instantiated and collect() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_github_trending()

        mock_explorer_class.assert_called_once()
        mock_explorer.collect.assert_called_once()
        mock_print.assert_any_call("GitHubのトレンドリポジトリを収集しています...")
        mock_print.assert_any_call("GitHubのトレンドリポジトリ収集が完了しました。")

    @patch("nook.services.run_services_sync.GithubTrending")
    @patch("builtins.print")
    def test_run_github_trending_exception(
        self, mock_print, mock_explorer_class
    ) -> None:
        """
        Given: GithubTrending raises an exception.
        When: run_github_trending is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.collect.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_github_trending()

        mock_print.assert_any_call("GitHubのトレンドリポジトリを収集しています...")
        mock_print.assert_any_call(
            "GitHubのトレンドリポジトリ収集中にエラーが発生しました: Test error"
        )


class TestRunHackerNews:
    """Tests for run_hacker_news function."""

    @patch("nook.services.run_services_sync.HackerNewsRetriever")
    @patch("builtins.print")
    def test_run_hacker_news_success(self, mock_print, mock_explorer_class) -> None:
        """
        Given: A working HackerNewsRetriever.
        When: run_hacker_news is called.
        Then: The explorer is instantiated and run() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_hacker_news()

        mock_explorer_class.assert_called_once()
        mock_explorer.run.assert_called_once()
        mock_print.assert_any_call("Hacker Newsの人気記事を収集しています...")
        mock_print.assert_any_call("Hacker Newsの人気記事収集が完了しました。")

    @patch("nook.services.run_services_sync.HackerNewsRetriever")
    @patch("builtins.print")
    def test_run_hacker_news_exception(self, mock_print, mock_explorer_class) -> None:
        """
        Given: HackerNewsRetriever raises an exception.
        When: run_hacker_news is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.run.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_hacker_news()

        mock_print.assert_any_call("Hacker Newsの人気記事を収集しています...")
        mock_print.assert_any_call(
            "Hacker Newsの人気記事収集中にエラーが発生しました: Test error"
        )


class TestRunNoteExplorer:
    """Tests for run_note_explorer function."""

    @patch("nook.services.run_services_sync.NoteExplorer")
    @patch("builtins.print")
    def test_run_note_explorer_success(self, mock_print, mock_explorer_class) -> None:
        """
        Given: A working NoteExplorer.
        When: run_note_explorer is called.
        Then: The explorer is instantiated and run() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_note_explorer()

        mock_explorer_class.assert_called_once()
        mock_explorer.run.assert_called_once()
        mock_print.assert_any_call("Noteの技術記事を収集しています...")
        mock_print.assert_any_call("Noteの技術記事収集が完了しました。")

    @patch("nook.services.run_services_sync.NoteExplorer")
    @patch("builtins.print")
    def test_run_note_explorer_exception(self, mock_print, mock_explorer_class) -> None:
        """
        Given: NoteExplorer raises an exception.
        When: run_note_explorer is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.run.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_note_explorer()

        mock_print.assert_any_call("Noteの技術記事を収集しています...")
        mock_print.assert_any_call(
            "Noteの技術記事収集中にエラーが発生しました: Test error"
        )


class TestRunZennExplorer:
    """Tests for run_zenn_explorer function."""

    @patch("nook.services.run_services_sync.ZennExplorer")
    @patch("builtins.print")
    def test_run_zenn_explorer_success(self, mock_print, mock_explorer_class) -> None:
        """
        Given: A working ZennExplorer.
        When: run_zenn_explorer is called.
        Then: The explorer is instantiated and run() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_zenn_explorer()

        mock_explorer_class.assert_called_once()
        mock_explorer.run.assert_called_once()
        mock_print.assert_any_call("Zennの技術記事を収集しています...")
        mock_print.assert_any_call("Zennの技術記事収集が完了しました。")

    @patch("nook.services.run_services_sync.ZennExplorer")
    @patch("builtins.print")
    def test_run_zenn_explorer_exception(self, mock_print, mock_explorer_class) -> None:
        """
        Given: ZennExplorer raises an exception.
        When: run_zenn_explorer is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.run.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_zenn_explorer()

        mock_print.assert_any_call("Zennの技術記事を収集しています...")
        mock_print.assert_any_call(
            "Zennの技術記事収集中にエラーが発生しました: Test error"
        )


class TestRunQiitaExplorer:
    """Tests for run_qiita_explorer function."""

    @patch("nook.services.run_services_sync.QiitaExplorer")
    @patch("builtins.print")
    def test_run_qiita_explorer_success(self, mock_print, mock_explorer_class) -> None:
        """
        Given: A working QiitaExplorer.
        When: run_qiita_explorer is called.
        Then: The explorer is instantiated and run() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_qiita_explorer()

        mock_explorer_class.assert_called_once()
        mock_explorer.run.assert_called_once()
        mock_print.assert_any_call("Qiitaの技術記事を収集しています...")
        mock_print.assert_any_call("Qiitaの技術記事収集が完了しました。")

    @patch("nook.services.run_services_sync.QiitaExplorer")
    @patch("builtins.print")
    def test_run_qiita_explorer_exception(
        self, mock_print, mock_explorer_class
    ) -> None:
        """
        Given: QiitaExplorer raises an exception.
        When: run_qiita_explorer is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.run.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_qiita_explorer()

        mock_print.assert_any_call("Qiitaの技術記事を収集しています...")
        mock_print.assert_any_call(
            "Qiitaの技術記事収集中にエラーが発生しました: Test error"
        )


class TestRunTechFeed:
    """Tests for run_tech_feed function."""

    @patch("nook.services.run_services_sync.TechFeed")
    @patch("builtins.print")
    def test_run_tech_feed_success(self, mock_print, mock_explorer_class) -> None:
        """
        Given: A working TechFeed.
        When: run_tech_feed is called.
        Then: The explorer is instantiated and run() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_tech_feed()

        mock_explorer_class.assert_called_once()
        mock_explorer.run.assert_called_once()
        mock_print.assert_any_call("Tech系ニュースを収集しています...")
        mock_print.assert_any_call("Tech系ニュース収集が完了しました。")

    @patch("nook.services.run_services_sync.TechFeed")
    @patch("builtins.print")
    def test_run_tech_feed_exception(self, mock_print, mock_explorer_class) -> None:
        """
        Given: TechFeed raises an exception.
        When: run_tech_feed is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.run.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_tech_feed()

        mock_print.assert_any_call("Tech系ニュースを収集しています...")
        mock_print.assert_any_call(
            "Tech系ニュース収集中にエラーが発生しました: Test error"
        )


class TestRunBusinessFeed:
    """Tests for run_business_feed function."""

    @patch("nook.services.run_services_sync.BusinessFeed")
    @patch("builtins.print")
    def test_run_business_feed_success(self, mock_print, mock_explorer_class) -> None:
        """
        Given: A working BusinessFeed.
        When: run_business_feed is called.
        Then: The explorer is instantiated and run() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_business_feed()

        mock_explorer_class.assert_called_once()
        mock_explorer.run.assert_called_once()
        mock_print.assert_any_call("ビジネスニュースを収集しています...")
        mock_print.assert_any_call("ビジネスニュース収集が完了しました。")

    @patch("nook.services.run_services_sync.BusinessFeed")
    @patch("builtins.print")
    def test_run_business_feed_exception(self, mock_print, mock_explorer_class) -> None:
        """
        Given: BusinessFeed raises an exception.
        When: run_business_feed is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.run.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_business_feed()

        mock_print.assert_any_call("ビジネスニュースを収集しています...")
        mock_print.assert_any_call(
            "ビジネスニュース収集中にエラーが発生しました: Test error"
        )


class TestRunArxivSummarizer:
    """Tests for run_arxiv_summarizer function."""

    @patch("nook.services.run_services_sync.ArxivSummarizer")
    @patch("builtins.print")
    def test_run_arxiv_summarizer_success(
        self, mock_print, mock_explorer_class
    ) -> None:
        """
        Given: A working ArxivSummarizer.
        When: run_arxiv_summarizer is called.
        Then: The explorer is instantiated and run() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_arxiv_summarizer()

        mock_explorer_class.assert_called_once()
        mock_explorer.run.assert_called_once()
        mock_print.assert_any_call("ArXivの論文を要約しています...")
        mock_print.assert_any_call("ArXivの論文要約が完了しました。")

    @patch("nook.services.run_services_sync.ArxivSummarizer")
    @patch("builtins.print")
    def test_run_arxiv_summarizer_exception(
        self, mock_print, mock_explorer_class
    ) -> None:
        """
        Given: ArxivSummarizer raises an exception.
        When: run_arxiv_summarizer is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.run.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_arxiv_summarizer()

        mock_print.assert_any_call("ArXivの論文を要約しています...")
        mock_print.assert_any_call(
            "ArXivの論文要約中にエラーが発生しました: Test error"
        )


class TestRunFourChanExplorer:
    """Tests for run_fourchan_explorer function."""

    @patch("nook.services.run_services_sync.FourChanExplorer")
    @patch("builtins.print")
    def test_run_fourchan_explorer_success(
        self, mock_print, mock_explorer_class
    ) -> None:
        """
        Given: A working FourChanExplorer.
        When: run_fourchan_explorer is called.
        Then: The explorer is instantiated and run() is called.
        """
        mock_explorer = MagicMock()
        mock_explorer_class.return_value = mock_explorer

        run_fourchan_explorer()

        mock_explorer_class.assert_called_once()
        mock_explorer.run.assert_called_once()
        mock_print.assert_any_call("4chanの技術板からスレッドを収集しています...")
        mock_print.assert_any_call("4chanの技術板スレッド収集が完了しました。")

    @patch("nook.services.run_services_sync.FourChanExplorer")
    @patch("builtins.print")
    def test_run_fourchan_explorer_exception(
        self, mock_print, mock_explorer_class
    ) -> None:
        """
        Given: FourChanExplorer raises an exception.
        When: run_fourchan_explorer is called.
        Then: Error is caught and printed.
        """
        mock_explorer = MagicMock()
        mock_explorer.run.side_effect = Exception("Test error")
        mock_explorer_class.return_value = mock_explorer

        run_fourchan_explorer()

        mock_print.assert_any_call("4chanの技術板からスレッドを収集しています...")
        mock_print.assert_any_call(
            "4chanの技術板スレッド収集中にエラーが発生しました: Test error"
        )


class TestMain:
    """Tests for main function."""

    @patch("nook.services.run_services_sync.ArgumentParser")
    @patch("nook.services.run_services_sync.run_fivechan_explorer")
    @patch("builtins.print")
    def test_main_fivechan_argument(
        self, mock_print, mock_runner, mock_parser_class
    ) -> None:
        """
        Given: Command line argument '5chan'.
        When: main is called.
        Then: run_fivechan_explorer is called.
        """
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = MagicMock(service="5chan")
        mock_parser_class.return_value = mock_parser

        main()

        mock_parser_class.assert_called_once()
        mock_parser.parse_args.assert_called_once()
        mock_runner.assert_called_once()

    @patch("nook.services.run_services_sync.ArgumentParser")
    @patch("nook.services.run_services_sync.run_reddit_explorer")
    @patch("builtins.print")
    def test_main_reddit_argument(
        self, mock_print, mock_runner, mock_parser_class
    ) -> None:
        """
        Given: Command line argument 'reddit'.
        When: main is called.
        Then: run_reddit_explorer is called.
        """
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = MagicMock(service="reddit")
        mock_parser_class.return_value = mock_parser

        main()

        mock_runner.assert_called_once()

    @patch("nook.services.run_services_sync.ArgumentParser")
    @patch("builtins.print")
    def test_main_all_argument(self, mock_print, mock_parser_class) -> None:
        """
        Given: Command line argument 'all'.
        When: main is called.
        Then: All service runners are called.
        """
        with patch.multiple(
            "nook.services.run_services_sync",
            run_fivechan_explorer=MagicMock(),
            run_reddit_explorer=MagicMock(),
            run_github_trending=MagicMock(),
            run_hacker_news=MagicMock(),
            run_note_explorer=MagicMock(),
            run_zenn_explorer=MagicMock(),
            run_qiita_explorer=MagicMock(),
            run_tech_feed=MagicMock(),
            run_business_feed=MagicMock(),
            run_arxiv_summarizer=MagicMock(),
            run_fourchan_explorer=MagicMock(),
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = MagicMock(service="all")
            mock_parser_class.return_value = mock_parser

            main()

            # Verify all service runners were called
            from nook.services import run_services_sync

            run_services_sync.run_fivechan_explorer.assert_called_once()
            run_services_sync.run_reddit_explorer.assert_called_once()
            run_services_sync.run_github_trending.assert_called_once()
            run_services_sync.run_hacker_news.assert_called_once()
            run_services_sync.run_note_explorer.assert_called_once()
            run_services_sync.run_zenn_explorer.assert_called_once()
            run_services_sync.run_qiita_explorer.assert_called_once()
            run_services_sync.run_tech_feed.assert_called_once()
            run_services_sync.run_business_feed.assert_called_once()
            run_services_sync.run_arxiv_summarizer.assert_called_once()
            run_services_sync.run_fourchan_explorer.assert_called_once()
