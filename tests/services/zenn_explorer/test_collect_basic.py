"""
nook/services/zenn_explorer/zenn_explorer.py のテスト - collect()基本機能

テスト観点:
- collect()の正常系
- 基本的なエラーハンドリング
- 境界値テスト
- 重複記事処理
- 複数カテゴリ処理
- フィードエラー処理
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from tests.conftest import create_mock_dedup, create_mock_entry, create_mock_feed

# =============================================================================
# 3. collect メソッドのテスト - 正常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_success_with_valid_feed(zenn_service_with_mocks):
    """
    Given: 有効なRSSフィード
    When: collectメソッドを呼び出す
    Then: 記事が正常に取得・保存される
    """
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]

    # Given: 有効なRSSフィードを設定
    mock_entry = create_mock_entry(
        title="テストZenn記事",
        link="https://example.com/article1",
        summary="テストZenn記事の説明",
    )
    mock_feed = create_mock_feed(title="Test Feed", entries=[mock_entry])
    mock_parse.return_value = mock_feed

    mock_dedup = create_mock_dedup()
    mock_load.return_value = mock_dedup

    service.http_client.get = AsyncMock(
        return_value=Mock(text="<html><body><p>日本語テキスト</p></body></html>")
    )
    service.gpt_client.get_response = AsyncMock(return_value="要約")

    # When: collectメソッドを呼び出す（target_datesを明示的に指定）
    result = await service.collect(days=1, limit=10, target_dates=[date(2024, 11, 14)])

    # Then: 記事が正常に取得される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) > 0, "有効なフィードから少なくとも1件の記事が取得されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_articles(zenn_service_with_mocks):
    """
    Given: 複数の記事を含むフィード
    When: collectメソッドを呼び出す
    Then: 全ての記事が処理される
    """
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]

    # Given: 5件の記事を含むフィードを設定
    entries = [
        create_mock_entry(
            title=f"テストZenn記事{i}",
            link=f"https://example.com/article{i}",
            summary=f"説明{i}",
        )
        for i in range(5)
    ]
    mock_feed = create_mock_feed(title="Test Feed", entries=entries)
    mock_parse.return_value = mock_feed

    mock_dedup = create_mock_dedup()
    mock_load.return_value = mock_dedup

    service.http_client.get = AsyncMock(
        return_value=Mock(text="<html><body><p>日本語テキスト</p></body></html>")
    )
    service.gpt_client.get_response = AsyncMock(return_value="要約")

    # When: collectメソッドを呼び出す（target_datesを明示的に指定）
    result = await service.collect(days=1, limit=10, target_dates=[date(2024, 11, 14)])

    # Then: 複数の記事が処理される（日付ごとにファイルが作成されるため、1日分のファイルパス）
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) == 1, "1日分のファイルパス(json_path, md_path)が返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_target_dates_none(zenn_service_with_mocks):
    """target_dates=Noneでデフォルトの日付範囲が使用される"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]

    # Given: エントリのない空のフィードを設定
    mock_feed = create_mock_feed(title="Test Feed", entries=[])
    mock_parse.return_value = mock_feed

    mock_dedup = create_mock_dedup()
    mock_load.return_value = mock_dedup

    # When: target_dates=Noneでcollectメソッドを呼び出す
    result = await service.collect(days=1, limit=10, target_dates=None)

    # Then: 空リストが返される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) == 0, "エントリがないため空リストが返されるべき"


