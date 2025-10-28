"""GitHubのトレンドリポジトリを収集するサービス。"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import dedent
import re

from typing import Any

import tomli
from bs4 import BeautifulSoup

from nook.common.base_service import BaseService
from nook.common.decorators import handle_errors
from nook.common.exceptions import APIException
from nook.common.dedup import DedupTracker
from nook.common.daily_merge import merge_grouped_records


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
            self.languages_config = tomli.load(f)

    async def collect(self, limit: int = 15) -> None:
        """
        GitHubのトレンドリポジトリを収集して保存します。

        Parameters
        ----------
        limit : int, default=10
            各言語から取得するリポジトリ数。
        """
        # HTTPクライアントの初期化を確認
        if self.http_client is None:
            await self.setup_http_client()

        dedup_tracker = self._load_existing_repositories()
        all_repositories = []

        # 言語指定なしのリポジトリを取得（新規追加）
        repositories = await self._retrieve_repositories("any", limit, dedup_tracker)
        all_repositories.append(("all", repositories))
        await self.rate_limit()  # レート制限を遵守

        # 一般的な言語のリポジトリを取得
        for language in self.languages_config["general"]:
            repositories = await self._retrieve_repositories(language, limit, dedup_tracker)
            all_repositories.append((language, repositories))
            await self.rate_limit()  # レート制限を遵守

        # 特定の言語のリポジトリを取得（limitと同じ数に変更）
        for language in self.languages_config["specific"]:
            # limit // 2 → limit
            repositories = await self._retrieve_repositories(language, limit, dedup_tracker)
            all_repositories.append((language, repositories))
            await self.rate_limit()  # レート制限を遵守

        # 翻訳処理
        all_repositories = await self._translate_repositories(all_repositories)

        # 保存
        await self._store_summaries(all_repositories, limit)

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
                description = (
                    description_element.text.strip() if description_element else None
                )

                # スター数を取得
                stars_element = repo_element.select_one("a.Link--muted")
                stars_text = stars_element.text.strip() if stars_element else "0"
                stars = (
                    int(stars_text.replace(",", ""))
                    if stars_text.replace(",", "").isdigit()
                    else 0
                )

                repository = Repository(
                    name=name, description=description, link=link, stars=stars
                )

                repositories.append(repository)
                dedup_tracker.add(name)

                if len(repositories) >= limit:
                    break

            return repositories

        except Exception as e:
            self.logger.error(
                f"Error retrieving repositories for language {language}: {str(e)}"
            )
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
        self, repositories_by_language: list[tuple[str, list[Repository]]]
    ) -> list[tuple[str, list[Repository]]]:
        """
        リポジトリの説明を日本語に翻訳します。

        Parameters
        ----------
        repositories_by_language : List[tuple[str, List[Repository]]]
            言語ごとのリポジトリリスト。

        Returns
        -------
        List[tuple[str, List[Repository]]]
            翻訳されたリポジトリリスト。
        """
        try:
            for language, repositories in repositories_by_language:
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
                        except Exception as e:
                            self.logger.error(
                                f"Error translating description for {repo.name}: {str(e)}"
                            )

        except Exception as e:
            self.logger.error(f"Error in translation process: {str(e)}")

        return repositories_by_language

    async def _store_summaries(
        self,
        repositories_by_language: list[tuple[str, list[Repository]]],
        limit_per_language: int | None,
    ) -> None:
        """
        リポジトリ情報を保存します。

        Parameters
        ----------
        repositories_by_language : List[tuple[str, List[Repository]]]
            言語ごとのリポジトリリスト。
        limit_per_language : int | None
            各言語の最大件数。None の場合は入力データの件数を利用。
        """
        today = datetime.now()
        filename = f"{today.strftime('%Y-%m-%d')}.md"
        filename_json = f"{today.strftime('%Y-%m-%d')}.json"

        incoming_map = self._serialize_repositories(repositories_by_language)

        existing_map = await self._load_existing_repository_map(
            filename_json, filename
        )

        limit_per_group = (
            limit_per_language
            if limit_per_language is not None
            else len(next(iter(incoming_map.values()), [])) or 15
        )

        merged_map = merge_grouped_records(
            existing_map,
            incoming_map,
            key=lambda item: item.get("name", ""),
            sort_key=lambda item: item.get("stars", 0),
            limit_per_group=limit_per_group,
        )

        await self.save_json(merged_map, filename_json)

        markdown_content = self._render_markdown(merged_map, today)
        await self.save_markdown(markdown_content, filename)

    def _serialize_repositories(
        self, repositories_by_language: list[tuple[str, list[Repository]]]
    ) -> dict[str, list[dict[str, Any]]]:
        serialized: dict[str, list[dict[str, Any]]] = {}
        for language, repositories in repositories_by_language:
            serialized[language] = [
                {
                    "name": repo.name,
                    "description": repo.description,
                    "link": repo.link,
                    "stars": repo.stars,
                }
                for repo in repositories
            ]
        return serialized

    async def _load_existing_repository_map(
        self, filename_json: str, filename_md: str
    ) -> dict[str, list[dict[str, Any]]]:
        existing_json = await self.load_json(filename_json)
        if existing_json:
            return existing_json

        markdown_content = await self.storage.load(filename_md)
        if not markdown_content:
            return {}

        return self._parse_markdown(markdown_content)

    def _render_markdown(
        self, repositories_by_language: dict[str, list[dict[str, Any]]], today: datetime
    ) -> str:
        content = f"# GitHub トレンドリポジトリ ({today.strftime('%Y-%m-%d')})\n\n"

        for language, repositories in repositories_by_language.items():
            if not repositories:
                continue

            language_display = language if language != "all" else "すべての言語"
            content += f"## {language_display.capitalize()}\n\n"

            for repo in repositories:
                content += f"### [{repo['name']}]({repo['link']})\n\n"

                description = repo.get("description")
                if description:
                    content += f"{description}\n\n"

                content += f"⭐ スター数: {repo.get('stars', 0)}\n\n"
                content += "---\n\n"

        return content

    def _parse_markdown(self, content: str) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
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
                "all"
                if language_header.lower().startswith("すべて")
                else language_header.lower()
            )

            repos: list[dict[str, Any]] = []
            for repo_match in repo_pattern.finditer(section_content):
                name = repo_match.group("name").strip()
                link = repo_match.group("link").strip()
                description = repo_match.group("description").strip()
                stars_text = repo_match.group("stars")
                stars = int(stars_text.replace(",", "")) if stars_text else 0

                repos.append(
                    {
                        "name": name,
                        "link": link,
                        "description": description,
                        "stars": stars,
                    }
                )

            result[language_key] = repos

        return result
