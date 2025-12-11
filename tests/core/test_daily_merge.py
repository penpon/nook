from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.core.storage.daily_merge import (  # noqa: E402
    merge_grouped_records,
    merge_records,
)


def test_merge_records_overwrites_existing_and_sorts_by_score():
    # Given: existing sorted records and incoming updates
    existing = [
        {"id": "keep", "score": 5},
        {"id": "replace", "score": 1},
    ]
    # And: incoming records that update and add IDs
    incoming = [
        {"id": "replace", "score": 10},
        {"id": "new", "score": 7},
    ]

    # When: merged with custom key and sort order
    result = merge_records(
        existing,
        incoming,
        key=lambda item: item["id"],
        sort_key=lambda item: item["score"],
        reverse=True,
    )

    # Then: updated result keeps highest scores and order
    assert [item["id"] for item in result] == ["replace", "new", "keep"]
    assert next(item for item in result if item["id"] == "replace")["score"] == 10


def test_merge_records_respects_limit():
    # Given: existing and incoming batches exceeding limit
    existing = [{"id": idx, "score": idx} for idx in range(3)]
    incoming = [{"id": idx + 3, "score": idx + 3} for idx in range(3)]

    # When: merge is executed with limit
    limited = merge_records(
        existing,
        incoming,
        key=lambda item: item["id"],
        sort_key=lambda item: item["score"],
        limit=4,
    )

    # Then: resulting records are capped appropriately
    assert len(limited) == 4
    assert {item["id"] for item in limited} <= {0, 1, 2, 3, 4, 5}


def test_merge_grouped_records_merges_and_preserves_missing_groups():
    # Given: grouped existing and incoming records
    existing = {
        "tech": [{"id": "old", "score": 1}],
        "ai": [{"id": "stay", "score": 9}],
    }
    incoming = {
        "tech": [
            {"id": "old", "score": 5},
            {"id": "new", "score": 2},
        ],
        "science": [{"id": "fresh", "score": 8}],
    }

    # When: grouped merge runs with limits
    merged = merge_grouped_records(
        existing,
        incoming,
        key=lambda item: item["id"],
        sort_key=lambda item: item["score"],
        limit_per_group=2,
    )

    # Then: groups preserve new and existing order
    assert [item["id"] for item in merged["tech"]] == ["old", "new"]
    assert merged["science"][0]["id"] == "fresh"
    assert merged["ai"][0]["id"] == "stay"


def test_merge_records_raises_when_key_missing():
    # Given: merge inputs lacking required key
    # When & Then: accessing missing key raises KeyError
    with pytest.raises(KeyError):
        merge_records([{}], [{}], key=lambda item: item["missing"])
