# TASK-013: サービス名検出ロジックの修正

## タスク概要
GPTClientのサービス名検出ロジックを修正して、正しいサービス名がログに記録されるようにする。現在「thread」として誤記録される問題を解決する。

## 問題の詳細
- 現在の`_get_calling_service`メソッドはスタックフレームのファイル名を使用
- 非同期実行時にPython内部の`thread.py`が検出されて「thread」として記録される
- 実際は`paper_summarizer`などのサービスが実行されているのに誤記録される

## 実装内容

### 1. GPTClientの修正（`nook/common/gpt_client.py`）

#### generate_content メソッドの修正
```python
def generate_content(
    self, 
    prompt: str, 
    system_instruction: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    service_name: Optional[str] = None  # 追加
) -> str:
    # ...
    # トークン数の計算
    service = service_name or self._get_calling_service()  # 修正
    # ...
```

#### generate_async メソッドの修正
```python
async def generate_async(
    self, 
    prompt: str, 
    system_instruction: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    service_name: Optional[str] = None  # 追加
) -> str:
    # ...
    service = service_name or self._get_calling_service()  # 修正
    # ...
```

#### _generate_summaries_from_thread メソッドの修正
```python
async def _generate_summaries_from_thread(
    self, 
    threads: List[Dict], 
    model: str = "gpt-4.1-nano",
    service_name: Optional[str] = None  # 追加
) -> List[str]:
    # ...
    service = service_name or self._get_calling_service()  # 修正
    # ...
```

#### _generate_with_chain_of_thought メソッドの修正
```python
async def _generate_with_chain_of_thought(
    self, 
    prompt: str, 
    threads: List[Dict], 
    model: str = "gpt-4.1-nano",
    service_name: Optional[str] = None  # 追加
) -> List[str]:
    # ...
    service = service_name or self._get_calling_service()  # 修正
    # ...
```

### 2. _get_calling_serviceメソッドの改善
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
                        if service_name == 'run_services.py':
                            continue
                        return service_name
                
                filename = filepath.name
                if filename not in ['gpt_client.py', 'openai.py', 'tenacity.py', 'thread.py'] and not filename.startswith('_'):
                    return filename.replace('.py', '')
        return 'unknown'
    except Exception:
        return 'unknown'
```

### 3. BaseServiceの修正（`nook/common/base_service.py`）

BaseServiceでgpt_clientを使用している箇所がある場合、service_nameを渡すように修正：
```python
# 例：
response = await self.gpt_client.generate_async(
    prompt=prompt,
    service_name=self.service_name  # 追加
)
```

## 変更予定ファイル
- `nook/common/gpt_client.py`
- `nook/common/base_service.py`（必要に応じて）

## 前提タスク
なし

## テスト方法
1. paper_summarizerサービスを実行
2. `data/api_usage/llm_usage_log.jsonl`を確認
3. 新しいログエントリーが「thread」ではなく「paper_summarizer」として記録されることを確認
4. 他のサービスも同様に正しく記録されることを確認

## 注意事項
- 後方互換性を維持するため、service_name引数はOptionalとする
- 既存のコードは変更なしで動作するようにする
- _get_calling_serviceメソッドの改善により、service_nameが指定されていない場合でも、より正確な検出が可能になる