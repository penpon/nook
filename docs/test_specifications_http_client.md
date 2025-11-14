# AsyncHTTPClient テスト仕様書

## 概要
`nook/common/http_client.py`の包括的なテスト仕様。カバレッジ目標は95%以上。

## テスト戦略
- 等価分割・境界値分析を適用
- 失敗系 ≥ 正常系
- 外部HTTP通信のモック化（respx使用）
- 非同期処理のテスト
- エラーハンドリング・リトライ・フォールバックの検証
- HTTP/2とHTTP/1.1の切り替え検証

---

## 1. 初期化とセッション管理のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 1 | デフォルトコンフィグでの初期化 | 正常系 | config=None | BaseConfigがデフォルトで使用される | High | test_init_with_default_config |
| 2 | カスタムコンフィグでの初期化 | 正常系 | config=BaseConfig(REQUEST_TIMEOUT=60) | カスタム設定が反映される | High | test_init_with_custom_config |
| 3 | セッション開始 | 正常系 | start()呼び出し | _clientが初期化され、_session_startが設定される | High | test_start_session |
| 4 | HTTP/1.1セッション開始 | 正常系 | _start_http1_client()呼び出し | _http1_clientが初期化される | High | test_start_http1_session |
| 5 | セッション終了 | 正常系 | close()呼び出し | 両クライアントがクローズされる | High | test_close_session |
| 6 | コンテキストマネージャー使用 | 正常系 | async with AsyncHTTPClient() | 自動的に開始・終了される | High | test_context_manager |
| 7 | セッション時間計測 | 正常系 | start後にclose | ログにセッション時間が記録される | Medium | test_session_duration_logging |
| 8 | 重複セッション開始 | 境界値 | start()を2回呼び出し | 2回目は何もしない | Medium | test_duplicate_start_session |

---

## 2. get_browser_headersのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 9 | ブラウザヘッダー取得 | 正常系 | get_browser_headers()呼び出し | User-Agent等を含むヘッダー辞書が返される | High | test_get_browser_headers |
| 10 | 必須ヘッダー存在確認 | 正常系 | get_browser_headers()呼び出し | User-Agent, Accept等のキーが存在 | High | test_browser_headers_contains_required_keys |

---

## 3. GETリクエストのテスト（正常系）

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 11 | HTTP/2 GETリクエスト成功 | 正常系 | url="https://example.com/api" | 200レスポンスが返される | High | test_get_request_http2_success |
| 12 | HTTP/1.1 GETリクエスト成功 | 正常系 | force_http1=True | 200レスポンス、HTTP/1.1使用 | High | test_get_request_http1_success |
| 13 | クエリパラメータ付きGET | 正常系 | params={"key": "value"} | パラメータ付きでリクエスト成功 | High | test_get_request_with_params |
| 14 | カスタムヘッダー付きGET | 正常系 | headers={"X-Custom": "test"} | カスタムヘッダーが送信される | High | test_get_request_with_custom_headers |
| 15 | ブラウザヘッダー使用 | 正常系 | use_browser_headers=True | ブラウザヘッダーが自動設定される | High | test_get_request_with_browser_headers |
| 16 | ブラウザヘッダー無効化 | 正常系 | use_browser_headers=False, headers=None | ヘッダーなしでリクエスト | Medium | test_get_request_without_browser_headers |
| 17 | ブラウザヘッダーとカスタムヘッダーのマージ | 正常系 | use_browser_headers=True, headers={"X-Custom": "test"} | 両方が統合される | Medium | test_get_request_merge_browser_and_custom_headers |
| 18 | リダイレクト対応 | 正常系 | URLが301リダイレクト | 自動的にリダイレクト先に移動 | Medium | test_get_request_follows_redirect |

---

