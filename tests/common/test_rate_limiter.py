from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nook.common.config import BaseConfig
from nook.common.rate_limiter import RateLimitedHTTPClient, RateLimiter

# --- RateLimiter Tests ---


@pytest.mark.asyncio
async def test_rate_limiter_init():
    rl = RateLimiter(rate=10, per=timedelta(seconds=1))
    assert rl.rate == 10
    assert rl.per == timedelta(seconds=1)
    assert rl.burst == 10
    assert rl.allowance == 10.0

    rl2 = RateLimiter(rate=10, burst=20)
    assert rl2.burst == 20
    assert rl2.allowance == 20.0


@pytest.mark.asyncio
async def test_acquire_no_wait():
    rl = RateLimiter(rate=10, per=timedelta(seconds=1))
    # Initially full (10)
    await rl.acquire(1)
    assert rl.allowance == 9.0


@pytest.mark.asyncio
async def test_acquire_wait():
    rl = RateLimiter(rate=1, per=timedelta(seconds=1))
    rl.allowance = 0.0  # Force wait

    with patch("nook.common.rate_limiter.asyncio.sleep") as mock_sleep:
        # Need 1 token, rate is 1/sec. Deficit 1. Wait should be 1 sec.
        await rl.acquire(1)

        mock_sleep.assert_called_once()
        args, _ = mock_sleep.call_args
        wait_time = args[0]
        assert 0.99 <= wait_time <= 1.01


@pytest.mark.asyncio
async def test_acquire_wait_burst_cap_after_wait():
    """Test that burst cap is applied after waiting when allowance recovery exceeds burst."""
    # We need to mock datetime.now to simulate time passing during the wait
    # The acquire method calls datetime.now multiple times:
    # 1. At __init__ (line 26) to set last_check
    # 2. Initial check in acquire (line 32)
    # 3. After sleep (line 54) - this is where elapsed time matters for line 59
    base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    call_count = [0]

    def mock_now(tz=None):
        call_count[0] += 1
        if call_count[0] <= 2:
            # First two calls: __init__ and initial check in acquire
            return base_time
        else:
            # Third call: after sleep - simulate 1 second elapsed
            # This will cause recovery of 100 tokens (100 rate * 1 sec),
            # which exceeds burst of 10, triggering line 59
            return base_time + timedelta(seconds=1)

    with (
        patch("nook.common.rate_limiter.asyncio.sleep") as mock_sleep,
        patch("nook.common.rate_limiter.datetime") as mock_datetime,
    ):
        mock_datetime.now = mock_now
        # Allow timedelta to work (used in RateLimiter constructor default)
        mock_datetime.timedelta = timedelta

        # Create rate limiter with high rate (100 tokens/sec, burst=10)
        rl = RateLimiter(rate=100, per=timedelta(seconds=1), burst=10)
        rl.allowance = 0.0  # Force wait since we need 1 token

        await rl.acquire(1)

        mock_sleep.assert_called_once()
        # After recovery of 100 tokens (100 rate * 1 second), should be capped at burst (10)
        # Then 1 token consumed, so allowance should be 9
        assert rl.allowance == 9.0


@pytest.mark.asyncio
async def test_burst_cap():
    rl = RateLimiter(rate=10, burst=10, per=timedelta(seconds=1))
    rl.allowance = 0.0
    rl.last_check = datetime.now(UTC) - timedelta(seconds=100)  # Long time ago

    await rl.acquire(0)  # Just trigger update
    assert rl.allowance == 10.0  # Should be capped at burst


# --- RateLimitedHTTPClient Tests ---


@pytest.fixture
def mock_config():
    config = MagicMock(spec=BaseConfig)
    config.REQUEST_TIMEOUT = 30.0
    return config


@pytest.mark.asyncio
async def test_client_init(mock_config):
    client = RateLimitedHTTPClient(config=mock_config)
    assert client.default_rate_limit is not None
    assert client.default_rate_limit.rate == 60


@pytest.mark.asyncio
async def test_add_domain_rate_limit(mock_config):
    client = RateLimitedHTTPClient(config=mock_config)
    client.add_domain_rate_limit("example.com", rate=5)
    assert "example.com" in client.domain_rate_limits
    assert client.domain_rate_limits["example.com"].rate == 5


@pytest.mark.asyncio
async def test_get_domain(mock_config):
    client = RateLimitedHTTPClient(config=mock_config)
    assert client._get_domain("https://example.com/api/v1") == "example.com"
    assert client._get_domain("http://sub.test.org") == "sub.test.org"


@pytest.mark.asyncio
async def test_acquire_rate_limit_selection(mock_config):
    client = RateLimitedHTTPClient(config=mock_config)
    default_rl = MagicMock(spec=RateLimiter)
    default_rl.acquire = AsyncMock(return_value=None)
    client.default_rate_limit = default_rl

    specific_rl = MagicMock(spec=RateLimiter)
    specific_rl.acquire = AsyncMock(return_value=None)
    client.domain_rate_limits["special.com"] = specific_rl

    # Case 1: Use specific
    await client._acquire_rate_limit("https://special.com/foo")
    specific_rl.acquire.assert_called_once()
    default_rl.acquire.assert_not_called()

    # Case 2: Use default
    specific_rl.acquire.reset_mock()
    await client._acquire_rate_limit("https://other.com/bar")
    default_rl.acquire.assert_called_once()
    specific_rl.acquire.assert_not_called()


@pytest.mark.asyncio
async def test_get_method(mock_config):
    client = RateLimitedHTTPClient(config=mock_config)
    client._acquire_rate_limit = AsyncMock(return_value=None)

    with patch(
        "nook.common.http_client.AsyncHTTPClient.get", new_callable=AsyncMock
    ) as mock_super_get:
        mock_super_get.return_value = "response"

        resp = await client.get("https://example.com")

        client._acquire_rate_limit.assert_called_with("https://example.com")
        mock_super_get.assert_called_with("https://example.com")
        assert resp == "response"


@pytest.mark.asyncio
async def test_post_method(mock_config):
    client = RateLimitedHTTPClient(config=mock_config)
    client._acquire_rate_limit = AsyncMock(return_value=None)

    with patch(
        "nook.common.http_client.AsyncHTTPClient.post", new_callable=AsyncMock
    ) as mock_super_post:
        mock_super_post.return_value = "response"

        resp = await client.post("https://example.com", json={"a": 1})

        client._acquire_rate_limit.assert_called_with("https://example.com")
        mock_super_post.assert_called_with("https://example.com", json={"a": 1})
        assert resp == "response"
