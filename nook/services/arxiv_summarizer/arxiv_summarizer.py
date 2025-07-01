"""arXiv論文を収集・要約するサービス。"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import asyncio

import arxiv
from bs4 import BeautifulSoup
from tqdm import tqdm

from nook.common.base_service import BaseService
from nook.common.http_client import AsyncHTTPClient
from nook.common.decorators import handle_errors
from nook.common.exceptions import APIException


def remove_tex_backticks(text: str) -> str:
    r"""
    文字列が TeX 形式、つまり
      `$\ldots$`
    の場合、外側のバッククォート (`) だけを削除して
      $\ldots$
    に変換します。
    それ以外の場合は、文字列を変更しません。
    """
    pattern = r"^`(\$.*?\$)`$"
    return re.sub(pattern, r"\1", text)


def remove_outer_markdown_markers(text: str) -> str:
    """
    文章中の "```markdown" で始まるブロックについて、
    最も遠くにある "```" を閉じマーカーとして認識し、
    開始の "```markdown" とその閉じマーカー "```" のみを削除します。
    """
    pattern = r"```markdown(.*)```"
    return re.sub(pattern, lambda m: m.group(1), text, flags=re.DOTALL)


def remove_outer_singlequotes(text: str) -> str:
    """
    文章中の "'''" で始まるブロックについて、
    最も遠くにある "'''" を閉じマーカーとして認識し、
    開始の "'''" とその閉じマーカー "'''" のみを削除します。
    """
    pattern = r"'''(.*)'''"
    return re.sub(pattern, lambda m: m.group(1), text, flags=re.DOTALL)


@dataclass
class PaperInfo:
    """
    arXiv論文情報。

    Parameters
    ----------
    title : str
        論文タイトル。
    abstract : str
        要約。
    url : str
        URL。
    contents : str
        論文の内容。
    """

    title: str
    abstract: str
    url: str
    contents: str
    summary: str = field(init=False)


class ArxivSummarizer(BaseService):
    """
    arXiv論文を収集・要約するクラス。

    Parameters
    ----------
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """

    def __init__(self, storage_dir: str = "data"):
        """
        ArxivSummarizerを初期化します。

        Parameters
        ----------
        storage_dir : str, default="data"
            ストレージディレクトリのパス。
        """
        super().__init__("arxiv_summarizer")
        self.http_client = None  # setup_http_clientで初期化

    async def collect(self, limit: int = 5) -> None:
        """
        arXiv論文を収集・要約して保存します。

        Parameters
        ----------
        limit : int, default=5
            取得する論文数。
        """
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()
        
        # Hugging Faceでキュレーションされた論文IDを取得
        paper_ids = await self._get_curated_paper_ids(limit)

        # 論文情報を並行して取得
        tasks = []
        for paper_id in paper_ids:
            tasks.append(self._retrieve_paper_info(paper_id))

        paper_results = await asyncio.gather(*tasks, return_exceptions=True)

        papers = []
        for result in paper_results:
            if isinstance(result, PaperInfo):
                papers.append(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Error retrieving paper: {result}")

        # 論文を並行して要約
        await self._summarize_papers(papers)

        # 要約を保存
        await self._store_summaries(papers)

        # 処理済みの論文IDを保存
        await self._save_processed_ids(paper_ids)

    # 同期版の互換性のためのラッパー
    def run(self, limit: int = 5) -> None:
        """同期的に実行するためのラッパー"""
        asyncio.run(self.collect(limit))

    def _is_valid_body_line(self, line: str, min_length: int = 80):
        """本文として妥当な行かを判断するための簡易ヒューリスティック。"""
        if "@" in line:
            return False
        for kw in [
            "university",
            "lab",
            "department",
            "institute",
            "corresponding author",
        ]:
            if kw in line.lower():
                return False
        if len(line) < min_length:
            return False
        return False if "." not in line else True

    @handle_errors(retries=3)
    async def _get_curated_paper_ids(self, limit: int) -> List[str]:
        """
        Hugging Faceでキュレーションされた論文IDを取得します。

        Parameters
        ----------
        limit : int
            取得する論文数。

        Returns
        -------
        List[str]
            論文IDのリスト。
        """
        # Hugging Faceの論文ページから最新の論文IDを取得
        url = "https://huggingface.co/papers"
        response = await self.http_client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        paper_ids = []
        paper_links = soup.select("a[href^='/papers/']")

        for link in paper_links:
            href = link.get("href", "")
            if "/papers/" in href:
                paper_id_match = re.search(r"/papers/(\d+\.\d+)", href)
                if paper_id_match:
                    paper_id = paper_id_match.group(1)
                    if paper_id not in paper_ids:
                        paper_ids.append(paper_id)
                        if len(paper_ids) >= limit:
                            break

        # 既に処理済みの論文IDを除外
        processed_ids = await self._get_processed_ids()
        paper_ids = [pid for pid in paper_ids if pid not in processed_ids]

        return paper_ids[:limit]

    async def _get_processed_ids(self) -> List[str]:
        """
        既に処理済みの論文IDを取得します。

        Returns
        -------
        List[str]
            処理済みの論文IDのリスト。
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        filename = f"arxiv_ids-{date_str}.txt"

        content = await self.storage.load(filename)
        if not content:
            return []

        return [line.strip() for line in content.split("\n") if line.strip()]

    async def _save_processed_ids(self, paper_ids: List[str]) -> None:
        """
        処理済みの論文IDを保存します。

        Parameters
        ----------
        paper_ids : List[str]
            処理済みの論文IDのリスト。
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        filename = f"arxiv_ids-{date_str}.txt"

        # 既存のIDを読み込む
        existing_ids = await self._get_processed_ids()

        # 新しいIDを追加
        all_ids = existing_ids + paper_ids
        all_ids = list(dict.fromkeys(all_ids))  # 重複を削除

        content = "\n".join(all_ids)
        await self.save_data(content, filename)

    async def _retrieve_paper_info(self, paper_id: str) -> Optional[PaperInfo]:
        """
        論文情報を取得します。

        Parameters
        ----------
        paper_id : str
            論文ID。

        Returns
        -------
        PaperInfo or None
            取得した論文情報。取得に失敗した場合はNone。
        """
        try:
            # arxivライブラリは同期的なので、別スレッドで実行
            loop = asyncio.get_event_loop()

            def get_paper():
                client = arxiv.Client()
                search = arxiv.Search(id_list=[paper_id])
                results = list(client.results(search))
                return results[0] if results else None

            paper = await loop.run_in_executor(None, get_paper)

            if not paper:
                return None

            # PDFから本文を抽出
            arxiv_id = paper.entry_id.split("/")[-1]  # URLからIDを抽出
            contents = await self._extract_body_text(arxiv_id)
            if not contents:  # HTML抽出に失敗した場合はアブストラクトを使用
                contents = paper.summary

            # タイトルとアブストラクトを日本語に翻訳
            title = paper.title
            abstract_ja = await self._translate_to_japanese(paper.summary)

            return PaperInfo(
                title=title, abstract=abstract_ja, url=paper.entry_id, contents=contents
            )

        except Exception as e:
            self.logger.error(f"Error retrieving paper {paper_id}: {str(e)}")
            return None

    async def _translate_to_japanese(self, text: str) -> str:
        """
        テキストを日本語に翻訳します。

        Parameters
        ----------
        text : str
            翻訳するテキスト。

        Returns
        -------
        str
            翻訳されたテキスト。
        """
        try:
            prompt = f"以下の英語の学術論文のテキストを自然な日本語に翻訳してください。専門用語は適切に翻訳し、必要に応じて英語の専門用語を括弧内に残してください。\n\n{text}"

            translated_text = await self.gpt_client.generate_async(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1000,
                service_name=self.service_name,
            )

            await self.rate_limit()

            return translated_text
        except Exception as e:
            self.logger.error(f"Error translating text: {str(e)}")
            return text  # 翻訳に失敗した場合は原文を返す

    async def _extract_body_text(self, arxiv_id: str, min_line_length: int = 40) -> str:
        """ArXivのHTMLから本文を抽出"""
        try:
            response = await self.http_client.get(f"https://arxiv.org/html/{arxiv_id}")
            soup = BeautifulSoup(response, "html.parser")

            body = soup.body
            if body:
                for tag in body.find_all(
                    ["header", "nav", "footer", "script", "style"]
                ):
                    tag.decompose()
                full_text = body.get_text(separator="\n", strip=True)
            else:
                full_text = ""

            lines = full_text.splitlines()

            # ヒューリスティックにより、実際の論文本文の開始行を探す
            start_index = 0
            for i, line in enumerate(lines):
                clean_line = line.strip()
                # 先頭部分の空行や短すぎる行はスキップ
                if len(clean_line) < min_line_length:
                    continue
                if self._is_valid_body_line(clean_line, min_length=100):
                    start_index = i
                    break

            # 開始行以降を本文として抽出
            body_lines = lines[start_index:]
            # ノイズ除去: 短すぎる行は除外
            filtered_lines = []
            for line in body_lines:
                if len(line.strip()) >= min_line_length:
                    line = line.strip()
                    line = line.replace("Â", " ")
                    filtered_lines.append(line.strip())
            return "\n".join(filtered_lines)
        except Exception as e:
            self.logger.error(f"Error extracting body text: {str(e)}")
            return ""  # エラー時は空文字列を返す

    async def _summarize_papers(self, papers: List[PaperInfo]) -> None:
        """複数の論文を並行して要約"""
        tasks = []
        for paper in papers:
            tasks.append(self._summarize_paper_info(paper))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _summarize_paper_info(self, paper_info: PaperInfo) -> None:
        """論文を要約します。"""
        prompt = """
        以下の8つの質問について、順を追って非常に詳細に、分かりやすく答えてください。

        1. 既存研究では何ができなかったのか
        2. どのようなアプローチでそれを解決しようとしたか
        3. 結果、何が達成できたのか
        4. 制限や問題点は何ですか。本文で言及されているやあなたが考えるものも含めて教えてください
        5. 技術的な詳細について。技術者が読むことを想定したトーンで教えてください
        6. コストや物理的な詳細について教えてください。例えばトレーニングに使用したGPUの数や時間、データセット、モデルのサイズなど
        7. 参考文献のうち、特に参照すべきものを教えてください
        8. この論文を140字以内で要約するとどうなりますか？

        フォーマットは以下の通りで、markdown形式で回答してください。このフォーマットに沿った文言以外の出力は不要です。
        なお、数式は表示が崩れがちで面倒なので、説明に数式を使うときは、代わりにPython風の疑似コードを書いてください。

        1. 既存研究では何ができなかったのか

        ...

        2. どのようなアプローチでそれを解決しようとしたか

        ...

        （以下同様）
        """

        system_instruction = f"""
        以下のテキストは、ある論文のタイトルとURL、abstract、および本文のコンテンツです。
        本文はhtmlから抽出されたもので、ノイズや不要な部分が含まれている可能性があります。
        よく読んで、ユーザーの質問に答えてください。

        title
        '''
        {paper_info.title}
        '''

        url
        '''
        {paper_info.url}
        '''

        abstract
        '''
        {paper_info.abstract}
        '''

        contents
        '''
        {paper_info.contents}
        '''
        """

        try:
            summary = await self.gpt_client.generate_async(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.3,
                max_tokens=3000,  # 8つの質問に対応するため増量
                service_name=self.service_name,
            )

            # 出力の整形
            summary = remove_tex_backticks(summary)
            summary = remove_outer_markdown_markers(summary)
            summary = remove_outer_singlequotes(summary)

            paper_info.summary = summary
            await self.rate_limit()
        except Exception as e:
            self.logger.error(f"Error generating summary: {type(e).__name__}: {str(e)}")
            if hasattr(e, "last_attempt") and hasattr(e.last_attempt, "exception"):
                inner_error = e.last_attempt.exception()
                self.logger.error(
                    f"Inner error: {type(inner_error).__name__}: {str(inner_error)}"
                )
            paper_info.summary = f"要約の生成中にエラーが発生しました: {str(e)}"

    async def _store_summaries(self, papers: List[PaperInfo]) -> None:
        """
        要約を保存します。

        Parameters
        ----------
        papers : List[PaperInfo]
            保存する論文のリスト。
        """
        if not papers:
            return

        today = datetime.now()
        content = f"# arXiv 論文要約 ({today.strftime('%Y-%m-%d')})\n\n"

        for paper in papers:
            content += f"## [{paper.title}]({paper.url})\n\n"
            content += f"**abstract**:\n{paper.abstract}\n\n"
            content += f"**summary**:\n{paper.summary}\n\n"
            content += "---\n\n"

        # 保存
        filename = f"{today.strftime('%Y-%m-%d')}.md"
        await self.save_markdown(content, filename)
