# GPTClient テスト仕様書

## 概要
`nook/common/gpt_client.py`の包括的なテスト仕様。カバレッジ目標は95%以上。

## テスト戦略
- 等価分割・境界値分析を適用
- 失敗系 ≥ 正常系
- 外部依存（OpenAI API）のモック化
- 非同期処理のテスト
- エラーハンドリング・リトライの検証

---

## 1. `__init__` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 1 | API key明示指定 | 正常系 | api_key="test-key", model="gpt-4o-mini" | インスタンス作成成功、api_keyが設定される | High | test_init_with_explicit_api_key |
| 2 | API key環境変数から取得 | 正常系 | api_key=None, 環境変数OPENAI_API_KEY設定 | 環境変数から取得成功 | High | test_init_from_env_api_key |
| 3 | モデル名明示指定 | 正常系 | model="gpt-5-turbo" | 指定したモデル名が設定される | High | test_init_with_explicit_model |
| 4 | モデル名環境変数から取得 | 正常系 | model=None, 環境変数OPENAI_MODEL設定 | 環境変数から取得成功 | High | test_init_model_from_env |
| 5 | モデル名デフォルト値 | 正常系 | model=None, 環境変数なし | デフォルト"gpt-4.1-nano"が設定される | Medium | test_init_model_default_value |
| 6 | API key未指定・環境変数なし | 異常系 | api_key=None, 環境変数なし | ValueError発生 | High | test_init_no_api_key_raises_error |
| 7 | API keyが空文字 | 異常系 | api_key="" | ValueError発生 | High | test_init_empty_api_key_raises_error |
| 8 | モデル名が空文字 | 異常系 | model="" | ValueError発生 | Medium | test_init_empty_model_raises_error |
| 9 | tiktoken初期化成功（gpt-4） | 正常系 | デフォルト | gpt-4用encodingが取得される | Medium | test_init_tiktoken_encoding_success |
| 10 | tiktoken初期化失敗時のフォールバック | 異常系 | gpt-4のエンコーダーが取得不可 | cl100k_baseにフォールバック | Medium | test_init_tiktoken_fallback_to_cl100k_base |
| 11 | OpenAIクライアント初期化 | 正常系 | 正常なAPI key | OpenAI clientインスタンスが作成される | High | test_init_openai_client_created |
| 12 | API keyにNone型を明示指定 | 異常系 | api_key=None, 環境変数なし | ValueError発生 | High | test_init_none_api_key_no_env |

---

## 2. `_count_tokens` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 13 | 通常テキストのトークン数計算 | 正常系 | "Hello, world!" | 正の整数が返される | High | test_count_tokens_normal_text |
| 14 | 空文字のトークン数 | 境界値 | "" | 0が返される | High | test_count_tokens_empty_string |
| 15 | 日本語テキストのトークン数 | 正常系 | "こんにちは世界" | 正の整数が返される | High | test_count_tokens_japanese_text |
| 16 | 長文テキストのトークン数 | 正常系 | 10000文字の文字列 | 正の整数が返される | Medium | test_count_tokens_long_text |
| 17 | 特殊文字を含むテキスト | 正常系 | "!@#$%^&*()" | 正の整数が返される | Medium | test_count_tokens_special_characters |
| 18 | エンコードエラー時の処理 | 異常系 | encoding.encodeがException発生 | 0が返される | High | test_count_tokens_encoding_error_returns_zero |
| 19 | None入力時の処理 | 異常系 | None | Exception発生またはエラー処理 | High | test_count_tokens_none_input |
| 20 | 数値型入力 | 異常系 | 12345 | Exception発生 | Medium | test_count_tokens_numeric_input |
| 21 | Unicode特殊文字 | 正常系 | "😀🎉🌟" | 正の整数が返される | Medium | test_count_tokens_unicode_emoji |

---

