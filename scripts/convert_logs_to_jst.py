#!/usr/bin/env python3
"""Docker logsのUTCタイムスタンプをJSTに変換するスクリプト"""

import re
import sys
from datetime import datetime, timedelta, timezone

# JSTタイムゾーン
JST = timezone(timedelta(hours=9))

# タイムスタンプのパターン
pattern = re.compile(
    r"^(.*?\s+\|\s+)(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)Z(\s+.*)$"
)

for line in sys.stdin:
    match = pattern.match(line)
    if match:
        prefix = match.group(1)
        timestamp_str = match.group(2)
        suffix = match.group(3)

        # UTCタイムスタンプをパース
        utc_time = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)

        # JSTに変換
        jst_time = utc_time.astimezone(JST)

        # 新しい形式で出力
        print(
            f"{prefix}{jst_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} JST{suffix.rstrip()}"
        )
    else:
        # タイムスタンプがない行はそのまま出力
        print(line, end="")
