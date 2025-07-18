#!/usr/bin/env python3
"""
LLM使用量ログの修正スクリプト
service: "thread" を service: "chan_explorer" に変更
"""

import json
from datetime import datetime
from pathlib import Path


def fix_llm_usage_logs():
    """LLM使用量ログファイルのthreadエントリを修正"""
    log_file = Path("data/api_usage/llm_usage_log.jsonl")

    # ファイルが存在しない場合は終了
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return

    # 一時ファイルのパス
    temp_file = log_file.with_suffix(".tmp")

    # 統計情報
    total_lines = 0
    fixed_lines = 0
    error_lines = 0

    print(f"Processing: {log_file}")

    # ファイルを読み込んで修正
    with open(log_file, encoding="utf-8") as f_in, open(
        temp_file, "w", encoding="utf-8"
    ) as f_out:

        for line_num, line in enumerate(f_in, 1):
            total_lines += 1
            line = line.strip()

            if not line:  # 空行はスキップ
                continue

            try:
                data = json.loads(line)

                # threadを chan_explorer に変更
                if data.get("service") == "thread":
                    data["service"] = "chan_explorer"
                    fixed_lines += 1

                # 修正したデータを書き出し
                f_out.write(json.dumps(data, ensure_ascii=False) + "\n")

            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                error_lines += 1
                # エラーが発生した行はそのまま出力
                f_out.write(line + "\n")

    # バックアップファイルの作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = log_file.with_name(
        f"{log_file.stem}_backup_{timestamp}{log_file.suffix}"
    )

    # 元のファイルをバックアップ
    log_file.rename(backup_file)

    # 修正済みファイルをリネーム
    temp_file.rename(log_file)

    # 結果の表示
    print("\n=== 修正完了 ===")
    print(f"処理行数: {total_lines}")
    print(f"修正行数: {fixed_lines}")
    print(f"エラー行数: {error_lines}")
    print(f"バックアップ: {backup_file}")
    print(f"修正済みファイル: {log_file}")


if __name__ == "__main__":
    fix_llm_usage_logs()
