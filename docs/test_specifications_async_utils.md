# async_utils.py テスト観点表

## 対象モジュール
`nook/common/async_utils.py`

## カバレッジ目標
95%以上

## テスト観点一覧

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 1 | TaskResult初期化（成功） | 正常系 | name="task1", success=True, result="data" | TaskResultオブジェクト生成、timestampが設定される | High | test_task_result_success |
| 2 | TaskResult初期化（失敗） | 正常系 | name="task1", success=False, error=Exception() | TaskResultオブジェクト生成、errorが設定される | High | test_task_result_failure |
| 3 | gather_with_errors: 全タスク成功 | 正常系 | 3つの成功タスク | 3つのTaskResult、全success=True | High | test_gather_with_errors_all_success |
| 4 | gather_with_errors: 一部タスク失敗 | 正常系 | 成功2、失敗1のタスク | 3つのTaskResult、success混在 | High | test_gather_with_errors_partial_failure |
| 5 | gather_with_errors: カスタムtask_names | 正常系 | task_names=["A", "B", "C"] | TaskResult.nameがカスタム名 | Medium | test_gather_with_errors_custom_names |
| 6 | gather_with_errors: 全タスク失敗 | 異常系 | 3つの失敗タスク | 3つのTaskResult、全success=False | High | test_gather_with_errors_all_failure |
| 7 | gather_with_errors: task_names長さ不一致 | 異常系 | coros=3、task_names=2 | ValueError発生 | High | test_gather_with_errors_invalid_task_names_length |
| 8 | gather_with_errors: return_exceptions=False | 異常系 | 失敗タスク、return_exceptions=False | 例外が再発生 | Medium | test_gather_with_errors_no_return_exceptions |
| 9 | gather_with_errors: 空リスト | 境界値 | coros=[] | 空リスト返却 | Medium | test_gather_with_errors_empty |
| 10 | gather_with_errors: 単一タスク | 境界値 | coros=1つ | 1つのTaskResult返却 | Low | test_gather_with_errors_single_task |
| 11 | run_with_semaphore: 並行数制限 | 正常系 | max_concurrent=2、5タスク | 最大2並行、全結果返却 | High | test_run_with_semaphore_concurrency_limit |
| 12 | run_with_semaphore: progress_callback | 正常系 | progress_callback設定 | コールバックが進捗で呼ばれる | High | test_run_with_semaphore_progress_callback |
| 13 | run_with_semaphore: 全タスク成功 | 正常系 | 3つの成功タスク | 全結果が正常に返却 | High | test_run_with_semaphore_all_success |
| 14 | run_with_semaphore: タスク実行失敗 | 異常系 | 失敗するタスク | 例外が伝播 | High | test_run_with_semaphore_task_failure |
| 15 | run_with_semaphore: progress_callback失敗 | 異常系 | progress_callbackが例外 | タスク自体は例外で失敗 | Medium | test_run_with_semaphore_callback_failure |
| 16 | run_with_semaphore: max_concurrent=1 | 境界値 | max_concurrent=1、3タスク | 完全直列実行 | High | test_run_with_semaphore_max_concurrent_one |
| 17 | run_with_semaphore: 空リスト | 境界値 | coros=[] | 空リスト返却 | Low | test_run_with_semaphore_empty |
| 18 | batch_process: 複数バッチ処理 | 正常系 | items=250、batch_size=100 | 3バッチに分割処理 | High | test_batch_process_multiple_batches |
| 19 | batch_process: 単一バッチ | 正常系 | items=50、batch_size=100 | 1バッチで処理 | Medium | test_batch_process_single_batch |
| 20 | batch_process: processor失敗 | 異常系 | processorが例外 | 例外が伝播 | High | test_batch_process_processor_failure |
| 21 | batch_process: 並行数制限 | 異常系 | max_concurrent_batches=2 | 最大2バッチ並行 | Medium | test_batch_process_concurrent_limit |
| 22 | batch_process: 空リスト | 境界値 | items=[] | 空リスト返却 | Medium | test_batch_process_empty |
| 23 | batch_process: batch_size境界 | 境界値 | items=100、batch_size=100 | ちょうど1バッチ | Low | test_batch_process_exact_batch_size |
| 24 | run_sync_in_thread: 同期関数実行 | 正常系 | 通常の同期関数 | Futureが返却、結果取得可能 | High | test_run_sync_in_thread_success |
| 25 | run_sync_in_thread: 引数・kwargs渡し | 正常系 | args、kwargs付き | 引数が正しく渡される | Medium | test_run_sync_in_thread_with_args |
| 26 | run_sync_in_thread: 同期関数内例外 | 異常系 | 関数が例外発生 | Futureから例外取得可能 | High | test_run_sync_in_thread_exception |
| 27 | run_sync_in_thread: 時間のかかる処理 | 異常系 | time.sleep(0.1) | 非ブロッキング実行 | Medium | test_run_sync_in_thread_blocking_operation |
| 28 | AsyncTaskManager: 初期化 | 正常系 | max_concurrent=5 | 空の状態で初期化 | High | test_async_task_manager_init |
| 29 | AsyncTaskManager: submit成功 | 正常系 | 1タスクsubmit | タスクIDが返却、実行開始 | High | test_async_task_manager_submit_success |
| 30 | AsyncTaskManager: 複数submit | 正常系 | 3タスクsubmit | 全タスクが実行される | High | test_async_task_manager_submit_multiple |
| 31 | AsyncTaskManager: wait_for成功 | 正常系 | タスク完了をwait_for | 結果が返却される | High | test_async_task_manager_wait_for_success |
| 32 | AsyncTaskManager: wait_all成功 | 正常系 | 全タスク完了をwait_all | results/errors辞書が返却 | High | test_async_task_manager_wait_all_success |
| 33 | AsyncTaskManager: get_status | 正常系 | 実行中・完了・失敗混在 | 正しいステータス返却 | High | test_async_task_manager_get_status |
| 34 | AsyncTaskManager: submit重複名 | 異常系 | 同じ名前で2回submit | ValueError発生 | High | test_async_task_manager_submit_duplicate_name |
| 35 | AsyncTaskManager: wait_for存在しないタスク | 異常系 | 存在しないタスク名 | ValueError発生 | High | test_async_task_manager_wait_for_not_found |
| 36 | AsyncTaskManager: wait_for失敗タスク | 異常系 | 失敗したタスクをwait_for | 保存された例外が再発生 | High | test_async_task_manager_wait_for_failed_task |
| 37 | AsyncTaskManager: wait_forタイムアウト | 異常系 | timeout内に完了しない | TimeoutError発生 | High | test_async_task_manager_wait_for_timeout |
| 38 | AsyncTaskManager: タスク内例外 | 異常系 | タスクが例外を発生 | errorsに記録される | High | test_async_task_manager_task_exception |
| 39 | AsyncTaskManager: wait_all部分完了 | 異常系 | timeout内に一部完了 | 完了分のみresultsに | Medium | test_async_task_manager_wait_all_partial |
| 40 | AsyncTaskManager: タスク0件 | 境界値 | submitせずwait_all | 空のresults/errors | Low | test_async_task_manager_empty |
| 41 | AsyncTaskManager: wait_for完了済み | 境界値 | 完了済みタスクをwait_for | 即座に結果返却 | Medium | test_async_task_manager_wait_for_completed |
| 42 | AsyncTaskManager: wait_for失敗済み | 境界値 | 失敗済みタスクをwait_for | 即座に例外発生 | Medium | test_async_task_manager_wait_for_failed_completed |

## テスト分類サマリー
- **正常系**: 17ケース
- **異常系**: 15ケース
- **境界値**: 10ケース
- **合計**: 42ケース

## カバレッジ戦略
1. 全関数・メソッドを網羅
2. 分岐条件（if/else）を全パターンテスト
3. 例外処理パスを全て検証
4. 境界値（0、1、空、最大値）を検証
5. 非同期処理の並行性を検証
6. ロックとセマフォの動作を検証

## 特記事項
- 失敗系（異常系+境界値の一部）が正常系より多い設計
- 等価分割: タスク数（0、1、複数）、実行結果（成功、失敗、混在）
- 境界値分析: 並行数（0、1、最大）、バッチサイズ、タイムアウト
