"""
nook/common/base_service.py のテスト

テスト観点:
- BaseServiceの初期化
- 抽象メソッドのテスト（collectなど）
- データ保存フロー
- クリーンアップ処理
- エラーハンドリング
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from nook.common.base_service import BaseService
from nook.common.config import BaseConfig

# =============================================================================
# テスト用の具象クラス
# =============================================================================


class ConcreteService(BaseService):
    """テスト用の具象クラス"""

    async def collect(self):
        """テスト用のcollect実装"""
        return [{"title": "Test", "url": "http://example.com"}]


class CustomCleanupService(BaseService):
    """クリーンアップをオーバーライドするテスト用クラス"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cleanup_called = False

    async def collect(self):
        return []

    async def cleanup(self):
        """カスタムクリーンアップ処理"""
        self.cleanup_called = True


# =============================================================================
# 1. __init__ メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_init_with_service_name_only():
    """
    Given: 有効なservice_name
    When: BaseServiceを初期化
    Then: インスタンスが正常に作成される
    """
    with patch("nook.common.base_service.setup_logger") as mock_logger:
        service = ConcreteService(service_name="test_service")

        assert service.service_name == "test_service"
        assert service.config is not None
        assert service.storage is not None
        assert service.gpt_client is not None
        mock_logger.assert_called_once_with("test_service")


@pytest.mark.unit
def test_init_with_explicit_config():
    """
    Given: configを明示的に指定
    When: BaseServiceを初期化
    Then: 指定したconfigが使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        custom_config = Mock(spec=BaseConfig)
        custom_config.REQUEST_DELAY = 2.5
        service = ConcreteService(service_name="test", config=custom_config)

        assert service.config is custom_config
        assert service.request_delay == 2.5


@pytest.mark.unit
def test_init_with_none_config():
    """
    Given: config=None
    When: BaseServiceを初期化
    Then: デフォルトBaseConfig()が使用される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test", config=None)

        assert isinstance(service.config, BaseConfig)


@pytest.mark.unit
def test_init_storage_created():
    """
    Given: service_name="test"
    When: BaseServiceを初期化
    Then: storage.base_dirが"data/test"になる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        assert service.storage is not None
        # LocalStorageのbase_dirを確認
        assert str(service.storage.base_dir).endswith("data/test")


@pytest.mark.unit
def test_init_gpt_client_created():
    """
    Given: service_name="test"
    When: BaseServiceを初期化
    Then: gpt_clientがGPTClientインスタンスである
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        assert service.gpt_client is not None


@pytest.mark.unit
def test_init_logger_created():
    """
    Given: service_name="test"
    When: BaseServiceを初期化
    Then: loggerが正しく設定される
    """
    with patch("nook.common.base_service.setup_logger") as mock_logger:
        mock_logger.return_value = Mock(name="test")
        service = ConcreteService(service_name="test")

        assert service.logger is not None
        mock_logger.assert_called_once_with("test")


@pytest.mark.unit
def test_init_request_delay_set():
    """
    Given: config.REQUEST_DELAY=2.0
    When: BaseServiceを初期化
    Then: self.request_delay==2.0
    """
    with patch("nook.common.base_service.setup_logger"):
        custom_config = Mock(spec=BaseConfig)
        custom_config.REQUEST_DELAY = 2.0
        service = ConcreteService(service_name="test", config=custom_config)

        assert service.request_delay == 2.0


@pytest.mark.unit
def test_init_http_client_none():
    """
    Given: 初期化時
    When: BaseServiceを初期化
    Then: self.http_client is None
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        assert service.http_client is None


@pytest.mark.unit
def test_init_empty_service_name():
    """
    Given: service_name=""
    When: BaseServiceを初期化
    Then: エラーなく初期化（storageパスは"data"）
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="")

        assert service.service_name == ""
        # 空文字列の場合、"data/"ではなく"data"となる
        assert str(service.storage.base_dir) == "data"


@pytest.mark.unit
def test_init_special_chars_service_name():
    """
    Given: service_name="test-service_123"
    When: BaseServiceを初期化
    Then: エラーなく初期化
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test-service_123")

        assert service.service_name == "test-service_123"


# =============================================================================
# 2. collect メソッド（抽象メソッド）のテスト
# =============================================================================


@pytest.mark.unit
def test_collect_abstract_method_cannot_instantiate():
    """
    Given: BaseServiceを直接インスタンス化しようとする
    When: BaseService()を呼び出す
    Then: TypeErrorが発生する
    """
    with pytest.raises(TypeError):
        BaseService(service_name="test")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_concrete_implementation():
    """
    Given: ConcreteService.collect()
    When: collectを呼び出す
    Then: サブクラスのcollect実装が呼ばれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        result = await service.collect()

        assert result == [{"title": "Test", "url": "http://example.com"}]