## 3. `_calculate_cost` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 22 | 正常なコスト計算 | 正常系 | input_tokens=1000, output_tokens=500 | 正しいコスト（0.0006）が返される | High | test_calculate_cost_normal |
| 23 | 入力トークン0 | 境界値 | input_tokens=0, output_tokens=500 | output分のみのコストが返される | High | test_calculate_cost_zero_input_tokens |
| 24 | 出力トークン0 | 境界値 | input_tokens=1000, output_tokens=0 | input分のみのコストが返される | High | test_calculate_cost_zero_output_tokens |
| 25 | 両方とも0 | 境界値 | input_tokens=0, output_tokens=0 | 0.0が返される | High | test_calculate_cost_both_zero |
| 26 | 負の入力トークン数 | 異常系 | input_tokens=-100, output_tokens=500 | 負のコストまたはエラー | Medium | test_calculate_cost_negative_input_tokens |
| 27 | 負の出力トークン数 | 異常系 | input_tokens=1000, output_tokens=-100 | 負のコストまたはエラー | Medium | test_calculate_cost_negative_output_tokens |
| 28 | 巨大なトークン数 | 境界値 | input_tokens=10000000, output_tokens=5000000 | 正しいコストが返される | Medium | test_calculate_cost_large_numbers |
| 29 | 小数点以下の精度確認 | 正常系 | input_tokens=123, output_tokens=456 | 小数点以下の精度が保たれる | Medium | test_calculate_cost_decimal_precision |
| 30 | 文字列型の入力 | 異常系 | input_tokens="1000", output_tokens="500" | TypeError発生 | Medium | test_calculate_cost_string_input |

---

## 4. `_supports_max_completion_tokens` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 31 | gpt-5モデル（小文字） | 正常系 | model="gpt-5-turbo" | Trueが返される | High | test_supports_max_completion_tokens_gpt5_lowercase |
| 32 | gpt-5モデル（大文字） | 正常系 | model="GPT-5-TURBO" | Trueが返される | High | test_supports_max_completion_tokens_gpt5_uppercase |
| 33 | gpt-4.1モデル | 正常系 | model="gpt-4.1-nano" | Trueが返される | High | test_supports_max_completion_tokens_gpt41 |
| 34 | gpt-4oモデル（非対応） | 正常系 | model="gpt-4o-mini" | Falseが返される | High | test_supports_max_completion_tokens_gpt4o_false |
| 35 | gpt-4モデル（非対応） | 正常系 | model="gpt-4" | Falseが返される | High | test_supports_max_completion_tokens_gpt4_false |
| 36 | gpt-3.5モデル（非対応） | 正常系 | model="gpt-3.5-turbo" | Falseが返される | Medium | test_supports_max_completion_tokens_gpt35_false |
| 37 | 空文字モデル名 | 異常系 | model="" | Falseが返される | Medium | test_supports_max_completion_tokens_empty_model |
| 38 | gpt-5.1のような将来のモデル | 境界値 | model="gpt-5.1-advanced" | Trueが返される | Medium | test_supports_max_completion_tokens_gpt5_future |

---

## 5. `_is_gpt5_model` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 39 | gpt-5モデル判定（小文字） | 正常系 | model="gpt-5-turbo" | Trueが返される | High | test_is_gpt5_model_lowercase |
| 40 | gpt-5モデル判定（大文字） | 正常系 | model="GPT-5-PREVIEW" | Trueが返される | High | test_is_gpt5_model_uppercase |
| 41 | gpt-4.1は非GPT-5 | 正常系 | model="gpt-4.1-nano" | Falseが返される | High | test_is_gpt5_model_gpt41_false |
| 42 | gpt-4oは非GPT-5 | 正常系 | model="gpt-4o-mini" | Falseが返される | High | test_is_gpt5_model_gpt4o_false |
| 43 | 空文字モデル名 | 異常系 | model="" | Falseが返される | Medium | test_is_gpt5_model_empty_string |
| 44 | gpt-50のような将来モデル | 境界値 | model="gpt-50-ultra" | Trueが返される | Low | test_is_gpt5_model_gpt50 |

