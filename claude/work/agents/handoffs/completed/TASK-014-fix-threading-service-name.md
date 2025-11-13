# TASK-014: threadingサービス名記録問題の修正

## タスク概要
LLM API使用状況ダッシュボードで「threading」というサービス名が記録される問題を修正する。

## 現状の問題
- `nook/common/gpt_client.py`の`_get_calling_service()`メソッドが、Pythonの`threading`モジュールをサービス名として記録している
- これは実際のサービスではなく、実行環境に由来する名前

## 修正内容
`_get_calling_service()`メソッドをホワイトリスト方式に変更し、`nook/services/`配下のファイルのみをサービスとして認識するようにする。

## 変更予定ファイル
- nook/common/gpt_client.py

## 前提タスク
- なし（単独で実行可能）

## 実装詳細

### 修正前の問題のあるコード（81-101行目）
```python
def _get_calling_service(self) -> str:
    """呼び出し元のサービス名を取得します。"""
    try:
        import inspect
        import os
        
        excluded_dirs = ['gpt_client', 'openai', 'httpx', 'tenacity']
        
        for frame_info in inspect.stack()[2:]:
            frame = frame_info.frame
            filename = frame.f_code.co_filename
            
            # 除外ディレクトリのチェック
            if any(excluded in filename for excluded in excluded_dirs):
                continue
                
            # ファイル名からサービス名を抽出
            if '/' in filename:
                parts = filename.split('/')
                for i, part in enumerate(parts):
                    if part == 'services' and i + 1 < len(parts):
                        return parts[i + 1]
                # servicesディレクトリが見つからない場合は、最後のディレクトリ名を使用
                filename = os.path.basename(os.path.dirname(filename))
                if filename and filename not in excluded_dirs:
                    return filename.replace('.py', '')
        return 'unknown'
    except Exception:
        return 'unknown'
```

### 修正後のコード
```python
def _get_calling_service(self) -> str:
    """呼び出し元のサービス名を取得します。"""
    try:
        import inspect
        import os
        
        # nook/services/配下のファイルのみをサービスとして認識
        for frame_info in inspect.stack()[2:]:
            frame = frame_info.frame
            filename = frame.f_code.co_filename
            
            # nook/services/を含むパスのみを対象とする
            if '/nook/services/' in filename:
                # ファイル名からサービス名を抽出
                parts = filename.split('/')
                for i, part in enumerate(parts):
                    if part == 'services' and i + 1 < len(parts):
                        # services/の次のディレクトリ名をサービス名として使用
                        service_name = parts[i + 1]
                        # .pyファイルの場合は拡張子を除去
                        if service_name.endswith('.py'):
                            service_name = service_name[:-3]
                        return service_name
        
        # nook/services/配下の呼び出しが見つからない場合
        return 'unknown'
    except Exception:
        return 'unknown'
```

## テスト方法
1. 修正後、各サービス（tech_feed, reddit_explorer等）からgpt_clientを呼び出してログを確認
2. threadingやその他のPythonライブラリ名が記録されないことを確認
3. 正当なサービス名が正しく記録されることを確認

## worktree名
TASK-014-backend