# テスト実行とカバレッジ取得方法

## 概要

本ドキュメントでは、Nookプロジェクトの全サービステストの実行方法とカバレッジ測定方法を説明します。

## 前提条件

```bash
# Python仮想環境のアクティベート
source .venv/bin/activate

# 必要なパッケージのインストール（初回のみ）
uv pip install -r requirements-test.txt
```

## テスト実行コマンド

### 1. 全テスト実行

```bash
# 全テスト実行（簡潔出力）
pytest tests/services/ -v

# 全テスト実行（詳細出力）
pytest tests/services/ -vv

# 全テスト実行（失敗時のみスタックトレース表示）
pytest tests/services/ -v --tb=short
```

### 2. 特定サービスのテスト実行

#### BaseFeedService系サービス

```bash
# TechFeed
pytest tests/services/test_tech_feed.py -v

# BusinessFeed
pytest tests/services/test_business_feed.py -v

# ZennExplorer
pytest tests/services/test_zenn_explorer.py -v

# QiitaExplorer
pytest tests/services/test_qiita_explorer.py -v

# NoteExplorer
pytest tests/services/test_note_explorer.py -v
```

#### BaseService系サービス

```bash
# GitHubTrending
pytest tests/services/test_github_trending.py -v

# HackerNews
pytest tests/services/test_hacker_news.py -v

# RedditExplorer
pytest tests/services/test_reddit_explorer.py -v

# ArxivSummarizer
pytest tests/services/test_arxiv_summarizer.py -v

# FourChanExplorer
pytest tests/services/test_fourchan_explorer.py -v

# FiveChanExplorer
pytest tests/services/test_fivechan_explorer.py -v
```

### 3. 特定のテストケース実行

```bash
# 特定のテスト関数のみ実行
pytest tests/services/test_tech_feed.py::test_init_with_service_name -v

# パターンマッチでテスト実行
pytest tests/services/ -k "test_collect" -v

# マーカー指定でテスト実行
pytest tests/services/ -m unit -v
```

### 4. 並列実行（高速化）

```bash
# 自動並列数（CPUコア数に応じて）
pytest tests/services/ -n auto

# 並列数を指定
pytest tests/services/ -n 4
```

## カバレッジ測定

### 1. 基本的なカバレッジ測定

```bash
# サービス全体のカバレッジ測定
pytest tests/services/ --cov=nook/services --cov-report=term

# カバレッジ測定（未カバー行表示）
pytest tests/services/ --cov=nook/services --cov-report=term-missing

# カバレッジ測定（分岐カバレッジ含む）
pytest tests/services/ --cov=nook/services --cov-branch --cov-report=term
```

### 2. HTMLレポート生成

```bash
# HTMLレポート生成
pytest tests/services/ --cov=nook/services --cov-report=html

# ブラウザでレポート表示
open htmlcov/index.html
```

### 3. サービス別カバレッジ測定

```bash
# TechFeedのカバレッジ
pytest tests/services/test_tech_feed.py \
  --cov=nook/services/tech_feed \
  --cov-report=term-missing

# GitHubTrendingのカバレッジ
pytest tests/services/test_github_trending.py \
  --cov=nook/services/github_trending \
  --cov-report=term-missing

# 複数サービスのカバレッジ
pytest tests/services/test_tech_feed.py tests/services/test_github_trending.py \
  --cov=nook/services/tech_feed \
  --cov=nook/services/github_trending \
  --cov-report=term-missing
```

### 4. 詳細カバレッジレポート

```bash
# JSON形式でカバレッジ出力
pytest tests/services/ \
  --cov=nook/services \
  --cov-report=json

# XML形式でカバレッジ出力（CI/CD用）
pytest tests/services/ \
  --cov=nook/services \
  --cov-report=xml

# 複数フォーマット同時出力
pytest tests/services/ \
  --cov=nook/services \
  --cov-report=term \
  --cov-report=html \
  --cov-report=json \
  --cov-report=xml
```

### 5. カバレッジ閾値チェック

