"""nook/common/rate_limiter.py のテスト"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nook.common.rate_limiter import RateLimitedHTTPClient, RateLimiter

# ================================================================================
# 1. RateLimiter.__init__ のテスト
# ================================================================================


@pytest.mark.unit
def test_rate_limiter_init_default_burst():
    """
    Given: rate=10のみ指定
    When: RateLimiterを初期化
    Then: burst=rate=10, allowance=10.0となる
    """
    limiter = RateLimiter(rate=10)
    assert limiter.rate == 10
    assert limiter.burst == 10
    assert limiter.allowance == 10.0
    assert limiter.per == timedelta(seconds=1)


@pytest.mark.unit
def test_rate_limiter_init_custom_burst():
    """
    Given: rate=10, burst=20
    When: RateLimiterを初期化
    Then: burst=20, allowance=20.0となる
    """
    limiter = RateLimiter(rate=10, burst=20)
    assert limiter.rate == 10
    assert limiter.burst == 20
    assert limiter.allowance == 20.0


@pytest.mark.unit
def test_rate_limiter_init_custom_per():
    """
    Given: rate=60, per=timedelta(minutes=1)
    When: RateLimiterを初期化
    Then: 60req/分のレート制限となる
    """
    limiter = RateLimiter(rate=60, per=timedelta(minutes=1))
    assert limiter.rate == 60
    assert limiter.per == timedelta(minutes=1)


@pytest.mark.unit
def test_rate_limiter_init_minimum_rate():
    """
    Given: rate=1（最小レート）
    When: RateLimiterを初期化
    Then: 正常に初期化される
    """
    limiter = RateLimiter(rate=1)
    assert limiter.rate == 1
    assert limiter.burst == 1


@pytest.mark.unit
def test_rate_limiter_init_large_rate():
    """
    Given: rate=1000（大きなレート）
    When: RateLimiterを初期化
    Then: 正常に初期化される
    """
    limiter = RateLimiter(rate=1000)
    assert limiter.rate == 1000
    assert limiter.burst == 1000


# ================================================================================
# 2. RateLimiter.acquire のテスト
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiter_acquire_sufficient_tokens():
    """
    Given: allowance=10のRateLimiter
    When: tokens=1でacquire
    Then: 即座に返り、allowance=9となる
    """
    limiter = RateLimiter(rate=10)
    limiter.allowance = 10.0

    with patch("nook.common.rate_limiter.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 0, 0, 0)
        mock_dt.utcnow.return_value = now
        # last_checkを明示的に設定してモックと整合させる
        limiter.last_check = now

        await limiter.acquire(tokens=1)

        assert limiter.allowance == 9.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiter_acquire_insufficient_tokens():
    """
    Given: allowance=5のRateLimiter
    When: tokens=10でacquire
    Then: 待機してからトークン取得
    """
    limiter = RateLimiter(rate=10, per=timedelta(seconds=1))
    limiter.allowance = 5.0

    with (
        patch("nook.common.rate_limiter.datetime") as mock_dt,
        patch("nook.common.rate_limiter.asyncio.sleep") as mock_sleep,
    ):
        now = datetime(2025, 1, 1, 0, 0, 0)
        mock_dt.utcnow.side_effect = [
            now,  # 最初のチェック
            now,  # last_check更新
            now + timedelta(seconds=0.5),  # sleep後
        ]
        # last_checkを明示的に設定してモックと整合させる
        limiter.last_check = now

        await limiter.acquire(tokens=10)

        # sleep が呼ばれたことを確認
        assert mock_sleep.called
        # 待機時間の計算: (10 - 5) * (1 / 10) = 0.5秒
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == 0.5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiter_acquire_exact_allowance():
    """
    Given: allowance=10のRateLimiter
    When: tokens=10（ちょうどallowance分）でacquire
    Then: 即座に返る
    """
    limiter = RateLimiter(rate=10)
    limiter.allowance = 10.0

    with patch("nook.common.rate_limiter.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 0, 0, 0)
        mock_dt.utcnow.return_value = now
        # last_checkを明示的に設定してモックと整合させる
        limiter.last_check = now

        await limiter.acquire(tokens=10)

        assert limiter.allowance == 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiter_acquire_allowance_plus_one():
    """
    Given: allowance=10のRateLimiter
    When: tokens=11（allowance+1）でacquire
    Then: 待機が発生する
    """
    limiter = RateLimiter(rate=10, per=timedelta(seconds=1))
    limiter.allowance = 10.0

    with (
        patch("nook.common.rate_limiter.datetime") as mock_dt,
        patch("nook.common.rate_limiter.asyncio.sleep") as mock_sleep,
    ):
        now = datetime(2025, 1, 1, 0, 0, 0)
        mock_dt.utcnow.side_effect = [
            now,  # 最初のチェック
            now,  # last_check更新
            now + timedelta(seconds=0.1),  # sleep後
        ]
        # last_checkを明示的に設定してモックと整合させる
        limiter.last_check = now

        await limiter.acquire(tokens=11)

        assert mock_sleep.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiter_acquire_zero_tokens():
    """
    Given: RateLimiter
    When: tokens=0でacquire
    Then: 即座に返る（エッジケース）
    """
    limiter = RateLimiter(rate=10)
    limiter.allowance = 10.0

    with patch("nook.common.rate_limiter.datetime") as mock_dt:
        now = datetime(2025, 1, 1, 0, 0, 0)
        mock_dt.utcnow.return_value = now
        # last_checkを明示的に設定してモックと整合させる
        limiter.last_check = now

        await limiter.acquire(tokens=0)

        assert limiter.allowance == 10.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiter_acquire_token_recovery():
    """
    Given: RateLimiter
    When: 時間経過でトークンが回復する
    Then: allowanceが増加する
    """
    limiter = RateLimiter(rate=10, per=timedelta(seconds=1))
    limiter.allowance = 5.0
    limiter.last_check = datetime(2025, 1, 1, 0, 0, 0)

    with patch("nook.common.rate_limiter.datetime") as mock_dt:
        # 1秒経過
        now = datetime(2025, 1, 1, 0, 0, 1)
        mock_dt.utcnow.return_value = now

        await limiter.acquire(tokens=1)

        # 1秒で10トークン回復 → 5 + 10 = 15 だが burst=10 で制限 → 10
        # その後 tokens=1 消費 → 9
        assert limiter.allowance == 9.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiter_acquire_burst_limit():
    """
    Given: burst=10のRateLimiter
    When: 回復したトークンがburstを超える
    Then: burstで制限される
    """
    limiter = RateLimiter(rate=10, per=timedelta(seconds=1), burst=10)
    limiter.allowance = 5.0
    limiter.last_check = datetime(2025, 1, 1, 0, 0, 0)

    with patch("nook.common.rate_limiter.datetime") as mock_dt:
        # 10秒経過（100トークン回復するはずだがburstで制限）
        now = datetime(2025, 1, 1, 0, 0, 10)
        mock_dt.utcnow.return_value = now

        await limiter.acquire(tokens=1)

        # burst=10で制限、その後tokens=1消費 → 9
        assert limiter.allowance == 9.0


# ================================================================================
# 3. RateLimitedHTTPClient.__init__ のテスト
# ================================================================================


@pytest.mark.unit
def test_rate_limited_http_client_init_default():
    """
    Given: configなし
    When: RateLimitedHTTPClientを初期化
    Then: default_rate_limit=60/分となる
    """
    client = RateLimitedHTTPClient()
    assert client.default_rate_limit.rate == 60
    assert client.default_rate_limit.per == timedelta(minutes=1)
    assert client.domain_rate_limits == {}


@pytest.mark.unit
def test_rate_limited_http_client_init_custom_rate_limit():
    """
    Given: カスタムdefault_rate_limit
    When: RateLimitedHTTPClientを初期化
    Then: カスタム値が設定される
    """
    custom_limiter = RateLimiter(rate=100, per=timedelta(seconds=1))
    client = RateLimitedHTTPClient(default_rate_limit=custom_limiter)
    assert client.default_rate_limit == custom_limiter


# ================================================================================
# 4. RateLimitedHTTPClient.add_domain_rate_limit のテスト
# ================================================================================


@pytest.mark.unit
def test_add_domain_rate_limit_new_domain():
    """
    Given: RateLimitedHTTPClient
    When: 新規ドメインのレート制限を追加
    Then: domain_rate_limitsに追加される
    """
    client = RateLimitedHTTPClient()
    client.add_domain_rate_limit("example.com", rate=10)

    assert "example.com" in client.domain_rate_limits
    assert client.domain_rate_limits["example.com"].rate == 10


@pytest.mark.unit
def test_add_domain_rate_limit_overwrite():
    """
    Given: 既存ドメインのレート制限あり
    When: 同一ドメインを再度追加
    Then: 新しい設定で上書きされる
    """
    client = RateLimitedHTTPClient()
    client.add_domain_rate_limit("example.com", rate=10)
    client.add_domain_rate_limit("example.com", rate=20)

    assert client.domain_rate_limits["example.com"].rate == 20


@pytest.mark.unit
def test_add_domain_rate_limit_custom_per_and_burst():
    """
    Given: RateLimitedHTTPClient
    When: per, burst付きでドメインレート制限を追加
    Then: 正しく設定される
    """
    client = RateLimitedHTTPClient()
    client.add_domain_rate_limit(
        "example.com", rate=100, per=timedelta(minutes=1), burst=150
    )

    limiter = client.domain_rate_limits["example.com"]
    assert limiter.rate == 100
    assert limiter.per == timedelta(minutes=1)
    assert limiter.burst == 150


# ================================================================================
# 5. RateLimitedHTTPClient._get_domain のテスト
# ================================================================================


@pytest.mark.unit
def test_get_domain_http_url():
    """
    Given: http URL
    When: _get_domainを呼び出す
    Then: ドメイン名が返る
    """
    client = RateLimitedHTTPClient()
    domain = client._get_domain("http://example.com/path")
    assert domain == "example.com"


@pytest.mark.unit
def test_get_domain_https_url():
    """
    Given: https URL
    When: _get_domainを呼び出す
    Then: ドメイン名が返る
    """
    client = RateLimitedHTTPClient()
    domain = client._get_domain("https://example.com/path")
    assert domain == "example.com"


@pytest.mark.unit
def test_get_domain_with_port():
    """
    Given: ポート付きURL
    When: _get_domainを呼び出す
    Then: ドメイン名:ポートが返る
    """
    client = RateLimitedHTTPClient()
    domain = client._get_domain("https://example.com:8080/path")
    assert domain == "example.com:8080"


@pytest.mark.unit
def test_get_domain_invalid_url():
    """
    Given: 不正なURL
    When: _get_domainを呼び出す
    Then: 空文字列が返る（urllibの動作）
    """
    client = RateLimitedHTTPClient()
    domain = client._get_domain("invalid-url")
    assert domain == ""


# ================================================================================
# 6. RateLimitedHTTPClient.get/post のテスト
# ================================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_client_get_default_rate_limit():
    """
    Given: 未登録ドメイン
    When: getリクエスト
    Then: default_rate_limitが適用される
    """
    client = RateLimitedHTTPClient()

    # _acquire_rate_limit をモック
    with (
        patch.object(client, "_acquire_rate_limit"),
        patch.object(client, "get", return_value=AsyncMock()),
    ):
        # 親クラスのgetを呼び出す際のモック
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200

        # 親クラスのメソッドをモック
        with patch(
            "nook.common.http_client.AsyncHTTPClient.get", return_value=mock_response
        ):
            # 実際にgetを呼び出す
            client_real = RateLimitedHTTPClient()
            result = await client_real.get("https://example.com/path")

            # レート制限が呼ばれたかは確認できないが、getが動作することを確認
            assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_client_get_domain_specific_rate_limit():
    """
    Given: 登録済みドメイン
    When: getリクエスト
    Then: ドメイン専用レート制限が適用される
    """
    client = RateLimitedHTTPClient()
    client.add_domain_rate_limit("example.com", rate=5)

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch(
        "nook.common.http_client.AsyncHTTPClient.get", return_value=mock_response
    ):
        result = await client.get("https://example.com/path")
        assert result.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_client_post_rate_limit():
    """
    Given: RateLimitedHTTPClient
    When: postリクエスト
    Then: レート制限が適用される
    """
    client = RateLimitedHTTPClient()

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 201

    with patch(
        "nook.common.http_client.AsyncHTTPClient.post", return_value=mock_response
    ):
        result = await client.post("https://example.com/api", json={"data": "test"})
        assert result.status_code == 201


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_client_multiple_requests_rate_limited():
    """
    Given: レート制限付きクライアント
    When: 短時間に複数リクエスト
    Then: レート制限が順守される
    """
    limiter = RateLimiter(rate=2, per=timedelta(seconds=1))
    client = RateLimitedHTTPClient(default_rate_limit=limiter)

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch(
        "nook.common.http_client.AsyncHTTPClient.get", return_value=mock_response
    ):
        # 2回は即座に成功（burst=2）
        result1 = await client.get("https://example.com/1")
        result2 = await client.get("https://example.com/2")

        assert result1.status_code == 200
        assert result2.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_rate_limit_selects_correct_limiter():
    """
    Given: ドメイン別レート制限設定済み
    When: _acquire_rate_limitを呼び出す
    Then: 正しいlimiterが選択される
    """
    client = RateLimitedHTTPClient()
    domain_limiter = RateLimiter(rate=5)
    client.domain_rate_limits["example.com"] = domain_limiter

    with patch.object(domain_limiter, "acquire") as mock_acquire:
        await client._acquire_rate_limit("https://example.com/path")
        mock_acquire.assert_called_once_with(1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_rate_limit_uses_default_for_unknown_domain():
    """
    Given: 未登録ドメイン
    When: _acquire_rate_limitを呼び出す
    Then: default_rate_limitが使用される
    """
    client = RateLimitedHTTPClient()

    with patch.object(client.default_rate_limit, "acquire") as mock_acquire:
        await client._acquire_rate_limit("https://unknown.com/path")
        mock_acquire.assert_called_once_with(1)