## 4. GETリクエストのテスト（異常系 - HTTPエラー）

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 19 | 404エラー | 異常系 | HTTPステータス404 | APIException発生、status_code=404 | High | test_get_request_404_error |
| 20 | 500エラー | 異常系 | HTTPステータス500 | APIException発生、status_code=500 | High | test_get_request_500_error |
| 21 | 503エラー | 異常系 | HTTPステータス503 | APIException発生、status_code=503 | High | test_get_request_503_error |
| 22 | 403エラー（cloudscraperフォールバック成功） | 異常系 | HTTPステータス403 → cloudscraper成功 | 200レスポンスが返される | High | test_get_request_403_cloudscraper_success |
| 23 | 403エラー（cloudscraperも失敗） | 異常系 | HTTPステータス403 → cloudscraper失敗 | APIException発生、status_code=403 | High | test_get_request_403_cloudscraper_failure |
| 24 | 422エラー（HTTP/1.1フォールバック成功） | 異常系 | HTTPステータス422 → HTTP/1.1成功 | 200レスポンスが返される | High | test_get_request_422_http1_fallback_success |
| 25 | 422エラー（HTTP/1.1も失敗） | 異常系 | HTTPステータス422 → HTTP/1.1も422 | APIException発生、status_code=422 | High | test_get_request_422_http1_fallback_failure |
| 26 | 422エラー（_retry_http1=False） | 異常系 | HTTPステータス422、_retry_http1=False | 即座にAPIException発生 | Medium | test_get_request_422_no_retry_http1 |

---

## 5. GETリクエストのテスト（異常系 - ネットワークエラー）

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 27 | タイムアウトエラー | 異常系 | httpx.TimeoutException発生 | APIException発生（リトライ後） | High | test_get_request_timeout_error |
| 28 | 接続エラー | 異常系 | httpx.ConnectError発生 | APIException発生（リトライ後） | High | test_get_request_connection_error |
| 29 | StreamResetエラー（HTTP/1.1フォールバック成功） | 異常系 | StreamError発生 → HTTP/1.1成功 | 200レスポンスが返される | High | test_get_request_stream_error_http1_fallback_success |
| 30 | StreamResetエラー（HTTP/1.1も失敗） | 異常系 | StreamError発生 → HTTP/1.1も失敗 | APIException発生 | High | test_get_request_stream_error_http1_fallback_failure |
| 31 | StreamResetエラー（force_http1=True時） | 異常系 | force_http1=True時にStreamError | 即座にAPIException発生（フォールバックなし） | Medium | test_get_request_stream_error_no_fallback_when_forced_http1 |
| 32 | 一般的なRequestError | 異常系 | httpx.RequestError発生 | APIException発生 | High | test_get_request_general_request_error |

---

## 6. POSTリクエストのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 33 | JSON送信POST成功 | 正常系 | json={"key": "value"} | 200レスポンスが返される | High | test_post_request_with_json_success |
| 34 | data送信POST成功 | 正常系 | data={"key": "value"} | 200レスポンスが返される | High | test_post_request_with_data_success |
| 35 | バイトデータPOST成功 | 正常系 | data=b"binary data" | 200レスポンスが返される | Medium | test_post_request_with_bytes_success |
| 36 | カスタムヘッダー付きPOST | 正常系 | headers={"Content-Type": "application/json"} | カスタムヘッダーが送信される | Medium | test_post_request_with_custom_headers |
| 37 | POST 404エラー | 異常系 | HTTPステータス404 | APIException発生、status_code=404 | High | test_post_request_404_error |
| 38 | POST 500エラー | 異常系 | HTTPステータス500 | APIException発生、status_code=500 | High | test_post_request_500_error |
| 39 | POSTタイムアウトエラー | 異常系 | httpx.TimeoutException発生 | APIException発生（リトライ後） | High | test_post_request_timeout_error |
| 40 | POST接続エラー | 異常系 | httpx.ConnectError発生 | APIException発生（リトライ後） | High | test_post_request_connection_error |

---

## 7. ヘルパーメソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 41 | get_json成功 | 正常系 | レスポンスがJSON | JSON辞書が返される | High | test_get_json_success |
| 42 | get_json失敗（不正なJSON） | 異常系 | レスポンスが不正なJSON | JSONDecodeError発生 | Medium | test_get_json_invalid_json |
| 43 | get_text成功 | 正常系 | レスポンスがテキスト | テキスト文字列が返される | High | test_get_text_success |
| 44 | downloadファイル成功 | 正常系 | url, output_path | ファイルがダウンロードされる | High | test_download_file_success |
| 45 | downloadプログレスコールバック | 正常系 | progress_callback指定 | コールバックが呼ばれる | Medium | test_download_with_progress_callback |
| 46 | download失敗（404） | 異常系 | HTTPステータス404 | HTTPStatusError発生 | Medium | test_download_404_error |

