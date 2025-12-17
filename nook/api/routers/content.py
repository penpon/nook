"""コンテンツAPIルーター。"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Response

from nook.api.models.schemas import ContentItem, ContentResponse
from nook.core.config import BaseConfig
from nook.core.storage import LocalStorage
from nook.services.explorers.trendradar.utils import parse_popularity_score

router = APIRouter()
storage = LocalStorage(BaseConfig().DATA_DIR)

# 論文要約の質問文を読みやすいタイトルに変換するマッピング
PAPER_SUMMARY_TITLE_MAPPING = {
    "1. 既存研究では何ができなかったのか": "🔍 研究背景と課題",
    "2. どのようなアプローチでそれを解決しようとしたか": "💡 提案手法",
    "3. 結果、何が達成できたのか": "🎯 主要な成果",
    "4. 制限や問題点は何ですか。本文で言及されているやあなたが考えるものも含めて教えてください": "⚠️ 限界と今後の課題",
    "5. 技術的な詳細について。技術者が読むことを想定したトーンで教えてください": "🔧 技術詳細",
    "6. コストや物理的な詳細について教えてください。例えばトレーニングに使用したGPUの数や時間、データセット、モデルのサイズなど": "💻 計算リソースと規模",
    "7. 参考文献のうち、特に参照すべきものを教えてください": "📚 重要な関連研究",
    "8. この論文を140字以内で要約するとどうなりますか？": "📝 140字要約",
}


def convert_paper_summary_titles(content: str) -> str:
    """論文要約の質問文を読みやすいタイトルに変換"""
    result = content

    # 各質問文を対応するタイトルに置換
    for original_title in PAPER_SUMMARY_TITLE_MAPPING:
        # 質問文の全体または一部にマッチするよう調整
        # "4. 制限や問題点は何ですか。"のような質問文に対応
        if original_title in result:
            result = result.replace(
                original_title, PAPER_SUMMARY_TITLE_MAPPING[original_title]
            )

    return result


SOURCE_MAPPING = {
    "arxiv": "arxiv_summarizer",
    "github": "github_trending",
    "hacker-news": "hacker_news",
    "tech-news": "tech_feed",
    "business-news": "business_feed",
    "zenn": "zenn_explorer",
    "qiita": "qiita_explorer",
    "note": "note_explorer",
    "reddit": "reddit_explorer",
    "4chan": "fourchan_explorer",
    "5chan": "fivechan_explorer",
    "trendradar-zhihu": "trendradar-zhihu",
    "trendradar-juejin": "trendradar-juejin",
    "trendradar-ithome": "trendradar-ithome",
}


def _create_content_item(
    title: str, content: str, source: str, url: str | None = None
) -> ContentItem:
    """ContentItemを作成するヘルパー関数"""
    return ContentItem(
        title=title,
        content=content,
        url=url,
        source=source,
    )


def _process_trendradar_articles(
    articles_data: list[dict], source: str
) -> list[ContentItem]:
    """TrendRadar系記事をContentItemリストに変換する共通関数.

    Parameters
    ----------
    articles_data : list[dict]
        TrendRadar系サービスから取得した記事データのリスト。
    source : str
        ソース名（例: "trendradar-zhihu", "trendradar-juejin"）。

    Returns
    -------
    list[ContentItem]
        変換されたContentItemのリスト。
    """
    items = []
    # 人気度（popularity_score）の降順でソート
    # 変換不可能な値（None, "N/A"等）は0として扱う
    # Note: sorted()を使用して元のリストを変更しない（副作用防止）
    sorted_articles = sorted(
        articles_data,
        key=lambda x: parse_popularity_score(x.get("popularity_score")),
        reverse=True,
    )

    for article in sorted_articles:
        content = ""
        if article.get("summary"):
            # 要約は既にMarkdown形式で構造化されているため、そのまま使用
            content = f"{article['summary']}\n\n"
        if article.get("category"):
            content += f"カテゴリ: {article['category']}"

        items.append(
            _create_content_item(
                title=article.get("title", ""),
                content=content,
                url=article.get("url"),
                source=source,
            )
        )
    return items


@router.get("/content/{source}", response_model=ContentResponse)
async def get_content(
    source: str, date: str | None = None, response: Response = None
) -> ContentResponse:
    """
    特定のソースのコンテンツを取得します。

    Parameters
    ----------
    source : str
        データソース（reddit, hackernews, github, techfeed, paper）。
    date : str, optional
        表示する日付（YYYY-MM-DD形式）。

    Returns
    -------
    ContentResponse
        コンテンツレスポンス。

    Raises
    ------
    HTTPException
        ソースが無効な場合や、コンテンツが見つからない場合。
    """
    if source not in SOURCE_MAPPING and source != "all":
        raise HTTPException(status_code=404, detail=f"Source '{source}' not found")

    # キャッシュ制御ヘッダーを設定（キャッシュを無効化）
    if response:
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    # 日付の処理
    target_date = None
    explicit_date_requested = date is not None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid date format: {date}"
            ) from None
    else:
        target_date = datetime.now()

    items = []

    # 特定のソースからコンテンツを取得
    if source != "all":
        service_name = SOURCE_MAPPING[source]

        # Hacker Newsの場合はJSONから個別記事を取得
        if source == "hacker-news":
            stories_data = storage.load_json(service_name, target_date)
            if stories_data:
                # スコアで降順ソート
                sorted_stories = sorted(
                    stories_data, key=lambda x: x.get("score", 0), reverse=True
                )
                for story in sorted_stories:
                    # 要約があれば要約を、なければ本文を使用
                    content = ""
                    if story.get("summary"):
                        content = f"**要約**:\n{story['summary']}\n\n"
                    elif story.get("text"):
                        text_preview = story["text"][:1000]
                        if len(story["text"]) > 1000:
                            text_preview += "..."
                        content = f"{text_preview}\n\n"

                    content += f"スコア: {story['score']}"

                    items.append(
                        _create_content_item(
                            title=story["title"],
                            content=content,
                            url=story.get("url"),
                            source=source,
                        )
                    )
        # TrendRadar (Zhihu/Juejin/ITHome) の場合はJSONから個別記事を取得
        elif source in ("trendradar-zhihu", "trendradar-juejin", "trendradar-ithome"):
            articles_data = storage.load_json(service_name, target_date)
            if articles_data:
                items.extend(_process_trendradar_articles(articles_data, source))
        else:
            # 他のソースは従来通りMarkdownから取得
            content = storage.load_markdown(service_name, target_date)

            if content:
                # 論文要約の場合はタイトルを変換
                if source == "arxiv":
                    content = convert_paper_summary_titles(content)

                # マークダウンからContentItemを作成
                items.append(
                    _create_content_item(
                        title=(
                            ""
                            if source == "github"
                            else f"{_get_source_display_name(source)} - "
                            f"{target_date.strftime('%Y-%m-%d')}"
                        ),
                        content=content,
                        source=source,
                    )
                )
    else:
        # すべてのソースからコンテンツを取得
        for src, service_name in SOURCE_MAPPING.items():
            if src == "hacker-news":
                # Hacker Newsは個別記事として追加
                stories_data = storage.load_json(service_name, target_date)
                if stories_data:
                    # スコアで降順ソート
                    sorted_stories = sorted(
                        stories_data, key=lambda x: x.get("score", 0), reverse=True
                    )
                    for story in sorted_stories:
                        # 要約があれば要約を、なければ本文を使用
                        content = ""
                        if story.get("summary"):
                            content = f"**要約**:\n{story['summary']}\n\n"
                        elif story.get("text"):
                            text_preview = story["text"][:500]
                            if len(story["text"]) > 500:
                                text_preview += "..."
                            content = f"{text_preview}\n\n"

                        content += f"スコア: {story['score']}"

                        items.append(
                            _create_content_item(
                                title=story["title"],
                                content=content,
                                url=story.get("url"),
                                source=src,
                            )
                        )
            elif src in ("trendradar-zhihu", "trendradar-juejin", "trendradar-ithome"):
                # TrendRadar系はJSONから個別記事として追加
                articles_data = storage.load_json(service_name, target_date)
                if articles_data:
                    items.extend(_process_trendradar_articles(articles_data, src))
            else:
                # 他のソースは従来通りMarkdownから取得
                content = storage.load_markdown(service_name, target_date)
                if content:
                    # 論文要約の場合はタイトルを変換
                    if src == "arxiv":
                        content = convert_paper_summary_titles(content)

                    items.append(
                        _create_content_item(
                            title=(
                                ""
                                if src == "github"
                                else f"{_get_source_display_name(src)} - "
                                f"{target_date.strftime('%Y-%m-%d')}"
                            ),
                            content=content,
                            source=src,
                        )
                    )

    if not items:
        if explicit_date_requested:
            return ContentResponse(items=[])

        # 利用可能な日付を確認
        available_dates = []
        if source != "all":
            service_name = SOURCE_MAPPING[source]
            available_dates = storage.list_dates(service_name)
        else:
            for service_name in SOURCE_MAPPING.values():
                dates = storage.list_dates(service_name)
                available_dates.extend(dates)

        if not available_dates:
            raise HTTPException(
                status_code=404,
                detail="No content available. Please run the services first.",
            )
        else:
            # 最新の利用可能な日付のコンテンツを取得
            latest_date = max(available_dates)
            return await get_content(source, latest_date.strftime("%Y-%m-%d"))

    return ContentResponse(items=items)


def _get_source_display_name(source: str) -> str:
    """
    ソースの表示名を取得します。

    Parameters
    ----------
    source : str
        データソース

    Returns
    -------
    str
        表示名
    """
    source_names = {
        "reddit": "Reddit",
        "hacker-news": "Hacker News",
        "github": "GitHub Trending",
        "tech-news": "Tech News",
        "business-news": "Business News",
        "paper": "ArXiv",
        "zenn": "Zenn",
        "qiita": "Qiita",
        "note": "Note",
        "4chan": "4chan",
        "5chan": "5ちゃんねる",
        "trendradar-zhihu": "知乎 (Zhihu)",
        "trendradar-juejin": "掘金 (Juejin)",
        "trendradar-ithome": "IT之家 (ITHome)",
    }
    return source_names.get(source, source)
