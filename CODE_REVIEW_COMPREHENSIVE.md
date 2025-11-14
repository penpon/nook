# test_fivechan_explorer.py 包括的レビュー（第2回）
## 可読性・保守性・DRY原則・テスト速度

## レビュー実施日
2025-11-14

## 総合評価: A- → A（修正後目標）

---

## 🔴 Critical Issues（重大な問題）

### 1. httpx.AsyncClientモック設定の大量重複（DRY原則違反）

**影響度:** 🔴 HIGH - 保守性・可読性・テスト速度

**場所:** 12箇所のテストで同じパターンが繰り返される

**問題コード:**
```python
# Lines 222-227, 254-259, 284-289, 315-320, 349-354,
# 795-800, 827-832, 848-853, 888-893, 959-964, 1036-1041, 1074-1079

with patch("httpx.AsyncClient") as mock_client:
    client_instance = AsyncMock()
    client_instance.__aenter__.return_value = client_instance
    client_instance.__aexit__.return_value = AsyncMock()
    client_instance.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = client_instance
```

**問題点:**
1. **保守性:** モックの実装変更時に12箇所を修正必要
2. **可読性:** 本質的なテストロジックが埋もれる（6行のボイラープレート）
3. **テスト速度:** モック作成のオーバーヘッドが12回発生
4. **DRY原則:** 完全に同じコードが12回繰り返される

**推奨修正:**
```python
# conftest.pyにフィクスチャを追加
@pytest.fixture
def mock_httpx_client():
    """httpx.AsyncClientのモックを提供"""
    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.__aexit__.return_value = AsyncMock()
        mock_client.return_value = client_instance
        yield client_instance

# テストで使用
async def test_something(fivechan_service, mock_httpx_client):
    mock_response = Mock(status_code=200, content=b"data")
    mock_httpx_client.get = AsyncMock(return_value=mock_response)

    result = await fivechan_service._get_subject_txt_data("ai")
    # テストロジック...
```

**削減効果:**
- コード削減: 約60行（5行 × 12箇所 - フィクスチャ定義）
- 保守性: 1箇所で管理
- 可読性: テストが3-4行短縮
- テスト速度: モック作成が1回のみ（setup時）

**優先度:** 🔴 CRITICAL

---

### 2. cloudscraperモック設定の重複（DRY原則違反）

**影響度:** 🔴 HIGH - 保守性・可読性

**場所:** 8箇所のテストで同じパターンが繰り返される

**問題コード:**
```python
# Lines 405-411, 439-445, 466-472, 492-498,
# 519-525, 868-874, 933-939

mock_scraper = Mock()
mock_scraper.get = Mock(return_value=mock_response)
mock_scraper.headers = {}

with patch("cloudscraper.create_scraper", return_value=mock_scraper), patch(
    "asyncio.to_thread", side_effect=lambda f, *args: f(*args)
):
```

**推奨修正:**
```python
# conftest.pyにフィクスチャを追加
@pytest.fixture
def mock_cloudscraper():
    """cloudscraperのモックを提供"""
    mock_scraper = Mock()
    mock_scraper.headers = {}

    with patch("cloudscraper.create_scraper", return_value=mock_scraper), \
         patch("asyncio.to_thread", side_effect=lambda f, *args: f(*args)):
        yield mock_scraper

# テストで使用
async def test_dat_parsing(fivechan_service, mock_cloudscraper):
    mock_response = Mock(status_code=200, content=b"data")
    mock_cloudscraper.get = Mock(return_value=mock_response)

    posts, latest = await fivechan_service._get_thread_posts_from_dat("http://test.dat")
    # テストロジック...
```

**削減効果:**
- コード削減: 約40行（5行 × 8箇所 - フィクスチャ定義）
- 保守性: 1箇所で管理
- 可読性: 各テストが5行短縮

**優先度:** 🔴 CRITICAL

---

## 🟡 Warnings（警告）

### 3. Mock Responseファクトリーの欠如（可読性・保守性）

**影響度:** 🟡 MEDIUM

**問題コード:**
```python
# 繰り返しパターン（20箇所以上）
mock_response = Mock()
mock_response.status_code = 200
mock_response.content = subject_data
```

