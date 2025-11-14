"""
ArxivSummarizer - 性能・パフォーマンステスト

このファイルはレスポンスタイム、メモリ使用量、スループットをテストします。

必要なライブラリ:
- pytest-benchmark: pip install pytest-benchmark
- memory-profiler: pip install memory-profiler

実行方法:
```bash
# 性能テストのみ実行
pytest tests/services/arxiv_summarizer/test_performance.py -v

# ベンチマーク結果を保存
pytest tests/services/arxiv_summarizer/test_performance.py --benchmark-save=baseline

# ベンチマーク比較
pytest tests/services/arxiv_summarizer/test_performance.py --benchmark-compare=baseline
```
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest


# =============================================================================
# レスポンスタイムテスト
# =============================================================================


@pytest.mark.performance
@pytest.mark.asyncio
@pytest.mark.parametrize("paper_count", [1, 10, 50, 100])
async def test_performance_serialize_papers(
    arxiv_service, paper_info_factory, paper_count
):
    """
    レスポンスタイムテスト: 論文シリアライズ

    Given: 様々な数の論文データ
    When: _serialize_papersメソッドを呼び出す
    Then: 期待されるレスポンスタイム内に完了する

    期待値:
    - 1論文: < 10ms
    - 10論文: < 50ms
    - 50論文: < 200ms
    - 100論文: < 400ms
    """
    # Given
    papers = [
        paper_info_factory(
            arxiv_id=f"2301.{i:05d}",
            title=f"Paper {i}",
            summary=f"Summary {i}",
        )
        for i in range(paper_count)
    ]

    # 期待されるレスポンスタイム（秒）
    expected_time = {
        1: 0.01,
        10: 0.05,
        50: 0.2,
        100: 0.4,
    }

    # When
    start_time = time.perf_counter()
    result = arxiv_service._serialize_papers(papers)
    elapsed_time = time.perf_counter() - start_time

    # Then
    assert len(result) == paper_count
    assert (
        elapsed_time < expected_time[paper_count]
    ), f"シリアライズに{elapsed_time:.4f}秒かかりました（期待: {expected_time[paper_count]}秒未満）"

    print(
        f"\n✓ {paper_count}論文のシリアライズ: {elapsed_time*1000:.2f}ms"
    )


@pytest.mark.performance
@pytest.mark.parametrize("text_length", [100, 1000, 10000, 100000])
def test_performance_is_valid_body_line(
    arxiv_service, arxiv_helper, text_length
):
    """
    レスポンスタイムテスト: 本文行検証

    Given: 様々な長さのテキスト
    When: _is_valid_body_lineメソッドを呼び出す
    Then: O(n)の時間複雑度で完了する

    期待値:
    - 100文字: < 1ms
    - 1,000文字: < 5ms
    - 10,000文字: < 20ms
    - 100,000文字: < 100ms
    """
    # Given
    text = "a" * (text_length - 1) + "."

    # 期待されるレスポンスタイム（秒）
    expected_time = {
        100: 0.001,
        1000: 0.005,
        10000: 0.02,
        100000: 0.1,
    }

    # When
    start_time = time.perf_counter()
    result = arxiv_service._is_valid_body_line(
        text, min_length=arxiv_helper.DEFAULT_MIN_LINE_LENGTH
    )
    elapsed_time = time.perf_counter() - start_time

    # Then
    assert isinstance(result, bool)
    assert (
        elapsed_time < expected_time[text_length]
    ), f"検証に{elapsed_time:.4f}秒かかりました（期待: {expected_time[text_length]}秒未満）"

    print(
        f"\n✓ {text_length}文字の検証: {elapsed_time*1000:.2f}ms"
    )


@pytest.mark.performance
@pytest.mark.parametrize("markdown_papers", [1, 10, 50, 100])
def test_performance_parse_markdown(arxiv_service, markdown_papers):
    """
    レスポンスタイムテスト: Markdown解析

    Given: 様々な数の論文を含むMarkdown
    When: _parse_markdownメソッドを呼び出す
    Then: 期待されるレスポンスタイム内に完了する

    期待値:
    - 1論文: < 10ms
    - 10論文: < 50ms
    - 50論文: < 200ms
    - 100論文: < 400ms
    """
    # Given: 大きなMarkdownを生成
    markdown_template = """
