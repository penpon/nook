"""
nook/common/storage.py のテスト

テスト観点:
- LocalStorageの初期化
- Markdownデータの保存・読み込み
- 日付一覧の取得
- 非同期データ保存・読み込み
- ファイル存在確認・リネーム
- JSONデータの読み込み
- エラーハンドリング
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.storage import LocalStorage


# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_creates_new_directory(tmp_path):
    """
    Given: 存在しないディレクトリパス
    When: LocalStorageを初期化
    Then: ディレクトリが作成され、base_dirが設定される
    """
    new_dir = tmp_path / "new_storage"
    storage = LocalStorage(base_dir=str(new_dir))

    assert storage.base_dir == new_dir
    assert new_dir.exists()
    assert new_dir.is_dir()


@pytest.mark.unit
def test_init_uses_existing_directory(tmp_path):
    """
    Given: 既存のディレクトリパス
    When: LocalStorageを初期化
    Then: エラーなくインスタンス作成、既存ディレクトリはそのまま
    """
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()

    storage = LocalStorage(base_dir=str(existing_dir))

    assert storage.base_dir == existing_dir
    assert existing_dir.exists()


@pytest.mark.unit
def test_init_creates_nested_directories(tmp_path):
    """
    Given: ネストしたディレクトリパス
    When: LocalStorageを初期化
    Then: parents=Trueで全階層作成される
    """
    nested_dir = tmp_path / "parent" / "child" / "grandchild"
    storage = LocalStorage(base_dir=str(nested_dir))

    assert storage.base_dir == nested_dir
    assert nested_dir.exists()
    assert (tmp_path / "parent" / "child").exists()


@pytest.mark.unit
def test_init_with_relative_path(tmp_path, monkeypatch):
    """
    Given: 相対パス
    When: LocalStorageを初期化
    Then: 相対パスからPathオブジェクトが作成される
    """
    monkeypatch.chdir(tmp_path)
    relative_path = "./test_data"
    storage = LocalStorage(base_dir=relative_path)

    assert storage.base_dir == Path(relative_path)
    assert Path(relative_path).exists()


@pytest.mark.unit
def test_init_permission_error():
    """
    Given: 書き込み権限のないパス
    When: LocalStorageを初期化
    Then: OSError/PermissionError発生
    """
    with patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")):
        with pytest.raises(PermissionError):
            LocalStorage(base_dir="/root/restricted")


# =============================================================================
# 2. save_markdown メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_save_markdown_without_date(tmp_path):
    """
    Given: content, service_name, date=None
    When: save_markdownを呼び出す
    Then: 現在日付でファイル保存、Pathが返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    content = "# Test Markdown"
    service_name = "test_service"

    result_path = storage.save_markdown(content, service_name)

    today_str = datetime.now().strftime("%Y-%m-%d")
    expected_path = tmp_path / service_name / f"{today_str}.md"

    assert result_path == expected_path
    assert result_path.exists()
    assert result_path.read_text(encoding="utf-8") == content


@pytest.mark.unit
def test_save_markdown_with_date(tmp_path):
    """
    Given: content, service_name, 指定日付
    When: save_markdownを呼び出す
    Then: 指定日付でファイル保存
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    content = "# Test"
    service_name = "test"
    test_date = datetime(2024, 1, 15, 10, 30)

    result_path = storage.save_markdown(content, service_name, date=test_date)

    expected_path = tmp_path / service_name / "2024-01-15.md"
    assert result_path == expected_path
    assert result_path.exists()
    assert result_path.read_text(encoding="utf-8") == content


@pytest.mark.unit
def test_save_markdown_empty_content(tmp_path):
    """
    Given: 空文字列のcontent
    When: save_markdownを呼び出す
    Then: 空ファイルが作成される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    content = ""
    service_name = "test"

    result_path = storage.save_markdown(content, service_name)

    assert result_path.exists()
    assert result_path.read_text(encoding="utf-8") == ""