# =============================================================================
# 3. save_data メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_data_normal():
    """
    Given: data={"key":"value"}, filename="test.json"
    When: save_dataを呼び出す
    Then: storage.saveが呼ばれ、Pathが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/test.json"))

        result = await service.save_data({"key": "value"}, "test.json")

        assert result == Path("/data/test/test.json")
        service.storage.save.assert_called_once_with({"key": "value"}, "test.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_data_empty_dict():
    """
    Given: data={}, filename="empty.json"
    When: save_dataを呼び出す
    Then: 空JSONが保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/empty.json"))

        result = await service.save_data({}, "empty.json")

        assert result == Path("/data/test/empty.json")
        service.storage.save.assert_called_once_with({}, "empty.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_data_empty_list():
    """
    Given: data=[], filename="empty.json"
    When: save_dataを呼び出す
    Then: 空配列が保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/empty.json"))

        result = await service.save_data([], "empty.json")

        assert result == Path("/data/test/empty.json")
        service.storage.save.assert_called_once_with([], "empty.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_data_text():
    """
    Given: data="text content", filename="test.txt"
    When: save_dataを呼び出す
    Then: テキストが保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/test.txt"))

        result = await service.save_data("text content", "test.txt")

        assert result == Path("/data/test/test.txt")
        service.storage.save.assert_called_once_with("text content", "test.txt")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_data_storage_error():
    """
    Given: storage.saveがOSErrorをraise
    When: save_dataを呼び出す
    Then: ログ出力後、例外が再raiseされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(side_effect=OSError("Disk error"))

        with pytest.raises(OSError, match="Disk error"):
            await service.save_data({"key": "value"}, "test.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_data_permission_error():
    """
    Given: storage.saveがPermissionErrorをraise
    When: save_dataを呼び出す
    Then: ログ出力後、例外が再raiseされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(side_effect=PermissionError("Permission denied"))

        with pytest.raises(PermissionError, match="Permission denied"):
            await service.save_data({"key": "value"}, "test.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_data_large_data():
    """
    Given: data=10MBのデータ
    When: save_dataを呼び出す
    Then: 正常に保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/large.json"))

        large_data = {"data": "x" * (10 * 1024 * 1024)}
        result = await service.save_data(large_data, "large.json")

        assert result == Path("/data/test/large.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_data_none_data():
    """
    Given: data=None
    When: save_dataを呼び出す
    Then: storage.saveの動作に依存（エラーの可能性）
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/none.json"))

        result = await service.save_data(None, "none.json")

        assert result == Path("/data/test/none.json")
        service.storage.save.assert_called_once_with(None, "none.json")


# =============================================================================
# 4. save_markdown メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_markdown_normal():
    """
    Given: content="# Title", filename="test.md"
    When: save_markdownを呼び出す
    Then: save_dataが呼ばれ、Pathが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/test.md"))

        result = await service.save_markdown("# Title", "test.md")

        assert result == Path("/data/test/test.md")
        service.storage.save.assert_called_once_with("# Title", "test.md")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_markdown_empty():
    """
    Given: content="", filename="empty.md"
    When: save_markdownを呼び出す
    Then: 空ファイルが保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/empty.md"))

        result = await service.save_markdown("", "empty.md")

        assert result == Path("/data/test/empty.md")
        service.storage.save.assert_called_once_with("", "empty.md")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_markdown_unicode():
    """
    Given: content="日本語😀", filename="test.md"
    When: save_markdownを呼び出す
    Then: UTF-8で保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/test.md"))

        result = await service.save_markdown("日本語😀", "test.md")

        assert result == Path("/data/test/test.md")
        service.storage.save.assert_called_once_with("日本語😀", "test.md")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_markdown_save_data_error():
    """
    Given: save_dataがExceptionをraise
    When: save_markdownを呼び出す
    Then: 例外が伝播される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(side_effect=Exception("Save failed"))

        with pytest.raises(Exception, match="Save failed"):
            await service.save_markdown("# Title", "test.md")


# =============================================================================
# 5. fetch_with_retry メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_with_retry_not_implemented():
    """
    Given: fetch_with_retry("http://example.com")
    When: メソッドを呼び出す
    Then: RetryExceptionが発生する（NotImplementedErrorがリトライされた後）
    """
    from nook.common.exceptions import RetryException

    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        with pytest.raises(RetryException, match="Failed after 3 attempts"):
            await service.fetch_with_retry("http://example.com")


@pytest.mark.unit
def test_fetch_with_retry_decorator_applied():
    """
    Given: fetch_with_retryメソッド
    When: デコレータが適用されているか確認
    Then: @handle_errorsデコレータが適用されている
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        # デコレータが適用されていることを確認
        assert hasattr(service.fetch_with_retry, "__wrapped__")


# =============================================================================
# 6. rate_limit メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_default_delay():
    """
    Given: request_delay=1.0（デフォルト）
    When: rate_limitを呼び出す
    Then: 1秒待機する
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        # デフォルトのREQUEST_DELAYを設定
        service.request_delay = 1.0

        with patch("asyncio.sleep") as mock_sleep:
            await service.rate_limit()
            mock_sleep.assert_called_once_with(1.0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_custom_delay():
    """
    Given: request_delay=0.5
    When: rate_limitを呼び出す
    Then: 0.5秒待機する
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.request_delay = 0.5

        with patch("asyncio.sleep") as mock_sleep:
            await service.rate_limit()
            mock_sleep.assert_called_once_with(0.5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_min_delay():
    """
    Given: request_delay=0.1（境界値）
    When: rate_limitを呼び出す
    Then: 0.1秒待機する
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.request_delay = 0.1

        with patch("asyncio.sleep") as mock_sleep:
            await service.rate_limit()
            mock_sleep.assert_called_once_with(0.1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_max_delay():
    """
    Given: request_delay=10.0（境界値）
    When: rate_limitを呼び出す
    Then: 10秒待機する
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.request_delay = 10.0

        with patch("asyncio.sleep") as mock_sleep:
            await service.rate_limit()
            mock_sleep.assert_called_once_with(10.0)


# =============================================================================
# 7. get_config_path メソッドのテスト
# =============================================================================


@pytest.mark.unit
def test_get_config_path_normal():
    """
    Given: filename="config.yaml"
    When: get_config_pathを呼び出す
    Then: Path("nook/services/test/config.yaml")が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        result = service.get_config_path("config.yaml")

        assert result == Path("nook/services/test/config.yaml")


@pytest.mark.unit
def test_get_config_path_with_subdir():
    """
    Given: filename="subdir/config.yaml"
    When: get_config_pathを呼び出す
    Then: 正しいPathが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        result = service.get_config_path("subdir/config.yaml")

        assert result == Path("nook/services/test/subdir/config.yaml")


@pytest.mark.unit
def test_get_config_path_empty_filename():
    """
    Given: filename=""
    When: get_config_pathを呼び出す
    Then: Path("nook/services/test/")が返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        result = service.get_config_path("")

        assert result == Path("nook/services/test/")


# =============================================================================
# 8. save_json メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_json_normal():
    """
    Given: data={"key":"value"}, filename="test.json"
    When: save_jsonを呼び出す
    Then: storage.saveが呼ばれ、Pathが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/test.json"))

        result = await service.save_json({"key": "value"}, "test.json")

        assert result == Path("/data/test/test.json")
        service.storage.save.assert_called_once_with({"key": "value"}, "test.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_json_empty():
    """
    Given: data={}, filename="empty.json"
    When: save_jsonを呼び出す
    Then: 空JSONが保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/empty.json"))

        result = await service.save_json({}, "empty.json")

        assert result == Path("/data/test/empty.json")
        service.storage.save.assert_called_once_with({}, "empty.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_json_nested():
    """
    Given: data={"a":{"b":"c"}}, filename="nested.json"
    When: save_jsonを呼び出す
    Then: 正常に保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/nested.json"))

        result = await service.save_json({"a": {"b": "c"}}, "nested.json")

        assert result == Path("/data/test/nested.json")
        service.storage.save.assert_called_once_with({"a": {"b": "c"}}, "nested.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_json_storage_error():
    """
    Given: storage.saveがExceptionをraise
    When: save_jsonを呼び出す
    Then: 例外が伝播される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(side_effect=Exception("Storage error"))

        with pytest.raises(Exception, match="Storage error"):
            await service.save_json({"key": "value"}, "test.json")


# =============================================================================
# 9. load_json メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_json_existing_file():
    """
    Given: 有効なJSONファイル
    When: load_jsonを呼び出す
    Then: JSONデータがパースされて返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.load = AsyncMock(return_value='{"key": "value"}')

        result = await service.load_json("test.json")

        assert result == {"key": "value"}
        service.storage.load.assert_called_once_with("test.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_json_nonexistent_file():
    """
    Given: storage.loadがNone返却
    When: load_jsonを呼び出す
    Then: Noneが返される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.load = AsyncMock(return_value=None)

        result = await service.load_json("nonexistent.json")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_json_empty_file():
    """
    Given: content=""
    When: load_jsonを呼び出す
    Then: Noneが返される（contentがFalsyなので）
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.load = AsyncMock(return_value="")

        result = await service.load_json("empty.json")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_json_invalid_json():
    """
    Given: content="{invalid}"
    When: load_jsonを呼び出す
    Then: json.JSONDecodeErrorが発生
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.load = AsyncMock(return_value="{invalid}")

        with pytest.raises(json.JSONDecodeError):
            await service.load_json("invalid.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_json_storage_error():
    """
    Given: storage.loadがExceptionをraise
    When: load_jsonを呼び出す
    Then: 例外が伝播される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.load = AsyncMock(side_effect=Exception("Load error"))

        with pytest.raises(Exception, match="Load error"):
            await service.load_json("test.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_json_unicode():
    """
    Given: content='{"msg":"日本語"}'
    When: load_jsonを呼び出す
    Then: 正しくパースされる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.load = AsyncMock(return_value='{"msg":"日本語"}')

        result = await service.load_json("unicode.json")

        assert result == {"msg": "日本語"}


# =============================================================================
# 10. save_with_backup メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_with_backup_first_time():
    """
    Given: 既存ファイルなし
    When: save_with_backupを呼び出す
    Then: バックアップなしで保存される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.exists = AsyncMock(return_value=False)
        service.storage.save = AsyncMock(return_value=Path("/data/test/test.json"))

        await service.save_with_backup({"key": "value"}, "test.json", keep_backups=3)

        service.storage.exists.assert_called_once_with("test.json")
        service.storage.save.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_with_backup_second_time():
    """
    Given: 既存ファイルあり
    When: save_with_backupを呼び出す
    Then: filename.1が作成され、新データ保存
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        # 1回目: 既存ファイルあり、2回目以降: バックアップファイルなし
        service.storage.exists = AsyncMock(side_effect=[True, False, False])
        service.storage.rename = AsyncMock()
        service.storage.save = AsyncMock(return_value=Path("/data/test/test.json"))

        await service.save_with_backup({"key": "new"}, "test.json", keep_backups=3)

        # test.json -> test.json.1 にリネーム
        service.storage.rename.assert_called_once_with("test.json", "test.json.1")
        service.storage.save.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_with_backup_rotation():
    """
    Given: keep_backups=3で4回保存
    When: save_with_backupを呼び出す
    Then: .1, .2, .3のみ保持、.4は作られない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        # 既存ファイルあり、.1と.2が存在
        service.storage.exists = AsyncMock(
            side_effect=[
                True,  # test.jsonが存在
                True,  # .2が存在
                True,  # .1が存在
            ]
        )
        service.storage.rename = AsyncMock()
        service.storage.save = AsyncMock(return_value=Path("/data/test/test.json"))

        await service.save_with_backup({"key": "value"}, "test.json", keep_backups=3)

        # .2 -> .3, .1 -> .2, test.json -> .1 の順でリネーム
        assert service.storage.rename.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_with_backup_keep_one():
    """
    Given: keep_backups=1
    When: save_with_backupを呼び出す
    Then: バックアップなし、上書きのみ
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.exists = AsyncMock(return_value=True)
        service.storage.rename = AsyncMock()
        service.storage.save = AsyncMock(return_value=Path("/data/test/test.json"))

        await service.save_with_backup({"key": "value"}, "test.json", keep_backups=1)

        # keep_backups=1なので、ループは range(0, 0, -1) で空
        # よって rename は test.json -> test.json.1 のみ
        service.storage.rename.assert_called_once_with("test.json", "test.json.1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_with_backup_exists_error():
    """
    Given: storage.existsがExceptionをraise
    When: save_with_backupを呼び出す
    Then: 例外が伝播される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.exists = AsyncMock(side_effect=Exception("Exists error"))

        with pytest.raises(Exception, match="Exists error"):
            await service.save_with_backup({"key": "value"}, "test.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_with_backup_rename_error():
    """
    Given: storage.renameがExceptionをraise
    When: save_with_backupを呼び出す
    Then: 例外が伝播される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.exists = AsyncMock(return_value=True)
        service.storage.rename = AsyncMock(side_effect=Exception("Rename error"))

        with pytest.raises(Exception, match="Rename error"):
            await service.save_with_backup({"key": "value"}, "test.json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_with_backup_save_error():
    """
    Given: save_dataがExceptionをraise
    When: save_with_backupを呼び出す
    Then: 例外が伝播される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.exists = AsyncMock(return_value=False)
        service.storage.save = AsyncMock(side_effect=Exception("Save error"))

        with pytest.raises(Exception, match="Save error"):
            await service.save_with_backup({"key": "value"}, "test.json")


# =============================================================================
# 11. setup_http_client メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_http_client_first_time():
    """
    Given: http_client=None
    When: setup_http_clientを呼び出す
    Then: get_http_client()が呼ばれ、http_clientが設定される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        mock_http_client = Mock()

        with patch("nook.common.http_client.get_http_client", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_http_client

            await service.setup_http_client()

            assert service.http_client is mock_http_client
            mock_get.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_http_client_already_set():
    """
    Given: http_client is not None
    When: setup_http_clientを呼び出す
    Then: get_http_client()は呼ばれない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        existing_client = Mock()
        service.http_client = existing_client

        with patch("nook.common.http_client.get_http_client", new_callable=AsyncMock) as mock_get:
            await service.setup_http_client()

            # 既にセットされているので呼ばれない
            mock_get.assert_not_called()
            assert service.http_client is existing_client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_http_client_get_client_error():
    """
    Given: get_http_client()がExceptionをraise
    When: setup_http_clientを呼び出す
    Then: 例外が伝播される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        with patch("nook.common.http_client.get_http_client", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("HTTP client error")

            with pytest.raises(Exception, match="HTTP client error"):
                await service.setup_http_client()


# =============================================================================
# 12. cleanup メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_default_implementation():
    """
    Given: cleanup()
    When: メソッドを呼び出す
    Then: エラーなく完了
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        # デフォルト実装は何もしないので、エラーなく完了
        await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_override():
    """
    Given: カスタムcleanup実装
    When: cleanupを呼び出す
    Then: カスタム処理が実行される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = CustomCleanupService(service_name="test")

        await service.cleanup()

        assert service.cleanup_called is True


# =============================================================================
# 13. initialize メソッドのテスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_initialize_calls_setup_http_client():
    """
    Given: initialize()
    When: メソッドを呼び出す
    Then: setup_http_client()が呼ばれる
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        with patch.object(service, "setup_http_client", new_callable=AsyncMock) as mock_setup:
            await service.initialize()

            mock_setup.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_initialize_setup_error():
    """
    Given: setup_http_client()がExceptionをraise
    When: initializeを呼び出す
    Then: 例外が伝播される
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")

        with patch.object(service, "setup_http_client", new_callable=AsyncMock) as mock_setup:
            mock_setup.side_effect = Exception("Setup error")

            with pytest.raises(Exception, match="Setup error"):
                await service.initialize()


# =============================================================================
# 14. 統合テスト
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_lifecycle():
    """
    Given: 完全なライフサイクル
    When: initialize→collect→save→cleanupを実行
    Then: 全フローが正常に動作
    """
    with patch("nook.common.base_service.setup_logger"):
        service = ConcreteService(service_name="test")
        service.storage.save = AsyncMock(return_value=Path("/data/test/result.json"))

        with patch("nook.common.http_client.get_http_client", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock()

            # 初期化
            await service.initialize()
            assert service.http_client is not None

            # データ収集
            result = await service.collect()
            assert result == [{"title": "Test", "url": "http://example.com"}]

            # 保存
            saved_path = await service.save_data(result, "result.json")
            assert saved_path == Path("/data/test/result.json")

            # クリーンアップ
            await service.cleanup()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multiple_instances():
    """
    Given: 複数BaseServiceインスタンス
    When: 各インスタンスを操作
    Then: 各インスタンスが独立動作
    """
    with patch("nook.common.base_service.setup_logger") as mock_logger:
        # 各呼び出しで異なるloggerを返すようにする
        mock_logger.side_effect = [Mock(name="service1"), Mock(name="service2")]

        service1 = ConcreteService(service_name="service1")
        service2 = ConcreteService(service_name="service2")

        assert service1.service_name == "service1"
        assert service2.service_name == "service2"
        assert service1.storage is not service2.storage
        assert service1.gpt_client is not service2.gpt_client
        assert service1.logger is not service2.logger
