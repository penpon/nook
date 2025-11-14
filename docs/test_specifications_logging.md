# テスト仕様書: logging.py

## 対象モジュール
- ファイル: nook/common/logging.py
- 現在のカバレッジ: 30.56%
- 目標カバレッジ: 95%以上

## テスト対象の関数/クラス一覧

### 1. SimpleConsoleFormatter クラス
- コンソール用シンプルフォーマッタ
- メッセージのみ出力

### 2. JSONFormatter クラス
- JSON形式ログフォーマッタ
- 構造化ログ出力

### 3. setup_logger 関数
- ロガーセットアップ
- コンソール・ファイルハンドラー設定

## テスト観点

### SimpleConsoleFormatter.format

#### 正常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 通常メッセージ | LogRecord("test message") | "test message" | メッセージのみ |
| 空メッセージ | LogRecord("") | "" | - |
| 長いメッセージ | 1000文字のメッセージ | 全文字列 | - |

### JSONFormatter.format

#### 正常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 通常メッセージ | 基本LogRecord | JSON文字列 | 必須フィールド含む |
| 例外情報あり | exc_info付きLogRecord | exceptionフィールド含む | - |
| カスタムフィールド | extraパラメータ付き | カスタムフィールド含む | - |

#### フィールド検証
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| timestamp | 任意のLogRecord | ISO形式UTC時刻 | - |
| level | INFO/ERROR/DEBUG | 対応するlevelname | - |
| logger名 | 任意のロガー | name フィールド | - |
| message | 任意のメッセージ | message フィールド | - |
| module | 任意のモジュール | module フィールド | - |
| function | 任意の関数 | funcName フィールド | - |
| line | 任意の行番号 | lineno フィールド | - |

#### 異常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 非ASCII文字 | 日本語メッセージ | ensure_ascii=False | UTF-8 |
| 例外フォーマット | Exception含む | formatException呼び出し | - |

#### 除外フィールド確認
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 標準フィールド除外 | LogRecord | 除外リストのフィールドなし | created, msecs等 |

### setup_logger

#### 正常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| デフォルト設定 | name="test" | INFO, JSON, logs/test.log | - |
| カスタムレベル | level="DEBUG" | DEBUGレベル設定 | - |
| カスタムディレクトリ | log_dir="custom_logs" | custom_logs/test.log | - |
| テキスト形式 | use_json=False | 標準フォーマット | - |
| JSON形式 | use_json=True | JSONフォーマット | - |

#### ハンドラー検証
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| コンソールハンドラー | 任意の設定 | StreamHandler追加 | SimpleConsoleFormatter |
| ファイルハンドラー | 任意の設定 | RotatingFileHandler追加 | - |
| ハンドラークリア | 既存ハンドラーあり | 既存ハンドラー削除 | - |

#### ファイルハンドラー設定
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| ファイルパス | name="test", log_dir="logs" | logs/test.log | - |
| ローテーション設定 | デフォルト | maxBytes=10MB, backupCount=5 | - |
| エンコーディング | デフォルト | utf-8 | - |

#### ディレクトリ作成
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| ディレクトリ未作成 | log_dir不存在 | ディレクトリ作成される | exist_ok=True |
| ディレクトリ既存 | log_dir存在 | エラーなし | - |

#### 異常系
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 無効なレベル | level="INVALID" | AttributeError | getattr失敗 |
| 無効なパス | log_dir="/invalid/path" | OSError/PermissionError | - |

#### 境界値
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| 全レベル確認 | DEBUG/INFO/WARNING/ERROR/CRITICAL | 各レベル設定可能 | - |
| 長いパス | 255文字のlog_dir | 正常動作 | OS制限内 |

#### フォーマッター確認
| テストケース | 入力 | 期待する出力 | 備考 |
|------------|------|-------------|------|
| コンソールフォーマット | 任意 | SimpleConsoleFormatter | 常に |
| JSONファイル | use_json=True | JSONFormatter | - |
| テキストファイル | use_json=False | 標準Formatter | asctime含む |

## カバレッジ目標
- 分岐網羅率: 95%以上
- 境界値テスト: 全て実施
- 異常系テスト: 正常系以上の数
- ファイルI/O処理の確認
- 一時ディレクトリでのテスト
- ログ出力内容の検証
