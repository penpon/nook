# TASK-007: データ保存パス重複ネスト問題修正

## タスク概要
各サービスで `data/service_name/service_name/` という余計なネストディレクトリが作成される問題を修正。
BaseService初期化時の `LocalStorage(f"data/{service_name}")` と各サービス内での `save_markdown(content, "service_name", today)` による重複指定が原因。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/services/business_feed/business_feed.py` (418行目)
- `/Users/nana/workspace/nook/nook/services/qiita_explorer/qiita_explorer.py` (342行目)
- `/Users/nana/workspace/nook/nook/services/reddit_explorer/reddit_explorer.py` (383行目)
- `/Users/nana/workspace/nook/nook/services/tech_feed/tech_feed.py` (418行目)
- `/Users/nana/workspace/nook/nook/services/zenn_explorer/zenn_explorer.py` (342行目)

## 前提タスク
なし（独立タスク）

## worktree名
worktrees/TASK-007-data-path-nesting-fix

## 作業内容

### 1. 問題の根本原因

**現在のフロー**:
1. BaseService初期化: `LocalStorage(f"data/{service_name}")` でbase_dir設定
2. 各サービス内: `save_markdown(content, "service_name", today)` で重複指定
3. 結果: `data/service_name/service_name/file.md` の余計なネスト

**影響を受けるファイル**（2025-07-01分）:
- `data/business_feed/business_feed/2025-07-01.md`
- `data/qiita_explorer/qiita_explorer/2025-07-01.md`
- `data/reddit_explorer/reddit_explorer/2025-07-01.md`
- `data/tech_feed/tech_feed/2025-07-01.md`
- `data/zenn_explorer/zenn_explorer/2025-07-01.md`

### 2. コード修正（各サービス共通）

各サービスの `_store_summaries` メソッド内で以下を修正：

#### business_feed/business_feed.py:418
```python
# 修正前
self.storage.save_markdown(content, "business_feed", today)

# 修正後
self.storage.save_markdown(content, "", today)
```

#### qiita_explorer/qiita_explorer.py:342
```python
# 修正前
self.storage.save_markdown(content, "qiita_explorer", today)

# 修正後
self.storage.save_markdown(content, "", today)
```

#### reddit_explorer/reddit_explorer.py:383
```python
# 修正前
self.storage.save_markdown(content, "reddit_explorer", today)

# 修正後
self.storage.save_markdown(content, "", today)
```

#### tech_feed/tech_feed.py:418
```python
# 修正前
self.storage.save_markdown(content, "tech_feed", today)

# 修正後
self.storage.save_markdown(content, "", today)
```

#### zenn_explorer/zenn_explorer.py:342
```python
# 修正前
self.storage.save_markdown(content, "zenn_explorer", today)

# 修正後
self.storage.save_markdown(content, "", today)
```

### 3. データ移行作業

既存の誤配置ファイルを正しい場所に移動：

```bash
# business_feed
mv data/business_feed/business_feed/2025-07-01.md data/business_feed/
rmdir data/business_feed/business_feed/

# qiita_explorer
mv data/qiita_explorer/qiita_explorer/2025-07-01.md data/qiita_explorer/
rmdir data/qiita_explorer/qiita_explorer/

# reddit_explorer
mv data/reddit_explorer/reddit_explorer/2025-07-01.md data/reddit_explorer/
rmdir data/reddit_explorer/reddit_explorer/

# tech_feed
mv data/tech_feed/tech_feed/2025-07-01.md data/tech_feed/
rmdir data/tech_feed/tech_feed/

# zenn_explorer
mv data/zenn_explorer/zenn_explorer/2025-07-01.md data/zenn_explorer/
rmdir data/zenn_explorer/zenn_explorer/
```

### 4. 検証方法

#### 4.1 コード修正の確認
- 各サービスファイルで `save_markdown` 呼び出しがサービス名を重複指定していないことを確認
- 引数が空文字列になっていることを確認

#### 4.2 データ配置の確認
- 余計なネストディレクトリが削除されていることを確認
- ファイルが正しい場所（`data/service_name/2025-07-01.md`）に配置されていることを確認

#### 4.3 機能テスト
- 各サービスを個別実行して新しいファイルが正しい場所に保存されることを確認
- フロントエンドでデータが正常に表示されることを確認

### 5. 実行コマンド例

```bash
# 個別サービステスト
python -m nook.services.run_services --service business_news
python -m nook.services.run_services --service qiita
python -m nook.services.run_services --service reddit
python -m nook.services.run_services --service tech_news
python -m nook.services.run_services --service zenn
```

## 技術的注意点

### 修正時の注意
- 各サービスの `save_markdown` 呼び出しは1箇所のみ
- 他のロジックには影響しない単純な引数変更
- BaseServiceクラス自体は変更不要

### データ移行時の注意
- ファイル移動前にバックアップ不要（既存ファイルは元の場所に残存）
- 空ディレクトリの削除で整理
- 他の日付のファイルには影響なし

### 検証時の注意
- 新しいファイル生成で正しいパス構造になることを確認
- 既存データの表示に影響しないことを確認
- 5つのサービスすべてで動作確認