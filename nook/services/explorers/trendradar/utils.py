"""TrendRadar Explorer共通ユーティリティ.

このモジュールは、TrendRadar系ExplorerとAPIルーターで
共通して使用されるユーティリティ関数を提供します。
"""

import html
import math
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser


def create_empty_soup() -> BeautifulSoup:
    """空のBeautifulSoupオブジェクトを生成するファクトリ関数.

    Article.soup は base_feed_service.Article の必須フィールドだが
    TrendRadar系Explorerでは HTML コンテンツを使用しないため、プレースホルダーとして使用。
    BeautifulSoupはmutableなので、毎回新しいインスタンスを返すことで
    意図しない副作用を防止する。

    Returns
    -------
    BeautifulSoup
        空のBeautifulSoupインスタンス。
    """
    return BeautifulSoup("", "html.parser")


def parse_popularity_score(value: object) -> float:
    """人気スコアを安全にパース.

    Parameters
    ----------
    value : object
        パースする値。

    Returns
    -------
    float
        パースされた人気スコア。失敗時は0.0。
    """
    if value is None:
        return 0.0
    try:
        # 文字列の場合、カンマやプラス記号を正規化
        if isinstance(value, str):
            normalized = value.strip().replace(",", "")
            if normalized.startswith("+"):
                normalized = normalized[1:]
            result = float(normalized)
        else:
            result = float(value)
        # NaN/Infinity は 0.0 にフォールバック
        if not math.isfinite(result):
            return 0.0
        return result
    except (ValueError, TypeError):
        return 0.0


def sanitize_prompt_input(text: str, max_length: int = 500) -> str:
    """プロンプト入力用のサニタイズ処理.

    プロンプトインジェクション対策として、外部入力を安全に処理します。
    - 制御文字を除去（Cc: 制御文字, Cf: フォーマット制御文字）
    - 過度な改行を正規化
    - 長さを制限

    Parameters
    ----------
    text : str
        サニタイズするテキスト。
    max_length : int, default=500
        最大文字数。超過分は切り捨て。

    Returns
    -------
    str
        サニタイズ済みテキスト。
    """
    if not text:
        return ""
    # 制御文字を除去（改行・タブは保持）
    sanitized = "".join(
        char
        for char in text
        if char in ("\n", "\t") or unicodedata.category(char) not in ("Cc", "Cf")
    )
    # 連続する改行を1つに正規化
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
    # 長さ制限
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized.strip()


def escape_markdown_text(text: str) -> str:
    """Markdownテキスト用のエスケープ処理.

    HTMLエンティティとMarkdownリンク構文を壊す文字をエスケープします。

    Parameters
    ----------
    text : str
        エスケープするテキスト。

    Returns
    -------
    str
        エスケープ済みテキスト。
    """
    escaped = html.escape(text)
    return escaped.replace("[", "\\[").replace("]", "\\]")


def escape_markdown_url(url: str) -> str:
    """MarkdownリンクのURL用エスケープ処理.

    Markdownリンク構文 `[text](url)` を壊す文字をエスケープします。

    Parameters
    ----------
    url : str
        エスケープするURL。

    Returns
    -------
    str
        エスケープ済みURL。
    """
    return (
        url.replace("[", "\\[")
        .replace("]", "\\]")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def parse_published_at(item: dict[str, Any]) -> datetime:
    """記事の公開日時を解析.

    Parameters
    ----------
    item : dict[str, Any]
        TrendRadarアイテム。

    Returns
    -------
    datetime
        UTCタイムゾーン付きの解析された公開日時、または現在日時。
    """
    # 候補フィールド
    candidates = ["time", "published_at", "timestamp", "pub_date", "created_at"]

    for candidate_field in candidates:
        val = item.get(candidate_field)
        if val is None:
            continue

        # Epoch timestamp handling
        if isinstance(val, (int, float, str)) and not isinstance(val, bool):
            try:
                ts = float(str(val))
                # Reasonable timestamp check (e.g. > 1980) or exactly 0
                if ts > 315360000 or ts == 0:
                    # ms epoch の場合は秒に正規化（例: 1704067200000 -> 1704067200）
                    # 10^11 (1000億) 以上をミリ秒とみなす（2286年以降）
                    if ts > 100000000000:
                        ts = ts / 1000

                    try:
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        # 2100年を超えるような値は、不正なデータ（または巨大な秒数）とみなして
                        # 文字列パースへフォールバックさせる
                        if dt.year > 2100:
                            raise ValueError("Timestamp too far in future")
                        return dt
                    except (OverflowError, OSError, ValueError):
                        # 変換できない場合は文字列パースへフォールバック
                        pass
                else:
                    # 1970~1980年の間の小さな数値は、後の文字列パース（"2024"など）に任せる
                    pass
            except (ValueError, TypeError):
                # 数値に変換できない場合はスキップして文字列パースへ
                pass

        # String parsing
        try:
            dt = parser.parse(str(val))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            continue

    return datetime.now(timezone.utc)