```bash
# カバレッジ95%未満でFAIL
pytest tests/services/ \
  --cov=nook/services \
  --cov-report=term \
  --cov-fail-under=95

# カバレッジ80%未満でFAIL
pytest tests/services/ \
  --cov=nook/services \
  --cov-report=term \
  --cov-fail-under=80
```

## 高度なテスト実行オプション

### 1. デバッグオプション

```bash
# 最初の失敗で停止
pytest tests/services/ -x

# 最初のN個の失敗で停止
pytest tests/services/ --maxfail=3

# 標準出力を表示
pytest tests/services/ -s

# PDB（Python Debugger）起動
pytest tests/services/ --pdb
```

### 2. テスト選択オプション

```bash
# 前回失敗したテストのみ再実行
pytest tests/services/ --lf

# 前回失敗したテストを先に実行
pytest tests/services/ --ff

# 新規/変更されたテストのみ実行
pytest tests/services/ --testmon
```

### 3. 出力制御

```bash
# 簡潔出力
pytest tests/services/ -q

# 非常に簡潔出力
pytest tests/services/ -qq

# 詳細出力
pytest tests/services/ -v

# 非常に詳細出力
pytest tests/services/ -vv
```

### 4. 警告制御

```bash
# 警告を表示
pytest tests/services/ -W default

# 警告をエラーとして扱う
pytest tests/services/ -W error

# 警告を無視
pytest tests/services/ -W ignore
```

## カバレッジ結果の解釈

### カバレッジメトリクス

```
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
tech_feed/tech_feed.py              164     52    68%   138-158, 171-223
```

- **Stmts**: 総ステートメント数
- **Miss**: 未実行ステートメント数
- **Cover**: カバレッジ率（%）
- **Missing**: 未実行行番号

### 分岐カバレッジ

```bash
pytest tests/services/ --cov=nook/services --cov-branch --cov-report=term
```

```
Name                              Stmts   Miss Branch BrPart  Cover
--------------------------------------------------------------------
tech_feed/tech_feed.py              164     52     62      9   65%
```

- **Branch**: 総分岐数
- **BrPart**: 部分的にカバーされた分岐数

### カバレッジ目標

| メトリクス | 目標値 | 説明 |
|-----------|--------|------|
| 行カバレッジ | 95%以上 | コード行の実行率 |
| 分岐カバレッジ | 90%以上 | if/else等の分岐網羅率 |
| 関数カバレッジ | 100% | 全関数の実行 |

## CI/CD統合

### GitHub Actions設定例

```yaml
name: Test Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -r requirements-test.txt

      - name: Run tests with coverage
        run: |
          pytest tests/services/ \
            --cov=nook/services \
            --cov-report=xml \
            --cov-fail-under=95

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## トラブルシューティング

### 問題: カバレッジが0%と表示される

```bash
# 原因: ソースファイルが正しく指定されていない
# 解決: --cov オプションで正しいパスを指定

pytest tests/services/test_tech_feed.py \
  --cov=nook/services/tech_feed \
  --cov-report=term-missing
```

### 問題: テストが遅い

```bash
# 解決策1: 並列実行
pytest tests/services/ -n auto

# 解決策2: 特定のテストのみ実行
pytest tests/services/ -k "test_init" -v

# 解決策3: 失敗時に停止
pytest tests/services/ -x
```

### 問題: モックが動作しない

```bash
# デバッグモードで実行
pytest tests/services/test_tech_feed.py -vv -s

# 特定のテストのみデバッグ
pytest tests/services/test_tech_feed.py::test_collect_success -vv -s --pdb
```

## まとめ

### 推奨コマンド

```bash
# 開発時の基本コマンド
pytest tests/services/ -v --tb=short

# カバレッジ確認
pytest tests/services/ \
  --cov=nook/services \
  --cov-report=term-missing \
  --cov-report=html

# CI/CD用
pytest tests/services/ \
  --cov=nook/services \
  --cov-report=xml \
  --cov-fail-under=95 \
  -n auto
```

### カバレッジレポートの確認

```bash
# HTMLレポート生成と表示
pytest tests/services/ --cov=nook/services --cov-report=html
open htmlcov/index.html

# ターミナルで確認
pytest tests/services/ --cov=nook/services --cov-report=term-missing
```