---

## 6. `_get_calling_service` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 45 | services/配下からの呼び出し | 正常系 | 呼び出し元がservices/reddit_explorer/ | "reddit_explorer"が返される | High | test_get_calling_service_from_services_dir |
| 46 | services/配下でない場合 | 正常系 | 呼び出し元がservices/外 | "unknown"が返される | High | test_get_calling_service_not_in_services |
| 47 | run_services.pyからの呼び出し | 異常系 | 呼び出し元がrun_services.py | スキップして次のフレームへ | Medium | test_get_calling_service_skip_run_services |
| 48 | __pycache__ディレクトリ | 異常系 | フレームに__pycache__が含まれる | スキップして次のフレームへ | Medium | test_get_calling_service_skip_pycache |
| 49 | .pyファイル名がサービス名 | 異常系 | service_name.pyのような形式 | スキップして次のフレームへ | Medium | test_get_calling_service_skip_py_filename |
| 50 | inspectエラー時の処理 | 異常系 | inspect.currentframe()がException | "unknown"が返される | Medium | test_get_calling_service_inspect_error |
| 51 | filepathがNoneの場合 | 異常系 | frame.f_code.co_filenameがNone | "unknown"が返される | Medium | test_get_calling_service_no_filepath |

---

## 7. `_messages_to_responses_input` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 52 | 正常なメッセージ変換 | 正常系 | [{"role": "user", "content": "Hello"}] | Responses API形式に変換される | High | test_messages_to_responses_input_normal |
| 53 | システムメッセージを含む | 正常系 | [{"role": "system", "content": "You are..."}, {"role": "user", "content": "Hi"}] | 両方のメッセージが変換される | High | test_messages_to_responses_input_with_system |
| 54 | 空のメッセージリスト | 境界値 | [] | 空リストが返される | High | test_messages_to_responses_input_empty_list |
| 55 | roleキーがない | 異常系 | [{"content": "Hello"}] | デフォルトで"user"が設定される | High | test_messages_to_responses_input_no_role |
| 56 | contentキーがない | 異常系 | [{"role": "user"}] | 空文字列""が設定される | High | test_messages_to_responses_input_no_content |
| 57 | role・content両方なし | 異常系 | [{}] | デフォルト値で変換される | Medium | test_messages_to_responses_input_empty_dict |
| 58 | 複数メッセージの変換 | 正常系 | 5件のメッセージリスト | 全て正しく変換される | Medium | test_messages_to_responses_input_multiple |
| 59 | assistantロールのメッセージ | 正常系 | [{"role": "assistant", "content": "Response"}] | assistant roleで変換される | Medium | test_messages_to_responses_input_assistant_role |

---

## 8. `_extract_text_from_response` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 60 | output_text属性がある場合 | 正常系 | resp.output_text="Response text" | "Response text"が返される | High | test_extract_text_output_text_attribute |
| 61 | output_textが空文字 | 境界値 | resp.output_text="" | 辞書から走査して抽出 | High | test_extract_text_empty_output_text |
| 62 | output_textがNone | 境界値 | resp.output_text=None | 辞書から走査して抽出 | High | test_extract_text_none_output_text |
| 63 | model_dumpメソッドで抽出 | 正常系 | resp.model_dump()で辞書取得 | テキストが抽出される | High | test_extract_text_via_model_dump |
| 64 | dictメソッドで抽出 | 正常系 | resp.dict()で辞書取得 | テキストが抽出される | High | test_extract_text_via_dict_method |
| 65 | __dict__属性で抽出 | 正常系 | resp.__dict__から取得 | テキストが抽出される | Medium | test_extract_text_via_dict_attribute |
| 66 | ネストされた構造から抽出 | 正常系 | {"output": [{"type": "output_text", "text": "Hello"}]} | "Hello"が抽出される | High | test_extract_text_nested_structure |
| 67 | 複数のテキスト要素 | 正常系 | 複数のoutput_textが存在 | 改行で結合されて返される | Medium | test_extract_text_multiple_texts |
| 68 | テキストが見つからない | 異常系 | レスポンスにテキスト要素なし | 空文字列""が返される | High | test_extract_text_no_text_found |
| 69 | すべてのメソッドが失敗 | 異常系 | model_dump, dict, __dict__全て例外 | 空文字列""が返される | Medium | test_extract_text_all_methods_fail |

