# 拡張版クローラー使用ガイド

## 概要
`crawl_scheduled.sh`は、日付や時刻、曜日などの条件を指定してクローリングを実行できる拡張版スクリプトです。

**重要な変更**: 現在日付に関係なく、指定した日付でクローリングを実行できるようになりました。これにより過去のデータの再取得や、将来の日付での事前実行が可能です。

## 主な機能

### 1. 日付指定実行
特定の日付でのみ実行したい場合：
```bash
# 2025年7月1日のデータを取得
./crawl_scheduled.sh --date 2025-07-01

# 過去の日付のデータを再取得
./crawl_scheduled.sh --date 2025-06-30

# 時刻も指定（9時と18時）
./crawl_scheduled.sh --date 2025-07-01 --time 09:00,18:00
```

**注意**: データソースによっては過去のデータが取得できない場合があります。現在のデータが返される可能性があります。

### 2. 日付範囲実行
期間を指定して実行：
```bash
# 7月1日から7月7日まで毎日実行
./crawl_scheduled.sh --from 2025-07-01 --to 2025-07-07

# 期間中の9時と17時に実行
./crawl_scheduled.sh --from 2025-07-01 --to 2025-07-07 --time 09:00,17:00
```

### 3. 曜日指定実行
特定の曜日のみ実行：
```bash
# 月曜と金曜のみ
./crawl_scheduled.sh --weekday monday,friday

# 平日（月〜金）の業務時間
./crawl_scheduled.sh --weekday monday,tuesday,wednesday,thursday,friday --time 09:00,12:00,17:00
```

### 4. 営業日実行
日本の祝日と週末を除外：
```bash
# 営業日のみ実行
./crawl_scheduled.sh --business-days-only

# 営業日の9時と17時
./crawl_scheduled.sh --business-days-only --time 09:00,17:00
```

### 5. Dry-runモード
実際には実行せず、実行予定を確認：
```bash
# 7月の実行予定を確認
./crawl_scheduled.sh --dry-run --from 2025-07-01 --to 2025-07-31 --time 09:00,17:00

# 営業日の実行予定を確認
./crawl_scheduled.sh --dry-run --business-days-only --from 2025-07-01 --to 2025-07-31
```

### 6. サービス選択
特定のサービスのみ実行：
```bash
# HackerNewsとGitHubのみ
./crawl_scheduled.sh --services hacker_news,github_trending

# 軽量サービスのみ週末実行
./crawl_scheduled.sh --weekday saturday,sunday --services hacker_news,reddit
```

## crontabとの連携

### 基本的な設定
```bash
# 毎時0分に条件をチェックして実行
0 * * * * /path/to/crawl_scheduled.sh --business-days-only --time 09:00,12:00,17:00 >> /path/to/logs/scheduled_crawl.log 2>&1

# 5分ごとに時刻をチェック（より正確な時刻実行）
*/5 * * * * /path/to/crawl_scheduled.sh --weekday monday,wednesday,friday --time 09:00,14:00,18:00 >> /path/to/logs/scheduled_crawl.log 2>&1
```

### 高度な設定例

#### 1. 月初営業日の特別実行
```bash
# 月初（1-7日）の営業日9時に全サービス実行
0 9 1-7 * * /path/to/crawl_scheduled.sh --business-days-only --services ALL
```

#### 2. 四半期末の集中実行
```bash
# 3,6,9,12月の最終週に集中実行
0 */3 24-31 3,6,9,12 * /path/to/crawl_scheduled.sh --business-days-only --time 09:00,12:00,15:00,18:00
```

#### 3. スケジュールファイルを使用
```bash
# 外部スケジュールファイルで管理
0 * * * * /path/to/crawl_scheduled.sh --schedule-file /path/to/schedule.txt
```

## スケジュールファイルの書き方

`schedule.txt`の例：
```
# 特定日付の実行
2025-07-01 09:00 ALL
2025-07-15 18:00 hacker_news,github_trending

# 曜日ベースの実行
monday,wednesday,friday 09:00 ALL
tuesday,thursday 14:00 tech_news,arxiv

# 営業日実行
business_days 09:00,17:00 ALL
```

## トラブルシューティング

### 1. 実行されない場合
```bash
# dry-runで条件を確認
./crawl_scheduled.sh --dry-run --verbose [オプション]

# ログを確認
tail -f logs/scheduled_crawl.log
```

### 2. 日付計算エラー
```bash
# GNU date（Linux）とBSD date（macOS）の違いに注意
# macOS の場合は GNU coreutils をインストール
brew install coreutils
```

### 3. 祝日が反映されない
スクリプト内の`JAPANESE_HOLIDAYS`配列を更新してください。

## パフォーマンス考慮事項

1. **頻繁なチェックを避ける**
   - crontabで毎分実行は避ける
   - 5分または10分間隔を推奨

2. **サービスの分散**
   - 全サービス同時実行は避ける
   - 時間帯でサービスを分散

3. **リソース監視**
   ```bash
   # 実行前後のリソース確認
   ./crawl_scheduled.sh --dry-run --verbose
   ```

## セキュリティ

1. **ログファイルの管理**
   ```bash
   # ログローテーション設定
   logrotate -f /etc/logrotate.d/crawl_scheduled
   ```

2. **実行権限**
   ```bash
   # 適切な権限設定
   chmod 750 crawl_scheduled.sh
   chown user:group crawl_scheduled.sh
   ```

## 今後の拡張案

1. **通知機能**
   - 実行完了時のSlack通知
   - エラー時のメール通知

2. **統計機能**
   - 実行履歴の記録
   - 成功/失敗率の集計

3. **動的スケジュール**
   - APIから取得したスケジュール
   - 外部カレンダーとの連携

4. **分散実行**
   - 複数サーバーでの協調実行
   - ロードバランシング