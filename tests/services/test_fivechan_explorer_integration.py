"""nook/services/fivechan_explorer/fivechan_explorer.py の統合テスト (セキュリティ観点)

テスト観点:
- XSS攻撃シミュレーション (悪意あるスクリプト含むレスポンス)
- DoS対策 (大量リクエスト制限)
- データサニタイゼーション検証
"""

from __future__ import annotations

import time
import tracemalloc
from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest

# =============================================================================
# テスト用定数
# =============================================================================
MAX_RESPONSE_SIZE_MB = 10
MAX_RESPONSE_SIZE_BYTES = MAX_RESPONSE_SIZE_MB * 1024 * 1024
MAX_PROCESSING_TIME_SECONDS = 60.0
MAX_MEMORY_USAGE_MB = 100
MAX_MEMORY_USAGE_BYTES = MAX_MEMORY_USAGE_MB * 1024 * 1024


# =============================================================================
# セキュリティ統合テスト
# =============================================================================


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.asyncio
async def test_xss_prevention_fivechan_explorer(mock_env_vars):
    """Given: <script>タグを含む悪意のあるスレッドタイトルとコンテンツ
    When: collect()メソッドでデータ取得→GPT要約→Storage保存の全体フローを実行
    Then: XSS攻撃が適切に処理され、データが安全に保存される

    検証項目:
    - 悪意のあるスクリプトタグを含むデータでもエラーにならない
    - データ構造が正しく保たれる
    - Storage保存が成功する
    - GPT要約が実行される

    注: XSS対策は表示層で行う設計のため、ここでは元データが安全に保存されることを検証
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # テストデータ: XSSペイロードを含むスレッドタイトル
        malicious_subject = "1234567890.dat<><script>alert('XSS')</script>悪意のあるスレ (100)\n"
        subject_data = malicious_subject.encode("shift_jis", errors="ignore")

        # テストデータ: XSSペイロードを含むスレッド本文
        malicious_dat = "<script>alert('XSS')</script><>sage<>2024/11/14<>悪意のある投稿<>\n"
        dat_data = malicious_dat.encode("shift_jis", errors="ignore")

        # モックレスポンス設定
        subject_response = Mock()
        subject_response.status_code = 200
        subject_response.content = subject_data

        dat_response = Mock()
        dat_response.status_code = 200
        dat_response.content = dat_data

        scraper_mock = Mock()
        scraper_mock.get = Mock(return_value=dat_response)
        scraper_mock.headers = {}

        # _get_thread_posts_from_datのモック設定
        # XSSペイロードを含む投稿データを返す
        async def mock_get_thread_posts(dat_url):
            posts = [
                {
                    "no": 1,
                    "name": "<script>alert('XSS')</script>",
                    "mail": "sage",
                    "date": "2024/11/14",
                    "com": "<script>alert('XSS')</script>悪意のある投稿",
                    "time": "2024/11/14",
                    "title": "<script>alert('XSS')</script>悪意のあるスレ",
                }
            ]
            return (posts, None)

        with (
            patch(
                "nook.services.fivechan_explorer.fivechan_explorer.httpx.AsyncClient"
            ) as mock_client,
            patch("cloudscraper.create_scraper", return_value=scraper_mock),
            patch(
                "asyncio.to_thread",
                side_effect=lambda f, *args, **kwargs: f(*args, **kwargs),
            ),
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service, "_store_summaries", return_value=[("test.json", "test.md")]),
            patch.object(service, "_get_thread_posts_from_dat", side_effect=mock_get_thread_posts),
        ):
            # HTTPクライアントのモック設定 (_get_subject_txt_data用)
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.__aexit__.return_value = AsyncMock()
            client_instance.get = AsyncMock(return_value=subject_response)
            mock_client.return_value = client_instance
            service.http_client = client_instance

            # GPTClientのモック (既存のテストと同じ方法)
            service.gpt_client.generate_content = Mock(return_value="安全な要約テキスト")

            # collect()実行
            result = await service.collect(target_dates=[date.today()])

            # 検証
            assert result is not None, "collect()の結果がNoneでないこと"
            assert isinstance(result, list), "結果がlistオブジェクトであること"

            # 悪意あるデータでも GPT 要約が実行されていることを確認
            service.gpt_client.generate_content.assert_called()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.asyncio
async def test_dos_protection_fivechan_explorer(mock_env_vars):
    """Given: 10MBの巨大なレスポンス（DoS攻撃シミュレーション）
    When: collect()メソッドでデータ取得を実行
    Then: メモリオーバーフローせずに処理または適切に拒否される

    検証項目:
    - 10MB以上のレスポンスを安全に処理
    - メモリ使用量が閾値以下 (100MB以下)
    - 処理時間が許容範囲内 (60秒以下)
    - クラッシュしない
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # テストデータ: 10MBの巨大なレスポンス (有効なsubject.txt形式)
        # subject.txt形式: "timestamp.dat<>title (count)\n"
        single_thread_entry = b"1234567890.dat<>" + b"A" * 200 + b" (100)\n"
        num_entries = MAX_RESPONSE_SIZE_BYTES // len(single_thread_entry)
        huge_response_data = single_thread_entry * num_entries

        # モックレスポンス設定
        subject_response = Mock()
        subject_response.status_code = 200
        subject_response.content = huge_response_data

        # _get_thread_posts_from_datのモック設定
        # DoSテストでは空のリストを返す（大量のHTTPリクエストを避けるため）
        async def mock_get_thread_posts_dos(dat_url):
            return ([], None)

        with (
            patch(
                "nook.services.fivechan_explorer.fivechan_explorer.httpx.AsyncClient"
            ) as mock_client,
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(
                service, "_get_thread_posts_from_dat", side_effect=mock_get_thread_posts_dos
            ),
            patch.object(service, "_store_summaries", return_value=[]),
        ):
            # HTTPクライアントのモック設定
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.__aexit__.return_value = AsyncMock()
            client_instance.get = AsyncMock(return_value=subject_response)
            mock_client.return_value = client_instance
            service.http_client = client_instance

            # GPTClientのモック (既存のテストと同じ方法)
            service.gpt_client.generate_content = Mock(return_value="要約")

            # メモリと時間を計測
            tracemalloc.start()
            start_time = time.time()

            try:
                # collect()実行 (大量データでもクラッシュしないこと)
                result = await service.collect(target_dates=[date.today()])
                processing_time = time.time() - start_time
                current, peak = tracemalloc.get_traced_memory()

                # 処理が完了することを確認
                # 注: 大量データの場合、空のリストを返すことがある
                # ここでは「クラッシュしない」ことが重要
                assert isinstance(result, list), "処理が完了しlistを返すこと"

                # 処理時間が許容範囲内 (大量データ処理のため緩く設定: 60秒)
                # 注: DoS攻撃シミュレーションのため、実際には長時間かかる
                assert processing_time < MAX_PROCESSING_TIME_SECONDS, (
                    f"処理時間が長すぎる: {processing_time}秒"
                )

                # メモリ使用量が許容範囲内 (100MB以下に緩和)
                memory_mb = peak / 1024 / 1024
                assert memory_mb < MAX_MEMORY_USAGE_MB, f"メモリ使用量が多すぎる: {memory_mb}MB"
            finally:
                tracemalloc.stop()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.asyncio
