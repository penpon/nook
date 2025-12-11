import asyncio
import json
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from nook.services.base.base_service import BaseService
from nook.core.config import BaseConfig


@pytest.fixture(autouse=True)
def _set_env(monkeypatch) -> None:
    """必須環境変数をテスト用ダミーで埋める"""
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")


class DummyConfig(BaseConfig):
    """テスト用の設定（必須キーをデフォルトで埋める）"""

    OPENAI_API_KEY: SecretStr = SecretStr("dummy-key")


class DummyService(BaseService):
    """テスト用のBaseServiceサブクラス。

    Args:
        request_delay: リクエスト間の待機秒数。
        config: 設定オブジェクト（未指定時はDummyConfig）。
    """

    def __init__(self, request_delay: float = 0.05, config: BaseConfig | None = None):
        super().__init__("dummy", config=config or DummyConfig())
        self.request_delay = request_delay

    async def collect(self):
        """データ収集処理（テスト用ダミーで何もしない）。

        Returns:
            None
        """
        return None


@pytest.mark.asyncio
async def test_save_data_uses_storage(monkeypatch, tmp_path: Path):
    # Given
    service = DummyService()
    calls: dict[str, object] = {}

    async def fake_save(data, filename):
        calls["data"] = data
        calls["filename"] = filename
        return tmp_path / filename

    service.storage = types.SimpleNamespace(save=fake_save)

    # When
    path = await service.save_data({"x": 1}, "foo.json")

    # Then
    assert path == tmp_path / "foo.json"
    assert calls == {"data": {"x": 1}, "filename": "foo.json"}


@pytest.mark.asyncio
async def test_rate_limit_uses_request_delay(monkeypatch):
    # Given
    service = DummyService(request_delay=0.2)

    recorded: dict[str, float] = {}

    async def fake_sleep(delay):
        recorded["delay"] = delay

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    # When
    await service.rate_limit()

    # Then
    assert recorded["delay"] == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_setup_http_client_called_once(monkeypatch):
    # Given
    service = DummyService()
    sentinel_client = object()
    calls = {"count": 0}

    async def fake_get_http_client():
        calls["count"] += 1
        return sentinel_client

    monkeypatch.setattr("nook.core.clients.http_client.get_http_client", fake_get_http_client)

    # When
    await service.setup_http_client()
    first_client = service.http_client

    # 再呼び出しでも新規取得しない
    await service.setup_http_client()

    # Then
    assert first_client is sentinel_client
    assert service.http_client is sentinel_client
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_initialize_calls_setup_http_client(monkeypatch):
    # Given
    service = DummyService()
    sentinel_client = object()
    calls = {"count": 0}

    async def fake_setup():
        calls["count"] += 1
        service.http_client = sentinel_client

    monkeypatch.setattr(service, "setup_http_client", fake_setup)

    # When
    await service.initialize()

    # Then
    assert calls["count"] == 1
    assert service.http_client is sentinel_client


@pytest.mark.asyncio
async def test_save_data_logs_and_raises_on_error(monkeypatch, caplog):
    # Given
    service = DummyService()
    calls: dict[str, object] = {}

    async def failing_save(data, filename):
        calls["data"] = data
        calls["filename"] = filename
        raise ValueError("boom")

    service.storage = types.SimpleNamespace(save=failing_save)
    caplog.set_level("ERROR")

    # When / Then
    with pytest.raises(ValueError):
        await service.save_data({"x": 1}, "foo.json")

    # Then
    assert calls == {"data": {"x": 1}, "filename": "foo.json"}
    assert "Failed to save data foo.json: boom" in caplog.text


@pytest.mark.asyncio
async def test_save_markdown_calls_save_data(monkeypatch, tmp_path: Path):
    """save_markdownがsave_dataを呼び出すテスト"""
    service = DummyService()
    calls: dict[str, object] = {}

    async def fake_save(data, filename):
        calls["data"] = data
        calls["filename"] = filename
        return tmp_path / filename

    service.storage = types.SimpleNamespace(save=fake_save)

    # When
    path = await service.save_markdown("# Test Content", "test.md")

    # Then
    assert path == tmp_path / "test.md"
    assert calls == {"data": "# Test Content", "filename": "test.md"}


