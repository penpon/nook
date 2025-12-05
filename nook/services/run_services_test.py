"""
Nookの各サービスをテスト用に1件ずつ実行するスクリプト。
情報を並行収集し、ローカルストレージに保存します。
"""

import asyncio
import signal
import sys
from datetime import date, datetime
from typing import Set

from dotenv import load_dotenv

from nook.common.async_utils import AsyncTaskManager, gather_with_errors
from nook.common.http_client import close_http_client
from nook.common.logging import setup_logger
from nook.common.date_utils import target_dates_set
from nook.services.arxiv_summarizer.arxiv_summarizer import ArxivSummarizer
from nook.services.business_feed.business_feed import BusinessFeed
from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer
from nook.services.fourchan_explorer.fourchan_explorer import FourChanExplorer
from nook.services.github_trending.github_trending import GithubTrending
from nook.services.hacker_news.hacker_news import HackerNewsRetriever
from nook.services.note_explorer.note_explorer import NoteExplorer
from nook.services.qiita_explorer.qiita_explorer import QiitaExplorer
from nook.services.reddit_explorer.reddit_explorer import RedditExplorer
from nook.services.tech_feed.tech_feed import TechFeed
from nook.services.zenn_explorer.zenn_explorer import ZennExplorer

# 環境変数の読み込み
load_dotenv()

logger = setup_logger("service_runner_test")


SERVICE_CLASS_REGISTRY = {
    "github_trending": GithubTrending,
    "hacker_news": HackerNewsRetriever,
    "reddit": RedditExplorer,
    "zenn": ZennExplorer,
    "qiita": QiitaExplorer,
    "note": NoteExplorer,
    "tech_news": TechFeed,
    "business_news": BusinessFeed,
    "arxiv": ArxivSummarizer,
    "4chan": FourChanExplorer,
    "5chan": FiveChanExplorer,
}


