# テスト仕様書: service_errors.py

## 対象モジュール
- ファイル: nook/common/service_errors.py
- 現在のカバレッジ: 0%
- 目標カバレッジ: 95%以上

## テスト対象の関数/クラス一覧

### 1. ServiceErrorHandler クラス
- サービス層のエラーハンドリング
- APIエラーとデータ処理エラーの変換

### 2. handle_api_error デコレータ
- API呼び出しエラーをAPIExceptionに変換

### 3. handle_data_processing デコレータ
- データ処理エラーをServiceExceptionに変換

## テスト観点

### ServiceErrorHandler.__init__

#### 正常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 通常初期化 | service_name="test_service" | 正常に初期化 | - |
| ロガー設定 | service_name="test" | logger.name="test" | - |

### handle_api_error デコレータ

#### 正常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 正常な関数 | 例外なし | 関数結果を返す | - |
| 正常終了 | 任意の戻り値 | そのまま返す | - |

#### 異常系（response属性あり）
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| HTTPエラー | response.status_code=404 | APIException発生 | status_code含む |
| レスポンスボディあり | response.text="error" | response_body含む | - |
| status_code=500 | サーバーエラー | APIException | - |
| status_code=401 | 認証エラー | APIException | - |

#### 異常系（response属性なし）
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 一般Exception | ValueError発生 | APIException | status_code=None |
| RuntimeError | 実行時エラー | APIException | - |
| KeyError | キーエラー | APIException | - |

#### エラーメッセージ
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| api_name含む | api_name="test_api" | "test_api API error:" | - |
| 元のエラー含む | Exception("original") | "original"含む | - |

#### ログ出力
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| errorログ | 任意の例外 | "API call failed" | - |
| extra情報 | 任意の例外 | service, api, function, error | - |
| exc_info | 任意の例外 | exc_info=True | スタックトレース |

#### 例外チェーン
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| from句 | 元の例外 | raise ... from e | - |

### handle_data_processing デコレータ

#### 正常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 正常な関数 | 例外なし | 関数結果を返す | - |
| 正常終了 | 任意の戻り値 | そのまま返す | - |

#### 異常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| ValueError | データエラー | ServiceException発生 | - |
| KeyError | キー不在 | ServiceException発生 | - |
| TypeError | 型エラー | ServiceException発生 | - |
| 一般Exception | 任意の例外 | ServiceException発生 | - |

#### エラーメッセージ
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| operation含む | operation="parse data" | "Failed to parse data:" | - |
| 元のエラー含む | Exception("original") | "original"含む | - |

#### ログ出力
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| errorログ | 任意の例外 | "Data processing failed" | - |
| extra情報 | 任意の例外 | service, operation, function, error | - |
| exc_info | 任意の例外 | exc_info=True | スタックトレース |

#### 例外チェーン
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| from句 | 元の例外 | raise ... from e | - |

### デコレータの組み合わせ

#### 正常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 複数デコレータ | 両方適用 | 正常動作 | - |
| functools.wraps | デコレート後 | 元の関数名・docstring保持 | - |

### 非同期関数対応

#### 正常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| async関数 | 非同期関数 | 正常動作 | await必要 |

## カバレッジ目標
- 分岐網羅率: 95%以上
- 境界値テスト: 全て実施
- 異常系テスト: 正常系以上の数
- ログ出力の検証
- 例外変換の確認
- 例外チェーンの検証
