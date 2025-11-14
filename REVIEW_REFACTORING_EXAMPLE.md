# テストコードのリファクタリング例

## Before（現状）

```python
@pytest.mark.unit
def test_init_with_default_storage_dir(mock_env_vars):
    """
    Given: デフォルトのstorage_dir
    When: FiveChanExplorerを初期化
    Then: インスタンスが正常に作成される
    """
    with patch("nook.common.logging.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        assert service.service_name == "fivechan_explorer"
```

**問題点:**
- 重複したモック設定
- インポートの繰り返し
- 保守性の低さ

---

## After（改善後）

```python
@pytest.mark.unit
def test_init_with_default_storage_dir(fivechan_service):
    """
    Given: デフォルトのstorage_dir
    When: FiveChanExplorerを初期化
    Then: インスタンスが正常に作成される
    """
    assert fivechan_service.service_name == "fivechan_explorer"
```

**改善点:**
- フィクスチャで共通処理を集約
- テストコードが簡潔に
- 保守性向上

---

## より複雑なテストのリファクタリング

### Before

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_success(mock_env_vars):
    """..."""
    with patch("nook.common.logging.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # Shift_JISエンコードのsubject.txtデータ
        subject_data = "1234567890.dat<>AI・人工知能について語るスレ (100)\n9876543210.dat<>機械学習の最新動向 (50)\n".encode("shift_jis")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = subject_data

        with patch("httpx.AsyncClient") as mock_client:
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.__aexit__.return_value = AsyncMock()
            client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = client_instance

            result = await service._get_subject_txt_data("ai")

            assert len(result) == 2
            assert result[0]["title"] == "AI・人工知能について語るスレ"
```

### After

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subject_txt_data_success(
    fivechan_service,
    mock_shift_jis_subject_data,
    mock_httpx_response
):
    """..."""
    response = mock_httpx_response(status_code=200, content=mock_shift_jis_subject_data)

    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        client_instance.get = AsyncMock(return_value=response)
        mock_client.return_value = client_instance

        result = await fivechan_service._get_subject_txt_data("ai")

        assert len(result) == 2
        assert result[0]["title"] == "AI・人工知能について語るスレ"
```

**改善点:**
- フィクスチャでテストデータを共有
- モックレスポンスの生成を簡略化
- テストの意図が明確に

---

## パラメータ化テストの活用

### Before（複数の同様なテスト）

```python
@pytest.mark.unit
def test_calculate_backoff_delay(mock_env_vars):
    with patch("nook.common.logging.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer
        service = FiveChanExplorer()

        assert service._calculate_backoff_delay(0) == 1
        assert service._calculate_backoff_delay(1) == 2
        assert service._calculate_backoff_delay(2) == 4
        assert service._calculate_backoff_delay(8) == 256
```

### After（パラメータ化）

```python
@pytest.mark.unit
@pytest.mark.parametrize("retry_count,expected_delay", [
    (0, 1),    # 2^0 = 1
    (1, 2),    # 2^1 = 2
    (2, 4),    # 2^2 = 4
    (3, 8),    # 2^3 = 8
    (8, 256),  # 2^8 = 256
])
def test_calculate_backoff_delay(fivechan_service, retry_count, expected_delay):
    """
    Given: リトライ回数
    When: _calculate_backoff_delayを呼び出す
    Then: 指数バックオフの遅延時間が正しく計算される
    """
    assert fivechan_service._calculate_backoff_delay(retry_count) == expected_delay
```

**改善点:**
- テストケースの追加が容易
- 各ケースが明確に
- コード量削減

---

## エラーケーステストの改善

### Before

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_thread_posts_from_dat_http_error(mock_env_vars):
    """..."""
    with patch("nook.common.logging.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_scraper = Mock()
        mock_scraper.get = Mock(return_value=mock_response)
        mock_scraper.headers = {}

        with patch("cloudscraper.create_scraper", return_value=mock_scraper), \
             patch("asyncio.to_thread", side_effect=lambda f, *args: f(*args)):

            posts, latest = await service._get_thread_posts_from_dat("http://test.dat")

            assert posts == []
            assert latest is None
```

### After

```python
@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("status_code,expected_posts,expected_latest", [
    (404, [], None),  # Not Found
    (500, [], None),  # Internal Server Error
    (503, [], None),  # Service Unavailable
])
async def test_get_thread_posts_from_dat_http_errors(
    fivechan_service,
    mock_cloudscraper,
    status_code,
    expected_posts,
    expected_latest
):
    """
    Given: HTTPエラーレスポンス
    When: _get_thread_posts_from_datを呼び出す
    Then: 空配列とNoneを返す
    """
    response = Mock(status_code=status_code, text=f"Error {status_code}")
    scraper = mock_cloudscraper(response=response)

    with patch("cloudscraper.create_scraper", return_value=scraper), \
         patch("asyncio.to_thread", side_effect=lambda f, *args: f(*args)):

        posts, latest = await fivechan_service._get_thread_posts_from_dat("http://test.dat")

        assert posts == expected_posts
        assert latest == expected_latest
```

**改善点:**
- 複数のHTTPエラーケースを1つのテストでカバー
- テストケースの追加が容易
- 重複コード削減

---

## アサーションの改善

### Before（弱いアサーション）

```python
assert len(result) == 2
```

### After（具体的なアサーション）

```python
assert len(result) == 2, f"Expected 2 threads, got {len(result)}"
assert result[0]["title"] == "AI・人工知能について語るスレ"
assert result[0]["post_count"] == 100
assert result[0]["board"] == "ai"
assert "dat_url" in result[0]
assert "html_url" in result[0]
```

---

## 非同期テストの改善

### Before（複雑なモック設定）

```python
with patch("asyncio.sleep", new_callable=AsyncMock):
    with patch.object(service, "_get_subject_txt_data", new_callable=AsyncMock, return_value=subject_data):
        # テストロジック
```

### After（pytest-asyncioの活用）

```python
@pytest.fixture
async def mock_async_sleep():
    """asyncio.sleepのモック"""
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        yield mock_sleep

@pytest.mark.asyncio
async def test_with_sleep(fivechan_service, mock_async_sleep):
    """..."""
    # テストロジック
    mock_async_sleep.assert_called()  # sleep が呼ばれたことを確認
```

---

## まとめ

### リファクタリングの利点

1. **保守性向上**: 共通ロジックの変更が1箇所で済む
2. **可読性向上**: テストの意図が明確に
3. **テスト追加の容易さ**: パラメータ化により新ケースの追加が簡単
4. **DRY原則**: 重複コードの削減
5. **実行速度**: フィクスチャの再利用により高速化

### 推奨される次のステップ

1. 既存テストのフィクスチャへの移行
2. パラメータ化テストの導入
3. アサーションの強化
4. テストカバレッジの継続的監視