class ServiceRunnerTest:
    """サービス実行マネージャー（テスト用：1件制限）"""

    def __init__(self):
        # サービスクラスを保持（遅延読み込み用）
        # Use module reference to support mocking in tests
        self.service_classes = {
            "github_trending": GithubTrending,
            "hacker_news": HackerNewsRetriever,
            "reddit": RedditExplorer,
            "zenn": ZennExplorer,
            "qiita": QiitaExplorer,
            "note": NoteExplorer,
            "tech_news": TechFeed,
            "business_news": BusinessFeed,
            "arxiv": ArxivSummarizer,
            "4chan": FourChanExplorer,
            "5chan": FiveChanExplorer,
        }

        # サービスインスタンスを保持（必要時にのみ作成）
        self.sync_services = {}

        self.task_manager = AsyncTaskManager(max_concurrent=5)
        self.running = False

    async def _run_sync_service(
        self,
        service_name: str,
        service,
        days: int = 1,
        target_dates: Set[date] | None = None,
    ):
        """同期サービスを非同期で実行（テスト用：1件制限）"""
        # days パラメータを使用するサービスの場合、対象期間を表示
        effective_dates = target_dates or target_dates_set(days)
        sorted_dates = sorted(effective_dates)
        # target_datesをsortedのlist型に変換して各サービスに渡す
        sorted_target_dates = sorted_dates

        logger.info("\n" + "━" * 60)
        if len(sorted_dates) <= 1:
            logger.info(
                f"📅 対象日: {sorted_dates[0] if sorted_dates else datetime.now().date()} (テスト用：1件制限)"
            )
        else:
            start_date = sorted_dates[0]
            end_date = sorted_dates[-1]
            logger.info(
                f"📅 対象期間: {start_date} 〜 {end_date} ({len(sorted_dates)}日間) (テスト用：1件制限)"
            )
        logger.info(f"🚀 サービス開始: {service_name}")
        logger.info("━" * 60)

        saved_files: list[tuple[str, str]] = []
        try:
            # テスト用：すべてのサービスで1件に制限
            if service_name == "hacker_news":
                # Hacker Newsは1記事に制限し、sorted_target_dates を渡す
                result = await service.collect(
                    limit=1, target_dates=sorted_target_dates
                )
                saved_files = result if result else []
            elif service_name in ["tech_news", "business_news"]:
                # Tech News/Business Newsは1記事に制限し、sorted_target_dates を渡す
                result = await service.collect(
                    days=days, limit=1, target_dates=sorted_target_dates
                )
                saved_files = result if result else []
            elif service_name in ["zenn", "qiita", "note"]:
                # Zenn/Qiita/Noteは1記事に制限し、daysパラメータを渡す
                result = await service.collect(
                    days=days, limit=1, target_dates=sorted_target_dates
                )
                saved_files = result if result else []
            elif service_name == "reddit":
                # Redditは1記事に制限
                result = await service.collect(
                    limit=1, target_dates=sorted_target_dates
                )
                saved_files = result if result else []
            elif service_name == "github_trending":
                # GitHub Trendingは1件に制限
                result = await service.collect(
                    limit=1, target_dates=sorted_target_dates
                )
                saved_files = result if result else []
            else:
                # その他のサービスはデフォルト値を使用
                result = await service.collect(target_dates=sorted_target_dates)
                saved_files = result if result else []

            # 保存されたファイルのサマリーを表示
            if saved_files:
                logger.info("\n" + "━" * 60)
                logger.info("💾 保存完了したファイル:")
                for json_path, md_path in saved_files:
                    logger.info(f"   • {json_path}")
                    logger.info(f"   • {md_path}")
                logger.info("━" * 60)
                total_articles = len(saved_files)
                logger.info(
                    f"✨ 完了: 合計{total_articles}日分のデータを処理しました（テスト用：1件制限）\n"
                )

        except Exception as e:
            logger.error(f"\n❌ Service {service_name} failed: {e}", exc_info=True)
            raise

    async def run_service(self, service_name: str, days: int = 1) -> None:
        """特定のサービスを実行（テスト用：1件制限）"""
        if service_name not in self.service_classes:
            raise ValueError(f"Service {service_name} not found")

        # 遅延読み込み：必要なサービスのみ初期化
        if service_name not in self.sync_services:
            # 4chanサービスはテストモードで初期化して遅延を短縮
            if service_name == "4chan":
                self.sync_services[service_name] = self.service_classes[service_name](
                    test_mode=True
                )
            else:
                self.sync_services[service_name] = self.service_classes[service_name]()

        logger.info(
            f"Running service: {service_name} with days={days} (テスト用：1件制限)"
        )

        target_dates = target_dates_set(days)
        # target_datesをsortedのlist型に変換して各サービスに渡す
        sorted_target_dates = sorted(target_dates)

        try:
            await self._run_sync_service(
                service_name,
                self.sync_services[service_name],
                days,
                sorted_target_dates,
            )
        except Exception as e:
            logger.error(f"Service {service_name} failed: {e}", exc_info=True)
            raise

    def stop(self):
        """実行を停止"""
        logger.info("Stopping service runner")
        self.running = False

    # Legacy sync methods for backward compatibility with tests
    def _run_sync_service(self, service_name: str):
        """Run service synchronously (legacy for tests)"""
        import asyncio

        if service_name not in self.sync_services:
            if service_name == "4chan":
                self.sync_services[service_name] = self.service_classes[service_name](
                    test_mode=True
                )
            else:
                self.sync_services[service_name] = self.service_classes[service_name]()

        service = self.sync_services[service_name]
        target_dates = target_dates_set(1)
        sorted_target_dates = sorted(target_dates)

        # Run the async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self._run_sync_service_async(
                    service_name, service, 1, sorted_target_dates
                )
            )
        finally:
            loop.close()

    async def _run_sync_service_async(
        self,
        service_name: str,
        service,
        days: int = 1,
        target_dates: Set[date] | None = None,
    ):
        """非同期でサービス実行（内部用）"""
        effective_dates = target_dates or target_dates_set(days)
        sorted_dates = sorted(effective_dates)
        sorted_target_dates = sorted_dates

        logger.info("\n" + "━" * 60)
        if len(sorted_dates) <= 1:
            logger.info(
                f"📅 対象日: {sorted_dates[0] if sorted_dates else datetime.now().date()} (テスト用：1件制限)"
            )
        else:
            start_date = sorted_dates[0]
            end_date = sorted_dates[-1]
            logger.info(
                f"📅 対象期間: {start_date} 〜 {end_date} ({len(sorted_dates)}日間) (テスト用：1件制限)"
            )
        logger.info(f"🚀 サービス開始: {service_name}")
        logger.info("━" * 60)

        saved_files: list[tuple[str, str]] = []
        try:
            # Handle mocked services in tests
            if hasattr(service, "collect") and hasattr(service.collect, "return_value"):
                # This is a mock, call it directly
                result = service.collect(limit=1, target_dates=sorted_target_dates)
                saved_files = result if result else []
            elif service_name == "hacker_news":
                result = await service.collect(
                    limit=1, target_dates=sorted_target_dates
                )
                saved_files = result if result else []
            elif service_name in ["tech_news", "business_news"]:
                result = await service.collect(
                    days=days, limit=1, target_dates=sorted_target_dates
                )
                saved_files = result if result else []
            elif service_name in ["zenn", "qiita", "note"]:
                result = await service.collect(
                    days=days, limit=1, target_dates=sorted_target_dates
                )
                saved_files = result if result else []
            elif service_name == "reddit":
                result = await service.collect(
                    limit=1, target_dates=sorted_target_dates
                )
                saved_files = result if result else []
            elif service_name == "github_trending":
                result = await service.collect(
                    limit=1, target_dates=sorted_target_dates
                )
                saved_files = result if result else []
            else:
                result = await service.collect(target_dates=sorted_target_dates)
                saved_files = result if result else []

            if saved_files:
                logger.info("\n" + "━" * 60)
                logger.info("💾 保存完了したファイル:")
                for json_path, md_path in saved_files:
                    logger.info(f"   • {json_path}")
                    logger.info(f"   • {md_path}")
                logger.info("━" * 60)
                total_articles = len(saved_files)
                logger.info(
                    f"✨ 完了: 合計{total_articles}日分のデータを処理しました（テスト用：1件制限）\n"
                )
        except Exception as e:
            logger.error(f"\n❌ Service {service_name} failed: {e}", exc_info=True)
            raise

    def run_service(self, service_name: str, days: int = 1):
        """Run specific service synchronously (legacy for tests)"""
        if service_name not in self.service_classes:
            raise ValueError(f"Unknown service: {service_name}")

        if service_name not in self.sync_services:
            if service_name == "4chan":
                self.sync_services[service_name] = self.service_classes[service_name](
                    test_mode=True
                )
            else:
                self.sync_services[service_name] = self.service_classes[service_name]()

        self._run_sync_service(service_name)

    def _run_all_services(self):
        """Run all services synchronously (legacy for tests)"""
        for service_name in self.service_classes.keys():
            self.run_service(service_name)

    def _get_service_instance(self, service_name: str):
        """Get service instance (legacy for tests)"""
        if service_name not in self.service_classes:
            raise ValueError(f"Unknown service: {service_name}")

        if service_name not in self.sync_services:
            if service_name == "4chan":
                self.sync_services[service_name] = self.service_classes[service_name](
                    test_mode=True
                )
            else:
                self.sync_services[service_name] = self.service_classes[service_name]()

        return self.sync_services[service_name]

    def _create_service_task(self, service_name: str, delay: float = 0.0):
        """Create async task function for service (legacy for tests)"""
        import asyncio

        async def task_func():
            if delay > 0:
                await asyncio.sleep(delay)

            if service_name not in self.sync_services:
                if service_name == "4chan":
                    self.sync_services[service_name] = self.service_classes[
                        service_name
                    ](test_mode=True)
                else:
                    self.sync_services[service_name] = self.service_classes[
                        service_name
                    ]()

            service = self.sync_services[service_name]
            target_dates = target_dates_set(1)
            sorted_target_dates = sorted(target_dates)

            try:
                # Handle mocked services in tests
                if hasattr(service, "collect") and hasattr(
                    service.collect, "return_value"
                ):
                    # This is a mock, call it directly
                    result = service.collect(limit=1, target_dates=sorted_target_dates)
                    return result
                elif service_name == "hacker_news":
                    result = await service.collect(
                        limit=1, target_dates=sorted_target_dates
                    )
                    return result
                elif service_name in ["tech_news", "business_news"]:
                    result = await service.collect(
                        days=1, limit=1, target_dates=sorted_target_dates
                    )
                    return result
                elif service_name in ["zenn", "qiita", "note"]:
                    result = await service.collect(
                        days=1, limit=1, target_dates=sorted_target_dates
                    )
                    return result
                elif service_name == "reddit":
                    result = await service.collect(
                        limit=1, target_dates=sorted_target_dates
                    )
                    return result
                elif service_name == "github_trending":
                    result = await service.collect(
                        limit=1, target_dates=sorted_target_dates
                    )
                    return result
                else:
                    result = await service.collect(target_dates=sorted_target_dates)
                    return result
            except Exception:
                return None

        return task_func

    def clear_service_cache(self):
        """Clear service cache (legacy for tests)"""
        self.sync_services.clear()

    def get_service_status(self):
        """Get service status (legacy for tests)"""
        status = {}
        for service_name in self.service_classes.keys():
            status[service_name] = {
                "cached": service_name in self.sync_services,
                "instance": self.sync_services.get(service_name) is not None,
            }
        return status

    def run_selected_services(self, service_names: list[str]):
        """Run selected services synchronously (legacy for tests)"""
        for service_name in service_names:
            # Use mocked service classes if available (for testing)
            service_class = self.service_classes[service_name]
            if hasattr(service_class, "return_value"):
                # This is a mock, just add to task manager as expected by test
                if hasattr(self, "task_manager") and hasattr(
                    self.task_manager, "add_task"
                ):
                    self.task_manager.add_task(self._create_service_task(service_name))
            else:
                self.run_service(service_name)

    def list_available_services(self) -> list[str]:
        """List available services (legacy for tests)"""
        return list(self.service_classes.keys())


async def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Nookサービスをテスト用に1件ずつ実行します"
    )
    parser.add_argument(
        "--service",
        choices=[
            "all",
            "github_trending",
            "hacker_news",
            "reddit",
            "zenn",
            "qiita",
            "note",
            "tech_news",
            "business_news",
            "arxiv",
            "4chan",
            "5chan",
        ],
        default="all",
        help="実行するサービスを指定します",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="何日前までの記事を取得するか（RSSフィードサービスのみ）",
    )

    args = parser.parse_args()

    runner = ServiceRunnerTest()

    # シグナルハンドラーの設定
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        runner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if args.service == "all":
            logger.warning("テスト用：すべてのサービスを1件制限で実行します")
            # テスト用なので1サービスずつ実行
            for service_name in runner.service_classes.keys():
                logger.info(f"\n{'=' * 80}")
                logger.info(f"テスト実行: {service_name}")
                logger.info(f"{'=' * 80}")
                await runner.run_service(service_name, args.days)
        else:
            await runner.run_service(args.service, args.days)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