**推奨修正:**
```python
# tests/services/test_fivechan_explorer.py の先頭に追加
def create_http_response(status_code=200, content=b"", text=""):
    """HTTPレスポンスモックを作成するファクトリー関数"""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.content = content
    mock_response.text = text or content.decode("utf-8", errors="ignore")
    return mock_response

# 使用例
async def test_something(fivechan_service, mock_httpx_client):
    subject_data = "1234567890.dat<>AIスレッド (100)\n".encode("shift_jis")
    mock_response = create_http_response(content=subject_data)
    mock_httpx_client.get = AsyncMock(return_value=mock_response)
    # ...
```

**改善効果:**
- 可読性: 1行で済む
- 保守性: レスポンス構造変更時に1箇所のみ修正
- 一貫性: すべてのテストで同じ構造

**優先度:** 🟡 MEDIUM

---

### 4. エンコーディングボムの重複生成（テスト速度）

**影響度:** 🟡 MEDIUM - テスト速度

**問題コード:**
```python
# Line 882 - 毎回1000000回の繰り返し生成
async def test_encoding_bomb_attack(fivechan_service):
    bomb_data = b"\x81\x40" * ENCODING_BOMB_REPEAT_COUNT  # 2MB生成
    # ...

# Line 841 - 毎回10MB生成
async def test_dos_attack_oversized_response(fivechan_service):
    huge_data = b"x" * MAX_RESPONSE_SIZE_BYTES  # 10MB生成
    # ...
```

**問題点:**
- テスト実行のたびに12MBのデータを生成
- メモリ確保とGCのオーバーヘッド
- テスト速度に悪影響

**推奨修正:**
```python
# モジュールレベルで1回のみ生成（lazy evaluation）
@pytest.fixture(scope="module")
def encoding_bomb_data():
    """エンコーディングボム用データ（モジュールスコープでキャッシュ）"""
    return b"\x81\x40" * ENCODING_BOMB_REPEAT_COUNT

@pytest.fixture(scope="module")
def huge_response_data():
    """DoS攻撃用大容量データ（モジュールスコープでキャッシュ）"""
    return b"x" * MAX_RESPONSE_SIZE_BYTES

# 使用
async def test_encoding_bomb_attack(fivechan_service, encoding_bomb_data, mock_httpx_client):
    mock_response = create_http_response(content=encoding_bomb_data)
    # ...
```

**改善効果:**
- テスト速度: 12MBのデータ生成が1回のみ
- メモリ: 再利用によるGC削減

**優先度:** 🟡 MEDIUM

---

### 5. テストデータの可読性不足

**影響度:** 🟡 MEDIUM - 可読性

**問題コード:**
```python
# Line 216 - 何のバイト列か不明
subject_data = b"1234567890.dat<>\xff\xfe AI\x83X\x83\x8c\x83b\x83h (50)\n"

# Line 277 - マジック文字列
responses = [
    Exception("Connection failed"),
    Mock(status_code=200, content=subject_data),
]
```

**推奨修正:**
```python
# ファイル先頭に定数として定義
# テストデータ用の定数
VALID_SUBJECT_LINE = "1234567890.dat<>AIスレッド (100)\n"
MALFORMED_ENCODING_SUBJECT = b"1234567890.dat<>\xff\xfe AI\x83X\x83\x8c\x83b\x83h (50)\n"
INVALID_FORMAT_LINE = "invalid_format_line\n"

# エラーメッセージ
ERROR_CONNECTION_FAILED = "Connection failed"
ERROR_NETWORK = "Network error"
ERROR_NOT_FOUND = "Not Found"

# 使用
async def test_subdomain_retry(fivechan_service, mock_httpx_client):
    subject_data = VALID_SUBJECT_LINE.encode("shift_jis")
    responses = [
        Exception(ERROR_CONNECTION_FAILED),
        create_http_response(content=subject_data),
    ]
    mock_httpx_client.get = AsyncMock(side_effect=responses)
    # ...
```

**改善効果:**
- 可読性: 文字列の意味が明確
- 保守性: テストデータの一元管理
- 一貫性: 同じデータを複数テストで再利用