---

## 9. `generate_content` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 70 | 基本的なテキスト生成（非GPT-5） | 正常系 | prompt="Hello", model="gpt-4o-mini" | テキストが生成される | High | test_generate_content_basic_gpt4 |
| 71 | system_instruction付き | 正常系 | system_instruction="You are...", prompt="Hello" | システムメッセージ含みで生成 | High | test_generate_content_with_system_instruction |
| 72 | temperature指定 | 正常系 | temperature=0.5 | 指定したtemperatureで呼び出し | Medium | test_generate_content_with_temperature |
| 73 | max_tokens指定 | 正常系 | max_tokens=2000 | 指定したmax_tokensで呼び出し | Medium | test_generate_content_with_max_tokens |
| 74 | GPT-5モデルの場合 | 正常系 | model="gpt-5-turbo" | _call_gpt5が呼ばれる | High | test_generate_content_gpt5_model |
| 75 | max_completion_tokens対応モデル | 正常系 | model="gpt-4.1-nano" | max_completion_tokensパラメータ使用 | High | test_generate_content_max_completion_tokens |
| 76 | service_name明示指定 | 正常系 | service_name="test_service" | 指定したservice_nameが使用される | Medium | test_generate_content_with_service_name |
| 77 | service_name未指定 | 正常系 | service_name=None | _get_calling_service()で自動取得 | Medium | test_generate_content_auto_service_name |
| 78 | OpenAI API エラー（401） | 異常系 | API認証エラー | 例外が発生（リトライ後） | High | test_generate_content_api_auth_error |
| 79 | OpenAI API エラー（429） | 異常系 | レート制限エラー | リトライ後に例外 | High | test_generate_content_rate_limit_error |
| 80 | OpenAI API エラー（500） | 異常系 | サーバーエラー | リトライ後に例外 | High | test_generate_content_server_error |
| 81 | タイムアウトエラー | 異常系 | APIタイムアウト | リトライ後に例外 | High | test_generate_content_timeout_error |
| 82 | ネットワークエラー | 異常系 | 接続エラー | リトライ後に例外 | Medium | test_generate_content_network_error |
| 83 | 空のプロンプト | 境界値 | prompt="" | 空または警告 | Medium | test_generate_content_empty_prompt |
| 84 | リトライ成功ケース | 正常系 | 1回目失敗、2回目成功 | 最終的に成功する | High | test_generate_content_retry_success |
| 85 | 3回リトライ後失敗 | 異常系 | 3回とも失敗 | 例外が発生 | High | test_generate_content_retry_exhausted |

---

## 10. `generate_async` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 86 | 基本的な非同期生成 | 正常系 | prompt="Hello" | 非同期でテキスト生成 | High | test_generate_async_basic |
| 87 | system_instruction付き | 正常系 | system_instruction="You are..." | システムメッセージ含みで非同期生成 | High | test_generate_async_with_system |
| 88 | 複数の非同期呼び出し | 正常系 | 3つの非同期呼び出しを並行実行 | 全て成功する | Medium | test_generate_async_multiple_concurrent |
| 89 | 非同期でのエラー | 異常系 | OpenAI APIエラー | 非同期で例外が発生 | High | test_generate_async_error |

---

