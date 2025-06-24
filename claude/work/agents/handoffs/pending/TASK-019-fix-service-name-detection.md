# TASK-019: gpt_client.pyのサービス名検出ロジック修正

## タスク概要
LLM使用量ダッシュボードでサービス名が表示されない問題を修正します。`thread`という誤ったサービス名が記録される原因となっている、サービス名検出ロジックを改善します。

## 問題の詳細
- 4chan/5chanサービスが内部で`Thread`クラスを使用
- `gpt_client.py`の`_get_calling_service()`が`thread.py`をサービス名として認識
- `services/`ディレクトリ外のファイルもサービス名として使用される

## 変更予定ファイル
- nook/common/gpt_client.py

## 前提タスク
- なし（独立したタスク）

## 実装内容

`_get_calling_service()`メソッドを以下のように修正：

```python
def _get_calling_service(self) -> str:
    """呼び出し元のサービス名を取得します。"""
    try:
        frame = inspect.currentframe()
        while frame:
            frame = frame.f_back
            if frame and frame.f_code.co_filename:
                filepath = Path(frame.f_code.co_filename)
                # services/ディレクトリ内のファイルを検出
                if 'services' in filepath.parts:
                    # services/の次のディレクトリ名をサービス名として使用
                    service_idx = filepath.parts.index('services')
                    if service_idx + 1 < len(filepath.parts):
                        service_name = filepath.parts[service_idx + 1]
                        # 特殊ケースの処理
                        if service_name in ['run_services.py', 'run_services_sync.py']:
                            continue
                        # __pycache__や.pyファイルを除外
                        if service_name.startswith('__') or service_name.endswith('.py'):
                            continue
                        return service_name
        # services/ディレクトリ内でない場合はunknownを返す
        return 'unknown'
    except Exception:
        return 'unknown'
```

## テスト方法
1. 修正後、いずれかのサービスを実行
2. `data/api_usage/llm_usage_log.jsonl`に正しいサービス名が記録されることを確認
3. ダッシュボードでサービス名が正しく表示されることを確認

## 注意事項
- 既存のログデータは別タスクで修正が必要
- 今後は`generate_content`の`service_name`パラメータを積極的に使用することを推奨