**優先度:** 🟡 MEDIUM

---

## 🔵 Info（情報・改善提案）

### 6. テストグルーピングの改善（可読性）

**影響度:** 🔵 LOW - 可読性

**現状:**
```python
# =============================================================================
# 2. collect メソッドのテスト - 正常系
# =============================================================================

# =============================================================================
# 3. collect メソッドのテスト - 異常系
# =============================================================================
```

**推奨:**
```python
# =============================================================================
# HTTP Client Tests（HTTPクライアント関連）
# =============================================================================

class TestSubjectTxtParsing:
    """subject.txt解析のテストグループ"""

    async def test_success(self, fivechan_service, mock_httpx_client):
        """正常系: 標準的なsubject.txtを解析"""
        # ...

    async def test_malformed_encoding(self, fivechan_service, mock_httpx_client):
        """異常系: 文字化けを含むデータ"""
        # ...

class TestDatParsing:
    """DAT形式解析のテストグループ"""
    # ...
```

**改善効果:**
- 可読性: 関連テストがグループ化
- 実行制御: クラス単位でテスト実行可能
- 共有フィクスチャ: クラス内で共通セットアップ

**優先度:** 🔵 LOW

---

### 7. アサーション数の最適化（テスト速度）

**影響度:** 🔵 LOW - テスト速度・可読性

**問題コード:**
```python
# Line 199-204 - 6個のアサーション（独立した検証項目が混在）
assert len(result) == 2
assert result[0]["title"] == "AI・人工知能について語るスレ"
assert result[0]["post_count"] == 100
assert result[1]["title"] == "機械学習の最新動向"
assert result[1]["post_count"] == 50
```

**推奨:**
```python
# 構造検証と内容検証を分離
def test_get_subject_txt_data_success_structure(fivechan_service, ...):
    """subject.txt解析の構造検証"""
    result = await fivechan_service._get_subject_txt_data("ai")

    assert len(result) == 2, "2つのスレッドが解析される"
    assert all(isinstance(item, dict) for item in result)
    assert all("title" in item for item in result)
    assert all("post_count" in item for item in result)

def test_get_subject_txt_data_success_content(fivechan_service, ...):
    """subject.txt解析の内容検証"""
    result = await fivechan_service._get_subject_txt_data("ai")

    expected = [
        {"title": "AI・人工知能について語るスレ", "post_count": 100},
        {"title": "機械学習の最新動向", "post_count": 50},
    ]

    for actual, exp in zip(result, expected):
        assert actual["title"] == exp["title"]
        assert actual["post_count"] == exp["post_count"]
```

**改善効果:**
- テスト速度: 失敗時に早期終了
- 可読性: 1テスト1検証項目の原則に近づく
- デバッグ: どの検証で失敗したか明確

**優先度:** 🔵 LOW

---

### 8. パラメータ化テストの活用不足（可読性・保守性）

**影響度:** 🔵 LOW

**現状:**
```python
async def test_get_subject_txt_data_malformed_encoding(...):
    # 1つのケースのみ

async def test_get_subject_txt_data_malformed_format(...):
    # 別の1つのケース
```

**推奨:**
```python
@pytest.mark.parametrize(
    "test_data,expected_count,test_id",
    [
        (b"1234567890.dat<>\xff\xfe AI (50)\n", 0, "invalid_bytes"),
        (b"invalid_format_line\n", 0, "no_delimiter"),
        (b"1234567890.dat<>valid (100)\n", 1, "valid_line"),
    ],
    ids=lambda x: x[2] if isinstance(x, tuple) else x,
)
async def test_subject_txt_parsing_variations(
    fivechan_service, mock_httpx_client, test_data, expected_count, test_id
):
    """subject.txt解析の様々なバリエーション"""
    mock_response = create_http_response(content=test_data)
    mock_httpx_client.get = AsyncMock(return_value=mock_response)

    result = await fivechan_service._get_subject_txt_data("test")

    assert len(result) == expected_count, f"{test_id}: expected {expected_count} items"
```

**改善効果:**
- 保守性: テストケース追加が容易
- 可読性: パターンが統一
- 実行制御: 個別ケースの実行が可能