@pytest.mark.unit
def test_save_markdown_large_content(tmp_path):
    """
    Given: 10MB以上のcontent
    When: save_markdownを呼び出す
    Then: 正常に保存される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    # 10MBのテキストデータ
    content = "a" * (10 * 1024 * 1024)
    service_name = "test"

    result_path = storage.save_markdown(content, service_name)

    assert result_path.exists()
    assert len(result_path.read_text(encoding="utf-8")) == len(content)


@pytest.mark.unit
def test_save_markdown_unicode_content(tmp_path):
    """
    Given: Unicode文字を含むcontent
    When: save_markdownを呼び出す
    Then: UTF-8で正しく保存される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    content = "# 日本語タイトル\n\n絵文字もOK 😀🎉"
    service_name = "test"

    result_path = storage.save_markdown(content, service_name)

    assert result_path.exists()
    saved_content = result_path.read_text(encoding="utf-8")
    assert saved_content == content


@pytest.mark.unit
def test_save_markdown_special_chars_service_name(tmp_path):
    """
    Given: 特殊文字を含むservice_name
    When: save_markdownを呼び出す
    Then: ディレクトリ作成・保存成功
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    content = "# Test"
    service_name = "test-service_2024"

    result_path = storage.save_markdown(content, service_name)

    assert result_path.exists()
    assert result_path.parent.name == service_name


@pytest.mark.unit
def test_save_markdown_overwrite(tmp_path):
    """
    Given: 同じdate/service_nameで2回保存
    When: save_markdownを呼び出す
    Then: 上書き成功、新しいcontentが保存される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    test_date = datetime(2024, 1, 1)

    # 1回目の保存
    storage.save_markdown("Old content", service_name, date=test_date)

    # 2回目の保存（上書き）
    new_content = "New content"
    result_path = storage.save_markdown(new_content, service_name, date=test_date)

    assert result_path.read_text(encoding="utf-8") == new_content


@pytest.mark.unit
def test_save_markdown_permission_error(tmp_path):
    """
    Given: ファイル書き込み権限エラー
    When: save_markdownを呼び出す
    Then: PermissionError伝播
    """
    storage = LocalStorage(base_dir=str(tmp_path))

    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        with pytest.raises(PermissionError):
            storage.save_markdown("Test", "test")


@pytest.mark.unit
def test_save_markdown_disk_full_error(tmp_path):
    """
    Given: ディスク容量不足
    When: save_markdownを呼び出す
    Then: OSError伝播
    """
    storage = LocalStorage(base_dir=str(tmp_path))

    with patch("builtins.open", side_effect=OSError("No space left on device")):
        with pytest.raises(OSError):
            storage.save_markdown("Test", "test")


# =============================================================================
# 3. load_markdown メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_load_markdown_existing_file_without_date(tmp_path):
    """
    Given: 現在日付のファイルが存在
    When: load_markdownを呼び出す（date=None）
    Then: ファイル内容が文字列で返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    content = "# Existing content"

    # 事前にファイル保存
    storage.save_markdown(content, service_name)

    # 読み込み
    loaded_content = storage.load_markdown(service_name)

    assert loaded_content == content


@pytest.mark.unit
def test_load_markdown_existing_file_with_date(tmp_path):
    """
    Given: 指定日付のファイルが存在
    When: load_markdownを呼び出す（date指定）
    Then: ファイル内容が返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    test_date = datetime(2024, 1, 1)
    content = "# Historical content"

    # 事前にファイル保存
    storage.save_markdown(content, service_name, date=test_date)

    # 読み込み
    loaded_content = storage.load_markdown(service_name, date=test_date)

    assert loaded_content == content


@pytest.mark.unit
def test_load_markdown_nonexistent_file(tmp_path):
    """
    Given: ファイルが存在しない
    When: load_markdownを呼び出す
    Then: Noneが返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "nonexistent"

    result = storage.load_markdown(service_name)

    assert result is None


@pytest.mark.unit
def test_load_markdown_empty_file(tmp_path):
    """
    Given: 存在するが中身が空のファイル
    When: load_markdownを呼び出す
    Then: 空文字列""が返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"

    # 空ファイルを保存
    storage.save_markdown("", service_name)

    # 読み込み
    loaded_content = storage.load_markdown(service_name)

    assert loaded_content == ""


@pytest.mark.unit
def test_load_markdown_unicode_content(tmp_path):
    """
    Given: 日本語・絵文字を含むファイル
    When: load_markdownを呼び出す
    Then: UTF-8で正しく読み込まれる
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    content = "日本語コンテンツ\n絵文字😀🎉"

    # 保存
    storage.save_markdown(content, service_name)

    # 読み込み
    loaded_content = storage.load_markdown(service_name)

    assert loaded_content == content


@pytest.mark.unit
def test_load_markdown_permission_error(tmp_path):
    """
    Given: ファイル読み込み権限エラー
    When: load_markdownを呼び出す
    Then: PermissionError伝播
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"

    # ファイルを作成
    storage.save_markdown("Test", service_name)

    # 読み込み時にエラー
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        with pytest.raises(PermissionError):
            storage.load_markdown(service_name)


