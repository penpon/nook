# TASK-017: .envファイルのシンタックスエラー修正

## タスク概要
.envファイルの10行目でシェルのシンタックスエラーが発生しています。REDDIT_USER_AGENTの値に括弧が含まれているため、scripts/crawl_all.shがこのファイルを読み込む際にエラーになります。

## 問題の詳細
- エラーメッセージ: `.env: line 10: syntax error near unexpected token '('`
- 問題の行: `REDDIT_USER_AGENT=python:nook:v1.0 (by /u/UsefulMeasurement407)`
- 原因: シェルが括弧を特殊文字として解釈

## 変更予定ファイル
- .env

## 前提タスク
- なし（独立したタスク）

## 実装内容

1. .envファイルの10行目を修正
2. 値をダブルクォートで囲む

## 修正例

修正前:
```
REDDIT_USER_AGENT=python:nook:v1.0 (by /u/UsefulMeasurement407)
```

修正後:
```
REDDIT_USER_AGENT="python:nook:v1.0 (by /u/UsefulMeasurement407)"
```

## テスト方法
1. 修正後、scripts/crawl_all.shを実行
2. .envファイルのシンタックスエラーが発生しないことを確認
3. 環境変数が正しく設定されることを確認

## 注意事項
- 他の環境変数も括弧や特殊文字を含む場合は同様にクォートで囲む必要がある
- シェルスクリプトで読み込む際の互換性を考慮