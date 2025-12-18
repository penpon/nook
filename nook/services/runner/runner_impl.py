"""
Nookの各サービスを非同期で実行するスクリプト。
情報を並行収集し、ローカルストレージに保存します。
"""

import asyncio
import signal
import sys
import traceback
import warnings
from datetime import date, datetime
from typing import Set

from dotenv import load_dotenv

from nook.core.clients.http_client import close_http_client
from nook.core.logging import setup_logger
from nook.core.utils.async_utils import AsyncTaskManager, gather_with_errors
from nook.core.utils.date_utils import target_dates_set

# Suppress mcp internal deprecation warning
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r".*streamable_http_client.*",
)

# 環境変数の読み込み
load_dotenv(".env.production")

logger = setup_logger("service_runner")


# TrendRadar系のサービス一覧（単一日実行のみ対応）
TRENDRADAR_SERVICES = {
    "trendradar-zhihu",
    "trendradar-juejin",
    "trendradar-ithome",
    "trendradar-36kr",
    "trendradar-weibo",
    "trendradar-toutiao",
    "trendradar-sspai",
}


class ServiceRunner:
    """サービス実行マネージャー"""

    def __init__(self):
        # 既存のサービスをインポート（同期版として残す）
        from nook.services.analyzers.arxiv.arxiv_summarizer import ArxivSummarizer
        from nook.services.analyzers.github_trending.github_trending import (
            GithubTrending,
        )
        from nook.services.explorers.fivechan.fivechan_explorer import FiveChanExplorer
        from nook.services.explorers.fourchan.fourchan_explorer import FourChanExplorer
        from nook.services.explorers.note.note_explorer import NoteExplorer
        from nook.services.explorers.qiita.qiita_explorer import QiitaExplorer
        from nook.services.explorers.reddit.reddit_explorer import RedditExplorer
        from nook.services.explorers.trendradar.ithome_explorer import IthomeExplorer
        from nook.services.explorers.trendradar.juejin_explorer import JuejinExplorer
        from nook.services.explorers.trendradar.kr36_explorer import Kr36Explorer
        from nook.services.explorers.trendradar.sspai_explorer import SspaiExplorer
        from nook.services.explorers.trendradar.toutiao_explorer import ToutiaoExplorer
        from nook.services.explorers.trendradar.weibo_explorer import WeiboExplorer
        from nook.services.explorers.trendradar.zhihu_explorer import ZhihuExplorer
        from nook.services.explorers.zenn.zenn_explorer import ZennExplorer
        from nook.services.feeds.business.business_feed import BusinessFeed
        from nook.services.feeds.hacker_news.hacker_news import HackerNewsRetriever
        from nook.services.feeds.tech.tech_feed import TechFeed

        # サービスクラスを保持（遅延読み込み用）
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

        # TrendRadarサービスを動的に登録
        trendradar_mapping = {
            "trendradar-zhihu": ZhihuExplorer,
            "trendradar-juejin": JuejinExplorer,
            "trendradar-ithome": IthomeExplorer,
            "trendradar-36kr": Kr36Explorer,
            "trendradar-weibo": WeiboExplorer,
            "trendradar-toutiao": ToutiaoExplorer,
            "trendradar-sspai": SspaiExplorer,
        }
        for service_name in TRENDRADAR_SERVICES:
            if service_name in trendradar_mapping:
                self.service_classes[service_name] = trendradar_mapping[service_name]

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
        """同期サービスを非同期で実行"""
        # days パラメータを使用するサービスの場合、対象期間を表示
        effective_dates = target_dates or target_dates_set(days)
        sorted_dates = sorted(effective_dates)

        # trendradar系サービスは単一日のみ対応のため、days/target_dates の整合性を厳密に検証する
        # Note: Explorer.collect 内でも検証されるが、runner 側で早期に失敗させる
        if service_name in TRENDRADAR_SERVICES:
            if days != 1:
                raise ValueError(
                    f"{service_name} は単一日のみ対応しています。単一の日付を指定してください。"
                    f"指定された日数: {days}日"
                )
            if len(sorted_dates) > 1:
                raise ValueError(
                    f"{service_name} は単一日のみ対応しています。単一の日付を指定してください。"
                    f"指定された日数: {len(sorted_dates)}日"
                )

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
                # Hacker Newsは15記事に制限し、sorted_dates を渡す
                result = await service.collect(limit=15, target_dates=sorted_dates)
                saved_files = result if result else []
            elif service_name in ["tech_news", "business_news"]:
                # Tech News/Business Newsは15記事に制限し、sorted_dates を渡す
                result = await service.collect(
                    days=days, limit=15, target_dates=sorted_dates
                )
                saved_files = result if result else []
            elif service_name in ["zenn", "qiita", "note"]:
                # Zenn/Qiita/Noteは15記事に制限し、daysパラメータを渡す
                result = await service.collect(
                    days=days, limit=15, target_dates=sorted_dates
                )
                saved_files = result if result else []
            elif service_name == "reddit":
                # Redditは15記事に制限
                result = await service.collect(limit=15, target_dates=sorted_dates)
                saved_files = result if result else []
            else:
                # その他のサービスはデフォルト値を使用
                # trendradar系サービス は days の検証を service 側でも行う
                if service_name in TRENDRADAR_SERVICES:
                    result = await service.collect(days=days, target_dates=sorted_dates)
                else:
                    result = await service.collect(target_dates=sorted_dates)
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
            logger.error(
                f"Error executing {service_name}: {e}\n{traceback.format_exc()}"
            )
            raise

    async def run_all(self, days: int = 1) -> None:
        """すべてのサービスを並行実行"""
        self.running = True
        start_time = datetime.now()

        # 全サービスを遅延読み込み
        for service_name in self.service_classes:
            if service_name not in self.sync_services:
                self.sync_services[service_name] = self.service_classes[service_name]()

        logger.info(f"Starting {len(self.sync_services)} services with days={days}")

        target_dates = target_dates_set(days)
        # target_datesをsortedのlist型に変換して各サービスに渡す
        sorted_dates = sorted(target_dates)

        try:
            # 各サービスを並行実行
            service_tasks = [
                self._run_sync_service(name, service, days, sorted_dates)
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
        if service_name not in self.service_classes:
            raise ValueError(f"Service {service_name} not found")

        # 遅延読み込み：必要なサービスのみ初期化
        if service_name not in self.sync_services:
            self.sync_services[service_name] = self.service_classes[service_name]()

        logger.info(f"Running service: {service_name} with days={days}")

        target_dates = target_dates_set(days)
        # target_datesをsortedのlist型に変換して各サービスに渡す
        sorted_dates = sorted(target_dates)

        try:
            await self._run_sync_service(
                service_name,
                self.sync_services[service_name],
                days,
                sorted_dates,
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
    if service_name in runner.service_classes:
        print(f"{service_name}を実行しています...")
        try:
            # 遅延ロード
            if service_name not in runner.sync_services:
                runner.sync_services[service_name] = runner.service_classes[
                    service_name
                ]()

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
        ]
        + sorted(list(TRENDRADAR_SERVICES)),
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