# =============================================================================
# 4. list_dates メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_list_dates_multiple_files(tmp_path):
    """
    Given: 複数のMarkdownファイル
    When: list_datesを呼び出す
    Then: 日付リストが降順でソートされて返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"

    # 複数の日付でファイル作成
    dates = [
        datetime(2024, 1, 1),
        datetime(2024, 1, 3),
        datetime(2024, 1, 2),
    ]
    for date in dates:
        storage.save_markdown(f"Content for {date}", service_name, date=date)

    # 日付一覧取得
    result = storage.list_dates(service_name)

    # 降順でソートされていることを確認
    expected = sorted(dates, reverse=True)
    assert result == expected


@pytest.mark.unit
def test_list_dates_single_file(tmp_path):
    """
    Given: ファイルが1つ
    When: list_datesを呼び出す
    Then: 1要素のリストが返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    test_date = datetime(2024, 1, 1)

    storage.save_markdown("Content", service_name, date=test_date)

    result = storage.list_dates(service_name)

    assert len(result) == 1
    assert result[0] == test_date


@pytest.mark.unit
def test_list_dates_no_files(tmp_path):
    """
    Given: .mdファイルなし
    When: list_datesを呼び出す
    Then: 空リスト[]が返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"

    # サービスディレクトリは作成されているが、ファイルはない
    (tmp_path / service_name).mkdir()

    result = storage.list_dates(service_name)

    assert result == []


@pytest.mark.unit
def test_list_dates_service_dir_not_exists(tmp_path):
    """
    Given: サービスディレクトリが存在しない
    When: list_datesを呼び出す
    Then: 空リスト[]が返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "nonexistent_service"

    result = storage.list_dates(service_name)

    assert result == []


@pytest.mark.unit
def test_list_dates_invalid_filenames_ignored(tmp_path):
    """
    Given: 不正な形式のファイル名が混在
    When: list_datesを呼び出す
    Then: 正常な日付形式のみパースされ返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    service_dir = tmp_path / service_name
    service_dir.mkdir()

    # 正常なファイル
    valid_date = datetime(2024, 1, 1)
    storage.save_markdown("Valid", service_name, date=valid_date)

    # 不正な形式のファイル
    (service_dir / "invalid.md").touch()
    (service_dir / "20240101.md").touch()
    (service_dir / "2024-13-01.md").touch()  # 13月は存在しない

    result = storage.list_dates(service_name)

    # 正常なファイルのみが返される
    assert len(result) == 1
    assert result[0] == valid_date


@pytest.mark.unit
def test_list_dates_non_md_files_ignored(tmp_path):
    """
    Given: .md以外のファイルが混在
    When: list_datesを呼び出す
    Then: .mdファイルのみが対象
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    service_dir = tmp_path / service_name
    service_dir.mkdir()

    # .mdファイル
    md_date = datetime(2024, 1, 1)
    storage.save_markdown("MD content", service_name, date=md_date)

    # 他の拡張子のファイル
    (service_dir / "2024-01-02.json").touch()
    (service_dir / "2024-01-03.txt").touch()

    result = storage.list_dates(service_name)

    # .mdファイルのみ
    assert len(result) == 1
    assert result[0] == md_date


