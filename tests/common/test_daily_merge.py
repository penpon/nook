"""nook/common/daily_merge.py のテスト"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.daily_merge import merge_grouped_records, merge_records

# ================================================================================
# 1. merge_records の基本動作テスト
# ================================================================================


@pytest.mark.unit
def test_merge_records_incoming_only():
    """
    Given: existing=[], incoming=[1,2,3]
    When: merge_recordsを呼び出す
    Then: [1,2,3]が返る
    """
    result = merge_records([], [1, 2, 3], key=lambda x: x)
    assert result == [1, 2, 3]


@pytest.mark.unit
def test_merge_records_existing_only():
    """
    Given: existing=[1,2,3], incoming=[]
    When: merge_recordsを呼び出す
    Then: [1,2,3]が返る
    """
    result = merge_records([1, 2, 3], [], key=lambda x: x)
    assert result == [1, 2, 3]


@pytest.mark.unit
def test_merge_records_no_duplicates():
    """
    Given: 異なるキーのデータ
    When: merge_recordsを呼び出す
    Then: 全データが含まれる
    """
    existing = [{"id": 1}, {"id": 2}]
    incoming = [{"id": 3}, {"id": 4}]

    result = merge_records(existing, incoming, key=lambda x: x["id"])

    assert len(result) == 4
    assert {"id": 1} in result
    assert {"id": 4} in result


@pytest.mark.unit
def test_merge_records_with_duplicates():
    """
    Given: 同一キーあり
    When: merge_recordsを呼び出す
    Then: 新規データで上書きされる
    """
    existing = [{"id": 1, "value": "old"}]
    incoming = [{"id": 1, "value": "new"}]

    result = merge_records(existing, incoming, key=lambda x: x["id"])

    assert len(result) == 1
    assert result[0]["value"] == "new"


@pytest.mark.unit
def test_merge_records_empty_both():
    """
    Given: existing=[], incoming=[]
    When: merge_recordsを呼び出す
    Then: []が返る
    """
    result = merge_records([], [], key=lambda x: x)
    assert result == []


# ================================================================================
# 2. merge_records のソート機能テスト
# ================================================================================


@pytest.mark.unit
def test_merge_records_no_sort_key():
    """
    Given: sort_key=None
    When: merge_recordsを呼び出す
    Then: 挿入順（既存→新規）で返る
    """
    existing = [{"id": 2}, {"id": 1}]
    incoming = [{"id": 4}, {"id": 3}]

    result = merge_records(existing, incoming, key=lambda x: x["id"], sort_key=None)

    # 挿入順: 2, 1, 4, 3
    assert [r["id"] for r in result] == [2, 1, 4, 3]


@pytest.mark.unit
def test_merge_records_with_sort_key_descending():
    """
    Given: sort_key指定、reverse=True
    When: merge_recordsを呼び出す
    Then: 降順でソートされる
    """
    existing = [{"id": 2, "score": 20}, {"id": 1, "score": 10}]
    incoming = [{"id": 3, "score": 30}]

    result = merge_records(existing, incoming, key=lambda x: x["id"], sort_key=lambda x: x["score"])

    # score降順: 30, 20, 10
    assert [r["score"] for r in result] == [30, 20, 10]


@pytest.mark.unit
def test_merge_records_with_sort_key_ascending():
    """
    Given: sort_key指定、reverse=False
    When: merge_recordsを呼び出す
    Then: 昇順でソートされる
    """
    existing = [{"id": 2, "score": 20}, {"id": 1, "score": 10}]
    incoming = [{"id": 3, "score": 30}]

    result = merge_records(
        existing,
        incoming,
        key=lambda x: x["id"],
        sort_key=lambda x: x["score"],
        reverse=False,
    )

    # score昇順: 10, 20, 30
    assert [r["score"] for r in result] == [10, 20, 30]


# ================================================================================
# 3. merge_records の制限機能テスト
# ================================================================================


@pytest.mark.unit
def test_merge_records_no_limit():
    """
    Given: limit=None
    When: merge_recordsを呼び出す
    Then: 全データが返る
    """
    existing = list(range(10))
    incoming = list(range(10, 20))

    result = merge_records(existing, incoming, key=lambda x: x, limit=None)

    assert len(result) == 20


@pytest.mark.unit
def test_merge_records_with_limit():
    """
    Given: limit=10
    When: merge_recordsを呼び出す
    Then: 最大10件が返る
    """
    existing = list(range(10))
    incoming = list(range(10, 20))

    result = merge_records(existing, incoming, key=lambda x: x, limit=10)

    assert len(result) == 10


@pytest.mark.unit
def test_merge_records_limit_larger_than_data():
    """
    Given: limit > データ数
    When: merge_recordsを呼び出す
    Then: 全データが返る
    """
    existing = [1, 2, 3]
    incoming = [4, 5]

    result = merge_records(existing, incoming, key=lambda x: x, limit=100)

    assert len(result) == 5


@pytest.mark.unit
def test_merge_records_limit_zero():
    """
    Given: limit=0
    When: merge_recordsを呼び出す
    Then: []が返る
    """
    existing = [1, 2, 3]
    incoming = [4, 5]

    result = merge_records(existing, incoming, key=lambda x: x, limit=0)

    assert result == []


@pytest.mark.unit
def test_merge_records_limit_one():
    """
    Given: limit=1
    When: merge_recordsを呼び出す
    Then: 1件のみ返る
    """
    existing = [{"id": 1, "score": 10}]
    incoming = [{"id": 2, "score": 20}]

    result = merge_records(
        existing,
        incoming,
        key=lambda x: x["id"],
        sort_key=lambda x: x["score"],
        limit=1,
    )

    assert len(result) == 1
    assert result[0]["score"] == 20  # score降順で最大値


@pytest.mark.unit
def test_merge_records_exact_limit():
    """
    Given: データ数=limit
    When: merge_recordsを呼び出す
    Then: limit件が返る
    """
    existing = [1, 2, 3]
    incoming = [4, 5]

    result = merge_records(existing, incoming, key=lambda x: x, limit=5)

    assert len(result) == 5


@pytest.mark.unit
def test_merge_records_limit_plus_one():
    """
    Given: データ数=limit+1
    When: merge_recordsを呼び出す
    Then: limit件が返る（1件切り捨て）
    """
    existing = [1, 2, 3]
    incoming = [4, 5, 6]

    result = merge_records(existing, incoming, key=lambda x: x, limit=5)

    assert len(result) == 5


# ================================================================================
# 4. merge_records の重複処理テスト
# ================================================================================


@pytest.mark.unit
def test_merge_records_all_duplicates():
    """
    Given: existing=incoming（全て重複）
    When: merge_recordsを呼び出す
    Then: incomingのデータが残る
    """
    existing = [{"id": 1, "value": "old"}, {"id": 2, "value": "old"}]
    incoming = [{"id": 1, "value": "new"}, {"id": 2, "value": "new"}]

    result = merge_records(existing, incoming, key=lambda x: x["id"])

    assert len(result) == 2
    assert all(r["value"] == "new" for r in result)


@pytest.mark.unit
def test_merge_records_partial_duplicates():
    """
    Given: 一部同一キー
    When: merge_recordsを呼び出す
    Then: 新規で上書き、他は追加
    """
    existing = [{"id": 1, "value": "old"}, {"id": 2, "value": "old"}]
    incoming = [{"id": 2, "value": "new"}, {"id": 3, "value": "new"}]

    result = merge_records(existing, incoming, key=lambda x: x["id"])

    assert len(result) == 3
    # id=1は既存のまま、id=2は上書き、id=3は追加
    assert next(r for r in result if r["id"] == 1)["value"] == "old"
    assert next(r for r in result if r["id"] == 2)["value"] == "new"
    assert next(r for r in result if r["id"] == 3)["value"] == "new"


@pytest.mark.unit
def test_merge_records_duplicates_in_existing():
    """
    Given: existing内に重複キー
    When: merge_recordsを呼び出す
    Then: 最後のものが保持される
    """
    existing = [
        {"id": 1, "value": "first"},
        {"id": 1, "value": "second"},
        {"id": 1, "value": "third"},
    ]
    incoming = []

    result = merge_records(existing, incoming, key=lambda x: x["id"])

    assert len(result) == 1
    assert result[0]["value"] == "third"


# ================================================================================
# 5. merge_records のデータ型テスト
# ================================================================================


@pytest.mark.unit
def test_merge_records_dict_type():
    """
    Given: dict型の要素
    When: merge_recordsを呼び出す
    Then: 正常動作
    """
    existing = [{"id": 1}]
    incoming = [{"id": 2}]

    result = merge_records(existing, incoming, key=lambda x: x["id"])

    assert len(result) == 2


@pytest.mark.unit
def test_merge_records_string_type():
    """
    Given: 文字列リスト
    When: merge_recordsを呼び出す
    Then: 正常動作
    """
    existing = ["a", "b"]
    incoming = ["c", "d"]

    result = merge_records(existing, incoming, key=lambda x: x)

    assert result == ["a", "b", "c", "d"]


@pytest.mark.unit
def test_merge_records_complex_key():
    """
    Given: 複雑なkey関数（タプル返す）
    When: merge_recordsを呼び出す
    Then: 正常動作
    """
    existing = [{"name": "Alice", "age": 30}]
    incoming = [{"name": "Bob", "age": 25}]

    result = merge_records(existing, incoming, key=lambda x: (x["name"], x["age"]))

    assert len(result) == 2


# ================================================================================
# 6. merge_grouped_records の基本動作テスト
# ================================================================================


@pytest.mark.unit
def test_merge_grouped_records_incoming_only():
    """
    Given: existing=None, incoming={"group1": [1,2,3]}
    When: merge_grouped_recordsを呼び出す
    Then: incomingが返る
    """
    incoming = {"group1": [{"id": 1}, {"id": 2}]}

    result = merge_grouped_records(None, incoming, key=lambda x: x["id"])

    assert "group1" in result
    assert len(result["group1"]) == 2


@pytest.mark.unit
def test_merge_grouped_records_existing_empty():
    """
    Given: existing={}, incoming={"group1": [1,2,3]}
    When: merge_grouped_recordsを呼び出す
    Then: incomingが返る
    """
    existing = {}
    incoming = {"group1": [{"id": 1}, {"id": 2}]}

    result = merge_grouped_records(existing, incoming, key=lambda x: x["id"])

    assert "group1" in result
    assert len(result["group1"]) == 2


@pytest.mark.unit
def test_merge_grouped_records_no_overlap():
    """
    Given: 異なるグループ
    When: merge_grouped_recordsを呼び出す
    Then: 全グループが含まれる
    """
    existing = {"group1": [{"id": 1}]}
    incoming = {"group2": [{"id": 2}]}

    result = merge_grouped_records(existing, incoming, key=lambda x: x["id"])

    assert "group1" in result
    assert "group2" in result


@pytest.mark.unit
def test_merge_grouped_records_same_group():
    """
    Given: 同一グループキー
    When: merge_grouped_recordsを呼び出す
    Then: merge_recordsでマージされる
    """
    existing = {"group1": [{"id": 1, "value": "old"}]}
    incoming = {"group1": [{"id": 1, "value": "new"}, {"id": 2, "value": "new"}]}

    result = merge_grouped_records(existing, incoming, key=lambda x: x["id"])

    assert len(result["group1"]) == 2
    assert next(r for r in result["group1"] if r["id"] == 1)["value"] == "new"


@pytest.mark.unit
def test_merge_grouped_records_existing_group_preserved():
    """
    Given: incomingにないグループ
    When: merge_grouped_recordsを呼び出す
    Then: existingのまま保持される
    """
    existing = {"group1": [{"id": 1}], "group2": [{"id": 2}]}
    incoming = {"group1": [{"id": 3}]}

    result = merge_grouped_records(existing, incoming, key=lambda x: x["id"])

    assert "group1" in result
    assert "group2" in result
    # group2はそのまま
    assert result["group2"] == [{"id": 2}]


# ================================================================================
# 7. merge_grouped_records のパラメータ伝播テスト
# ================================================================================


@pytest.mark.unit
def test_merge_grouped_records_with_sort_key():
    """
    Given: sort_key指定
    When: merge_grouped_recordsを呼び出す
    Then: 各グループでソートされる
    """
    existing = {"group1": [{"id": 1, "score": 10}]}
    incoming = {"group1": [{"id": 2, "score": 20}]}

    result = merge_grouped_records(
        existing, incoming, key=lambda x: x["id"], sort_key=lambda x: x["score"]
    )

    # score降順
    assert result["group1"][0]["score"] == 20


@pytest.mark.unit
def test_merge_grouped_records_with_limit_per_group():
    """
    Given: limit_per_group=1
    When: merge_grouped_recordsを呼び出す
    Then: 各グループで1件に制限される
    """
    existing = {"group1": [{"id": 1, "score": 10}]}
    incoming = {"group1": [{"id": 2, "score": 20}, {"id": 3, "score": 30}]}

    result = merge_grouped_records(
        existing,
        incoming,
        key=lambda x: x["id"],
        sort_key=lambda x: x["score"],
        limit_per_group=1,
    )

    assert len(result["group1"]) == 1
    assert result["group1"][0]["score"] == 30  # 最高スコア


@pytest.mark.unit
def test_merge_grouped_records_with_reverse_false():
    """
    Given: reverse=False
    When: merge_grouped_recordsを呼び出す
    Then: 各グループで昇順
    """
    existing = {}
    incoming = {"group1": [{"id": 2, "score": 20}, {"id": 1, "score": 10}]}

    result = merge_grouped_records(
        existing,
        incoming,
        key=lambda x: x["id"],
        sort_key=lambda x: x["score"],
        reverse=False,
    )

    # score昇順
    assert result["group1"][0]["score"] == 10


# ================================================================================
# 8. merge_grouped_records の複雑なケーステスト
# ================================================================================


@pytest.mark.unit
def test_merge_grouped_records_multiple_groups():
    """
    Given: existing: A,B / incoming: B,C
    When: merge_grouped_recordsを呼び出す
    Then: A,B,C全て含む
    """
    existing = {"A": [{"id": 1}], "B": [{"id": 2}]}
    incoming = {"B": [{"id": 3}], "C": [{"id": 4}]}

    result = merge_grouped_records(existing, incoming, key=lambda x: x["id"])

    assert set(result.keys()) == {"A", "B", "C"}
    assert len(result["A"]) == 1  # 既存のまま
    assert len(result["B"]) == 2  # マージされた
    assert len(result["C"]) == 1  # 新規追加


@pytest.mark.unit
def test_merge_grouped_records_empty_group():
    """
    Given: incoming={"group": []}（空グループ）
    When: merge_grouped_recordsを呼び出す
    Then: 空リストが保持される
    """
    existing = {}
    incoming = {"group": []}

    result = merge_grouped_records(existing, incoming, key=lambda x: x)

    assert result["group"] == []


@pytest.mark.unit
def test_merge_grouped_records_limit_per_group_zero():
    """
    Given: limit_per_group=0
    When: merge_grouped_recordsを呼び出す
    Then: 各グループが0件
    """
    existing = {}
    incoming = {"group1": [{"id": 1}, {"id": 2}]}

    result = merge_grouped_records(existing, incoming, key=lambda x: x["id"], limit_per_group=0)

    assert result["group1"] == []


@pytest.mark.unit
def test_merge_grouped_records_ten_groups():
    """
    Given: 10グループ
    When: merge_grouped_recordsを呼び出す
    Then: 全て処理される
    """
    existing = {f"group{i}": [{"id": i}] for i in range(5)}
    incoming = {f"group{i}": [{"id": i + 10}] for i in range(5, 10)}

    result = merge_grouped_records(existing, incoming, key=lambda x: x["id"])

    assert len(result) == 10
