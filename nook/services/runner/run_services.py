"""
run_services.py - backward compatibility wrapper.

This module re-exports all symbols from runner_impl.py for backward compatibility.
Direct execution of this module via `python -m nook.services.runner.run_services`
is also supported.
"""

import asyncio

# Re-export all public symbols from runner_impl for backward compatibility
from nook.services.runner.runner_impl import (
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

__all__ = [
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
]

if __name__ == "__main__":
    asyncio.run(main())
