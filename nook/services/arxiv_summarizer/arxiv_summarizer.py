"""arXiv論文を収集・要約するサービス。"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from io import BytesIO

import arxiv
import httpx
import pdfplumber
from bs4 import BeautifulSoup

from nook.common.base_service import BaseService
from nook.common.daily_snapshot import group_records_by_date, store_daily_snapshots
from nook.common.date_utils import is_within_target_dates, target_dates_set
from nook.common.decorators import handle_errors
from nook.common.logging_utils import (
    log_article_counts,
    log_multiple_dates_processing,
    log_no_new_articles,
    log_processing_start,
    log_storage_complete,
    log_summarization_progress,
    log_summarization_start,
    log_summary_candidates,
)


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
    published_at: datetime | None = None


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

    async def collect(
        self,
        limit: int = 5,
        *,
        target_dates: list[date] | None = None,
    ) -> list[tuple[str, str]]:
        """
        arXiv論文を収集・要約して保存します。

        Parameters
        ----------
        limit : int, default=5
            取得する論文数。

        Returns
        -------
        list[tuple[str, str]]
            保存されたファイルパスのリスト [(json_path, md_path), ...]
        """
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        effective_target_dates = target_dates or target_dates_set(1)
        sorted_dates = sorted(effective_target_dates)

        # 対象期間のログ出力
        if not sorted_dates:
            self.logger.info("対象日が指定されていないため処理を終了します")
            return []

        if len(sorted_dates) == 1:
            log_processing_start(self.logger, sorted_dates[0].strftime("%Y-%m-%d"))
        else:
            log_multiple_dates_processing(self.logger, sorted_dates)

        # 対象日ごとにHugging Faceから論文IDを取得
        collected_ids: list[str] = []
        seen_ids: set[str] = set()
        for snapshot_date in reversed(sorted_dates):
            snapshot_str = snapshot_date.strftime("%Y-%m-%d")
            self.logger.info(f"\n🗓️ {snapshot_str} の候補論文IDを収集中...")

            daily_ids = await self._get_curated_paper_ids(limit, snapshot_date)

            if daily_ids is None:
                self.logger.info("   ℹ️ URLが見つかりませんでした")
                continue

            if not daily_ids:
                self.logger.info("   ℹ️ 取得できるIDがありませんでした")
                continue

            new_ids = [paper_id for paper_id in daily_ids if paper_id not in seen_ids]

            if not new_ids:
                self.logger.info("   ℹ️ すべて既存IDのためスキップしました")
                continue

            for paper_id in new_ids:
                seen_ids.add(paper_id)
                collected_ids.append(paper_id)

            self.logger.info(
                "   ✅ 新規ID %d件 (累計%d件)",
                len(new_ids),
                len(collected_ids),
            )

        if not collected_ids:
            self.logger.info("\n保存する論文がありません")
            return []

        # 論文情報を並行して取得
        tasks = []
        for paper_id in collected_ids:
            tasks.append(self._retrieve_paper_info(paper_id))

        paper_results = await asyncio.gather(*tasks, return_exceptions=True)

        papers = []
        for result in paper_results:
            if isinstance(result, PaperInfo):
                if is_within_target_dates(result.published_at, effective_target_dates):
                    papers.append(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Error retrieving paper: {result}")

        # 論文情報を表示
        if papers:
            existing_count = 0  # 既存論文数（簡略化）
            new_count = len(papers)  # 新規論文数

            # 論文情報を表示
            log_article_counts(self.logger, existing_count, new_count)
            log_summary_candidates(self.logger, papers, "published_at")

        # 論文を逐次要約（リアルタイム進捗表示）
        if papers:
            log_summarization_start(self.logger)
            for idx, paper in enumerate(papers, 1):
                await self._summarize_paper_info(paper)
                log_summarization_progress(self.logger, idx, len(papers), paper.title)

        # 要約を保存
        saved_files = await self._store_summaries(papers, limit, effective_target_dates)

        # 処理完了メッセージ
        if saved_files:
            self.logger.info(f"\n💾 {len(saved_files)}日分のデータを保存完了")
            for json_path, md_path in saved_files:
                log_storage_complete(self.logger, json_path, md_path)
        else:
            log_no_new_articles(self.logger)

        # 処理済みの論文IDを保存（日付ごとに分けて保存）
        await self._save_processed_ids_by_date(collected_ids, effective_target_dates)

        return saved_files

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
    async def _get_curated_paper_ids(self, limit: int, snapshot_date: date) -> list[str] | None:
        """
        Hugging Faceでキュレーションされた論文IDを取得します。

        Parameters
        ----------
        limit : int
            取得する論文数。
        snapshot_date : date
            参照するHugging Faceページの日付。

        Returns
        -------
        List[str] or None
            論文IDのリスト。URLが存在しない場合はNoneを返す。
        """
        paper_ids: list[str] = []

        # Upvote順で並んでいる日付ページから論文IDを抽出
        page_url = f"https://huggingface.co/papers/date/{snapshot_date:%Y-%m-%d}"
        try:
            response = await self.http_client.get(page_url)
            response.raise_for_status()

            # リダイレクトを検出（実際のURLとリクエストしたURLが異なる場合はリダイレクト）
            if str(response.url) != page_url:
                self.logger.info(
                    "Hugging Face日付ページが見つかりませんでした: %s",
                    page_url,
                )
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            for article in soup.select("article"):
                link = article.find("a", href=re.compile(r"^/papers/\d+\.\d+"))
                if not link:
                    continue

                href = link.get("href", "")
                paper_id_match = re.search(r"/papers/(\d+\.\d+)", href)
                if not paper_id_match:
                    continue

                paper_id = paper_id_match.group(1)
                if paper_id in paper_ids:
                    continue

                paper_ids.append(paper_id)
                if len(paper_ids) >= limit:
                    break

            if not paper_ids:
                self.logger.warning(
                    "Hugging Face日付ページから論文IDを取得できませんでした: %s",
                    page_url,
                )
        except httpx.HTTPStatusError as exc:
            # 404エラーの場合はURLが存在しないことを示す
            if exc.response.status_code == 404:
                self.logger.info(
                    "Hugging Face日付ページが見つかりませんでした: %s",
                    page_url,
                )
                return None
            else:
                self.logger.error(
                    "Hugging Face日付ページの取得に失敗しました (%s): %s",
                    page_url,
                    exc,
                )
        except Exception as exc:
            self.logger.error(
                "Hugging Face日付ページの取得に失敗しました (%s): %s",
                page_url,
                exc,
            )

        # フォールバック: 旧来のトップページから取得
        if not paper_ids:
            fallback_url = "https://huggingface.co/papers"
            response = await self.http_client.get(fallback_url)
            soup = BeautifulSoup(response.text, "html.parser")

            paper_links = soup.select("a[href^='/papers/']")
            for link in paper_links:
                href = link.get("href", "")
                paper_id_match = re.search(r"/papers/(\d+\.\d+)", href)
                if not paper_id_match:
                    continue

                paper_id = paper_id_match.group(1)
                if paper_id in paper_ids:
                    continue

                paper_ids.append(paper_id)
                if len(paper_ids) >= limit:
                    break

            if paper_ids:
                self.logger.warning("トップページから論文IDを取得しました (フォールバック)")

        # 既に処理済みの論文IDを除外（対象日付のファイルから取得）
        processed_ids = await self._get_processed_ids(snapshot_date)
        paper_ids = [pid for pid in paper_ids if pid not in processed_ids]

        return paper_ids[:limit] if paper_ids else []

    async def _get_processed_ids(self, target_date: date | None = None) -> list[str]:
        """
        既に処理済みの論文IDを取得します。

        Parameters
        ----------
        target_date : date, optional
            対象日付。指定しない場合は今日の日付を使用。

        Returns
        -------
        List[str]
            処理済みの論文IDのリスト。
        """
        if target_date is None:
            target_date = datetime.now().date()

        date_str = target_date.strftime("%Y-%m-%d")
        filename = f"arxiv_ids-{date_str}.txt"

        content = await self.storage.load(filename)
        if not content:
            return []

        return [line.strip() for line in content.split("\n") if line.strip()]

    async def _save_processed_ids_by_date(
        self, paper_ids: list[str], target_dates: list[date]
    ) -> None:
        """
        処理済みの論文IDを日付ごとに保存します。

        Parameters
        ----------
        paper_ids : List[str]
            処理済みの論文IDのリスト。
        target_dates : Set[date]
            対象の日付セット。
        """
        # 論文情報を取得して公開日を確認
        tasks = []
        for paper_id in paper_ids:
            tasks.append(self._get_paper_date(paper_id))

        paper_dates = await asyncio.gather(*tasks, return_exceptions=True)

        # 日付ごとにIDをグループ化
        ids_by_date = {}
        for paper_id, paper_date in zip(paper_ids, paper_dates, strict=True):
            if isinstance(paper_date, date):
                date_str = paper_date.strftime("%Y-%m-%d")
                if date_str not in ids_by_date:
                    ids_by_date[date_str] = []
                ids_by_date[date_str].append(paper_id)
            else:
                # 日付が不明の場合は今日の日付を使用
                today = datetime.now()
                date_str = today.strftime("%Y-%m-%d")
                if date_str not in ids_by_date:
                    ids_by_date[date_str] = []
                ids_by_date[date_str].append(paper_id)

        # 日付ごとにファイルに保存
        for date_str, ids in ids_by_date.items():
            filename = f"arxiv_ids-{date_str}.txt"

            # 既存のIDを読み込む
            existing_ids = await self._load_ids_from_file(filename)

            # 新しいIDを追加
            all_ids = existing_ids + ids
            all_ids = list(dict.fromkeys(all_ids))  # 重複を削除

            content = "\n".join(all_ids)
            await self.save_data(content, filename)

    async def _load_ids_from_file(self, filename: str) -> list[str]:
        """
        指定されたファイルからIDを読み込みます。

        Parameters
        ----------
        filename : str
            ファイル名。

        Returns
        -------
        List[str]
            IDのリスト。
        """
        content = await self.storage.load(filename)
        if not content:
            return []

        return [line.strip() for line in content.split("\n") if line.strip()]

    async def _get_paper_date(self, paper_id: str) -> date | None:
        """
        論文の公開日を取得します。

        Parameters
        ----------
        paper_id : str
            論文ID。

        Returns
        -------
        date or None
            論文の公開日。取得できない場合はNone。
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

            published = getattr(paper, "published", None)
            if isinstance(published, datetime):
                return published.date()

            return None
        except Exception as e:
            self.logger.error(f"Error getting paper date for {paper_id}: {str(e)}")
            return None

    async def _retrieve_paper_info(self, paper_id: str) -> PaperInfo | None:
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

            published_at = getattr(paper, "published", None)
            if isinstance(published_at, datetime):
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=UTC)
            else:
                published_at = datetime.now(UTC)

            return PaperInfo(
                title=title,
                abstract=abstract_ja,
                url=paper.entry_id,
                contents=contents,
                published_at=published_at,
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
        """
        ArXivから本文を抽出（HTML→PDF→アブストラクトのフォールバックチェーン）

        Parameters
        ----------
        arxiv_id : str
            arXiv論文ID
        min_line_length : int, default=40
            本文として扱う最小行長

        Returns
        -------
        str
            抽出された本文テキスト
        """
        # 1. HTML形式を試す
        html_text = await self._extract_from_html(arxiv_id, min_line_length)
        if html_text:
            self.logger.debug(f"HTMLから本文を抽出: {arxiv_id}")
            return html_text

        # 2. HTMLが取得できない場合はPDFを試す
        self.logger.info(f"HTML形式が利用できません: {arxiv_id} - PDF抽出に移行します")
        pdf_text = await self._extract_from_pdf(arxiv_id, min_line_length)
        if pdf_text:
            self.logger.info(f"PDFから本文を抽出: {arxiv_id}")
            return pdf_text

        # 3. どちらも失敗した場合は空文字列（呼び出し元でアブストラクトを使用）
        self.logger.warning(f"本文抽出失敗: {arxiv_id} - アブストラクトを使用します")
        return ""

    async def _download_html_without_retry(self, html_url: str) -> str:
        """
        リトライなしでHTMLをダウンロード（デコレータを回避）

        Parameters
        ----------
        html_url : str
            HTMLのURL

        Returns
        -------
        str
            HTMLコンテンツ
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(html_url)
                response.raise_for_status()
                return response.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # 404は正常なケースなので静かに処理
                return ""
            raise
        except Exception:
            # その他のエラーは再発生
            raise

    async def _extract_from_html(self, arxiv_id: str, min_line_length: int = 40) -> str:
        """
        HTML形式から本文を抽出

        Parameters
        ----------
        arxiv_id : str
            arXiv論文ID
        min_line_length : int
            最小行長

        Returns
        -------
        str
            抽出されたテキスト
        """
        try:
            # HTMLをダウンロード（リトライなし）
            html_url = f"https://arxiv.org/html/{arxiv_id}"
            html_content = await self._download_html_without_retry(html_url)

            if not html_content:
                return ""

            soup = BeautifulSoup(html_content, "html.parser")

            body = soup.body
            if body:
                for tag in body.find_all(["header", "nav", "footer", "script", "style"]):
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
            self.logger.debug(f"HTML抽出失敗: {arxiv_id} - {str(e)}")
            return ""

    async def _download_pdf_without_retry(self, pdf_url: str) -> httpx.Response:
        """
        リトライなしでPDFをダウンロード（デコレータを回避）

        Parameters
        ----------
        pdf_url : str
            PDFのURL

        Returns
        -------
        httpx.Response
            HTTPレスポンス
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()
            return response

    async def _extract_from_pdf(self, arxiv_id: str, min_line_length: int = 40) -> str:
        """
        PDF形式から本文を抽出

        Parameters
        ----------
        arxiv_id : str
            arXiv論文ID
        min_line_length : int
            最小行長

        Returns
        -------
        str
            抽出されたテキスト
        """
        try:
            # PDFをダウンロード（リトライなし）
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

            # リトライなしのダウンロードメソッドを使用
            response = await self._download_pdf_without_retry(pdf_url)

            if not response.content:
                return ""

            # pdfplumberでテキスト抽出
            with pdfplumber.open(BytesIO(response.content)) as pdf:
                text_parts = []

                for _page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and len(page_text.strip()) > 100:  # 有意なテキストのみ
                            # ページ番号やヘッダー/フッターを除去
                            lines = page_text.split("\n")
                            filtered_lines = []

                            for line in lines:
                                clean_line = line.strip()
                                # ページ番号や短すぎる行を除外
                                if (
                                    len(clean_line) >= min_line_length
                                    and not clean_line.isdigit()
                                    and not clean_line.startswith("arXiv:")
                                    and "References" not in clean_line[:20]
                                ):  # 参考文献セクションを除外
                                    filtered_lines.append(clean_line)

                            if filtered_lines:
                                text_parts.append("\n".join(filtered_lines))

                    except Exception as page_error:
                        self.logger.debug(
                            f"ページ抽出失敗: {arxiv_id} page {_page_num} - {page_error}"
                        )
                        continue

                if text_parts:
                    full_text = "\n\n".join(text_parts)
                    return full_text
                else:
                    return ""

        except Exception as e:
            self.logger.debug(f"PDF抽出失敗: {arxiv_id} - {str(e)}")
            return ""

    async def _summarize_papers(self, papers: list[PaperInfo]) -> None:
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
                self.logger.error(f"Inner error: {type(inner_error).__name__}: {str(inner_error)}")
            paper_info.summary = f"要約の生成中にエラーが発生しました: {str(e)}"

    async def _store_summaries(
        self,
        papers: list[PaperInfo],
        limit: int,
        target_dates: list[date],
    ) -> list[tuple[str, str]]:
        """
        要約を保存します。

        Parameters
        ----------
        papers : List[PaperInfo]
            保存する論文のリスト。

        Returns
        -------
        list[tuple[str, str]]
            保存されたファイルパスのリスト [(json_path, md_path), ...]
        """
        if not papers:
            return []

        default_date = max(target_dates) if target_dates else datetime.now().date()
        records = self._serialize_papers(papers)
        records_by_date = group_records_by_date(records, default_date=default_date)

        saved_files = await store_daily_snapshots(
            records_by_date,
            load_existing=self._load_existing_papers,
            save_json=self.save_json,
            save_markdown=self.save_markdown,
            render_markdown=self._render_markdown,
            key=lambda item: item.get("title", ""),
            sort_key=self._paper_sort_key,
            limit=limit,
            logger=self.logger,
        )

        return saved_files

    def _serialize_papers(self, papers: list[PaperInfo]) -> list[dict]:
        records: list[dict] = []
        for paper in papers:
            published = paper.published_at or datetime.now(UTC)
            records.append(
                {
                    "title": paper.title,
                    "abstract": paper.abstract,
                    "url": paper.url,
                    "summary": getattr(paper, "summary", ""),
                    "contents": paper.contents,
                    "published_at": published.isoformat(),
                }
            )
        return records

    async def _load_existing_papers(self, target_date: datetime) -> list[dict]:
        date_str = target_date.strftime("%Y-%m-%d")
        filename_json = f"{date_str}.json"
        existing_json = await self.load_json(filename_json)
        if existing_json:
            return existing_json

        markdown = await self.storage.load(f"{date_str}.md")
        if not markdown:
            return []

        return self._parse_markdown(markdown)

    def _paper_sort_key(self, item: dict) -> tuple[int, datetime]:
        # arXivではスコアが無いのでアップデート日時のみでソート
        published_raw = item.get("published_at")
        if published_raw:
            try:
                published = datetime.fromisoformat(published_raw)
            except ValueError:
                published = datetime.min.replace(tzinfo=UTC)
        else:
            published = datetime.min.replace(tzinfo=UTC)
        return (0, published)

    def _render_markdown(self, records: list[dict], today: datetime) -> str:
        content = f"# arXiv 論文要約 ({today.strftime('%Y-%m-%d')})\n\n"
        for paper in records:
            content += f"## [{paper['title']}]({paper['url']})\n\n"
            content += f"**abstract**:\n{paper.get('abstract', '')}\n\n"
            content += f"**summary**:\n{paper.get('summary', '')}\n\n"
            content += "---\n\n"
        return content

    def _parse_markdown(self, markdown: str) -> list[dict]:
        pattern = re.compile(
            r"## \[(?P<title>.+?)\]\((?P<url>[^\)]+)\)\n\n"
            r"\*\*abstract\*\*:\n(?P<abstract>.*?)(?:\n\n)?"
            r"\*\*summary\*\*:\n(?P<summary>.*?)(?:\n\n)?---",
            re.DOTALL,
        )

        records: list[dict] = []
        for match in pattern.finditer(markdown + "---"):
            records.append(
                {
                    "title": match.group("title").strip(),
                    "url": match.group("url").strip(),
                    "abstract": match.group("abstract").strip(),
                    "summary": match.group("summary").strip(),
                    "contents": None,
                }
            )

        return records
