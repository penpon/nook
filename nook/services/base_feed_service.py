"""RSSフィードベースのサービスの共通基底クラス。"""

import re
from abc import abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path

from bs4 import BeautifulSoup

from nook.common.base_service import BaseService
from nook.common.daily_merge import merge_records
from nook.common.date_utils import is_within_target_dates, normalize_datetime_to_local
from nook.common.feed_utils import parse_entry_datetime


@dataclass
class Article:
    """フィード記事の共通データクラス。

    Parameters
    ----------
    feed_name : str
        フィード名。
    title : str
        タイトル。
    url : str
        URL。
    text : str
        本文。
    soup : BeautifulSoup
        BeautifulSoupオブジェクト。
    category : str | None
        カテゴリ。

    """

    feed_name: str
    title: str
    url: str
    text: str
    soup: BeautifulSoup
    category: str | None = None
    summary: str = field(default="")
    popularity_score: float = field(default=0.0)
    published_at: datetime | None = None


class BaseFeedService(BaseService):
    """RSSフィードベースのサービスの共通基底クラス。

    このクラスは、RSSフィード取得、記事の重複チェック、要約生成、保存処理などの
    共通ロジックを提供します。

    サブクラスで実装が必要な抽象メソッド：
    - _extract_popularity(): 人気スコアの抽出
    - _get_markdown_header(): Markdownヘッダーテキスト
    - _get_summary_system_instruction(): 要約用のシステムインストラクション
    - _get_summary_prompt_template(): 要約用のプロンプトテンプレート
    """

    # サブクラスでオーバーライド可能
    TOTAL_LIMIT = 15

    async def _get_all_existing_dates(self) -> set[date]:
        """既存のJSONファイルの日付をすべて取得します。

        これにより、全ての既存記事を重複チェック対象にできます。
        （バグ修正：effective_target_datesだけでなく、全既存ファイルを対象にする）

        Returns
        -------
        set[date]
            既存のJSONファイルに対応する日付のセット。

        """
        existing_dates = set()
        storage_dir = Path(self.storage.base_dir)

        if storage_dir.exists():
            for json_file in storage_dir.glob("*.json"):
                try:
                    date_str = json_file.stem
                    file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    existing_dates.add(file_date)
                except ValueError:
                    # 日付形式でないファイル名はスキップ
                    continue

        return existing_dates

    def _filter_entries(
        self,
        entries: list[dict],
        target_dates: list[date],
        limit: int | None = None,
    ) -> list[dict]:
        """エントリを日付とリミットでフィルタリングします。

        Parameters
        ----------
        entries : list[dict]
            エントリのリスト。
        target_dates : list[date]
            対象日付のリスト。
        limit : int | None
            取得する記事数。Noneの場合は全て取得。

        Returns
        -------
        list[dict]
            フィルタリングされたエントリのリスト。

        """
        recent_entries = []

        for entry in entries:
            entry_date = parse_entry_datetime(entry)

            if entry_date:
                if is_within_target_dates(entry_date, target_dates):
                    recent_entries.append(entry)
                else:
                    self.logger.debug(
                        "対象外日付の記事をスキップします。 raw=%s",
                        getattr(entry, "published", getattr(entry, "updated", "")),
                    )

        if limit is None:
            return recent_entries

        return recent_entries[:limit]

    def _group_articles_by_date(self, articles: list[Article]) -> dict[str, list[Article]]:
        """記事を日付ごとにグループ化します。

        Parameters
        ----------
        articles : list[Article]
            記事のリスト。

        Returns
        -------
        dict[str, list[Article]]
            日付をキー、記事リストを値とする辞書。

        """
        by_date: dict[str, list[Article]] = {}
        default_date = datetime.now().strftime("%Y-%m-%d")

        for article in articles:
            if article.published_at:
                normalized = normalize_datetime_to_local(article.published_at)
                article.published_at = normalized.replace(tzinfo=None)
                date_key = article.published_at.strftime("%Y-%m-%d")
            else:
                date_key = default_date
            by_date.setdefault(date_key, []).append(article)

        return by_date

    def _serialize_articles(self, articles: list[Article]) -> list[dict]:
        """記事をdict形式にシリアライズします。

        Parameters
        ----------
        articles : list[Article]
            シリアライズする記事のリスト。

        Returns
        -------
        list[dict]
            シリアライズされた記事のリスト。

        """
        records: list[dict] = []
        for article in articles:
            category = article.category or "uncategorized"
            records.append(
                {
                    "title": article.title,
                    "url": article.url,
                    "feed_name": article.feed_name,
                    "summary": article.summary,
                    "popularity_score": article.popularity_score,
                    "published_at": (
                        article.published_at.isoformat() if article.published_at else None
                    ),
                    "category": category,
                }
            )
        return records

    async def _load_existing_articles(self, target_date: datetime) -> list[dict]:
        """既存の記事を日付から読み込みます。

        Parameters
        ----------
        target_date : datetime
            対象日付。

        Returns
        -------
        list[dict]
            既存記事のリスト。

        """
        date_str = target_date.strftime("%Y-%m-%d")
        filename_json = f"{date_str}.json"
        filename_md = f"{date_str}.md"

        existing_json = await self.load_json(filename_json)
        if existing_json:
            return existing_json

        markdown = await self.storage.load(filename_md)
        if not markdown:
            return []

        return self._parse_markdown(markdown)

    def _article_sort_key(self, item: dict) -> tuple[float, datetime]:
        """記事のソートキーを生成します（人気スコア、公開日時の順）。

        Parameters
        ----------
        item : dict
            記事データ。

        Returns
        -------
        tuple[float, datetime]
            ソートキー（人気スコア、公開日時）。

        """
        popularity = float(item.get("popularity_score", 0.0) or 0.0)
        published_raw = item.get("published_at")
        if published_raw:
            try:
                published = datetime.fromisoformat(published_raw)
            except ValueError:
                published = datetime.min
        else:
            published = datetime.min
        return (popularity, published)

    def _safe_parse_int(self, value) -> int | None:
        """さまざまな値から整数を抽出します。

        Parameters
        ----------
        value
            整数として解釈する値。

        Returns
        -------
        int | None
            抽出された整数。失敗した場合はNone。

        """
        if value is None:
            return None
        if isinstance(value, int | float):
            return int(value)
        if isinstance(value, str):
            match = re.search(r"(-?\d+)", value.replace(",", ""))
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None
        return None

    def _parse_markdown(self, markdown: str) -> list[dict]:
        """Markdownファイルから記事情報を抽出します。

        Parameters
        ----------
        markdown : str
            Markdownコンテンツ。

        Returns
        -------
        list[dict]
            抽出された記事のリスト。

        """
        result: list[dict] = []
        category_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        article_pattern = re.compile(
            r"### \[(?P<title>.+?)\]\((?P<url>[^\)]+)\)\n\n"
            r"\*\*フィード\*\*: (?P<feed>.+?)\n\n"
            r"\*\*要約\*\*:\n(?P<summary>.*?)(?:\n\n)?---",
            re.DOTALL,
        )

        sections = list(category_pattern.finditer(markdown))
        for idx, match in enumerate(sections):
            start = match.end()
            end = sections[idx + 1].start() if idx + 1 < len(sections) else len(markdown)
            block = markdown[start:end]
            category = match.group(1).strip().lower().replace(" ", "_")

            for article_match in article_pattern.finditer(block + "---"):
                result.append(
                    {
                        "title": article_match.group("title").strip(),
                        "url": article_match.group("url").strip(),
                        "feed_name": article_match.group("feed").strip(),
                        "summary": article_match.group("summary").strip(),
                        "popularity_score": 0.0,
                        "published_at": None,
                        "category": category,
                    }
                )

        return result

    def _select_top_articles(self, articles: list[Article]) -> list[Article]:
        """人気スコア順に記事をソートし、上位のみ返します。

        Parameters
        ----------
        articles : list[Article]
            記事のリスト。

        Returns
        -------
        list[Article]
            上位N件の記事。

        """
        if not articles:
            return []

        # 日付別に記事をグループ化
        articles_by_date = defaultdict(list)
        for article in articles:
            if article.published_at:
                local_dt = normalize_datetime_to_local(article.published_at)
                if local_dt:
                    date_key = local_dt.date()
                    articles_by_date[date_key].append(article)

        # 各日独立で上位記事を選択
        selected_articles = []
        for date_articles in articles_by_date.values():
            if len(date_articles) <= self.TOTAL_LIMIT:
                selected_articles.extend(date_articles)
            else:

                def sort_key(article: Article):
                    published = article.published_at or datetime.min
                    return (article.popularity_score, published)

                sorted_articles = sorted(date_articles, key=sort_key, reverse=True)
                selected_articles.extend(sorted_articles[: self.TOTAL_LIMIT])

        return selected_articles

    async def _store_summaries_for_date(
        self, articles: list[Article], date_str: str
    ) -> tuple[str, str]:
        """単一日付の記事をJSONとMarkdownファイルに保存します（ログ改善版）。

        Parameters
        ----------
        articles : list[Article]
            保存する記事のリスト。
        date_str : str
            日付文字列（"YYYY-MM-DD" 形式）。

        Returns
        -------
        tuple[str, str]
            保存されたファイルパスの組み合わせ (json_path, md_path)

        """
        if not articles:
            return ("", "")

        # 日付をdatetimeに変換
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        snapshot_datetime = datetime.combine(target_date, time.min)

        # 記事をシリアライズ
        records = self._serialize_articles(articles)

        # 既存記事を読み込んでマージ
        existing = await self._load_existing_articles(snapshot_datetime)

        merged = merge_records(
            existing,
            records,
            key=lambda item: item.get("title", ""),
            sort_key=self._article_sort_key,
            limit=self.TOTAL_LIMIT,
            reverse=True,
        )

        # JSONファイルを保存
        filename_json = f"{date_str}.json"
        json_path = await self.save_json(merged, filename_json)

        # Markdownファイルを保存
        filename_md = f"{date_str}.md"
        markdown = self._render_markdown(merged, snapshot_datetime)
        md_path = await self.save_markdown(markdown, filename_md)

        return (str(json_path), str(md_path))

    def _render_markdown(self, records: list[dict], today: datetime) -> str:
        """記事をMarkdown形式でレンダリングします。

        Parameters
        ----------
        records : list[dict]
            記事のリスト。
        today : datetime
            対象日付。

        Returns
        -------
        str
            Markdownコンテンツ。

        """
        content = f"# {self._get_markdown_header()} ({today.strftime('%Y-%m-%d')})\n\n"
        grouped: dict[str, list[dict]] = {}
        for record in records:
            category = record.get("category", "uncategorized")
            grouped.setdefault(category, []).append(record)

        for category, articles in grouped.items():
            heading = category.replace("_", " ").capitalize()
            content += f"## {heading}\n\n"

            for article in articles:
                content += f"### [{article['title']}]({article['url']})\n\n"
                content += f"**フィード**: {article.get('feed_name', '')}\n\n"
                content += f"**要約**:\n{article.get('summary', '')}\n\n"
                content += "---\n\n"
        return content

    async def _summarize_article(self, article: Article) -> None:
        """記事を要約します。

        Parameters
        ----------
        article : Article
            要約する記事。

        """
        prompt = self._get_summary_prompt_template(article)
        system_instruction = self._get_summary_system_instruction()

        try:
            summary = self.gpt_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.3,
                max_tokens=1000,
            )
            article.summary = summary
        except Exception as e:
            self.logger.error(f"要約の生成中にエラーが発生しました: {e!s}")
            article.summary = f"要約の生成中にエラーが発生しました: {e!s}"

    # ========================================
    # 抽象メソッド（サブクラスで実装必須）
    # ========================================

    @abstractmethod
    def _extract_popularity(self, entry, soup: BeautifulSoup) -> float:
        """記事の人気スコアを抽出します（サービス固有）。

        Parameters
        ----------
        entry
            フィードエントリ。
        soup : BeautifulSoup
            記事ページのBeautifulSoupオブジェクト。

        Returns
        -------
        float
            人気スコア。

        """
        pass

    @abstractmethod
    def _get_markdown_header(self) -> str:
        """Markdownファイルのヘッダーテキストを返します（サービス固有）。

        Returns
        -------
        str
            ヘッダーテキスト（例: "Zenn記事", "Qiita記事"）。

        """
        pass

    @abstractmethod
    def _get_summary_system_instruction(self) -> str:
        """要約生成用のシステムインストラクションを返します（サービス固有）。

        Returns
        -------
        str
            システムインストラクション。

        """
        pass

    @abstractmethod
    def _get_summary_prompt_template(self, article: Article) -> str:
        """要約生成用のプロンプトテンプレートを返します（サービス固有）。

        Parameters
        ----------
        article : Article
            要約対象の記事。

        Returns
        -------
        str
            プロンプト。

        """
        pass

    def _needs_japanese_check(self) -> bool:
        """日本語判定が必要かどうかを返します。

        デフォルトはFalse（日本語サイト前提）。
        business_feed, tech_feedなどはTrueにオーバーライド。

        Returns
        -------
        bool
            True: 日本語判定を実施, False: 不要

        """
        return False

    def _detect_japanese_content(self, soup, title, entry) -> bool:
        """記事が日本語であるかどうかを判定します。

        Parameters
        ----------
        soup : BeautifulSoup
            記事のHTMLパーサー。
        title : str
            記事のタイトル。
        entry : dict
            エントリ情報。

        Returns
        -------
        bool
            日本語記事であればTrue、そうでなければFalse。

        """
        # 方法1: HTMLのlang属性をチェック
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            lang = html_tag.get("lang").lower()
            if lang.startswith("ja") or lang == "jp":
                return True

        # 方法2: meta タグの言語情報をチェック
        meta_lang = soup.find("meta", attrs={"http-equiv": "content-language"})
        if meta_lang and meta_lang.get("content"):
            if meta_lang.get("content").lower().startswith("ja"):
                return True

        # 方法3: 日本語の文字コードパターンをチェック
        # ひらがな、カタカナ、漢字の文字コード範囲
        hiragana_pattern = range(0x3040, 0x309F)
        katakana_pattern = range(0x30A0, 0x30FF)
        kanji_pattern = range(0x4E00, 0x9FBF)

        # タイトルをチェック
        japanese_chars_count = 0
        for char in title:
            code = ord(char)
            if code in hiragana_pattern or code in katakana_pattern or code in kanji_pattern:
                japanese_chars_count += 1

        if japanese_chars_count > 2:  # 複数の日本語文字があれば日本語とみなす
            return True

        # 方法4: サマリーやディスクリプションもチェック
        text_to_check = ""
        if hasattr(entry, "summary"):
            text_to_check += entry.summary

        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            text_to_check += meta_desc.get("content")

        # 最初の段落をサンプリング
        paragraphs = soup.find_all("p")
        if paragraphs and len(paragraphs) > 0:
            text_to_check += paragraphs[0].get_text()

        # サンプリングしたテキストで日本語文字をチェック
        japanese_chars_count = 0
        for char in text_to_check[:100]:  # 最初の100文字だけチェック
            code = ord(char)
            if code in hiragana_pattern or code in katakana_pattern or code in kanji_pattern:
                japanese_chars_count += 1

        if japanese_chars_count > 5:  # 複数の日本語文字があれば日本語とみなす
            return True

        # 方法5: 特定の日本語サイトのドメインリスト（バックアップとして）
        japanese_domains = [
            "nikkei.com",
            "toyokeizai.net",
            "businessinsider.jp",
            "bloomberg.co.jp",
            "reuters.co.jp",
            "diamond.jp",
            "jbpress.co.jp",
            "president.jp",
        ]

        url = entry.link if hasattr(entry, "link") else ""
        return any(domain in url for domain in japanese_domains)
