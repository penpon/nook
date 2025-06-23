# TASK-001: GROK_API_KEY参照のOPENAI_API_KEY移行

## タスクの概要
run_services.pyとchat.pyに残存するGROK_API_KEY参照をOPENAI_API_KEYに修正する。

## 背景
- プロジェクトは2025年6月23日にGrok APIからGPT-4.1-nano APIへ移行済み
- しかし一部のファイルにGROK_API_KEYへの参照が残っている
- これによりpaper_summarizerが「GROK_API_KEYが設定されていません」エラーを出す

## 修正内容

### 1. run_services.py（行160-163）
```python
# 現在のコード
if not os.environ.get("GROK_API_KEY"):
    print("警告: GROK_API_KEY が設定されていません。")
    print("論文要約には Grok API が必要です。")
    return

# 修正後のコード
if not os.environ.get("OPENAI_API_KEY"):
    print("警告: OPENAI_API_KEY が設定されていません。")
    print("論文要約には OpenAI API (GPT-4.1-nano) が必要です。")
    return
```

### 2. chat.py（行43-48）
```python
# 現在のコード
api_key = os.environ.get("GROK_API_KEY")
if not api_key:
    return ChatResponse(
        response="申し訳ありませんが、GROK_API_KEYが設定されていないため、実際の応答ができません。環境変数を設定してください。"
    )

# 修正後のコード
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    return ChatResponse(
        response="申し訳ありませんが、OPENAI_API_KEYが設定されていないため、実際の応答ができません。環境変数を設定してください。"
    )
```

## 実装手順
1. run_services.pyを開き、160-163行目を修正
2. chat.pyを開き、43-48行目を修正
3. 変更をコミット

## テスト方法
1. `python -m nook.services.run_services --service paper`を実行
2. OPENAI_API_KEYが設定されていれば正常に動作することを確認
3. OPENAI_API_KEYを削除して実行し、適切なエラーメッセージが表示されることを確認

## 完了条件
- [ ] run_services.pyのGROK_API_KEY参照を修正
- [ ] chat.pyのGROK_API_KEY参照を修正
- [ ] 動作確認完了
- [ ] 変更をコミット