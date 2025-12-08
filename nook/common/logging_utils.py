"""サービス共通のログ出力ユーティリティ関数。"""

from datetime import date
from typing import Any, List


def log_processing_start(logger, date_str: str) -> None:
    """
    処理開始のログを出力します。

    Parameters
    ----------
    logger : Logger
        ロガーインスタンス
    date_str : str
        処理対象の日付 (YYYY-MM-DD形式)
    """
    logger.info(f"\n📰 [{date_str}] の記事を処理中...")


def log_article_counts(logger, existing_count: int, new_count: int) -> None:
    """
    既存・新規記事数のログを出力します。

    Parameters
    ----------
    logger : Logger
        ロガーインスタンス
    existing_count : int
        既存記事数
    new_count : int
        新規記事数
    """
    logger.info(f"   📊 既存: {existing_count}件（保持） | 新規: {new_count}件")


def log_summary_candidates(
    logger, candidates: List[Any], score_attr: str = "popularity_score"
) -> None:
    """
    要約対象記事のリストを出力します。

    Parameters
    ----------
    logger : Logger
        ロガーインスタンス
    candidates : List[Any]
        要約対象の記事リスト
    score_attr : str, default="popularity_score"
        スコア属性名
    """
    if not candidates:
        return

    logger.info(f"   ✅ 要約対象: {len(candidates)}件を選択")
    for idx, item in enumerate(candidates, 1):
        if hasattr(item, "title"):
            title = item.title
        else:
            title = getattr(item, "name", str(item))

        score = getattr(item, score_attr, 0)
        if isinstance(score, float):
            score_str = f"{score:.0f}"
        else:
            score_str = str(score)

        logger.info(f"      {idx}. 「{title}」(スコア: {score_str})")


def log_summarization_start(logger) -> None:
    """
    要約生成開始のログを出力します。

    Parameters
    ----------
    logger : Logger
        ロガーインスタンス
    """
    logger.info("\n   🤖 要約生成中...")


def log_summarization_progress(logger, idx: int, total: int, title: str) -> None:
    """
    要約生成の進捗を出力します。

    Parameters
    ----------
    logger : Logger
        ロガーインスタンス
    idx : int
        現在のインデックス
    total : int
        全体数
    title : str
        記事タイトル
    """
    truncated_title = title[:50] + "..." if len(title) > 50 else title
    logger.info(f"      ✓ {idx}/{total}: 「{truncated_title}」")


def log_storage_complete(logger, json_path: str, md_path: str) -> None:
    """
    保存完了のログを出力します。

    Parameters
    ----------
    logger : Logger
        ロガーインスタンス
    json_path : str
        JSONファイルパス
    md_path : str
        Markdownファイルパス
    """
    logger.info(f"\n   💾 保存完了: {json_path}, {md_path}")


def log_no_new_articles(logger) -> None:
    """
    新規記事がない場合のログを出力します。

    Parameters
    ----------
    logger : Logger
        ロガーインスタンス
    """
    logger.info("   ℹ️  新規記事がありません")


def log_multiple_dates_processing(logger, dates: List[date]) -> None:
    """
    複数日付処理のログを出力します。

    Parameters
    ----------
    logger : Logger
        ロガーインスタンス
    dates : List[date]
        処理対象の日付リスト
    """
    if len(dates) == 1:
        logger.info(f"📰 [{dates[0]:%Y-%m-%d}] の記事を処理中...")
    else:
        start_str = dates[0].strftime("%Y-%m-%d")
        end_str = dates[-1].strftime("%Y-%m-%d")
        logger.info(
            "📰 対象期間: %s 〜 %s (%d日間) を処理中...",
            start_str,
            end_str,
            len(dates),
        )
