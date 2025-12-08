"""日次スナップショットのマージヘルパー。"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable, Hashable, Iterable, Sequence, TypeVar

T = TypeVar("T")


def merge_records(
    existing: Iterable[T],
    incoming: Iterable[T],
    *,
    key: Callable[[T], Hashable],
    sort_key: Callable[[T], Any] | None = None,
    limit: int | None = None,
    reverse: bool = True,
) -> list[T]:
    """既存データと新規データをマージして返す。

    Parameters
    ----------
    existing : Iterable[T]
        既存レコードの反復可能オブジェクト。
    incoming : Iterable[T]
        新規レコードの反復可能オブジェクト。重複キーは新規で上書きされる。
    key : Callable[[T], Hashable]
        レコードを一意に識別するためのキー関数。
    sort_key : Callable[[T], Any] | None, default=None
        ソートキー。None の場合は挿入順を維持する（既存アイテムが先、新規アイテムが後。重複キーは新規で上書き）。
    limit : int | None, default=None
        返す最大件数。None の場合は制限なし。
    reverse : bool, default=True
        ソート時に降順で並べるかどうか。

    Returns
    -------
    list[T]
        マージ後のレコードリスト。
    """

    ordered: "OrderedDict[Hashable, T]" = OrderedDict()

    # 既存順を先に登録
    for item in existing:
        ordered[key(item)] = item

    # 新規で上書き
    for item in incoming:
        ordered[key(item)] = item

    records = list(ordered.values())

    if sort_key is not None:
        records.sort(key=sort_key, reverse=reverse)

    if limit is not None:
        return records[:limit]

    return records


def merge_grouped_records(
    existing: dict[str, Sequence[T]] | None,
    incoming: dict[str, Sequence[T]],
    *,
    key: Callable[[T], Hashable],
    sort_key: Callable[[T], Any] | None = None,
    limit_per_group: int | None = None,
    reverse: bool = True,
) -> dict[str, list[T]]:
    """カテゴリ/グループごとのレコードをマージする。"""

    merged: dict[str, list[T]] = {}

    existing = existing or {}

    for group, new_items in incoming.items():
        current = existing.get(group, [])
        merged[group] = merge_records(
            current,
            new_items,
            key=key,
            sort_key=sort_key,
            limit=limit_per_group,
            reverse=reverse,
        )

    # 既存で今回登場しなかったグループはそのまま引き継ぐ
    for group, current in existing.items():
        if group not in merged:
            merged[group] = list(current)

    return merged