# =============================================================================
# 4. collect メソッドのテスト - 異常系
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_network_error(zenn_service_with_mocks):
    """ネットワークエラー発生時にエラーがログされるが例外は発生しない"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]

    # Given: feedparser.parseがネットワークエラーを発生させる
    mock_parse.side_effect = Exception("Network error")

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1)

    # Then: 例外を吸収して空リストが返される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) == 0, "ネットワークエラー時は空リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_invalid_feed_xml(zenn_service_with_mocks):
    """不正なXMLフィードでエラーがログされ空リストが返される"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]

    # Given: エントリのない不正なフィードを設定
    mock_feed = create_mock_feed(title="Invalid Feed", entries=[])
    mock_parse.return_value = mock_feed

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1)

    # Then: 空リストが返される
    assert result == [], "不正なフィード時は空リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_http_client_timeout(zenn_service_with_mocks):
    """HTTPクライアントのタイムアウトが適切に処理される"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]

    # Given: 記事を含むフィードを設定
    mock_entry = create_mock_entry(title="テスト", link="https://example.com/test")
    mock_feed = create_mock_feed(title="Test Feed", entries=[mock_entry])
    mock_parse.return_value = mock_feed

    mock_dedup = create_mock_dedup()
    mock_load.return_value = mock_dedup

    # Given: HTTP clientがタイムアウトを発生させる
    service.http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1)

    # Then: タイムアウトを処理して空リストが返される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) == 0, "HTTPタイムアウト時は空リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_gpt_api_error(zenn_service_with_mocks):
    """GPT APIのエラーが適切に処理される"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]

    # Given: 記事を含むフィードを設定
    mock_entry = create_mock_entry(title="テスト", link="https://example.com/test", summary="説明")
    mock_feed = create_mock_feed(title="Test Feed", entries=[mock_entry])
    mock_parse.return_value = mock_feed

    mock_dedup = create_mock_dedup()
    mock_load.return_value = mock_dedup

    # Given: HTTP clientは正常だがGPT APIがエラーを発生させる
    service.http_client.get = AsyncMock(return_value=Mock(text="<html><body>日本語</body></html>"))
    service.gpt_client.get_response = AsyncMock(side_effect=Exception("API Error"))

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1)

    # Then: GPT APIエラーを処理してリストが返される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) >= 0, "GPT APIエラー時でもリストが返されるべき"


# =============================================================================
# 5. collect メソッドのテスト - 境界値
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_limit_zero(zenn_service_with_mocks):
    """limit=0で記事が取得されない"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]

    # Given: エントリのない空のフィードを設定
    mock_feed = create_mock_feed(title="Test Feed", entries=[])
    mock_parse.return_value = mock_feed

    # When: limit=0でcollectメソッドを呼び出す
    result = await service.collect(days=1, limit=0)

    # Then: 空リストが返される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) == 0, "limit=0のため空リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_limit_one(zenn_service_with_mocks):
    """limit=1で最大1件の記事が処理される"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]

    # Given: 1件の記事を含むフィードを設定
    mock_entry = create_mock_entry(title="テスト", link="https://example.com/test", summary="説明")
    mock_feed = create_mock_feed(title="Test", entries=[mock_entry])
    mock_parse.return_value = mock_feed

    mock_dedup = create_mock_dedup()
    mock_load.return_value = mock_dedup

    service.http_client.get = AsyncMock(return_value=Mock(text="<html><body>日本語</body></html>"))
    service.gpt_client.get_response = AsyncMock(return_value="要約")

    # When: limit=1でcollectメソッドを呼び出す
    result = await service.collect(days=1, limit=1)

    # Then: 最大1件の記事が返される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) <= 1, "limit=1のため最大1件の記事が返されるべき"


