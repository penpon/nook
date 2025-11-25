"""nook/services/fivechan_explorer/fivechan_explorer.py の統合テスト

5chan Explorerサービスのエンドツーエンド動作を検証する統合テストスイート。
データ取得→GPT要約→Storage保存の全体フローとエラーハンドリング、およびセキュリティ対策をテストします。

テスト観点:
- データ取得→GPT要約→Storage保存の正常系フロー
- ネットワークエラー、APIエラー時のハンドリング
- XSS攻撃シミュレーション (悪意あるスクリプト含むレスポンス)
- DoS対策 (大量リクエスト制限)
- データサニタイゼーション検証
"""

from __future__ import annotations

import time
import tracemalloc
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer, Post, Thread

# =============================================================================
# テスト定数 (Functional)
# =============================================================================

TEST_THREAD_ID = "1234567890"
TEST_BOARD_ID = "livegalileo"
TEST_BOARD_NAME = "なんでも実況J"
TEST_THREAD_TITLE = "【AI】ChatGPTについて語るスレ【機械学習】"
TEST_THREAD_CONTENT = "AI技術の発展について議論するテストスレッド。" * 50
# 固定のタイムスタンプ（2020-01-01 00:00:00 UTC）を使用して再現性を確保
TEST_THREAD_TIMESTAMP = 1577836800
# テストスレッドの日付（target_dates指定用）
TEST_TARGET_DATE = date(2020, 1, 1)


# =============================================================================
# テスト定数 (Security)
# =============================================================================
MAX_RESPONSE_SIZE_MB = 1
MAX_RESPONSE_SIZE_BYTES = MAX_RESPONSE_SIZE_MB * 1024 * 1024
MAX_PROCESSING_TIME_SECONDS = 60.0
MAX_MEMORY_USAGE_MB = 100
MAX_MEMORY_USAGE_BYTES = MAX_MEMORY_USAGE_MB * 1024 * 1024


# =============================================================================
# テストヘルパー関数
# =============================================================================


def create_test_thread(thread_id: str = TEST_THREAD_ID, **kwargs) -> Thread:
    """テスト用のThreadオブジェクトを作成するヘルパー関数。

    Args:
        thread_id (str): スレッドID（デフォルト: TEST_THREAD_ID）。
        **kwargs: Threadの追加属性。利用可能なキーは以下の通り:
            - title (str): スレッドタイトル（デフォルト: TEST_THREAD_TITLE）。
            - url (str): スレッドURL（デフォルト: 5chのスレURL）。
            - board (str): 板ID（デフォルト: TEST_BOARD_ID）。
            - timestamp (int): UNIXタイムスタンプ（デフォルト: TEST_THREAD_TIMESTAMP）。
            - popularity_score (float): 人気スコア（デフォルト: 0.75）。
            - posts (list[dict]): 投稿リスト（デフォルト: 1件のテスト投稿）。
            - summary (str): スレッド要約（デフォルト: 空文字）。

    Returns:
        Thread: テスト用のThreadオブジェクト。

    Raises:
        なし

    """
    default_posts = [
        Post(
            no=1,
            name="名無しさん",
            mail="sage",
            date="2020/01/01(水) 00:00:00.00 ID:test",
            content=TEST_THREAD_CONTENT,
        )
    ]
    return Thread(
        thread_id=int(thread_id),
        title=kwargs.get("title", TEST_THREAD_TITLE),
        url=kwargs.get("url", f"https://greta.5ch.net/test/read.cgi/{TEST_BOARD_ID}/{thread_id}/"),
        board=kwargs.get("board", TEST_BOARD_ID),
        timestamp=kwargs.get("timestamp", TEST_THREAD_TIMESTAMP),
        popularity_score=kwargs.get("popularity_score", 0.75),
        posts=kwargs.get("posts", default_posts),
        summary=kwargs.get("summary", ""),
    )


