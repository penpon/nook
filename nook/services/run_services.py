"""
Nookの各サービスを非同期で実行するスクリプト。
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

# 環境変数の読み込み
load_dotenv()

logger = setup_logger("service_runner")


class ServiceRunner:
    """サービス実行マネージャー"""

    def __init__(self):
        # 既存のサービスをインポート（同期版として残す）
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

        # サービスインスタンスを保持
        self.sync_services = {
            "github_trending": GithubTrending(),
            "hacker_news": HackerNewsRetriever(),
            "reddit": RedditExplorer(),
            "zenn": ZennExplorer(),
            "qiita": QiitaExplorer(),
            "note": NoteExplorer(),
            "tech_news": TechFeed(),
            "business_news": BusinessFeed(),
            "arxiv": ArxivSummarizer(),
            "4chan": FourChanExplorer(),
            "5chan": FiveChanExplorer(),
        }

        self.task_manager = AsyncTaskManager(max_concurrent=5)
        self.running = False

    async def _run_sync_service(
        self,
        service_name: str,
        service,
        days: int = 1,
        target_dates: Set[date] | None = None,
    ):
        """同期サービスを非同期で実行"""
        # days パラメータを使用するサービスの場合、対象期間を表示
        effective_dates = target_dates or target_dates_set(days)
        sorted_dates = sorted(effective_dates)

        logger.info("\n" + "━" * 60)
        if len(sorted_dates) <= 1:
            logger.info(
                f"📅 対象日: {sorted_dates[0] if sorted_dates else datetime.now().date()}"
            )
        else:
            start_date = sorted_dates[0]
            end_date = sorted_dates[-1]
            logger.info(
                f"📅 対象期間: {start_date} 〜 {end_date} ({len(sorted_dates)}日間)"
            )
        logger.info(f"🚀 サービス開始: {service_name}")
        logger.info("━" * 60)

        saved_files: list[tuple[str, str]] = []
        try:
            # サービスごとに異なるlimitパラメータを設定
            if service_name == "hacker_news":
                # Hacker Newsは15記事に制限し、target_dates を渡す
                result = await service.collect(limit=15, target_dates=effective_dates)
                saved_files = result if result else []
            elif service_name in ["tech_news", "business_news"]:
                # Tech News/Business Newsは各5記事に制限し、target_dates を渡す
                result = await service.collect(
                    days=days, limit=5, target_dates=effective_dates
                )
                saved_files = result if result else []
            elif service_name in ["zenn", "qiita", "note"]:
                # Zenn/Qiita/Noteは各3記事に制限し、daysパラメータを渡す
                result = await service.collect(
                    days=days, limit=3, target_dates=effective_dates
                )
                saved_files = result if result else []
            elif service_name == "reddit":
                # Redditは5記事に制限
                result = await service.collect(limit=5, target_dates=effective_dates)
                saved_files = result if result else []
            else:
                # その他のサービスはデフォルト値を使用
                result = await service.collect(target_dates=effective_dates)
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
                    f"✨ 完了: 合計{total_articles}日分のデータを処理しました\n"
                )

        except Exception as e:
            logger.error(f"\n❌ Service {service_name} failed: {e}", exc_info=True)
            raise

    async def run_all(self, days: int = 1) -> None:
        """すべてのサービスを並行実行"""
        self.running = True
        start_time = datetime.now()

        logger.info(f"Starting {len(self.sync_services)} services with days={days}")

        target_dates = target_dates_set(days)

        try:
            # 各サービスを並行実行
            service_tasks = [
                self._run_sync_service(name, service, days, target_dates)
                for name, service in self.sync_services.items()
            ]

            results = await gather_with_errors(
                *service_tasks, task_names=list(self.sync_services.keys())
            )

            # 結果をレポート
            successful = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Service run completed in {duration:.2f} seconds",
                extra={
                    "successful": successful,
                    "failed": failed,
                    "total": len(self.sync_services),
                },
            )

            # エラーの詳細をログ
            for result in results:
                if not result.success:
                    logger.error(
                        f"Service {result.name} failed",
                        extra={"error": str(result.error)},
                    )

        except Exception as e:
            logger.error(f"Service runner failed: {e}", exc_info=True)
            raise
        finally:
            self.running = False
            # HTTPクライアントをクリーンアップ
            await close_http_client()

    async def run_service(self, service_name: str, days: int = 1) -> None:
        """特定のサービスを実行"""
        if service_name not in self.sync_services:
            raise ValueError(f"Service {service_name} not found")

        logger.info(f"Running service: {service_name} with days={days}")

        target_dates = target_dates_set(days)

        try:
            await self._run_sync_service(
                service_name, self.sync_services[service_name], days, target_dates
            )
        except Exception as e:
            logger.error(f"Service {service_name} failed: {e}", exc_info=True)
            raise

    async def run_continuous(self, interval_seconds: int = 3600, days: int = 1) -> None:
        """定期的にサービスを実行"""
        logger.info(
            f"Starting continuous run with interval: {interval_seconds}s, days={days}"
        )

        while self.running:
            try:
                await self.run_all(days)
            except Exception as e:
                logger.error(f"Run failed: {e}", exc_info=True)

            # 次の実行まで待機
            logger.info(f"Waiting {interval_seconds} seconds until next run")
            await asyncio.sleep(interval_seconds)

    def stop(self):
        """実行を停止"""
        logger.info("Stopping service runner")
        self.running = False


def run_service_sync(service_name: str):
    """特定のサービスを同期的に実行（後方互換性のため）"""
    runner = ServiceRunner()
    if service_name in runner.sync_services:
        print(f"{service_name}を実行しています...")
        try:
            runner.sync_services[service_name].run()
            print(f"{service_name}の実行が完了しました。")
        except Exception as e:
            print(f"{service_name}の実行中にエラーが発生しました: {str(e)}")
    else:
        print(f"サービス '{service_name}' が見つかりません。")


async def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Nookサービスを実行します")
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
        "--continuous", action="store_true", help="サービスを定期的に実行します"
    )
    parser.add_argument(
        "--interval", type=int, default=3600, help="連続実行時の間隔（秒）"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="何日前までの記事を取得するか（RSSフィードサービスのみ）",
    )

    args = parser.parse_args()

    runner = ServiceRunner()

    # シグナルハンドラーの設定
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        runner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if args.continuous:
            await runner.run_continuous(args.interval, args.days)
        elif args.service == "all":
            await runner.run_all(args.days)
        else:
            await runner.run_service(args.service, args.days)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


# 後方互換性のための関数（同期版）
def run_github_trending():
    run_service_sync("github_trending")


def run_hacker_news():
    run_service_sync("hacker_news")


def run_reddit_explorer():
    run_service_sync("reddit")


def run_zenn_explorer():
    run_service_sync("zenn")


def run_qiita_explorer():
    run_service_sync("qiita")


def run_note_explorer():
    run_service_sync("note")


def run_tech_feed():
    run_service_sync("tech_news")


def run_business_feed():
    run_service_sync("business_news")


def run_arxiv_summarizer():
    run_service_sync("arxiv")


def run_fourchan_explorer():
    run_service_sync("4chan")


def run_fivechan_explorer():
    run_service_sync("5chan")


def run_all_services():
    """すべてのサービスを実行（同期版）"""
    asyncio.run(ServiceRunner().run_all())


if __name__ == "__main__":
    asyncio.run(main())