## 11. `create_chat` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 90 | system_instructionなし | 正常系 | system_instruction=None | 空のmessagesリストを持つ辞書 | High | test_create_chat_without_system |
| 91 | system_instruction付き | 正常系 | system_instruction="You are..." | systemメッセージを含む辞書 | High | test_create_chat_with_system |
| 92 | 空のsystem_instruction | 境界値 | system_instruction="" | systemメッセージが追加されない | Medium | test_create_chat_empty_system |
| 93 | 戻り値の構造確認 | 正常系 | デフォルト | {"messages": [...]}の形式 | High | test_create_chat_return_structure |

---

## 12. `send_message` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 94 | 基本的なメッセージ送信（非GPT-5） | 正常系 | chat_session, message="Hi" | AIの応答が返される | High | test_send_message_basic_gpt4 |
| 95 | GPT-5モデルでの送信 | 正常系 | model="gpt-5-turbo" | _call_gpt5_chatが呼ばれる | High | test_send_message_gpt5 |
| 96 | チャット履歴が更新される | 正常系 | メッセージ送信後 | user/assistantメッセージが追加される | High | test_send_message_history_updated |
| 97 | 複数回のメッセージ送信 | 正常系 | 3回連続送信 | 履歴が正しく積み上がる | High | test_send_message_multiple_turns |
| 98 | 空のメッセージ | 境界値 | message="" | 空メッセージでも処理される | Medium | test_send_message_empty_message |
| 99 | temperature指定 | 正常系 | temperature=0.3 | 指定したtemperatureで呼び出し | Medium | test_send_message_with_temperature |
| 100 | max_tokens指定 | 正常系 | max_tokens=500 | 指定したmax_tokensで呼び出し | Medium | test_send_message_with_max_tokens |
| 101 | OpenAI APIエラー | 異常系 | API呼び出しでエラー | リトライ後に例外 | High | test_send_message_api_error |
| 102 | 不正なchat_session | 異常系 | chat_session={"invalid": True} | KeyErrorまたは例外 | High | test_send_message_invalid_session |

---

## 13. `chat_with_search` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 103 | 基本的な検索チャット（非GPT-5） | 正常系 | message="質問", context="コンテキスト" | AIの応答が返される | High | test_chat_with_search_basic_gpt4 |
| 104 | chat_historyなし | 正常系 | chat_history=None | 履歴なしで処理される | High | test_chat_with_search_no_history |
| 105 | chat_history付き | 正常系 | chat_history=[{...}, {...}] | 履歴を含めて処理される | High | test_chat_with_search_with_history |
| 106 | GPT-5モデルでの検索チャット | 正常系 | model="gpt-5-turbo" | _call_gpt5_chatが呼ばれる | High | test_chat_with_search_gpt5 |
| 107 | 空のcontext | 境界値 | context="" | 空コンテキストで処理される | Medium | test_chat_with_search_empty_context |
| 108 | 空のmessage | 境界値 | message="" | 空メッセージで処理される | Medium | test_chat_with_search_empty_message |
| 109 | temperature指定 | 正常系 | temperature=0.8 | 指定したtemperatureで呼び出し | Medium | test_chat_with_search_with_temperature |
| 110 | max_tokens指定 | 正常系 | max_tokens=1500 | 指定したmax_tokensで呼び出し | Medium | test_chat_with_search_with_max_tokens |
| 111 | OpenAI APIエラー | 異常系 | API呼び出しでエラー | リトライ後に例外 | High | test_chat_with_search_api_error |

---