async def test_data_sanitization_fivechan_explorer(mock_env_vars):
    """Given: HTMLエスケープが必要な文字 (<, >, &, ", ') を含むデータ
    When: collect()メソッドでデータ取得→GPT要約→Storage保存の全体フローを実行
    Then: データが適切に保存され、構造が保たれる

    検証項目:
    - HTMLエスケープが必要な文字を含むデータが処理される
    - データ構造が正しく保たれる
    - Storage保存が成功する
    - GPT要約が実行される

    注: データ収集層では元データを保持し、サニタイゼーションは表示層で行う設計のため、
        ここでは元データが安全に保存されることを検証
    """
    with patch("nook.common.base_service.setup_logger"):
        from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

        service = FiveChanExplorer()

        # テストデータ: HTMLエスケープが必要な文字を含むスレッドタイトル
        html_special_chars_subject = (
            '1234567890.dat<>テスト&lt;script&gt;alert("XSS")&lt;/script&gt;スレ (50)\n'
        )
        subject_data = html_special_chars_subject.encode("shift_jis", errors="ignore")

        # テストデータ: HTMLエスケープが必要な文字を含むスレッド本文
        html_special_chars_dat = (
            "名無しさん<>sage<>2024/11/14<>"
            "テスト😀&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;🎉<>\n"
        )
        dat_data = html_special_chars_dat.encode("shift_jis", errors="ignore")

        # モックレスポンス設定
        subject_response = Mock()
        subject_response.status_code = 200
        subject_response.content = subject_data

        dat_response = Mock()
        dat_response.status_code = 200
        dat_response.content = dat_data

        scraper_mock = Mock()
        scraper_mock.get = Mock(return_value=dat_response)
        scraper_mock.headers = {}

        # Mock _store_summaries to capture the threads being stored
        stored_threads = []

        def capture_store(threads, target_dates):
            stored_threads.extend(threads)
            return [("test.json", "test.md")]

        # _get_thread_posts_from_datのモック設定
        # HTMLエスケープ済み文字を含む投稿データを返す
        async def mock_get_thread_posts_sanitization(dat_url):
            posts = [
                {
                    "no": 1,
                    "name": "名無しさん",
                    "mail": "sage",
                    "date": "2024/11/14",
                    "com": "テスト😀&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;🎉",
                    "time": "2024/11/14",
                    "title": 'テスト&lt;script&gt;alert("XSS")&lt;/script&gt;スレ',
                }
            ]
            return (posts, None)

        with (
            patch(
                "nook.services.fivechan_explorer.fivechan_explorer.httpx.AsyncClient"
            ) as mock_client,
            patch("cloudscraper.create_scraper", return_value=scraper_mock),
            patch(
                "asyncio.to_thread",
                side_effect=lambda f, *args, **kwargs: f(*args, **kwargs),
            ),
            patch.object(service, "setup_http_client", new_callable=AsyncMock),
            patch.object(service, "_store_summaries", side_effect=capture_store),
            patch.object(
                service,
                "_get_thread_posts_from_dat",
                side_effect=mock_get_thread_posts_sanitization,
            ),
        ):
            # HTTPクライアントのモック設定 (_get_subject_txt_data用)
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.__aexit__.return_value = AsyncMock()
            client_instance.get = AsyncMock(return_value=subject_response)
            mock_client.return_value = client_instance
            service.http_client = client_instance

            # GPTClientのモック (既存のテストと同じ方法)
            service.gpt_client.generate_content = Mock(return_value="安全な要約テキスト")

            # collect()実行
            result = await service.collect(target_dates=[date.today()])

            # 検証
            assert result is not None, "collect()の結果がNoneでないこと"
            assert isinstance(result, list), "結果がlistオブジェクトであること"

            # 収集されたスレッドデータにエスケープ済み文字列が保持されていることを確認
            assert len(stored_threads) > 0, "スレッドが収集されていること"
            # スレッドタイトルまたは投稿内容にエスケープ済み文字列が含まれていることを確認
            thread_data = "".join(
                str(thread.title) + "".join(str(post.content) for post in thread.posts)
                for thread in stored_threads
            )
            assert "&lt;script&gt;" in thread_data, "HTMLエスケープ済み文字列が保持されていること"
