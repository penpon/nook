"""ローカルファイルシステムでのデータ操作ユーティリティ。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles


class LocalStorage:
    """
    ローカルファイルシステムでのデータ操作を担当するクラス。

    Parameters
    ----------
    base_dir : str
        ベースディレクトリのパス。
    """

    def __init__(self, base_dir: str):
        """
        LocalStorageを初期化します。

        Parameters
        ----------
        base_dir : str
            ベースディレクトリのパス。
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_markdown(
        self, content: str, service_name: str, date: datetime | None = None
    ) -> Path:
        """
        Markdownコンテンツを保存します。

        Parameters
        ----------
        content : str
            保存するMarkdownコンテンツ。
        service_name : str
            サービス名（ディレクトリ名）。
        date : datetime, optional
            日付。指定しない場合は現在の日付。

        Returns
        -------
        Path
            保存されたファイルのパス。
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        service_dir = self.base_dir / service_name
        service_dir.mkdir(parents=True, exist_ok=True)

        file_path = service_dir / f"{date_str}.md"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    def load_markdown(
        self, service_name: str, date: datetime | None = None
    ) -> str | None:
        """
        Markdownコンテンツを読み込みます。

        Parameters
        ----------
        service_name : str
            サービス名（ディレクトリ名）。
        date : datetime, optional
            日付。指定しない場合は現在の日付。

        Returns
        -------
        str or None
            読み込まれたMarkdownコンテンツ。ファイルが存在しない場合はNone。
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        file_path = self.base_dir / service_name / f"{date_str}.md"

        if not file_path.exists():
            return None

        with open(file_path, encoding="utf-8") as f:
            return f.read()

    def list_dates(self, service_name: str) -> list[datetime]:
        """
        利用可能な日付の一覧を取得します。

        Parameters
        ----------
        service_name : str
            サービス名（ディレクトリ名）。

        Returns
        -------
        List[datetime]
            利用可能な日付のリスト。
        """
        service_dir = self.base_dir / service_name

        if not service_dir.exists():
            return []

        dates = []
        for file_path in service_dir.glob("*.md"):
            try:
                date_str = file_path.stem
                date = datetime.strptime(date_str, "%Y-%m-%d")
                dates.append(date)
            except ValueError:
                continue

        return sorted(dates, reverse=True)

    async def save(self, data: Any, filename: str) -> Path:
        """
        データを非同期で保存します。

        Parameters
        ----------
        data : Any
            保存するデータ（JSONシリアライズ可能）。
        filename : str
            保存するファイル名。

        Returns
        -------
        Path
            保存されたファイルのパス。
        """
        file_path = self.base_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # JSONファイルの場合
        if filename.endswith(".json"):
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        # テキストファイルの場合
        else:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(str(data))

        return file_path

    async def load(self, filename: str) -> str | None:
        """ファイルの内容を非同期で読み込み"""
        file_path = self.base_dir / filename
        if not file_path.exists():
            return None

        async with aiofiles.open(file_path, encoding="utf-8") as f:
            return await f.read()

    async def exists(self, filename: str) -> bool:
        """ファイルの存在を確認"""
        file_path = self.base_dir / filename
        return file_path.exists()

    async def rename(self, old_filename: str, new_filename: str) -> None:
        """ファイル名を変更"""
        old_path = self.base_dir / old_filename
        new_path = self.base_dir / new_filename
        if old_path.exists():
            old_path.rename(new_path)

    def load_json(
        self, service_name: str, date: datetime | None = None
    ) -> list[Any] | None:
        """
        JSONコンテンツを読み込みます。

        Parameters
        ----------
        service_name : str
            サービス名（ディレクトリ名）。
        date : datetime, optional
            日付。指定しない場合は現在の日付。

        Returns
        -------
        List[Any] or None
            読み込まれたJSONコンテンツ。ファイルが存在しない場合はNone。
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        file_path = self.base_dir / service_name / f"{date_str}.json"

        if not file_path.exists():
            return None

        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