## [Test Paper {i}](http://arxiv.org/abs/2301.{i:05d})

**abstract**:
Abstract for paper {i}

**summary**:
Summary for paper {i}

---
"""
    markdown = "# arXiv 論文要約 (2024-01-01)\n\n" + "".join(
        [markdown_template.format(i=i) for i in range(markdown_papers)]
    )

    # 期待されるレスポンスタイム（秒）
    expected_time = {
        1: 0.01,
        10: 0.05,
        50: 0.2,
        100: 0.4,
    }

    # When
    start_time = time.perf_counter()
    result = arxiv_service._parse_markdown(markdown)
    elapsed_time = time.perf_counter() - start_time

    # Then
    assert len(result) == markdown_papers
    assert (
        elapsed_time < expected_time[markdown_papers]
    ), f"解析に{elapsed_time:.4f}秒かかりました（期待: {expected_time[markdown_papers]}秒未満）"

    print(
        f"\n✓ {markdown_papers}論文のMarkdown解析: {elapsed_time*1000:.2f}ms"
    )


# =============================================================================
# スループットテスト
# =============================================================================


@pytest.mark.performance
@pytest.mark.asyncio
async def test_throughput_concurrent_operations(
    arxiv_service, paper_info_factory
):
    """
    スループットテスト: 並行操作

    Given: 複数の論文データ
    When: 複数の操作を並行実行
    Then: スループットが許容範囲内

    期待値: 100論文/秒以上
    """
    # Given
    paper_count = 100
    papers = [
        paper_info_factory(arxiv_id=f"2301.{i:05d}")
        for i in range(paper_count)
    ]

    # When: シリアライズ操作を繰り返し
    start_time = time.perf_counter()
    for _ in range(10):  # 10回繰り返し
        result = arxiv_service._serialize_papers(papers)
    elapsed_time = time.perf_counter() - start_time

    # Then: スループット計算
    total_operations = paper_count * 10
    throughput = total_operations / elapsed_time

    print(
        f"\n✓ スループット: {throughput:.0f}論文/秒 (合計{total_operations}論文を{elapsed_time:.2f}秒で処理)"
    )

    assert (
        throughput >= 100
    ), f"スループットが低い: {throughput:.0f}論文/秒（期待: 100論文/秒以上）"


# =============================================================================
# メモリ使用量テスト
# =============================================================================


@pytest.mark.memory
@pytest.mark.parametrize("paper_count", [100, 1000, 10000])
def test_memory_serialize_papers(
    arxiv_service, paper_info_factory, paper_count
):
    """
    メモリテスト: 大量データのシリアライズ

    Given: 大量の論文データ
    When: _serialize_papersメソッドを呼び出す
    Then: メモリ使用量が許容範囲内

    期待値:
    - 100論文: < 1MB
    - 1,000論文: < 10MB
    - 10,000論文: < 100MB

    Note: 実際のメモリ測定にはmemory_profilerまたはtracemalloc使用
    """
    import tracemalloc

    # Given
    papers = [
        paper_info_factory(arxiv_id=f"2301.{i:05d}")
        for i in range(paper_count)
    ]

    # メモリ測定開始
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    # When
    result = arxiv_service._serialize_papers(papers)

    # メモリ測定終了
    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Then: メモリ使用量を計算
    top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
    total_memory = sum(stat.size_diff for stat in top_stats)
    memory_mb = total_memory / (1024 * 1024)

    # 期待されるメモリ使用量（MB）
    expected_memory = {
        100: 1.0,
        1000: 10.0,
        10000: 100.0,
    }

    print(
        f"\n✓ {paper_count}論文のメモリ使用量: {memory_mb:.2f}MB"
    )

    assert (
        memory_mb < expected_memory[paper_count]
    ), f"メモリ使用量が多い: {memory_mb:.2f}MB（期待: {expected_memory[paper_count]}MB未満）"


# =============================================================================
# ストレステスト（負荷テスト）
# =============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
async def test_stress_continuous_operations(
    arxiv_service, paper_info_factory
):
    """
    ストレステスト: 連続操作

    Given: 一定時間連続で操作を実行
    When: 30秒間連続でシリアライズを実行
    Then: エラーなく完了し、パフォーマンスが劣化しない

    期待値:
    - エラー率: 0%
    - レスポンスタイム変動: < 20%
    """
    pytest.skip("Stress test - 手動実行用")

    # Given
    paper_count = 10
    papers = [
        paper_info_factory(arxiv_id=f"2301.{i:05d}")
        for i in range(paper_count)
    ]

    # When: 30秒間連続実行
    duration = 30  # 秒
    start_time = time.perf_counter()
    operation_count = 0
    response_times = []

    while time.perf_counter() - start_time < duration:
        op_start = time.perf_counter()
        try:
            result = arxiv_service._serialize_papers(papers)
            op_time = time.perf_counter() - op_start
            response_times.append(op_time)
            operation_count += 1
        except Exception as e:
            pytest.fail(f"ストレステスト中にエラー発生: {e}")

    # Then: 統計計算
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    min_response_time = min(response_times)
    variation = (max_response_time - min_response_time) / avg_response_time

    print(
        f"\n✓ ストレステスト結果:"
        f"\n  - 実行回数: {operation_count}回"
        f"\n  - 平均レスポンスタイム: {avg_response_time*1000:.2f}ms"
        f"\n  - 最大レスポンスタイム: {max_response_time*1000:.2f}ms"
        f"\n  - 最小レスポンスタイム: {min_response_time*1000:.2f}ms"
        f"\n  - 変動率: {variation*100:.1f}%"
    )

    assert variation < 0.2, f"レスポンスタイム変動が大きい: {variation*100:.1f}%"


# =============================================================================
# リグレッションテスト（性能劣化検出）
# =============================================================================


@pytest.mark.regression
@pytest.mark.parametrize("operation", ["serialize", "parse", "validate"])
def test_regression_performance_baseline(
    arxiv_service, paper_info_factory, operation, benchmark
):
    """
    リグレッションテスト: 性能ベースライン

    Given: 標準的なデータセット
    When: 各操作を実行
    Then: ベースラインと比較して性能劣化なし

    使用方法:
    ```bash
    # ベースライン保存
    pytest test_performance.py::test_regression_performance_baseline --benchmark-save=v1.0

    # 比較実行
    pytest test_performance.py::test_regression_performance_baseline --benchmark-compare=v1.0
    ```

    Note: pytest-benchmarkが必要
    """
    pytest.skip("pytest-benchmark not installed - example test")

    # # Given: 標準データセット
    # papers = [
    #     paper_info_factory(arxiv_id=f"2301.{i:05d}")
    #     for i in range(50)
    # ]
    #
    # # When/Then: ベンチマーク実行
    # if operation == "serialize":
    #     benchmark(arxiv_service._serialize_papers, papers)
    # elif operation == "parse":
    #     markdown = arxiv_service._render_markdown(
    #         [p.__dict__ for p in papers],
    #         datetime(2024, 1, 1)
    #     )
    #     benchmark(arxiv_service._parse_markdown, markdown)
    # elif operation == "validate":
    #     text = "This is a valid body line." * 10
    #     benchmark(arxiv_service._is_valid_body_line, text, 80)


# =============================================================================
# 設定とヘルパー
# =============================================================================


def pytest_configure(config):
    """pytestマーカーを登録"""
    config.addinivalue_line(
        "markers", "performance: 性能テスト（レスポンスタイム、スループット）"
    )
    config.addinivalue_line("markers", "memory: メモリ使用量テスト")
    config.addinivalue_line("markers", "stress: ストレステスト（負荷テスト）")
    config.addinivalue_line(
        "markers", "regression: リグレッションテスト（性能劣化検出）"
    )


"""
実行例:

# 全性能テスト実行
pytest tests/services/arxiv_summarizer/test_performance.py -v

# 特定のマーカーのみ
pytest tests/services/arxiv_summarizer/test_performance.py -v -m performance
pytest tests/services/arxiv_summarizer/test_performance.py -v -m memory

# CI/CDで性能テストをスキップ
pytest tests/services/arxiv_summarizer/ -v -m "not performance and not memory and not stress"

# 詳細出力
pytest tests/services/arxiv_summarizer/test_performance.py -v -s
"""
