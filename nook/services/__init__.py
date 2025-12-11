"""サービスパッケージ。"""

# 互換性レイヤー: 旧パスからのimportをサポート
# nook.services.run_services -> nook.services.runner.run_services
from nook.services.runner.run_services import (
    ServiceRunner,
    main,
    run_all_services,
    run_arxiv_summarizer,
    run_business_feed,
    run_fivechan_explorer,
    run_fourchan_explorer,
    run_github_trending,
    run_hacker_news,
    run_note_explorer,
    run_qiita_explorer,
    run_reddit_explorer,
    run_service_sync,
    run_tech_feed,
    run_zenn_explorer,
)

# nook.services.base_feed_service -> nook.services.base.base_feed_service
from nook.services.base.base_feed_service import Article, BaseFeedService

__all__ = [
    # runner
    "ServiceRunner",
    "main",
    "run_all_services",
    "run_arxiv_summarizer",
    "run_business_feed",
    "run_fivechan_explorer",
    "run_fourchan_explorer",
    "run_github_trending",
    "run_hacker_news",
    "run_note_explorer",
    "run_qiita_explorer",
    "run_reddit_explorer",
    "run_service_sync",
    "run_tech_feed",
    "run_zenn_explorer",
    # base
    "Article",
    "BaseFeedService",
]