## 14. `chat` メソッドのテスト

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 112 | 基本的なチャット（非GPT-5） | 正常系 | messages=[{"role": "user", "content": "Hi"}] | AIの応答が返される | High | test_chat_basic_gpt4 |
| 113 | systemメッセージなし | 正常系 | system=None | systemメッセージなしで処理 | High | test_chat_no_system |
| 114 | systemメッセージ付き | 正常系 | system="You are..." | systemメッセージ含みで処理 | High | test_chat_with_system |
| 115 | GPT-5モデルでのチャット | 正常系 | model="gpt-5-turbo" | _call_gpt5_chatが呼ばれる | High | test_chat_gpt5 |
| 116 | 複数ターンのメッセージ | 正常系 | messages=[user, assistant, user] | 複数メッセージで処理 | High | test_chat_multiple_messages |
| 117 | 空のmessagesリスト | 境界値 | messages=[] | 空リストで処理される | Medium | test_chat_empty_messages |
| 118 | temperature指定 | 正常系 | temperature=0.2 | 指定したtemperatureで呼び出し | Medium | test_chat_with_temperature |
| 119 | max_tokens指定 | 正常系 | max_tokens=3000 | 指定したmax_tokensで呼び出し | Medium | test_chat_with_max_tokens |
| 120 | OpenAI APIエラー | 異常系 | API呼び出しでエラー | リトライ後に例外 | High | test_chat_api_error |

---

## 15. `_call_gpt5` メソッドのテスト（内部メソッド）

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 121 | 基本的なGPT-5呼び出し | 正常系 | prompt="Hello", system_instruction="You are..." | output_textが返される | High | test_call_gpt5_basic |
| 122 | system_instructionなし | 正常系 | system_instruction=None | instructionsなしで呼び出し | High | test_call_gpt5_no_system |
| 123 | 1回目でoutput_text取得成功 | 正常系 | resp.output_textが存在 | 1回のAPI呼び出しで完了 | High | test_call_gpt5_first_attempt_success |
| 124 | 1回目失敗・2回目成功（継続生成） | 正常系 | 1回目output_text空、2回目成功 | previous_response_idで継続 | High | test_call_gpt5_continuation_success |
| 125 | 3回とも失敗 | 異常系 | 3回ともoutput_text空 | 空文字列または例外 | High | test_call_gpt5_all_attempts_fail |
| 126 | max_tokensの倍増 | 正常系 | 2回目以降のmax_tokens | 2倍になる | Medium | test_call_gpt5_max_tokens_doubled |

---

## 16. `_call_gpt5_chat` メソッドのテスト（内部メソッド）

| # | テスト観点 | 分類 | 入力値 | 期待結果 | 優先度 | テストメソッド名 |
|---|-----------|------|--------|---------|--------|----------------|
| 127 | 基本的なGPT-5チャット呼び出し | 正常系 | messages=[...] | output_textが返される | High | test_call_gpt5_chat_basic |
| 128 | system_instructionなし | 正常系 | system_instruction=None | instructionsなしで呼び出し | High | test_call_gpt5_chat_no_system |
| 129 | 1回目でoutput_text取得成功 | 正常系 | resp.output_textが存在 | 1回のAPI呼び出しで完了 | High | test_call_gpt5_chat_first_success |
| 130 | 1回目失敗・2回目成功（継続生成） | 正常系 | 1回目output_text空、2回目成功 | previous_response_idで継続 | High | test_call_gpt5_chat_continuation |
| 131 | 3回とも失敗 | 異常系 | 3回ともoutput_text空 | 空文字列が返される | High | test_call_gpt5_chat_all_fail |
| 132 | max_tokensの倍増 | 正常系 | 2回目以降のmax_tokens | 2倍になる | Medium | test_call_gpt5_chat_max_tokens_doubled |

---

## テストカバレッジ目標

### メソッド別カバレッジ
- 全メソッド: 95%以上
- 分岐カバレッジ: 90%以上
- 例外処理: 100%

### 優先度別実装順序
1. High優先度（初期化、主要メソッド、API呼び出し、エラーハンドリング）
2. Medium優先度（境界値、設定パラメータ）
3. Low優先度（将来の拡張性確認）

### テスト実行
```bash
# 全テスト実行
pytest tests/common/test_gpt_client.py -v

# カバレッジ測定
pytest tests/common/test_gpt_client.py --cov=nook.common.gpt_client --cov-report=html

# 特定のテストのみ実行
pytest tests/common/test_gpt_client.py -k "test_init" -v
```
