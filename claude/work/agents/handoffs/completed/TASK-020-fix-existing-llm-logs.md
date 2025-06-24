# TASK-020: 既存のLLM使用ログデータを修正

## タスク概要
`data/api_usage/llm_usage_log.jsonl`に記録された誤った`service: "thread"`エントリを修正します。

## 問題の詳細
- 4chan/5chanサービスの実行時に`thread`という誤ったサービス名が記録された
- ダッシュボードでサービス名が表示されない原因となっている

## 変更予定ファイル
- data/api_usage/llm_usage_log.jsonl

## 前提タスク
- TASK-019（gpt_client.pyの修正）- 新規データの問題を防ぐため

## 実装内容

1. `llm_usage_log.jsonl`を読み込み、修正されたデータを書き出すスクリプトを作成
2. 修正ロジック：
   - `"service": "thread"` → `"service": "chan_explorer"`に変更
   - または時刻や内容から推測できる場合は適切なサービス名に変更

### 修正スクリプトの例

```python
import json
from pathlib import Path

def fix_llm_usage_logs():
    log_file = Path("data/api_usage/llm_usage_log.jsonl")
    temp_file = log_file.with_suffix('.tmp')
    
    with open(log_file, 'r') as f_in, open(temp_file, 'w') as f_out:
        for line in f_in:
            try:
                data = json.loads(line.strip())
                # threadを適切なサービス名に変更
                if data.get('service') == 'thread':
                    # 時刻やpromptの内容から推測可能な場合は特定のサービス名に
                    # そうでない場合はchan_explorerという汎用名に
                    data['service'] = 'chan_explorer'
                
                f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
            except json.JSONDecodeError:
                # 不正な行はそのまま出力
                f_out.write(line)
    
    # バックアップを作成してからファイルを置き換え
    backup_file = log_file.with_suffix('.bak')
    log_file.rename(backup_file)
    temp_file.rename(log_file)
    print(f"Backup saved to: {backup_file}")
    print(f"Log file fixed: {log_file}")

if __name__ == "__main__":
    fix_llm_usage_logs()
```

## テスト方法
1. スクリプト実行前にバックアップを確認
2. スクリプトを実行
3. ダッシュボードを確認し、サービス名が表示されることを確認

## 注意事項
- 必ずバックアップを作成してから実行
- 大量のデータがある場合は処理に時間がかかる可能性がある
- 修正後はダッシュボードのキャッシュをクリアする必要があるかもしれない