**優先度:** 🔵 LOW

---

### 9. テスト実行時間の可視化不足（テスト速度）

**影響度:** 🔵 LOW

**現状:**
どのテストが遅いか不明

**推奨:**
```python
# pytest.ini に追加
[pytest]
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=nook
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=95
    --ignore=nook/frontend
    --ignore=node_modules
    --durations=10  # 最も遅い10テストを表示
    --durations-min=1.0  # 1秒以上のテストのみ
```

**改善効果:**
- テスト速度: ボトルネックの特定が容易
- 継続的改善: 遅いテストの監視

**優先度:** 🔵 LOW

---

### 10. 型ヒントの追加（可読性・保守性）

**影響度:** 🔵 LOW

**現状:**
```python
def create_http_response(status_code=200, content=b"", text=""):
    # ...
```

**推奨:**
```python
from typing import Optional

def create_http_response(
    status_code: int = 200,
    content: bytes = b"",
    text: str = ""
) -> Mock:
    """HTTPレスポンスモックを作成する

    Args:
        status_code: HTTPステータスコード
        content: レスポンスボディ（バイト列）
        text: レスポンスボディ（文字列）

    Returns:
        Mock: HTTPレスポンスのモックオブジェクト
    """
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.content = content
    mock_response.text = text or content.decode("utf-8", errors="ignore")
    return mock_response
```

**改善効果:**
- 可読性: 引数と戻り値の型が明確
- IDE支援: 型補完とエラー検出
- ドキュメント: 使い方が明確

**優先度:** 🔵 LOW

---

## 修正優先順位と期待効果

### Phase 1（即座に実施） - 最大の効果
1. 🔴 httpx.AsyncClientモックフィクスチャ化
2. 🔴 cloudscraperモックフィクスチャ化

**期待効果:**
- コード削減: **約100行** （現在1184行 → 1084行）
- テスト可読性: **各テスト5-6行短縮**
- 保守性: **2箇所 → 2箇所のフィクスチャで管理**
- テスト速度: **約5-10%改善**（モック作成オーバーヘッド削減）

### Phase 2（次回実施） - 追加改善
3. 🟡 Mock Responseファクトリー作成
4. 🟡 大容量データのモジュールスコープキャッシュ
5. 🟡 テストデータ定数化

**期待効果:**
- コード削減: **追加20-30行**
- 可読性: **さらに向上**
- テスト速度: **約10-15%改善**（データ生成削減）

### Phase 3（継続的改善） - 長期的品質向上
6. 🔵 テストクラスグルーピング
7. 🔵 アサーション最適化
8. 🔵 パラメータ化活用
9. 🔵 実行時間可視化
10. 🔵 型ヒント追加

**期待効果:**
- 可読性: **大幅向上**
- 保守性: **大幅向上**
- テスト速度: **継続的改善**

---

## 総評

### 現状（A-）の強み
✅ DRY原則（フィクスチャ化）が一部適用済み
✅ セキュリティ・パフォーマンステストが充実
✅ ドキュメントが充実
✅ パラメータIDが明確

### 改善の余地（A-）
❌ モックセットアップの重複（20箇所以上）
❌ テストデータの重複生成
⚠️ テストグルーピング不足
⚠️ 型ヒント不足

### 修正後の期待（A）
✅ モックが完全にフィクスチャ化
✅ テストコードが20%短縮
✅ テスト速度が15-20%改善
✅ 保守性が大幅向上

---

## 数値目標

| 指標 | 現在 | Phase1後 | Phase2後 | Phase3後 |
|------|------|----------|----------|----------|
| 総行数 | 1184 | 1084 (-100) | 1070 (-114) | 1050 (-134) |
| 重複パターン | 20+ | 0 | 0 | 0 |
| テスト実行時間 | 基準 | -5~10% | -10~15% | -15~20% |
| 保守性スコア | A- | A | A | A+ |
| 可読性スコア | A- | A | A | A+ |

---

**レビュアー:** Claude Code Review Expert
**レビュー日時:** 2025-11-14 (第2回)
**推奨アクション:** Phase 1の実施で評価A達成