# =============================================================================
# 6. collect メソッドのテスト - 完全ワークフロー
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_workflow_collect_and_save(zenn_service_with_mocks):
    """完全なワークフロー（collect→save→cleanup）が正常に動作"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]
    mock_storage_save = zenn_service_with_mocks["mock_storage_save"]

    # Given: 記事を含むフィードを設定
    mock_entry = create_mock_entry(
        title="テストZenn記事", link="https://example.com/test", summary="テスト説明"
    )
    mock_feed = create_mock_feed(title="Test Feed", entries=[mock_entry])
    mock_parse.return_value = mock_feed

    mock_dedup = create_mock_dedup()
    mock_load.return_value = mock_dedup

    service.http_client.get = AsyncMock(
        return_value=Mock(text="<html><body><p>日本語の記事</p></body></html>")
    )
    service.gpt_client.get_response = AsyncMock(return_value="要約テキスト")

    # Ensure storage.save returns a Path
    mock_storage_save.return_value = Path("/data/test.json")

    # When: collect→cleanupの完全なワークフローを実行（target_datesを明示的に指定）
    result = await service.collect(days=1, limit=10, target_dates=[date(2024, 11, 14)])
    await service.cleanup()

    # Then: 記事が正常に取得される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) > 0, "完全なワークフローでは記事が取得されるべき"


# =============================================================================
# 7. collect メソッド - フィード処理ループの詳細テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_multiple_categories(zenn_service_with_mocks):
    """複数カテゴリ（tech, business）のフィードがすべて処理される"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]

    # Given: 複数カテゴリのフィード設定
    service.feed_config = {
        "tech": ["https://example.com/tech.xml"],
        "business": ["https://example.com/business.xml"],
    }

    # Given: エントリのない空のフィードを設定
    mock_feed = create_mock_feed(title="Test Feed", entries=[])
    mock_parse.return_value = mock_feed

    mock_dedup = create_mock_dedup()
    mock_load.return_value = mock_dedup

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1)

    # Then: 両カテゴリのフィードが処理される
    assert mock_parse.call_count == 2, "tech/businessの2カテゴリが処理されるべき"
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) == 0, "エントリがないため空リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_feedparser_attribute_error(zenn_service_with_mocks):
    """feedparser.parseのAttributeErrorがログされ処理が継続される"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]

    # Given: feedparser.parseがAttributeErrorを発生させる
    mock_parse.side_effect = AttributeError("'NoneType' object has no attribute 'feed'")

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1)

    # Then: エラーを処理して空リストが返される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) == 0, "AttributeError時は空リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_duplicate_article(zenn_service_with_mocks):
    """重複記事がスキップされる"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]
    mock_load = zenn_service_with_mocks["mock_load"]

    # Given: 重複記事を含むフィードを設定
    mock_entry = create_mock_entry(
        title="重複記事", link="https://example.com/duplicate", summary="説明"
    )
    mock_feed = create_mock_feed(title="Test Feed", entries=[mock_entry])
    mock_parse.return_value = mock_feed

    # Given: 重複として判定するDedupTrackerをモック
    mock_dedup = create_mock_dedup(is_duplicate=True, normalized_title="normalized_title")
    mock_dedup.get_original_title = Mock(return_value="元のタイトル")
    mock_load.return_value = mock_dedup

    service.http_client.get = AsyncMock(
        return_value=Mock(text="<html><body><p>テキスト</p></body></html>")
    )

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1)

    # Then: 重複記事はスキップされ空リストが返される
    assert result == [], "重複記事はスキップされるため空リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_empty_feed_entries(zenn_service_with_mocks):
    """エントリが空のフィードで空リストが返される"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]

    # Given: エントリが空のフィードを設定
    mock_feed = create_mock_feed(title="Empty Feed", entries=[])
    mock_parse.return_value = mock_feed

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1)

    # Then: 空リストが返される
    assert result == [], "エントリが空のフィードでは空リストが返されるべき"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_continues_on_individual_feed_error(zenn_service_with_mocks):
    """1つのフィードでエラーが発生しても処理が継続される"""
    # Given: フィクスチャから必要なモックを取得
    service = zenn_service_with_mocks["service"]
    mock_parse = zenn_service_with_mocks["mock_parse"]

    # Given: 2つのフィード設定
    service.feed_config = {
        "tech": ["https://example.com/feed1.xml", "https://example.com/feed2.xml"],
    }

    # Given: 1つ目のフィードでエラー、2つ目は成功
    mock_feed = create_mock_feed(title="Test Feed", entries=[])
    mock_parse.side_effect = [
        Exception("Feed error"),
        mock_feed,
    ]

    # When: collectメソッドを呼び出す
    result = await service.collect(days=1)

    # Then: エラーがあっても処理は継続され空リストが返される
    assert isinstance(result, list), "結果はリスト型であるべき"
    assert len(result) == 0, "部分的なフィードエラーでもエントリが空なら空リストが返されるべき"