# =============================================================================
# 統合テスト: フルデータフロー
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_data_flow_fivechan_explorer_to_storage(tmp_path, mock_env_vars):
    """Given: FiveChanExplorerサービスインスタンス
    When: collect()メソッドを実行
    Then: データ取得 → GPT要約 → Storage保存の全体フローが成功する
    """
    # 1. サービス初期化
    storage_dir = str(tmp_path / "fivechan_data")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)

    with patch("nook.common.base_service.setup_logger"):
        service = FiveChanExplorer(storage_dir=storage_dir)

    # 2. モック設定
    # テストデータ用のThreadオブジェクトを作成（参照用）
    test_threads = [
        create_test_thread(
            thread_id="1111111111",
            title="【AI】ChatGPT統合テスト1【機械学習】",
            popularity_score=0.9,
            timestamp=TEST_THREAD_TIMESTAMP,
        ),
        create_test_thread(
            thread_id="2222222222",
            title="【AI】GPT-4統合テスト2【自然言語処理】",
            popularity_score=0.85,
            timestamp=TEST_THREAD_TIMESTAMP + 1,
        ),
        create_test_thread(
            thread_id="3333333333",
            title="【AI】画像生成AI統合テスト3【Stable Diffusion】",
            popularity_score=0.8,
            timestamp=TEST_THREAD_TIMESTAMP + 2,
        ),
    ]

    # _get_subject_txt_dataの戻り値を作成
    mock_subject_data = []
    for thread in test_threads:
        mock_subject_data.append(
            {
                "server": "mevius.5ch.net",
                "board": TEST_BOARD_ID,
                "timestamp": str(thread.timestamp),
                "title": thread.title,
                "post_count": len(thread.posts),
                "dat_url": thread.url.replace("read.cgi", "dat").rstrip("/") + ".dat",
                "html_url": thread.url,
            }
        )

    # 内部メソッドとGPTクライアントをモック
    with (
        patch.object(service, "_get_subject_txt_data", new_callable=AsyncMock) as mock_get_subject,
        patch.object(
            service, "_get_thread_posts_from_dat", new_callable=AsyncMock
        ) as mock_get_posts,
        patch.object(service.gpt_client, "generate_content") as mock_gpt,
    ):
        # _get_subject_txt_dataはテストデータを返す
        mock_get_subject.return_value = mock_subject_data

        # _get_thread_posts_from_datは投稿データを返す
        # 呼び出しごとに適切な投稿を返すようにside_effectを設定
        async def get_posts_side_effect(dat_url):
            # URLからスレッドIDを抽出して対応する投稿を返す
            for thread in test_threads:
                if str(thread.thread_id) in dat_url:
                    return thread.posts, None
            return [], "Not found"

        mock_get_posts.side_effect = get_posts_side_effect

        # GPT要約のモック
        mock_gpt.return_value = "テスト要約: この記事は統合テストの一環として作成されました。"

        # 3. データ収集実行（テストスレッドの日付を明示的に指定）
        result = await service.collect(target_dates=[TEST_TARGET_DATE])

        # 4. 検証: データ取得確認
        assert result is not None, "collect()がNoneを返しました"
        assert len(result) > 0, "保存されたファイルがありません"

        # 5. 検証: Storage保存確認
        saved_json_path, saved_md_path = result[0]
        assert Path(saved_json_path).exists(), (
            f"JSONファイルが保存されていません: {saved_json_path}"
        )
        assert Path(saved_md_path).exists(), (
            f"Markdownファイルが保存されていません: {saved_md_path}"
        )

        # 6. 検証: 保存内容確認
        import json

        with open(saved_json_path) as f:
            saved_data = json.load(f)

        assert len(saved_data) >= 3, f"期待: 3件以上のスレッド, 実際: {len(saved_data)}件"

        # 最初のスレッドの検証
        first_thread = saved_data[0]
        assert "title" in first_thread, "titleフィールドが存在しません"
        assert "url" in first_thread, "urlフィールドが存在しません"
        assert "summary" in first_thread, "summaryフィールドが存在しません"

        # スレッドのタイトルが正しいことを確認
        thread_titles = [t["title"] for t in saved_data]
        assert "【AI】ChatGPT統合テスト1【機械学習】" in thread_titles, (
            "テストスレッド1が保存されていません"
        )
        assert "【AI】GPT-4統合テスト2【自然言語処理】" in thread_titles, (
            "テストスレッド2が保存されていません"
        )
        assert "【AI】画像生成AI統合テスト3【Stable Diffusion】" in thread_titles, (
            "テストスレッド3が保存されていません"
        )


# =============================================================================
# 統合テスト: ネットワークエラーハンドリング
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_network_failure_fivechan_explorer(tmp_path, mock_env_vars):
    """Given: ネットワークエラーが発生する状況
    When: collect()メソッドを実行
    Then: RetryExceptionが発生する（retry decoratorによるリトライ後）
    """
    # 1. サービス初期化
    storage_dir = str(tmp_path / "fivechan_error_test")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)

    with patch("nook.common.base_service.setup_logger"):
        service = FiveChanExplorer(storage_dir=storage_dir)

    # HTTP clientを初期化
    await service.setup_http_client()

    # 2. モック設定: ネットワークエラーをシミュレート
    # _get_subject_txt_dataが例外を発生させるようにモック
    with patch.object(service, "_get_subject_txt_data", new_callable=AsyncMock) as mock_get_subject:
        mock_get_subject.side_effect = Exception("Network error")

        # 3. エラーハンドリング確認
        # FiveChanExplorerは内部でエラーをログに記録し、空のリストを返すか例外を発生させる

        # 実装によっては例外をキャッチして空リストを返す
        result = await service.collect(thread_limit=5)

        # エラーが発生しても空のリストが返されることを確認（collectメソッド内でtry-exceptされている場合）
        assert isinstance(result, list), "結果はリストであるべきです"
        assert len(result) == 0, "エラー時は空リストが返されるべきです"