@pytest.mark.asyncio
async def test_save_json_calls_storage_save(monkeypatch, tmp_path: Path):
    """save_jsonがstorage.saveを呼び出すテスト"""
    service = DummyService()
    calls: dict[str, object] = {}

    async def fake_save(data, filename):
        calls["data"] = data
        calls["filename"] = filename
        return tmp_path / filename

    service.storage = types.SimpleNamespace(save=fake_save)
    test_data = {"key": "value", "number": 123}

    # When
    path = await service.save_json(test_data, "test.json")

    # Then
    assert path == tmp_path / "test.json"
    assert calls["data"] == test_data
    assert calls["filename"] == "test.json"


@pytest.mark.asyncio
async def test_load_json_returns_parsed_data(monkeypatch):
    """load_jsonがJSONデータを解析して返すテスト"""
    service = DummyService()
    test_data = {"key": "value", "number": 123}

    async def fake_load(filename):
        return json.dumps(test_data)

    service.storage = types.SimpleNamespace(load=fake_load)

    # When
    result = await service.load_json("test.json")

    # Then
    assert result == test_data


@pytest.mark.asyncio
async def test_load_json_returns_none_for_empty_content(monkeypatch):
    """load_jsonが空コンテンツでNoneを返すテスト"""
    service = DummyService()

    async def fake_load(filename):
        return ""

    service.storage = types.SimpleNamespace(load=fake_load)

    # When
    result = await service.load_json("test.json")

    # Then
    assert result is None


@pytest.mark.asyncio
async def test_load_json_returns_none_for_null_content(monkeypatch):
    """load_jsonがnullコンテンツでNoneを返すテスト"""
    service = DummyService()

    async def fake_load(filename):
        return None

    service.storage = types.SimpleNamespace(load=fake_load)

    # When
    result = await service.load_json("test.json")

    # Then
    assert result is None


@pytest.mark.asyncio
async def test_save_with_backup_creates_backups(monkeypatch, tmp_path: Path):
    """save_with_backupがバックアップを作成するテスト"""
    service = DummyService()
    calls = []

    async def fake_exists(filename):
        return filename == "test.json"  # 既存ファイルがあると仮定

    async def fake_rename(old, new):
        calls.append(("rename", old, new))

    async def fake_save(data, filename):
        calls.append(("save", data, filename))
        return tmp_path / filename

    service.storage = types.SimpleNamespace(
        exists=fake_exists, rename=fake_rename, save=fake_save
    )

    # When
    await service.save_with_backup({"new": "data"}, "test.json", keep_backups=3)

    # Then
    # バックアップ作成と新規保存が行われる
    assert ("rename", "test.json", "test.json.1") in calls
    assert ("save", {"new": "data"}, "test.json") in calls


@pytest.mark.asyncio
async def test_save_with_backup_multiple_backups(monkeypatch, tmp_path: Path):
    """save_with_backupが複数バックアップを作成するテスト"""
    service = DummyService()
    calls = []

    async def fake_exists(filename):
        # 既存のバックアップファイルがあると仮定
        return filename in ["test.json", "test.json.1", "test.json.2"]

    async def fake_rename(old, new):
        calls.append(("rename", old, new))

    async def fake_save(data, filename):
        calls.append(("save", data, filename))
        return tmp_path / filename

    service.storage = types.SimpleNamespace(
        exists=fake_exists, rename=fake_rename, save=fake_save
    )

    # When
    await service.save_with_backup({"new": "data"}, "test.json", keep_backups=3)

    # Then
    # バックアップのローテーションが行われる
    assert ("rename", "test.json.2", "test.json.3") in calls
    assert ("rename", "test.json.1", "test.json.2") in calls
    assert ("rename", "test.json", "test.json.1") in calls
    assert ("save", {"new": "data"}, "test.json") in calls


