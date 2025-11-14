"""Nookで収集した情報をXにポストするサービス。"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

import tweepy
from dotenv import load_dotenv

from nook.common.storage import LocalStorage

# ロギングの設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TwitterPoster:
    """
    Nookで収集した情報をXにポストするクラス。

    Parameters
    ----------
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """

    def __init__(self, storage_dir: str = "data"):
        """
        TwitterPosterを初期化します。

        Parameters
        ----------
        storage_dir : str, default="data"
            ストレージディレクトリのパス。
        """
        load_dotenv()
        self.storage = LocalStorage(storage_dir)

        # Twitter API認証
        self.client = tweepy.Client(
            consumer_key=os.getenv("CONSUMER_KEY"),
            consumer_secret=os.getenv("CONSUMER_SECRET"),
            bearer_token=os.getenv("BEARER_TOKEN"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET"),
        )

    def run(self) -> None:
        """
        各種情報をXにポストします。
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")

        # GitHub Trending
        self.post_github_trending()

        # Hacker News
        self.post_hacker_news()

        # arXiv論文
        self.post_arxiv_papers()

        # Reddit記事
        self.post_reddit_articles()

        # 技術ブログ記事
        self.post_tech_feed()

    def post_github_trending(self) -> None:
        """
        GitHub Trendingの情報をポストします。
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        self._post_github_trending(date_str)

    def post_hacker_news(self) -> None:
        """
        Hacker Newsの情報をポストします。
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        self._post_hacker_news(date_str)

    def post_arxiv_papers(self) -> None:
        """
        arXiv論文の情報をポストします。
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        self._post_arxiv_papers(date_str)

    def post_reddit_articles(self) -> None:
        """
        Reddit記事の情報をポストします。
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        self._post_reddit_articles(date_str)

    def post_tech_feed(self) -> None:
        """
        技術ブログ記事の情報をポストします。
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        self._post_tech_feed(date_str)

    def _post_github_trending(self, date_str: str) -> None:
        """
        GitHub Trendingの情報をポストします。

        Parameters
        ----------
        date_str : str
            日付文字列。
        """
        logging.info("GitHub Trendingの情報をポストします...")

        # ファイルパス
        file_path = Path(self.storage.base_dir) / "github_trending" / f"{date_str}.md"

        if not file_path.exists():
            logging.warning(f"GitHub Trendingのファイルが見つかりません: {file_path}")
            return

        # ファイルを読み込む
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 「すべての言語」セクションを抽出
        all_languages_section = ""
        sections = re.split(r"## ", content)
        for section in sections:
            if (
                section.startswith("すべての言語")
                or section.startswith("all")
                or section.startswith("All")
            ):
                all_languages_section = section
                break

        if not all_languages_section:
            logging.warning(
                "「すべての言語」セクションが見つかりません。全体から抽出を試みます。"
            )
            # セクションが見つからない場合は、全体から抽出を試みる
            all_languages_section = content

        # リポジトリ情報を抽出
        repositories = self._extract_github_repositories(all_languages_section)

        if not repositories:
            logging.warning(
                "リポジトリ情報が抽出できませんでした。別の抽出方法を試みます。"
            )
            # 別の抽出方法を試す
            repositories = self._extract_github_repositories_alternative(content)

        if not repositories:
            logging.error("どの方法でもリポジトリ情報を抽出できませんでした。")
            return

        # ツイート文を生成
        tweet_text = f"【ニュース速報：GitHub Trending】{date_str}\n\n"

        for i, repo in enumerate(repositories[:5], 1):  # 上位5つのみ
            tweet_text += f"{i}. {repo['name']} ⭐{repo['stars']}\n"
            if repo.get("description"):  # 説明文があれば追加
                tweet_text += f"   {repo['description']}\n"
            tweet_text += f"   {repo['link']}\n"

        tweet_text += "\n#GitHub #Trending #開発"

        # ツイート投稿
        self._post_tweet(tweet_text)

    def _post_hacker_news(self, date_str: str) -> None:
        """
        Hacker Newsの情報をポストします。

        Parameters
        ----------
        date_str : str
            日付文字列。
        """
        logging.info("Hacker Newsの情報をポストします...")

        # ファイルパス
        file_path = Path(self.storage.base_dir) / "hacker_news" / f"{date_str}.md"

        if not file_path.exists():
            logging.warning(f"Hacker Newsのファイルが見つかりません: {file_path}")
            return

        # ファイルを読み込む
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 記事情報を抽出
        articles = self._extract_hacker_news_articles(content)

        if not articles:
            logging.warning("記事情報が抽出できませんでした")
            return

        # 修正: 全記事をポスト
        # ツイート文を生成
        tweet_text = f"【ニュース速報：Hacker News】{date_str}\n\n"

        for i, article in enumerate(articles, 1):  # 全記事
            tweet_text += f"{i}. {article['title']} (スコア: {article['score']})\n"
            if article["url"]:
                tweet_text += f"   {article['url']}\n"

        tweet_text += "\n#HackerNews #Tech #開発"

        # ツイート投稿
        self._post_tweet(tweet_text)

    def _post_arxiv_papers(self, date_str: str) -> None:
        """
        arXiv論文の情報をポストします。

        Parameters
        ----------
        date_str : str
            日付文字列。
        """
        logging.info("arXiv論文の情報をポストします...")

        # ファイルパス
        file_path = Path(self.storage.base_dir) / "paper_summarizer" / f"{date_str}.md"

        if not file_path.exists():
            logging.warning(f"arXiv論文のファイルが見つかりません: {file_path}")
            return

        # ファイルを読み込む
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 論文情報を抽出
        papers = self._extract_arxiv_papers(content)

        if not papers:
            logging.warning("論文情報が抽出できませんでした")
            return

        # 修正: アブストラクト全文をポスト
        # ツイート文を生成
        tweet_text = f"【ニュース速報：arXiv論文】{date_str}\n\n"

        for i, paper in enumerate(papers[:3], 1):  # 上位3つのみ
            tweet_text += f"{i}. {paper['title']}\n"
            tweet_text += f"   {paper['url']}\n"
            tweet_text += f"   {paper['abstract']}\n\n"

        tweet_text += "#arXiv #研究 #AI"

        # ツイート投稿
        self._post_tweet(tweet_text)

    def _post_reddit_articles(self, date_str: str) -> None:
        """
        Reddit記事の情報をポストします。

        Parameters
        ----------
        date_str : str
            日付文字列。
        """
        logging.info("Reddit記事の情報をポストします...")

        # ファイルパス
        file_path = Path(self.storage.base_dir) / "reddit_explorer" / f"{date_str}.md"

        if not file_path.exists():
            logging.warning(f"Reddit記事のファイルが見つかりません: {file_path}")
            return

        # ファイルを読み込む
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # カテゴリごとの記事を抽出
        categories = self._extract_reddit_categories(content)

        if not categories:
            logging.warning("Reddit記事情報が抽出できませんでした")
            return

        # カテゴリごとにツイートを作成
        for category, articles in categories.items():
            if not articles:
                continue

            # ツイート文を生成
            tweet_text = f"【ニュース速報：Reddit {category}】{date_str}\n\n"

            for i, article in enumerate(articles[:5], 1):  # 上位5つのみ
                tweet_text += f"{i}. {article['title']}\n"
                if article["link"]:
                    tweet_text += f"   {article['link']}\n"
                if article["summary"]:
                    tweet_text += f"   {article['summary']}\n\n"

            tweet_text += f"#Reddit #{category} #ニュース"

            # ツイート投稿
            self._post_tweet(tweet_text)

    def _post_tech_feed(self, date_str: str) -> None:
        """
        技術ブログ記事の情報をポストします。

        Parameters
        ----------
        date_str : str
            日付文字列。
        """
        logging.info("技術ブログ記事の情報をポストします...")

        # ファイルパス
        file_path = Path(self.storage.base_dir) / "tech_feed" / f"{date_str}.md"

        if not file_path.exists():
            logging.warning(f"技術ブログ記事のファイルが見つかりません: {file_path}")
            return

        # ファイルを読み込む
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # フィードごとの記事を抽出
        feeds = self._extract_tech_feed_articles(content)

        if not feeds:
            logging.warning("技術ブログ記事情報が抽出できませんでした")
            return

        # フィードごとにツイートを作成
        for feed_name, articles in feeds.items():
            if not articles:
                continue

            # ツイート文を生成
            tweet_text = f"【ニュース速報：{feed_name}】{date_str}\n\n"

            for i, article in enumerate(articles[:5], 1):  # 上位5つのみ
                tweet_text += f"{i}. {article['title']}\n"
                if article["url"]:
                    tweet_text += f"   {article['url']}\n"
                if article["summary"]:
                    tweet_text += f"   {article['summary']}\n\n"

            tweet_text += f"#TechFeed #{feed_name} #開発"

            # ツイート投稿
            self._post_tweet(tweet_text)

    def _extract_section(
        self, content: str, section_start: str, section_end: str
    ) -> str:
        """
        指定されたセクションを抽出します。

        Parameters
        ----------
        content : str
            コンテンツ。
        section_start : str
            セクション開始マーカー。
        section_end : str
            セクション終了マーカー。

        Returns
        -------
        str
            抽出されたセクション。
        """
        start_idx = content.find(section_start)
        if start_idx == -1:
            return ""

        start_idx += len(section_start)
        end_idx = content.find(section_end, start_idx)

        if end_idx == -1:
            return content[start_idx:]
        else:
            return content[start_idx:end_idx]

    def _extract_github_repositories(self, section: str) -> List[Dict[str, str]]:
        """
        GitHub Trendingのリポジトリ情報を抽出します。

        Parameters
        ----------
        section : str
            セクション。

        Returns
        -------
        List[Dict[str, str]]
            リポジトリ情報のリスト。
        """
        repositories = []

        # リポジトリ名とリンクを抽出
        repo_pattern = r"### \[(.*?)\]\((.*?)\)"
        repo_matches = re.finditer(repo_pattern, section)

        for match in repo_matches:
            name = match.group(1)
            link = match.group(2)

            # スター数と説明文を抽出
            stars_pattern = r"⭐ スター数: (\d+)"
            section_end = (
                section.find("---", match.end())
                if "---" in section[match.end() :]
                else len(section)
            )
            repo_section = section[match.end() : section_end]

            stars_match = re.search(stars_pattern, repo_section)
            stars = stars_match.group(1) if stars_match else "N/A"

            # 説明文を抽出 - スター数の行の後の最初の非空行
            description = ""
            lines = repo_section.split("\n")
            for i, line in enumerate(lines):
                if stars_match and line.strip().startswith("⭐ スター数:"):
                    # スター数の行の次の非空行を探す
                    for next_line in lines[i + 1 :]:
                        if next_line.strip() and not next_line.strip().startswith(
                            "---"
                        ):
                            description = next_line.strip()
                            break
                    break

            repositories.append(
                {"name": name, "link": link, "stars": stars, "description": description}
            )

        return repositories

    def _extract_github_repositories_alternative(
        self, content: str
    ) -> List[Dict[str, str]]:
        """
        GitHub Trendingのリポジトリ情報を別の方法で抽出します。

        Parameters
        ----------
        content : str
            コンテンツ全体。

        Returns
        -------
        List[Dict[str, str]]
            リポジトリ情報のリスト。
        """
        repositories = []

        # 別のパターンでリポジトリを抽出
        repo_pattern = r"## \[(.*?)\]\((https://github\.com/.*?)\)"
        repo_matches = re.finditer(repo_pattern, content)

        for match in repo_matches:
            name = match.group(1)
            link = match.group(2)

            # スター数と説明文を抽出
            section_end = content.find("##", match.end())
            if section_end == -1:
                section_end = len(content)

            section = content[match.end() : section_end]

            # スター数を抽出
            stars_pattern = r"スター数: (\d+)"
            stars_match = re.search(stars_pattern, section)
            stars = stars_match.group(1) if stars_match else "N/A"

            # 説明文を抽出 - 最初の非空行
            description = ""
            lines = section.split("\n")
            for line in lines:
                line = line.strip()
                if (
                    line
                    and not line.startswith("スター数:")
                    and not line.startswith("---")
                ):
                    description = line
                    break

            repositories.append(
                {"name": name, "link": link, "stars": stars, "description": description}
            )

        return repositories

    def _extract_hacker_news_articles(self, content: str) -> List[Dict[str, Any]]:
        """
        Hacker Newsの記事情報を抽出します。

        Parameters
        ----------
        content : str
            コンテンツ。

        Returns
        -------
        List[Dict[str, Any]]
            記事情報のリスト。
        """
        articles = []

        # 記事タイトルとURLを抽出
        article_pattern = r"## \[(.*?)\]\((.*?)\)"
        article_matches = re.finditer(article_pattern, content)

        for match in article_matches:
            title = match.group(1)
            url = match.group(2)

            # スコアを抽出
            score_pattern = r"スコア: (\d+)"
            next_section = content.find("##", match.end())
            if next_section == -1:
                next_section = len(content)

            section = content[match.end() : next_section]
            score_match = re.search(score_pattern, section)

            score = score_match.group(1) if score_match else "N/A"

            articles.append({"title": title, "url": url, "score": score})

        # タイトルのみの記事を抽出（URLなし）
        title_only_pattern = r"## ([^\[].+?)$"
        title_only_matches = re.finditer(title_only_pattern, content, re.MULTILINE)

        for match in title_only_matches:
            title = match.group(1).strip()

            # スコアを抽出
            score_pattern = r"スコア: (\d+)"
            next_section = content.find("##", match.end())
            if next_section == -1:
                next_section = len(content)

            section = content[match.end() : next_section]
            score_match = re.search(score_pattern, section)

            score = score_match.group(1) if score_match else "N/A"

            articles.append({"title": title, "url": None, "score": score})

        return articles

    def _extract_arxiv_papers(self, content: str) -> List[Dict[str, str]]:
        """
        arXiv論文の情報を抽出します。

        Parameters
        ----------
        content : str
            コンテンツ。

        Returns
        -------
        List[Dict[str, str]]
            論文情報のリスト。
        """
        papers = []

        # 論文タイトルとURLを抽出
        paper_pattern = r"## \[(.*?)\]\((.*?)\)"
        paper_matches = re.finditer(paper_pattern, content)

        for match in paper_matches:
            title = match.group(1)
            url = match.group(2)

            # アブストラクトを抽出
            abstract_pattern = r"\*\*アブストラクト\*\*:\s*(.*?)(?:\*\*要約\*\*|\-\-\-)"
            next_section = content.find("##", match.end())
            if next_section == -1:
                next_section = len(content)

            section = content[match.end() : next_section]
            abstract_match = re.search(abstract_pattern, section, re.DOTALL)

            abstract = abstract_match.group(1).strip() if abstract_match else ""

            papers.append({"title": title, "url": url, "abstract": abstract})

        return papers

    def _extract_reddit_categories(
        self, content: str
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Redditのカテゴリと記事情報を抽出します。

        Parameters
        ----------
        content : str
            コンテンツ。

        Returns
        -------
        Dict[str, List[Dict[str, str]]]
            カテゴリごとの記事情報のリスト。
        """
        categories = {}

        # カテゴリを抽出
        category_pattern = r"^## (.+?)$"
        category_matches = re.finditer(category_pattern, content, re.MULTILINE)

        for category_match in category_matches:
            category_name = category_match.group(1).strip()
            category_start = category_match.end()

            # 次のカテゴリまたはファイル終端を見つける
            next_category = re.search(r"^## ", content[category_start:], re.MULTILINE)
            if next_category:
                category_end = category_start + next_category.start()
            else:
                category_end = len(content)

            category_content = content[category_start:category_end]

            # サブレディットを抽出
            subreddit_pattern = r"^### (r/.+?)$"
            subreddit_matches = re.finditer(
                subreddit_pattern, category_content, re.MULTILINE
            )

            articles = []

            for subreddit_match in subreddit_matches:
                subreddit_name = subreddit_match.group(1).strip()
                subreddit_start = subreddit_match.end()

                # 次のサブレディットまたはカテゴリ終端を見つける
                next_subreddit = re.search(
                    r"^### ", category_content[subreddit_start:], re.MULTILINE
                )
                if next_subreddit:
                    subreddit_end = subreddit_start + next_subreddit.start()
                else:
                    subreddit_end = len(category_content)

                subreddit_content = category_content[subreddit_start:subreddit_end]

                # 記事を抽出
                article_pattern = r"^#### \[(.*?)\]\((.*?)\)"
                article_matches = re.finditer(
                    article_pattern, subreddit_content, re.MULTILINE
                )

                for article_match in article_matches:
                    title = article_match.group(1).strip()
                    link = article_match.group(2).strip()
                    article_start = article_match.end()

                    # 次の記事または終端を見つける
                    next_article = re.search(
                        r"^#### ", subreddit_content[article_start:], re.MULTILINE
                    )
                    if next_article:
                        article_end = article_start + next_article.start()
                    else:
                        article_end = len(subreddit_content)

                    article_content = subreddit_content[article_start:article_end]

                    # 投稿の主な内容を抽出
                    summary = ""
                    summary_pattern = r"\*\*要約\*\*:[\s\S]*?1\. 投稿の主な内容(?:\（1-2文\）)?:[\s\S]*?(.*?)(?:\n\n|\n2\.)"
                    summary_match = re.search(
                        summary_pattern, article_content, re.DOTALL
                    )

                    if summary_match:
                        summary = summary_match.group(1).strip()

                    articles.append(
                        {
                            "title": title,
                            "link": link,
                            "summary": summary,
                            "subreddit": subreddit_name,
                        }
                    )

            categories[category_name] = articles

        return categories

    def _extract_tech_feed_articles(
        self, content: str
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        技術ブログ記事の情報を抽出します。

        Parameters
        ----------
        content : str
            コンテンツ。

        Returns
        -------
        Dict[str, List[Dict[str, str]]]
            フィードごとの記事情報のリスト。
        """
        feeds = {}

        # フィードを抽出
        feed_pattern = r"^## (.+?)$"
        feed_matches = re.finditer(feed_pattern, content, re.MULTILINE)

        for feed_match in feed_matches:
            feed_name = feed_match.group(1).strip()
            feed_start = feed_match.end()

            # 次のフィードまたはファイル終端を見つける
            next_feed = re.search(r"^## ", content[feed_start:], re.MULTILINE)
            if next_feed:
                feed_end = feed_start + next_feed.start()
            else:
                feed_end = len(content)

            feed_content = content[feed_start:feed_end]

            # 記事を抽出
            article_pattern = r"^### \[(.*?)\]\((.*?)\)"
            article_matches = re.finditer(article_pattern, feed_content, re.MULTILINE)

            articles = []

            for article_match in article_matches:
                title = article_match.group(1).strip()
                url = article_match.group(2).strip()
                article_start = article_match.end()

                # 次の記事または終端を見つける
                next_article = re.search(
                    r"^### ", feed_content[article_start:], re.MULTILINE
                )
                if next_article:
                    article_end = article_start + next_article.start()
                else:
                    article_end = len(feed_content)

                article_content = feed_content[article_start:article_end]

                # フィード情報を抽出
                feed_info = ""
                feed_info_pattern = r"\*\*フィード\*\*: (.*?)$"
                feed_info_match = re.search(
                    feed_info_pattern, article_content, re.MULTILINE
                )

                if feed_info_match:
                    feed_info = feed_info_match.group(1).strip()

                # 記事の主な内容を抽出
                summary = ""
                summary_pattern = (
                    r"1\. 記事の主な内容(?:\（1-2文\）)?:(.*?)(?:\n\n|\n2\.)"
                )
                summary_match = re.search(summary_pattern, article_content, re.DOTALL)

                if summary_match:
                    summary = summary_match.group(1).strip()

                articles.append(
                    {
                        "title": title,
                        "url": url,
                        "feed_info": feed_info,
                        "summary": summary,
                    }
                )

            feeds[feed_name] = articles

        return feeds

    def _post_tweet(self, tweet_text: str) -> None:
        """
        ツイートを投稿します。

        Parameters
        ----------
        tweet_text : str
            ツイート文。
        """
        # 文字数制限は適用しない（X APIが自動的に処理）

        try:
            response = self.client.create_tweet(text=tweet_text)
            logging.info(f"ツイート投稿成功！ Tweet ID: {response.data['id']}")
        except tweepy.errors.Forbidden as e:
            logging.error(f"ツイート投稿エラー: {e}")
            logging.error("Twitter Developer Portalの設定とWrite権限を確認してください")
        except Exception as e:
            logging.error(f"予期せぬエラーが発生しました: {e}")