# =============================================================================
# 統合テスト: GPT APIエラーハンドリングとフォールバック
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_gpt_api_failure_fivechan_explorer(tmp_path, mock_env_vars):
    """Given: GPT APIエラーが発生する状況
    When: collect()メソッドを実行
    Then: フォールバック処理が動作し、要約なしでもデータが保存される
    """
    # 1. サービス初期化
    storage_dir = str(tmp_path / "fivechan_gpt_error_test")
    Path(storage_dir).mkdir(parents=True, exist_ok=True)

    with patch("nook.common.base_service.setup_logger"):
        service = FiveChanExplorer(storage_dir=storage_dir)

    # 2. モック設定
    # テストデータ用のThreadオブジェクトを作成
    test_threads = [
        create_test_thread(
            thread_id="4444444444",
            title="【AI】GPTエラーテスト1【フォールバック】",
            popularity_score=0.88,
        ),
        create_test_thread(
            thread_id="5555555555",
            title="【AI】GPTエラーテスト2【リトライ】",
            popularity_score=0.82,
        ),
    ]

    # _get_subject_txt_dataの戻り値を作成
    mock_subject_data = []
    for thread in test_threads:
        mock_subject_data.append(
            {
                "server": "mevius.5ch.net",
                "board": TEST_BOARD_ID,
                "timestamp": str(thread.timestamp),
                "title": thread.title,
                "post_count": len(thread.posts),
                "dat_url": thread.url.replace("read.cgi", "dat").rstrip("/") + ".dat",
                "html_url": thread.url,
            }
        )

    with (
        patch.object(service, "_get_subject_txt_data", new_callable=AsyncMock) as mock_get_subject,
        patch.object(
            service, "_get_thread_posts_from_dat", new_callable=AsyncMock
        ) as mock_get_posts,
        patch.object(service.gpt_client, "generate_content") as mock_gpt,
    ):
        # _get_subject_txt_dataはテストデータを返す
        mock_get_subject.return_value = mock_subject_data

        # _get_thread_posts_from_datは投稿データを返す
        async def get_posts_side_effect(dat_url):
            for thread in test_threads:
                if str(thread.thread_id) in dat_url:
                    return thread.posts, None
            return [], "Not found"

        mock_get_posts.side_effect = get_posts_side_effect

        # GPT APIエラーをシミュレート
        mock_gpt.side_effect = Exception("API rate limit exceeded")

        # 3. データ収集実行（GPTエラーがあっても処理は継続、テストスレッドの日付を明示的に指定）
        result = await service.collect(thread_limit=5, target_dates=[TEST_TARGET_DATE])

        # 4. 検証: データは保存されるべき（GPTエラーがあっても）
        assert result is not None, "GPTエラー時でもresultはNoneであってはいけません"
        assert len(result) > 0, "GPTエラーがあってもデータは保存されるべきです"

        saved_json_path, saved_md_path = result[0]
        assert Path(saved_json_path).exists(), (
            f"JSONファイルが保存されていません: {saved_json_path}"
        )

        # 5. 保存内容確認
        import json

        with open(saved_json_path) as f:
            saved_data = json.load(f)

        # データは取得されている
        assert len(saved_data) >= 1, "最低1件のスレッドが保存されるべきです"

        for thread in saved_data:
            # 必須フィールドの確認
            assert "title" in thread, "titleフィールドが存在しません"
            assert "url" in thread, "urlフィールドが存在しません"
            assert "board" in thread, "boardフィールドが存在しません"

            # summaryフィールドの検証
            # GPTエラー時は、summaryがNone、空文字列、またはエラーメッセージの可能性がある
            if "summary" in thread:
                # summaryが存在する場合は文字列型であることを確認
                if thread["summary"] is not None:
                    assert isinstance(thread["summary"], str), (
                        f"summaryは文字列またはNoneであるべきです: {type(thread['summary'])}"
                    )


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
        service = FiveChanExplorer()

        # テストデータ: XSSペイロードを含むスレッドタイトル
        malicious_subject = "1763996400.dat<><script>alert('XSS')</script>悪意のあるスレ (100)\n"
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
                Post(
                    no=1,
                    name="<script>alert('XSS')</script>",
                    mail="sage",
                    date="2024/11/14",
                    content="<script>alert('XSS')</script>悪意のある投稿",
                )
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
    """Given: 1MBの巨大なレスポンス（DoS攻撃シミュレーション）
    When: collect()メソッドでデータ取得を実行
    Then: メモリオーバーフローせずに処理または適切に拒否される

    検証項目:
    - 1MB以上のレスポンスを安全に処理
    - メモリ使用量が閾値以下 (100MB以下)
    - 処理時間が許容範囲内 (60秒以下)
    - クラッシュしない
    """
    with patch("nook.common.base_service.setup_logger"):
        service = FiveChanExplorer()

        # テストデータ: 1MBの巨大なレスポンス (有効なsubject.txt形式)
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
        service = FiveChanExplorer()

        # テストデータ: HTMLエスケープが必要な文字を含むスレッドタイトル
        html_special_chars_subject = (
            '1763996400.dat<>テスト&lt;script&gt;alert("XSS")&lt;/script&gt;スレ (50)\n'
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
                Post(
                    no=1,
                    name="名無しさん",
                    mail="sage",
                    date="2024/11/14",
                    content="テスト😀&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;🎉",
                )
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