@pytest.mark.asyncio
async def test_save_with_backup_no_existing_file(monkeypatch, tmp_path: Path):
    """既存ファイルがない場合のsave_with_backupテスト"""
    service = DummyService()
    calls = []

    async def fake_exists(filename):
        return False  # 既存ファイルなし

    async def fake_save(data, filename):
        calls.append(("save", data, filename))
        return tmp_path / filename

    service.storage = types.SimpleNamespace(exists=fake_exists, save=fake_save)

    # When
    await service.save_with_backup({"new": "data"}, "test.json")

    # Then
    # バックアップ作成なしで新規保存のみ
    assert len(calls) == 1
    assert calls[0] == ("save", {"new": "data"}, "test.json")


def test_get_config_path_returns_correct_path():
    """get_config_pathが正しいパスを返すテスト"""
    service = DummyService()

    # When
    path = service.get_config_path("config.json")

    # Then
    expected = Path("nook/services/dummy/config.json")
    assert path == expected


def test_get_config_path_with_different_service_name():
    """異なるサービス名でのget_config_pathテスト"""

    class OtherService(BaseService):
        async def collect(self):
            pass

    service = OtherService("other_service")

    # When
    path = service.get_config_path("settings.yaml")

    # Then
    expected = Path("nook/services/other_service/settings.yaml")
    assert path == expected


@pytest.mark.asyncio
async def test_setup_http_client_logs_debug_message(monkeypatch, caplog):
    """HTTPクライアントセットアップ時のデバッグログテスト"""
    service = DummyService()

    async def fake_get_http_client():
        return MagicMock()

    monkeypatch.setattr("nook.core.clients.http_client.get_http_client", fake_get_http_client)
    caplog.set_level("DEBUG", logger="dummy")

    # When
    await service.setup_http_client()

    # Then
    debug_records = [
        record
        for record in caplog.records
        if record.levelname == "DEBUG"
        and "HTTP client setup completed" in record.message
    ]
    assert len(debug_records) == 1


@pytest.mark.asyncio
async def test_cleanup_default_implementation():
    """cleanupのデフォルト実装テスト"""
    service = DummyService()

    # デフォルト実装は何もしないはず
    result = await service.cleanup()
    assert result is None


@pytest.mark.asyncio
async def test_cleanup_can_be_overridden():
    """cleanupがオーバーライド可能であることのテスト"""
    cleanup_called = False

    class CustomService(DummyService):
        async def cleanup(self):
            nonlocal cleanup_called
            cleanup_called = True
            await super().cleanup()

    service = CustomService()

    # When
    await service.cleanup()

    # Then
    assert cleanup_called is True


@pytest.mark.asyncio
async def test_initialize_can_be_overridden():
    """initializeがオーバーライド可能であることのテスト"""
    custom_init_called = False

    class CustomService(DummyService):
        async def initialize(self):
            nonlocal custom_init_called
            custom_init_called = True
            await super().initialize()

    service = CustomService()

    # When
    await service.initialize()

    # Then
    assert custom_init_called is True


def test_base_service_initialization_with_custom_config():
    """カスタム設定でのBaseService初期化テスト"""
    custom_config = DummyConfig()
    service = DummyService(config=custom_config)

    assert service.config is custom_config
    assert service.service_name == "dummy"
    assert service.storage is not None
    assert service.gpt_client is not None
    assert service.logger is not None
    assert service.http_client is None


def test_base_service_initialization_with_default_config():
    """デフォルト設定でのBaseService初期化テスト"""
    service = DummyService(config=None)

    assert service.config is not None
    assert isinstance(service.config, BaseConfig)
    assert service.service_name == "dummy"


def test_base_service_is_abstract():
    """BaseServiceが抽象クラスであることのテスト"""
    with pytest.raises(TypeError):
        # 抽象メソッドを実装していないのでエラー
        BaseService("test")


@pytest.mark.asyncio
async def test_fetch_with_retry_is_placeholder():
    """fetch_with_retryがプレースホルダーであることのテスト"""
    service = DummyService()

    # 現在の実装ではpassを返す
    result = await service.fetch_with_retry("http://example.com")
    assert result == ""
