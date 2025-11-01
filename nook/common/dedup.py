"""タイトル重複排除のための共通ユーティリティ。"""

import re
import unicodedata


class TitleNormalizer:
    """
    記事タイトルを正規化して重複判定を行うクラス。

    同一サービス内で異なるカテゴリに属していても、
    タイトルが実質的に同じであれば重複と判定します。

    正規化手順:
    1. Unicode正規化（NFKC）で全角/半角を統一
    2. casefold()で大文字小文字を無視
    3. 余分な空白を圧縮・トリム
    4. 軽度の装飾記号を除去（【】、[]、()など）
    """

    # 除去する装飾パターン（先頭・末尾の括弧系）
    DECORATION_PATTERNS = [
        r"^【[^】]*】",  # 先頭の【】
        r"^「[^」]*」",  # 先頭の「」
        r"^『[^』]*』",  # 先頭の『』
        r"【[^】]*】$",  # 末尾の【】
        r"「[^」]*」$",  # 末尾の「」
        r"『[^』]*』$",  # 末尾の『』
    ]

    @staticmethod
    def normalize(title: str) -> str:
        """
        タイトルを正規化します。

        Parameters
        ----------
        title : str
            正規化するタイトル。

        Returns
        -------
        str
            正規化されたタイトル。
        """
        if not title:
            return ""

        # 1. Unicode正規化（NFKC: 全角/半角の統一）
        normalized = unicodedata.normalize("NFKC", title)

        # 2. 大文字小文字の無視（多言語対応）
        normalized = normalized.casefold()

        # 3. 余分な空白の圧縮とトリム
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # 4. 軽度の装飾除去（先頭・末尾の括弧系）
        for pattern in TitleNormalizer.DECORATION_PATTERNS:
            normalized = re.sub(pattern, "", normalized).strip()

        # 5. 記号の正規化（連続する記号を1つに）
        normalized = re.sub(r"[!！]{2,}", "!", normalized)
        normalized = re.sub(r"[?？]{2,}", "?", normalized)
        normalized = re.sub(r"[~～]{2,}", "~", normalized)

        return normalized

    @staticmethod
    def are_duplicates(title1: str, title2: str) -> bool:
        """
        2つのタイトルが重複しているか判定します。

        Parameters
        ----------
        title1 : str
            1つ目のタイトル。
        title2 : str
            2つ目のタイトル。

        Returns
        -------
        bool
            重複している場合はTrue、そうでなければFalse。
        """
        return TitleNormalizer.normalize(title1) == TitleNormalizer.normalize(title2)


class DedupTracker:
    """
    記事の重複追跡を行うクラス。

    サービス内のカテゴリ横断で、正規化タイトルによる重複を追跡します。
    """

    def __init__(self):
        """DedupTrackerを初期化します。"""
        self.seen_normalized_titles = set()
        self.title_mapping = {}  # 正規化タイトル -> 元のタイトル（ログ用）

    def is_duplicate(self, title: str) -> tuple[bool, str]:
        """
        タイトルが重複しているか確認します。

        Parameters
        ----------
        title : str
            確認するタイトル。

        Returns
        -------
        tuple[bool, str]
            (重複しているか, 正規化されたタイトル)
        """
        normalized = TitleNormalizer.normalize(title)
        is_dup = normalized in self.seen_normalized_titles
        return is_dup, normalized

    def add(self, title: str) -> str:
        """
        タイトルを追跡対象に追加します。

        Parameters
        ----------
        title : str
            追加するタイトル。

        Returns
        -------
        str
            正規化されたタイトル。
        """
        normalized = TitleNormalizer.normalize(title)
        self.seen_normalized_titles.add(normalized)
        if normalized not in self.title_mapping:
            self.title_mapping[normalized] = title
        return normalized

    def get_original_title(self, normalized_title: str) -> str | None:
        """
        正規化タイトルから元のタイトルを取得します（ログ用）。

        Parameters
        ----------
        normalized_title : str
            正規化されたタイトル。

        Returns
        -------
        str or None
            元のタイトル。見つからない場合はNone。
        """
        return self.title_mapping.get(normalized_title)

    def count(self) -> int:
        """
        追跡中の重複排除済みタイトル数を返します。

        Returns
        -------
        int
            追跡中のタイトル数。
        """
        return len(self.seen_normalized_titles)


async def load_existing_titles_from_storage(
    storage,
    target_dates: set,
    logger=None,
) -> DedupTracker:
    """
    指定期間の既存ファイルから記事タイトルをロードして重複チェッカーを返す。

    既存のJSON/Markdownファイルから記事タイトルを読み込み、
    DedupTrackerオブジェクトを初期化します。これにより、
    既に要約済みの記事を再度処理することを防ぎます。

    Parameters
    ----------
    storage : LocalStorage
        データ保存用のLocalStorageインスタンス。
    target_dates : set[date]
        チェック対象の日付のセット。
    logger : logging.Logger, optional
        ログ出力用のロガー（デバッグ用）。

    Returns
    -------
    DedupTracker
        既存タイトルが登録されたDedupTrackerインスタンス。

    Examples
    --------
    >>> from datetime import date
    >>> target_dates = {date(2025, 11, 1), date(2025, 11, 2)}
    >>> tracker = await load_existing_titles_from_storage(storage, target_dates)
    >>> is_dup, _ = tracker.is_duplicate("既存記事のタイトル")
    >>> print(is_dup)
    True
    """
    import json
    from datetime import time, datetime

    tracker = DedupTracker()

    for target_date in sorted(target_dates):
        date_str = target_date.strftime("%Y-%m-%d")

        # JSONファイルから既存記事を読み込み
        try:
            json_content = await storage.load(f"{date_str}.json")
            if json_content:
                articles = json.loads(json_content)
                for article in articles:
                    title = article.get("title", "")
                    if title:
                        tracker.add(title)
                if logger:
                    logger.debug(
                        f"📂 既存記事読み込み: {date_str}.json ({len(articles)}件)"
                    )
        except FileNotFoundError:
            # ファイルが存在しない場合はスキップ
            if logger:
                logger.debug(f"📂 ファイル未検出: {date_str}.json")
        except json.JSONDecodeError as e:
            if logger:
                logger.warning(f"⚠️ JSON解析エラー: {date_str}.json - {e}")
        except Exception as e:
            if logger:
                logger.debug(f"⚠️ ファイル読み込みエラー: {date_str}.json - {e}")

        # Markdownファイルからも読み込み（フォールバック）
        try:
            markdown_content = storage.load_markdown(
                "", datetime.combine(target_date, time.min)
            )
            if markdown_content:
                # Markdownから記事タイトルを抽出（### [タイトル](URL) 形式）
                import re

                for match in re.finditer(
                    r"^### \[(.+?)\]", markdown_content, re.MULTILINE
                ):
                    title = match.group(1)
                    tracker.add(title)
                if logger:
                    logger.debug(f"📂 既存記事読み込み: {date_str}.md")
        except Exception as e:
            if logger:
                logger.debug(f"⚠️ Markdown読み込みエラー: {date_str}.md - {e}")

    return tracker
