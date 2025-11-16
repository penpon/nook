"""GitHubのトレンドリポジトリを収集するサービス。"""

import re
import tomllib
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from textwrap import dedent
from typing import Any

from bs4 import BeautifulSoup

from nook.common.base_service import BaseService
from nook.common.daily_snapshot import group_records_by_date, store_daily_snapshots
from nook.common.date_utils import target_dates_set
from nook.common.decorators import handle_errors
from nook.common.dedup import DedupTracker
from nook.common.exceptions import APIException
from nook.common.logging_utils import (
    log_article_counts,
    log_processing_start,
    log_summarization_progress,
    log_summarization_start,
    log_summary_candidates,
)


@dataclass
class Repository:
    """
    GitHubリポジトリ情報。

    Parameters
    ----------
    name : str
        リポジトリ名。
    description : str | None
        説明。
    link : str
        リポジトリへのリンク。
    stars : int
        スター数。
    """

    name: str
    description: str | None
    link: str
    stars: int


class GithubTrending(BaseService):
    """
    GitHubのトレンドリポジトリを収集するクラス。

    Parameters
    ----------
    storage_dir : str, default="data"
        ストレージディレクトリのパス。
    """

    def __init__(self, storage_dir: str = "data"):
        """
        GithubTrendingを初期化します。

        Parameters
        ----------
        storage_dir : str, default="data"
            ストレージディレクトリのパス。
        """
        super().__init__("github_trending")
        self.base_url = "https://github.com/trending"
        self.http_client = None  # setup_http_clientで初期化

        # 言語の設定を読み込む
        script_dir = Path(__file__).parent
        with open(script_dir / "languages.toml", "rb") as f:
            self.languages_config = tomllib.load(f)

    async def collect(
        self,
        limit: int = 5,
        *,
        target_dates: list[date] | None = None,
    ) -> list[tuple[str, str]]:
        """
        GitHubのトレンドリポジトリを収集して保存します。

        Parameters
        ----------
        limit : int, default=5
            各言語から取得するリポジトリ数。

        Returns
        -------
        list[tuple[str, str]]
            保存されたファイルパスのリスト [(json_path, md_path), ...]
        """
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        effective_target_dates = target_dates if target_dates is not None else target_dates_set(1)

        # 日付ごとに処理
        saved_files: list[tuple[str, str]] = []
        for target_date in sorted(effective_target_dates):
            date_str = target_date.strftime("%Y-%m-%d")

            # その日の既存リポジトリ名を取得
            existing_names_for_date = set()
            try:
                existing_repos = await self._load_existing_repositories_by_date(
                    datetime.combine(target_date, time.min)
                )
                existing_names_for_date = {repo.get("name", "") for repo in existing_repos}
            except Exception as e:
                self.logger.debug(
                    f"既存リポジトリファイル {date_str}.json の読み込みに失敗しました: {e}"
                )

            # 重複トラッカーを初期化
            dedup_tracker = DedupTracker()
            for name in existing_names_for_date:
                dedup_tracker.add(name)

            all_repositories = []

            # 言語指定なしのリポジトリを取得
            repositories = await self._retrieve_repositories("any", limit, dedup_tracker)
            all_repositories.append(("all", repositories))
            await self.rate_limit()  # レート制限を遵守

            # 一般的な言語のリポジトリを取得
            for language in self.languages_config["general"]:
                repositories = await self._retrieve_repositories(language, limit, dedup_tracker)
                all_repositories.append((language, repositories))
                await self.rate_limit()  # レート制限を遵守

            # 特定の言語のリポジトリを取得
            for language in self.languages_config["specific"]:
                repositories = await self._retrieve_repositories(language, limit, dedup_tracker)
                all_repositories.append((language, repositories))
                await self.rate_limit()  # レート制限を遵守

            # 全リポジトリをフラット化
            all_repos_flat = []
            for _, repositories in all_repositories:
                for repo in repositories:
                    all_repos_flat.append(repo)

            # 既存/新規リポジトリ数をカウント
            existing_count = len(existing_names_for_date)

            # 真に新規のリポジトリを確認
            truly_new_repositories = [
                repo for repo in all_repos_flat if repo.name not in existing_names_for_date
            ]

            # 日付情報を先頭に表示
            log_processing_start(self.logger, date_str)
            log_article_counts(self.logger, existing_count, len(truly_new_repositories))

            if truly_new_repositories:
                # 上位15件を選択して表示
                selected_repos = sorted(
                    truly_new_repositories, key=lambda x: x.stars, reverse=True
                )[:15]

                log_summary_candidates(self.logger, selected_repos, "stars")

                # 要約生成
                log_summarization_start(self.logger)

                # 言語ごとに再グループ化して翻訳
                repos_by_language = {}
                for language, repositories in all_repositories:
                    repos_by_language[language] = [
                        repo for repo in repositories if repo in truly_new_repositories
                    ]

                repos_for_translation = [
                    (lang, repos) for lang, repos in repos_by_language.items() if repos
                ]

                translated_repos = await self._translate_repositories(
                    repos_for_translation,
                    progress_callback=lambda idx, total, name: log_summarization_progress(
                        self.logger, idx, total, name
                    ),
                )

                # 保存処理
                json_path, md_path = await self._store_summaries_for_date(
                    translated_repos, target_date
                )
                self.logger.info(f"\n   💾 保存完了: {json_path}, {md_path}")
                saved_files.append((json_path, md_path))
            else:
                self.logger.info("   ℹ️  新規リポジトリがありません")

        # 処理完了メッセージ
        if saved_files:
            self.logger.info(f"\n💾 {len(saved_files)}日分のデータを保存完了")
            for json_path, md_path in saved_files:
                self.logger.info(f"   💾 保存完了: {json_path}, {md_path}")
        else:
            self.logger.info("\n保存するリポジトリがありません")

        return saved_files

    @handle_errors(retries=3)
    async def _retrieve_repositories(
        self, language: str, limit: int, dedup_tracker: DedupTracker
    ) -> list[Repository]:
        """
        特定の言語のトレンドリポジトリを取得します。

        Parameters
        ----------
        language : str
            言語名（空文字列の場合はすべての言語）。
        limit : int
            取得するリポジトリ数。

        Returns
        -------
        List[Repository]
            取得したリポジトリのリスト。
        """
        url = self.base_url
        if language:
            url += f"/{language}"

        try:
            response = await self.http_client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            repositories = []
            repo_elements = soup.select("article.Box-row")

            for repo_element in repo_elements:
                # リポジトリ名を取得
                name_element = repo_element.select_one("h2 a")
                if not name_element:
                    continue

                name = name_element.text.strip().replace("\n", "").replace(" ", "")
                link = f"https://github.com{name_element['href']}"

                is_dup, normalized = dedup_tracker.is_duplicate(name)
                if is_dup:
                    original = dedup_tracker.get_original_title(normalized) or name
                    self.logger.info(
                        "重複リポジトリをスキップ: '%s' (初出: '%s')",
                        name,
                        original,
                    )
                    continue

                # 説明を取得
                description_element = repo_element.select_one("p")
                description = description_element.text.strip() if description_element else None

                # スター数を取得
                stars_element = repo_element.select_one("a.Link--muted")
                stars_text = stars_element.text.strip() if stars_element else "0"
                stars = (
                    int(stars_text.replace(",", "")) if stars_text.replace(",", "").isdigit() else 0
                )

                repository = Repository(name=name, description=description, link=link, stars=stars)

                repositories.append(repository)
                dedup_tracker.add(name)

                if len(repositories) >= limit:
                    break

            return repositories

        except Exception as e:
            self.logger.error(f"Error retrieving repositories for language {language}: {str(e)}")
            raise APIException(f"Failed to retrieve repositories for {language}") from e

    def _load_existing_repositories(self) -> DedupTracker:
        tracker = DedupTracker()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            file_path = Path(self.storage.base_dir) / f"{today}.md"
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                for match in re.finditer(r"^### \[(.+?)\]", content, re.MULTILINE):
                    tracker.add(match.group(1))
        except Exception as exc:
            self.logger.debug(f"既存リポジトリの読み込みに失敗しました: {exc}")
        return tracker

    async def _translate_repositories(
        self,
        repositories_by_language: list[tuple[str, list[Repository]]],
        *,
        progress_callback=None,
    ) -> list[tuple[str, list[Repository]]]:
        """
        リポジトリの説明を日本語に翻訳します。

        Parameters
        ----------
        repositories_by_language : List[tuple[str, List[Repository]]]
            言語ごとのリポジトリリスト。
        progress_callback : callable, optional
            進捗表示用のコールバック関数

        Returns
        -------
        List[tuple[str, List[Repository]]]
            翻訳されたリポジトリリスト。
        """
        # 進捗カウンターを初期化
        total_repos = sum(len(repos) for _, repos in repositories_by_language)
        current_idx = 0

        try:
            for _language, repositories in repositories_by_language:
                for repo in repositories:
                    if repo.description:
                        prompt = dedent(
                            f"""
                            以下のGitHubリポジトリの説明文を日本語で要約してください。
                            制約:
                            - 概要は合計で300文字以内を目安にまとめること。
                            - 箇条書きを追加し、3項目とすること。
                            - 新しい情報を推測せず、原文の内容に基づいて説明すること。
                            - 出力形式：
                              概要: <概要>
                              主なポイント:
                              - <ポイント1>
                              - <ポイント2>

                            リポジトリ名: {repo.name}
                            原文説明: {repo.description}
                            """
                        )
                        try:
                            repo.description = await self.gpt_client.generate_async(
                                prompt=prompt,
                                temperature=0.3,
                                max_tokens=300,
                            )
                            if repo.description:
                                repo.description = repo.description.strip()
                            await self.rate_limit()  # API呼び出し後のレート制限

                            # 進捗表示
                            current_idx += 1
                            if progress_callback:
                                progress_callback(current_idx, total_repos, repo.name)

                        except Exception as e:
                            self.logger.error(
                                f"Error translating description for {repo.name}: {str(e)}"
                            )

        except Exception as e:
            self.logger.error(f"Error in translation process: {str(e)}")

        return repositories_by_language

    async def _store_summaries_for_date(
        self,
        repositories_by_language: list[tuple[str, list[Repository]]],
        target_date: date,
    ) -> tuple[str, str]:
        """
        特定の日付のリポジトリ情報を保存します。

        Parameters
        ----------
        repositories_by_language : List[tuple[str, List[Repository]]]
            言語ごとのリポジトリリスト。
        target_date : date
            対象日付。

        Returns
        -------
        tuple[str, str]
            保存されたファイルパス (json_path, md_path)
        """
        if not repositories_by_language:
            raise ValueError("保存するリポジトリがありません")

        records = self._serialize_repositories(repositories_by_language, target_date)
        records_by_date = group_records_by_date(records, default_date=target_date)

        saved_files = await store_daily_snapshots(
            records_by_date,
            load_existing=self._load_existing_repositories_by_date,
            save_json=self.save_json,
            save_markdown=self.save_markdown,
            render_markdown=self._render_markdown,
            key=lambda item: item.get("name", ""),
            sort_key=self._repository_sort_key,
            limit=None,
            logger=None,  # 日付情報の二重表示を防ぐ
        )

        if saved_files and len(saved_files) > 0:
            return saved_files[0]  # 最初の（唯一の）ファイルパスを返す
        else:
            raise ValueError("保存に失敗しました")

    async def _store_summaries(
        self,
        repositories_by_language: list[tuple[str, list[Repository]]],
        limit_per_language: int | None,
        target_dates: list[date],
    ) -> list[tuple[str, str]]:
        """
        リポジトリ情報を保存します。

        Parameters
        ----------
        repositories_by_language : List[tuple[str, List[Repository]]]
            言語ごとのリポジトリリスト。
        limit_per_language : int | None
            各言語の最大件数。None の場合は入力データの件数を利用。

        Returns
        -------
        list[tuple[str, str]]
            保存されたファイルパスのリスト [(json_path, md_path), ...]
        """
        if not repositories_by_language:
            self.logger.info("保存するリポジトリがありません")
            return []

        default_date = max(target_dates) if target_dates else datetime.now().date()
        records = self._serialize_repositories(repositories_by_language, default_date)
        records_by_date = group_records_by_date(records, default_date=default_date)

        saved_files = await store_daily_snapshots(
            records_by_date,
            load_existing=self._load_existing_repositories_by_date,
            save_json=self.save_json,
            save_markdown=self.save_markdown,
            render_markdown=self._render_markdown,
            key=lambda item: item.get("name", ""),
            sort_key=self._repository_sort_key,
            limit=None,
            logger=self.logger,
        )

        return saved_files

    def _serialize_repositories(
        self,
        repositories_by_language: list[tuple[str, list[Repository]]],
        default_date: date,
    ) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        base_dt = datetime.combine(default_date, time.min, tzinfo=UTC)
        now_iso = base_dt.isoformat()
        for language, repositories in repositories_by_language:
            for repo in repositories:
                serialized.append(
                    {
                        "language": language,
                        "name": repo.name,
                        "description": repo.description,
                        "link": repo.link,
                        "stars": repo.stars,
                        "published_at": now_iso,
                    }
                )
        return serialized

    async def _load_existing_repositories_by_date(
        self, target_date: datetime
    ) -> list[dict[str, Any]]:
        date_str = target_date.strftime("%Y-%m-%d")
        filename_json = f"{date_str}.json"
        existing_json = await self.load_json(filename_json)
        if existing_json:
            if isinstance(existing_json, dict):
                flattened: list[dict[str, Any]] = []
                for language, repos in existing_json.items():
                    for repo in repos:
                        flattened.append({"language": language, **repo})
                return flattened
            return existing_json

        markdown_content = await self.storage.load(f"{date_str}.md")
        if not markdown_content:
            return []

        return self._parse_markdown(markdown_content)

    def _repository_sort_key(self, item: dict[str, Any]) -> tuple[int, datetime]:
        stars = int(item.get("stars", 0) or 0)
        published_raw = item.get("published_at")
        if published_raw:
            try:
                published = datetime.fromisoformat(published_raw)
            except ValueError:
                published = datetime.min.replace(tzinfo=UTC)
        else:
            published = datetime.min.replace(tzinfo=UTC)
        return (stars, published)

    def _render_markdown(self, records: list[dict[str, Any]], today: datetime) -> str:
        content = f"# GitHub トレンドリポジトリ ({today.strftime('%Y-%m-%d')})\n\n"

        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            language = record.get("language", "all")
            grouped.setdefault(language, []).append(record)

        for language, repositories in grouped.items():
            if not repositories:
                continue

            language_display = language if language != "all" else "すべての言語"
            content += f"## {language_display.capitalize()}\n\n"

            for repo in repositories:
                content += f"### [{repo['name']}]({repo.get('link')})\n\n"

                description = repo.get("description")
                if description:
                    content += f"{description}\n\n"

                content += f"⭐ スター数: {repo.get('stars', 0)}\n\n"
                content += "---\n\n"

        return content

    def _parse_markdown(self, content: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        language_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        repo_pattern = re.compile(
            r"### \[(?P<name>.+?)\]\((?P<link>[^\)]+)\)\n\n"
            r"(?P<description>.*?)(?:\n\n)?⭐ スター数: (?P<stars>[0-9,]+)",
            re.DOTALL,
        )

        sections = list(language_pattern.finditer(content))
        for idx, match in enumerate(sections):
            start = match.end()
            end = sections[idx + 1].start() if idx + 1 < len(sections) else len(content)
            section_content = content[start:end]

            language_header = match.group(1).strip()
            language_key = (
                "all" if language_header.lower().startswith("すべて") else language_header.lower()
            )

            for repo_match in repo_pattern.finditer(section_content):
                name = repo_match.group("name").strip()
                link = repo_match.group("link").strip()
                description = repo_match.group("description").strip()
                stars_text = repo_match.group("stars")
                stars = int(stars_text.replace(",", "")) if stars_text else 0

                records.append(
                    {
                        "language": language_key,
                        "name": name,
                        "link": link,
                        "description": description,
                        "stars": stars,
                    }
                )

        return records