@pytest.mark.unit
def test_list_dates_sorted_descending(tmp_path):
    """
    Given: 順不同の日付ファイル複数
    When: list_datesを呼び出す
    Then: 降順（新しい順）でソートされる
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"

    # ランダムな順序でファイル作成
    dates = [
        datetime(2024, 6, 15),
        datetime(2024, 1, 1),
        datetime(2024, 12, 31),
        datetime(2024, 3, 20),
    ]
    for date in dates:
        storage.save_markdown(f"Content {date}", service_name, date=date)

    result = storage.list_dates(service_name)

    # 降順確認
    expected = [
        datetime(2024, 12, 31),
        datetime(2024, 6, 15),
        datetime(2024, 3, 20),
        datetime(2024, 1, 1),
    ]
    assert result == expected


# =============================================================================
# 5. save メソッド（非同期）のテスト
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_json_data(tmp_path):
    """
    Given: JSON形式のデータ
    When: saveを呼び出す
    Then: JSONファイルが保存され、Pathが返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    data = {"key": "value", "number": 123}
    filename = "test.json"

    result_path = await storage.save(data, filename)

    expected_path = tmp_path / filename
    assert result_path == expected_path
    assert result_path.exists()

    # JSON内容確認
    with open(result_path, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_text_data(tmp_path):
    """
    Given: テキストデータ
    When: saveを呼び出す
    Then: テキストファイルが保存される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    data = "Plain text content"
    filename = "test.txt"

    result_path = await storage.save(data, filename)

    expected_path = tmp_path / filename
    assert result_path == expected_path
    assert result_path.exists()
    assert result_path.read_text(encoding="utf-8") == data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_empty_dict(tmp_path):
    """
    Given: 空の辞書
    When: saveを呼び出す
    Then: 空のJSON "{}"が保存される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    data = {}
    filename = "empty.json"

    result_path = await storage.save(data, filename)

    assert result_path.exists()
    with open(result_path, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == {}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_empty_list(tmp_path):
    """
    Given: 空のリスト
    When: saveを呼び出す
    Then: 空のJSON "[]"が保存される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    data = []
    filename = "empty.json"

    result_path = await storage.save(data, filename)

    assert result_path.exists()
    with open(result_path, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_nested_json(tmp_path):
    """
    Given: 深くネストしたdict/list
    When: saveを呼び出す
    Then: 正しくシリアライズされて保存
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    data = {
        "level1": {
            "level2": {"level3": {"list": [1, 2, 3], "nested_dict": {"key": "value"}}}
        }
    }
    filename = "nested.json"

    result_path = await storage.save(data, filename)

    assert result_path.exists()
    with open(result_path, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_with_subdirectory(tmp_path):
    """
    Given: サブディレクトリ付きファイル名
    When: saveを呼び出す
    Then: サブディレクトリも作成される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    data = {"test": "data"}
    filename = "subdir/nested/test.json"

    result_path = await storage.save(data, filename)

    expected_path = tmp_path / "subdir" / "nested" / "test.json"
    assert result_path == expected_path
    assert result_path.exists()
    assert (tmp_path / "subdir" / "nested").exists()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_json_unicode(tmp_path):
    """
    Given: Unicode文字を含むJSONデータ
    When: saveを呼び出す
    Then: ensure_ascii=Falseで正しく保存
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    data = {"message": "日本語メッセージ😀", "emoji": "🎉"}
    filename = "unicode.json"

    result_path = await storage.save(data, filename)

    assert result_path.exists()
    # ファイル内容を直接確認
    content = result_path.read_text(encoding="utf-8")
    assert "日本語メッセージ😀" in content
    assert "🎉" in content


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_non_serializable_object(tmp_path):
    """
    Given: 非シリアライズ可能オブジェクト
    When: saveを呼び出す
    Then: TypeError発生
    """
    storage = LocalStorage(base_dir=str(tmp_path))

    class NonSerializable:
        pass

    data = NonSerializable()
    filename = "test.json"

    with pytest.raises(TypeError):
        await storage.save(data, filename)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_async_io_error(tmp_path):
    """
    Given: ファイル書き込みIOエラー
    When: saveを呼び出す
    Then: OSError伝播
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    data = {"test": "data"}
    filename = "test.json"

    # aiofiles.openをモック
    with patch("aiofiles.open", side_effect=OSError("IO error")):
        with pytest.raises(OSError):
            await storage.save(data, filename)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_large_json_data(tmp_path):
    """
    Given: 10MB以上のdata
    When: saveを呼び出す
    Then: 正常に保存される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    # 大きなリストを生成（10MBを確実に超えるサイズ）
    data = [{"id": i, "data": "x" * 2000} for i in range(6000)]
    filename = "large.json"

    result_path = await storage.save(data, filename)

    assert result_path.exists()
    # ファイルサイズ確認（10MB以上）
    file_size = result_path.stat().st_size
    assert file_size > 10 * 1024 * 1024


# =============================================================================
# 6. load メソッド（非同期）のテスト
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_load_existing_file(tmp_path):
    """
    Given: 既存のファイル
    When: loadを呼び出す
    Then: ファイル内容が文字列で返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    filename = "test.txt"
    content = "Test content"

    # 事前にファイル保存
    await storage.save(content, filename)

    # 読み込み
    loaded_content = await storage.load(filename)

    assert loaded_content == content


@pytest.mark.asyncio
@pytest.mark.unit
async def test_load_nonexistent_file(tmp_path):
    """
    Given: 存在しないファイル名
    When: loadを呼び出す
    Then: Noneが返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    filename = "nonexistent.txt"

    result = await storage.load(filename)

    assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_load_empty_file(tmp_path):
    """
    Given: 空のファイル
    When: loadを呼び出す
    Then: 空文字列""が返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    filename = "empty.txt"

    # 空ファイルを保存
    await storage.save("", filename)

    # 読み込み
    loaded_content = await storage.load(filename)

    assert loaded_content == ""


@pytest.mark.asyncio
@pytest.mark.unit
async def test_load_unicode_file(tmp_path):
    """
    Given: UTF-8エンコードファイル
    When: loadを呼び出す
    Then: 正しく読み込まれる
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    filename = "unicode.txt"
    content = "日本語コンテンツ\n絵文字😀🎉"

    # 保存
    await storage.save(content, filename)

    # 読み込み
    loaded_content = await storage.load(filename)

    assert loaded_content == content


@pytest.mark.asyncio
@pytest.mark.unit
async def test_load_async_io_error(tmp_path):
    """
    Given: ファイル読み込みIOエラー
    When: loadを呼び出す
    Then: OSError伝播
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    filename = "test.txt"

    # ファイル作成
    await storage.save("content", filename)

    # 読み込み時にエラー
    with patch("aiofiles.open", side_effect=OSError("IO error")):
        with pytest.raises(OSError):
            await storage.load(filename)


# =============================================================================
# 7. exists メソッド（非同期）のテスト
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_exists_file_present(tmp_path):
    """
    Given: 既存のファイル名
    When: existsを呼び出す
    Then: Trueが返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    filename = "existing.txt"

    # ファイル作成
    await storage.save("content", filename)

    # 存在確認
    result = await storage.exists(filename)

    assert result is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_exists_file_absent(tmp_path):
    """
    Given: 存在しないファイル名
    When: existsを呼び出す
    Then: Falseが返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    filename = "nonexistent.txt"

    result = await storage.exists(filename)

    assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_exists_directory(tmp_path):
    """
    Given: ディレクトリパス
    When: existsを呼び出す
    Then: Trueが返される（ディレクトリもPath.exists()でTrue）
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    dirname = "subdir"

    # ディレクトリ作成
    (tmp_path / dirname).mkdir()

    result = await storage.exists(dirname)

    assert result is True


# =============================================================================
# 8. rename メソッド（非同期）のテスト
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_rename_existing_file(tmp_path):
    """
    Given: 既存ファイルを新しい名前に
    When: renameを呼び出す
    Then: ファイル名が変更される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    old_filename = "old.txt"
    new_filename = "new.txt"
    content = "Test content"

    # ファイル作成
    await storage.save(content, old_filename)

    # リネーム
    await storage.rename(old_filename, new_filename)

    # 確認
    assert not (tmp_path / old_filename).exists()
    assert (tmp_path / new_filename).exists()
    assert (tmp_path / new_filename).read_text(encoding="utf-8") == content


@pytest.mark.asyncio
@pytest.mark.unit
async def test_rename_nonexistent_file(tmp_path):
    """
    Given: 存在しないファイル名
    When: renameを呼び出す
    Then: 何も起こらない（エラーなし）
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    old_filename = "nonexistent.txt"
    new_filename = "new.txt"

    # エラーなく完了することを確認
    await storage.rename(old_filename, new_filename)

    assert not (tmp_path / new_filename).exists()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_rename_overwrite_existing(tmp_path):
    """
    Given: 既存ファイルを既存の名前に
    When: renameを呼び出す
    Then: 上書きされる
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    old_filename = "old.txt"
    new_filename = "new.txt"

    # 両方のファイルを作成
    await storage.save("Old content", old_filename)
    await storage.save("New content", new_filename)

    # リネーム（上書き）
    await storage.rename(old_filename, new_filename)

    # 確認
    assert not (tmp_path / old_filename).exists()
    assert (tmp_path / new_filename).exists()
    assert (tmp_path / new_filename).read_text(encoding="utf-8") == "Old content"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_rename_move_across_subdirs(tmp_path):
    """
    Given: サブディレクトリ間の移動
    When: renameを呼び出す
    Then: ファイルが移動される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    old_filename = "dir1/file.txt"
    new_filename = "dir2/file.txt"
    content = "Test content"

    # ファイル作成
    await storage.save(content, old_filename)

    # dir2を作成
    (tmp_path / "dir2").mkdir()

    # 移動
    await storage.rename(old_filename, new_filename)

    # 確認
    assert not (tmp_path / old_filename).exists()
    assert (tmp_path / new_filename).exists()
    assert (tmp_path / new_filename).read_text(encoding="utf-8") == content


# =============================================================================
# 9. load_json メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_load_json_existing_file_without_date(tmp_path):
    """
    Given: 現在日付のJSONファイル
    When: load_jsonを呼び出す（date=None）
    Then: リスト/辞書が返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    data = [{"id": 1, "name": "Test"}]

    # JSONファイルを手動作成
    today_str = datetime.now().strftime("%Y-%m-%d")
    service_dir = tmp_path / service_name
    service_dir.mkdir()
    json_file = service_dir / f"{today_str}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # 読み込み
    loaded_data = storage.load_json(service_name)

    assert loaded_data == data


@pytest.mark.unit
def test_load_json_existing_file_with_date(tmp_path):
    """
    Given: 指定日付のJSONファイル
    When: load_jsonを呼び出す（date指定）
    Then: JSONデータが返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    test_date = datetime(2024, 1, 15)
    data = {"key": "value", "number": 123}

    # JSONファイルを手動作成
    service_dir = tmp_path / service_name
    service_dir.mkdir()
    json_file = service_dir / "2024-01-15.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # 読み込み
    loaded_data = storage.load_json(service_name, date=test_date)

    assert loaded_data == data


@pytest.mark.unit
def test_load_json_nonexistent_file(tmp_path):
    """
    Given: ファイルが存在しない
    When: load_jsonを呼び出す
    Then: Noneが返される
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "nonexistent"

    result = storage.load_json(service_name)

    assert result is None


@pytest.mark.unit
def test_load_json_empty_file(tmp_path):
    """
    Given: 内容が空のファイル
    When: load_jsonを呼び出す
    Then: JSONDecodeError発生
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"

    # 空ファイルを作成
    today_str = datetime.now().strftime("%Y-%m-%d")
    service_dir = tmp_path / service_name
    service_dir.mkdir()
    json_file = service_dir / f"{today_str}.json"
    json_file.touch()  # 空ファイル

    with pytest.raises(json.JSONDecodeError):
        storage.load_json(service_name)


@pytest.mark.unit
def test_load_json_invalid_format(tmp_path):
    """
    Given: 壊れたJSON
    When: load_jsonを呼び出す
    Then: JSONDecodeError発生
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"

    # 不正なJSONファイルを作成
    today_str = datetime.now().strftime("%Y-%m-%d")
    service_dir = tmp_path / service_name
    service_dir.mkdir()
    json_file = service_dir / f"{today_str}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        f.write("{invalid json")

    with pytest.raises(json.JSONDecodeError):
        storage.load_json(service_name)


@pytest.mark.unit
def test_load_json_unicode_content(tmp_path):
    """
    Given: Unicode文字を含むJSON
    When: load_jsonを呼び出す
    Then: 正しくパースされる
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    data = {"message": "日本語メッセージ😀", "emoji": "🎉"}

    # JSONファイルを作成
    today_str = datetime.now().strftime("%Y-%m-%d")
    service_dir = tmp_path / service_name
    service_dir.mkdir()
    json_file = service_dir / f"{today_str}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    # 読み込み
    loaded_data = storage.load_json(service_name)

    assert loaded_data == data


@pytest.mark.unit
def test_load_json_nested_structure(tmp_path):
    """
    Given: 深くネストしたJSON
    When: load_jsonを呼び出す
    Then: 正しくパースされる
    """
    storage = LocalStorage(base_dir=str(tmp_path))
    service_name = "test"
    data = {
        "level1": {
            "level2": {"level3": {"list": [1, 2, 3], "nested_dict": {"key": "value"}}}
        }
    }

    # JSONファイルを作成
    today_str = datetime.now().strftime("%Y-%m-%d")
    service_dir = tmp_path / service_name
    service_dir.mkdir()
    json_file = service_dir / f"{today_str}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # 読み込み
    loaded_data = storage.load_json(service_name)

    assert loaded_data == data
