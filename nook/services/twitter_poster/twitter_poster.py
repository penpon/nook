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
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
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
            consumer_key=os.getenv('CONSUMER_KEY'),
            consumer_secret=os.getenv('CONSUMER_SECRET'),
            bearer_token=os.getenv('BEARER_TOKEN'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_SECRET')
        )
    
    def run(self) -> None:
        """
        各種情報をXにポストします。
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        
        # GitHub Trending
        self._post_github_trending(date_str)
        
        # Hacker News
        self._post_hacker_news(date_str)
        
        # arXiv論文
        self._post_arxiv_papers(date_str)
    
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
        # 修正: セクション抽出方法を改善
        all_languages_section = ""
        sections = re.split(r"## ", content)
        for section in sections:
            if section.startswith("すべての言語") or section.startswith("all") or section.startswith("All"):
                all_languages_section = section
                break
        
        if not all_languages_section:
            logging.warning("「すべての言語」セクションが見つかりません。全体から抽出を試みます。")
            # セクションが見つからない場合は、全体から抽出を試みる
            all_languages_section = content
        
        # リポジトリ情報を抽出
        repositories = self._extract_github_repositories(all_languages_section)
        
        if not repositories:
            logging.warning("リポジトリ情報が抽出できませんでした。別の抽出方法を試みます。")
            # 別の抽出方法を試す
            repositories = self._extract_github_repositories_alternative(content)
        
        if not repositories:
            logging.error("どの方法でもリポジトリ情報を抽出できませんでした。")
            return
        
        # ツイート文を生成
        tweet_text = f"【ニュース速報：GitHub Trending】{date_str}\n\n"
        
        for i, repo in enumerate(repositories[:5], 1):  # 上位5つのみ
            tweet_text += f"{i}. {repo['name']} ⭐{repo['stars']}\n"
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
            if article['url']:
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
    
    def _extract_section(self, content: str, section_start: str, section_end: str) -> str:
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
            
            # スター数を抽出
            stars_pattern = r"⭐ スター数: (\d+)"
            stars_match = re.search(stars_pattern, section[match.end():section.find("---", match.end()) if "---" in section[match.end():] else len(section)])
            
            stars = stars_match.group(1) if stars_match else "N/A"
            
            repositories.append({
                "name": name,
                "link": link,
                "stars": stars
            })
        
        return repositories
    
    def _extract_github_repositories_alternative(self, content: str) -> List[Dict[str, str]]:
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
        # 例: ## [リポジトリ名](URL)
        repo_pattern = r"## \[(.*?)\]\((https://github\.com/.*?)\)"
        repo_matches = re.finditer(repo_pattern, content)
        
        for match in repo_matches:
            name = match.group(1)
            link = match.group(2)
            
            # スター数を抽出（別パターン）
            stars_pattern = r"スター数: (\d+)"
            section_end = content.find("##", match.end())
            if section_end == -1:
                section_end = len(content)
            
            section = content[match.end():section_end]
            stars_match = re.search(stars_pattern, section)
            
            stars = stars_match.group(1) if stars_match else "N/A"
            
            repositories.append({
                "name": name,
                "link": link,
                "stars": stars
            })
        
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
            
            section = content[match.end():next_section]
            score_match = re.search(score_pattern, section)
            
            score = score_match.group(1) if score_match else "N/A"
            
            articles.append({
                "title": title,
                "url": url,
                "score": score
            })
        
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
            
            section = content[match.end():next_section]
            score_match = re.search(score_pattern, section)
            
            score = score_match.group(1) if score_match else "N/A"
            
            articles.append({
                "title": title,
                "url": None,
                "score": score
            })
        
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
            
            section = content[match.end():next_section]
            abstract_match = re.search(abstract_pattern, section, re.DOTALL)
            
            abstract = abstract_match.group(1).strip() if abstract_match else ""
            
            papers.append({
                "title": title,
                "url": url,
                "abstract": abstract
            })
        
        return papers
    
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