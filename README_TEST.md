# Nook プロジェクト テスト実行ガイド

このドキュメントでは、Nookプロジェクトのテスト実行方法とカバレッジ取得方法を説明します。

## 📋 目次

- [環境セットアップ](#環境セットアップ)
- [テスト実行方法](#テスト実行方法)
- [カバレッジ測定](#カバレッジ測定)
- [テスト構成](#テスト構成)
- [CI/CD](#cicd)

---

## 🔧 環境セットアップ

### 1. 依存関係のインストール

```bash
# プロジェクトルートディレクトリで実行
uv sync --group dev

# または、テスト専用の依存関係のみインストール
uv pip install -r requirements-test.txt
```

### 2. 必要なパッケージ

テスト実行に必要な主要パッケージ：
- `pytest>=7.4.0` - テストフレームワーク
- `pytest-asyncio>=0.21.0` - 非同期テスト対応
- `pytest-cov>=4.1.0` - カバレッジ測定
- `pytest-mock>=3.11.0` - モック機能
- `respx>=0.20.0` - HTTPモック
- `httpx[http2]>=0.24.0` - テスト用HTTPクライアント
- `faker>=19.0.0` - テストデータ生成
- `freezegun>=1.2.0` - 時刻固定

---

## 🧪 テスト実行方法

### 全テスト実行

```bash
# tests/ディレクトリ配下の全テストを実行
pytest tests/

# 詳細表示（-v: verbose）
pytest tests/ -v

# 並列実行（高速化）
pytest tests/ -n auto
```

### 特定のモジュール/ファイルのみ実行

```bash
# 共通モジュールのテストのみ
pytest tests/common/

# 特定のファイルのみ
pytest tests/common/test_gpt_client.py

# 特定のテストケースのみ
pytest tests/common/test_storage.py::test_save_json_normal
```

### テストマーカーによる絞り込み

```bash
# ユニットテストのみ実行
pytest tests/ -m unit

# 統合テストを除外（CI環境で推奨）
pytest tests/ -m "not integration"

# 遅いテストを除外
pytest tests/ -m "not slow"
```

### デバッグオプション

```bash
# 最初の失敗で停止
pytest tests/ -x

# 失敗したテストのみ再実行
pytest tests/ --lf

# より詳細なトレースバック
pytest tests/ --tb=long

# 標準出力を表示
pytest tests/ -s
```

---

## 📊 カバレッジ測定

### 基本的なカバレッジ測定

```bash
# ターミナルにカバレッジを表示
pytest tests/common/ --cov=nook/common --cov-report=term

# 未カバー行を表示
pytest tests/common/ --cov=nook/common --cov-report=term-missing
```

### HTMLレポート生成

```bash
# HTMLカバレッジレポートを生成
pytest tests/common/ --cov=nook/common --cov-report=html

# ブラウザで確認
open htmlcov/index.html
```

### 全体カバレッジ確認

```bash
# nook/common/モジュール全体
pytest tests/common/ --cov=nook/common --cov-report=term

# プロジェクト全体（services含む）
pytest tests/ --cov=nook --cov-report=term --cov-report=html
```

### カバレッジ閾値チェック

```bash
# カバレッジが95%未満なら失敗
pytest tests/common/ --cov=nook/common --cov-fail-under=95
```

### 特定モジュールのカバレッジ

```bash
# gpt_client.pyのカバレッジのみ
pytest tests/common/test_gpt_client.py \
  --cov=nook/common/gpt_client \
  --cov-report=term-missing

# storage.pyのカバレッジのみ
pytest tests/common/test_storage.py \
  --cov=nook/common/storage \
  --cov-report=term-missing
```

---

## 📁 テスト構成

### ディレクトリ構造

```
nook/
├── tests/
│   ├── conftest.py                    # 共通フィクスチャ定義
│   └── common/                        # nook/common/のテスト
│       ├── test_gpt_client.py         # GPTClientクラステスト (70件)
│       ├── test_storage.py            # LocalStorageクラステスト (56件)
│       ├── test_http_client.py        # AsyncHTTPClientテスト (68件)
│       ├── test_base_service.py       # BaseServiceテスト (59件)
│       ├── test_async_utils.py        # 非同期ユーティリティテスト (42件)
│       ├── test_feed_utils.py         # RSSフィードユーティリティ (42件)
│       ├── test_dedup.py              # 重複排除テスト (85件)
│       ├── test_date_utils.py         # 日付ユーティリティテスト (41件)
│       ├── test_rate_limiter.py       # レート制限テスト (27件)
│       ├── test_decorators.py         # デコレーターテスト (22件)
│       ├── test_error_metrics.py      # エラーメトリクステスト (27件)
│       ├── test_logging.py            # ロギングテスト (24件)
│       ├── test_service_errors.py     # サービスエラーテスト (20件)
│       └── test_daily_merge.py        # 日次マージテスト (33件)
├── pytest.ini                         # pytest設定
├── .coveragerc                        # カバレッジ設定
└── requirements-test.txt              # テスト依存関係
```

### カバレッジ目標

| モジュール | 目標カバレッジ | 達成カバレッジ | 状態 |
|-----------|--------------|--------------|------|
| gpt_client.py | 95% | 87.82% | ⚠️ 改善可能 |
| storage.py | 95% | 100% | ✅ 達成 |
| http_client.py | 95% | 96.63% | ✅ 達成 |
| base_service.py | 95% | 100% | ✅ 達成 |
| async_utils.py | 95% | 99.20% | ✅ 達成 |
| feed_utils.py | 95% | 97.56% | ✅ 達成 |
| dedup.py | 95% | 98.11% | ✅ 達成 |
| date_utils.py | 95% | 100% | ✅ 達成 |
| rate_limiter.py | 95% | 95%+ | ✅ 達成 |
| decorators.py | 95% | 95.29% | ✅ 達成 |
| error_metrics.py | 95% | 95%+ | ✅ 達成 |
| logging.py | 95% | 95%+ | ✅ 達成 |
| service_errors.py | 95% | 95%+ | ✅ 達成 |
| daily_merge.py | 95% | 100% | ✅ 達成 |

---

## テスト観点表

詳細なテスト観点表は `docs/` ディレクトリに格納されています：

- `docs/test_specifications_gpt_client.md` - GPTClient (132テストケース定義)
- `docs/test_specifications_storage.md` - LocalStorage (56ケース)
- `docs/test_specifications_http_client.md` - AsyncHTTPClient (68ケース)
- `docs/test_specifications_base_service.md` - BaseService (59ケース)
- `docs/test_specifications_async_utils.md` - 非同期ユーティリティ (42ケース)
- `docs/test_specifications_feed_utils.md` - RSSフィードユーティリティ (42ケース)
- `docs/test_specifications_dedup.md` - 重複排除 (85ケース)
- `docs/test_specifications_date_utils.md` - 日付ユーティリティ (41ケース)
- `docs/test_specifications_rate_limiter.md` - レート制限
- `docs/test_specifications_decorators.md` - デコレーター
- `docs/test_specifications_error_metrics.md` - エラーメトリクス
- `docs/test_specifications_logging.md` - ロギング
- `docs/test_specifications_service_errors.md` - サービスエラー
- `docs/test_specifications_daily_merge.md` - 日次マージ

各観点表には以下が記載されています：
- 等価分割・境界値分析
- 正常系・異常系・境界値のテストケース
- 期待結果と優先度
- テストメソッド名

---

## 🚀 CI/CD

### GitHub Actions

プロジェクトでは `.github/workflows/tests.yml` でCI/CDを設定しています。

```yaml
# テストジョブの実行内容
- name: ユニットテストの実行とカバレッジ確認
  run: |
    uv run pytest tests/ -v -m "not integration" \
      --cov=nook \
      --cov-report=xml \
      --cov-report=term-missing \
      --timeout=300 \
      --tb=short
```

### ローカルでCI同等のテスト実行

```bash
# CI環境と同じ条件でテスト実行
pytest tests/ -v -m "not integration" \
  --cov=nook \
  --cov-report=xml \
  --cov-report=term-missing \
  --timeout=300 \
  --tb=short
```

---

## 💡 Tips

### 高速化テクニック

```bash
# pytest-xdistで並列実行
pytest tests/ -n auto

# 失敗したテストのみ再実行
pytest tests/ --lf --ff

# カバレッジ計算をスキップ（開発中）
pytest tests/ --no-cov
```

### デバッグテクニック

```bash
# pdbデバッガーを起動
pytest tests/common/test_gpt_client.py --pdb

# 特定のテストで停止
pytest tests/common/test_gpt_client.py::test_init_with_api_key --pdb

# より詳細なログ出力
pytest tests/ -v -s --log-cli-level=DEBUG
```

### カバレッジ改善

```bash
# 未カバー行を特定
pytest tests/common/ --cov=nook/common --cov-report=term-missing

# HTMLで詳細確認
pytest tests/common/ --cov=nook/common --cov-report=html
open htmlcov/index.html

# 特定のモジュールに絞って改善
pytest tests/common/test_gpt_client.py \
  --cov=nook/common/gpt_client \
  --cov-report=annotate
```

---

## 📞 トラブルシューティング

### 問題: テストが失敗する

```bash
# 詳細なエラー情報を表示
pytest tests/ -v --tb=long

# 標準出力を確認
pytest tests/ -s
```

### 問題: カバレッジが低い

```bash
# 未カバー行を確認
pytest tests/ --cov=nook --cov-report=term-missing

# HTMLレポートで視覚的に確認
pytest tests/ --cov=nook --cov-report=html
open htmlcov/index.html
```

### 問題: テストが遅い

```bash
# 遅いテストを特定
pytest tests/ --durations=10

# 並列実行
pytest tests/ -n auto
```

---

## 📚 参考資料

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [respx](https://lundberg.github.io/respx/)

---

## ✅ チェックリスト

コミット前に確認：

- [ ] 全テストがパスする (`pytest tests/`)
- [ ] カバレッジが95%以上 (`pytest tests/common/ --cov=nook/common --cov-fail-under=95`)
- [ ] 新しいテストを追加した場合、テスト観点表を更新
- [ ] Given/When/Then形式のコメントを記載
- [ ] @pytest.mark.unit デコレータを付与

---

## 📝 最終更新

- 作成日: 2025-11-14
- テスト総数: 618+ テストケース
- カバレッジ: 95%以上（nook/common/）