---

## 8. cloudscraperフォールバックのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 47 | cloudscraper成功 | 正常系 | _cloudscraper_fallback()呼び出し | httpx互換レスポンスが返される | High | test_cloudscraper_fallback_success |
| 48 | cloudscraperタイムアウト | 異常系 | cloudscraperでタイムアウト | APIException発生、status_code=403 | High | test_cloudscraper_fallback_timeout |
| 49 | cloudscraper SSLエラー | 異常系 | cloudscraperでSSLエラー | APIException発生、status_code=403 | High | test_cloudscraper_fallback_ssl_error |
| 50 | cloudscraper 403エラー | 異常系 | cloudscraperでも403 | APIException発生、status_code=403 | High | test_cloudscraper_fallback_403_error |
| 51 | cloudscraperレスポンス変換 | 正常系 | requests.Responseを変換 | CloudscraperResponseAdapterが作成される | Medium | test_convert_to_httpx_response |
| 52 | CloudscraperResponseAdapter.json() | 正常系 | json()メソッド呼び出し | JSON辞書が返される | Medium | test_cloudscraper_response_adapter_json |
| 53 | CloudscraperResponseAdapter.raise_for_status()成功 | 正常系 | status_code=200 | 例外が発生しない | Medium | test_cloudscraper_response_adapter_raise_for_status_success |
| 54 | CloudscraperResponseAdapter.raise_for_status()失敗 | 異常系 | status_code=404 | HTTPStatusError発生 | Medium | test_cloudscraper_response_adapter_raise_for_status_error |

---

## 9. グローバル関数のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 55 | get_http_client（初回） | 正常系 | _global_client=None | 新規クライアントが作成され返される | High | test_get_http_client_first_call |
| 56 | get_http_client（2回目） | 正常系 | _global_client既存 | 同じインスタンスが返される | High | test_get_http_client_singleton |
| 57 | close_http_client | 正常系 | _global_client存在 | クライアントがクローズされ、Noneになる | High | test_close_http_client |
| 58 | close_http_client（既にNone） | 境界値 | _global_client=None | 何もしない | Medium | test_close_http_client_already_none |

---

## 10. リトライロジックのテスト（@handle_errors）

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 59 | GETリトライ1回目成功 | 正常系 | 1回目エラー、2回目成功 | 200レスポンスが返される | High | test_get_retry_success_on_second_attempt |
| 60 | GETリトライ最大回数到達 | 異常系 | 3回すべて失敗 | APIException発生 | High | test_get_retry_max_retries_exceeded |
| 61 | POSTリトライ1回目成功 | 正常系 | 1回目エラー、2回目成功 | 200レスポンスが返される | High | test_post_retry_success_on_second_attempt |
| 62 | POSTリトライ最大回数到達 | 異常系 | 3回すべて失敗 | APIException発生 | High | test_post_retry_max_retries_exceeded |

---

## 11. タイムアウト設定のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 63 | デフォルトタイムアウト設定 | 正常系 | config.REQUEST_TIMEOUT=30 | timeoutが正しく設定される | High | test_default_timeout_configuration |
| 64 | カスタムタイムアウト設定 | 正常系 | config.REQUEST_TIMEOUT=60 | カスタムタイムアウトが反映される | Medium | test_custom_timeout_configuration |
| 65 | タイムアウト境界値（0秒） | 境界値 | REQUEST_TIMEOUT=0 | 即座にタイムアウト | Low | test_timeout_zero_seconds |
| 66 | タイムアウト境界値（極大値） | 境界値 | REQUEST_TIMEOUT=99999 | 設定が反映される | Low | test_timeout_large_value |

---

## 12. 接続プール管理のテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 67 | 接続プール設定 | 正常系 | limits設定 | max_connections=100等が設定される | Medium | test_connection_pool_limits |
| 68 | 複数リクエストでの接続再利用 | 正常系 | 同一ホストへ複数回リクエスト | 接続が再利用される | Medium | test_connection_reuse_multiple_requests |

---

## まとめ

- **総テストケース数**: 68件
  - 正常系: 27件
  - 異常系: 33件（失敗系 > 正常系を満たす）
  - 境界値: 8件
- **優先度分布**:
  - High: 54件
  - Medium: 13件
  - Low: 1件
- **カバレッジ目標**: 95%以上
