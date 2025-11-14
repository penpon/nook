# 全サービステスト観点表

## 1. 共通テスト観点（全サービス）

### 1.1 collectメソッド

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | 正常なデータ収集 | valid target_dates | データ返却 | High |
| **正常系** | target_dates=None | None | デフォルト期間でデータ収集 | High |
| **正常系** | target_dates=空リスト | [] | 空リスト返却 | Medium |
| **境界値** | target_dates=1日分 | [today] | 1日分のデータ | High |
| **境界値** | target_dates=30日分 | 30 dates | 30日分のデータ | Medium |
| **異常系** | 外部API障害 | mock API error | ServiceError例外 | High |
| **異常系** | ネットワークエラー | network error | リトライ後例外 | High |
| **異常系** | タイムアウト | timeout | TimeoutError | Medium |
| **異常系** | レスポンス形式不正 | invalid JSON | パースエラー処理 | High |
| **異常系** | 空レスポンス | empty response | 空リスト返却 | Medium |

### 1.2 データ保存処理

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | JSONファイル保存 | valid data | ファイル作成 | High |
| **正常系** | Markdownファイル保存 | valid data | ファイル作成 | High |
| **異常系** | ディスク容量不足 | full disk | IOError | Medium |
| **異常系** | 権限エラー | no permission | PermissionError | Medium |
| **境界値** | 大容量データ | 10MB+ data | 正常保存 | Low |
| **境界値** | 空データ | empty list | 空ファイル作成 | Medium |

### 1.3 重複チェック

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | 新規データ | new data | 全件追加 | High |
| **正常系** | 重複データ | duplicate data | 重複除外 | High |
| **正常系** | 部分重複 | partial duplicate | 新規分のみ追加 | High |
| **境界値** | 完全一致 | exact match | 追加なし | Medium |
| **境界値** | タイトル類似 | similar title | 別データとして扱う | Low |

---

## 2. BaseFeedService継承サービス（5サービス）

### 対象サービス
- business_feed
- note_explorer
- qiita_explorer
- tech_feed
- zenn_explorer

### 2.1 RSSフィード処理

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | RSS 2.0フィード | valid RSS 2.0 | 正常解析 | High |
| **正常系** | Atom 1.0フィード | valid Atom | 正常解析 | High |
| **異常系** | 不正なXML | invalid XML | XMLParseError | High |
| **異常系** | RSS取得失敗 | HTTP 404 | エラーハンドリング | High |
| **境界値** | エントリ0件 | empty feed | 空リスト返却 | Medium |
| **境界値** | エントリ1000件 | 1000 entries | limit適用 | Low |

### 2.2 人気度スコア抽出

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | スコア情報あり | valid score data | float値返却 | High |
| **正常系** | スコア情報なし | no score | デフォルト0.0 | High |
| **境界値** | スコア=0 | score=0 | 0.0返却 | Medium |
| **境界値** | スコア=負数 | score=-10 | 0.0返却 | Medium |
| **境界値** | スコア=大きい数 | score=999999 | そのまま返却 | Low |
| **異常系** | 不正な形式 | "abc" | 0.0返却 | High |

### 2.3 日本語判定（tech_feed, business_feed）

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | 日本語記事 | Japanese content | True | High |
| **正常系** | 英語記事 | English content | False | High |
| **境界値** | 日本語タイトル+英語本文 | mixed content | True | Medium |
| **境界値** | HTML lang属性あり | lang="ja" | True | Medium |
| **境界値** | 特定ドメイン | nikkei.com | True | Low |

---

## 3. BaseService継承サービス（6サービス）

### 3.1 ArxivSummarizer

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | 論文ID取得 | valid query | 論文リスト取得 | High |
| **正常系** | HTML版ダウンロード | paper with HTML | HTML取得 | High |
| **正常系** | PDF版ダウンロード | paper with PDF | PDF取得 | High |
| **正常系** | HTMLから本文抽出 | valid HTML | テキスト抽出 | High |
| **正常系** | PDFから本文抽出 | valid PDF | テキスト抽出 | High |
| **異常系** | arXiv API障害 | API down | ServiceError | High |
| **異常系** | PDF解析失敗 | corrupted PDF | エラー処理 | Medium |
| **異常系** | HTML解析失敗 | invalid HTML | エラー処理 | Medium |
| **境界値** | 論文0件 | no results | 空リスト | Medium |
| **境界値** | 大容量PDF | 50MB PDF | 処理完了 | Low |

### 3.2 FiveChanExplorer

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | subject.txt取得 | valid board | スレッド一覧取得 | High |
| **正常系** | datファイル解析 | valid dat | 投稿リスト取得 | High |
| **正常系** | AIスレッド検出 | threads with AI | フィルタリング | High |
| **正常系** | リトライ処理 | 403 error | 代替エンドポイント試行 | High |
| **異常系** | 403エラー継続 | persistent 403 | 最終エラー | Medium |
| **異常系** | dat解析失敗 | invalid dat | エラー処理 | Medium |
| **境界値** | スレッド0件 | no threads | 空リスト | Medium |
| **境界値** | 投稿1000件超 | 1000+ posts | limit適用 | Low |

### 3.3 FourChanExplorer

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | カタログ取得 | valid board | スレッド一覧取得 | High |
| **正常系** | スレッド投稿取得 | valid thread | 投稿リスト取得 | High |
| **正常系** | AIスレッド検出 | threads with AI | フィルタリング | High |
| **正常系** | test_mode動作 | test_mode=True | 待機時間短縮 | High |
| **異常系** | 4chan API障害 | API down | ServiceError | High |
| **異常系** | スレッド404 | deleted thread | エラー処理 | Medium |
| **境界値** | スレッド0件 | no threads | 空リスト | Medium |
| **境界値** | 投稿数上限 | max posts | limit適用 | Low |

### 3.4 GithubTrending

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | トレンドページ取得 | valid language | リポジトリ一覧 | High |
| **正常系** | スター数抽出 | valid HTML | スター数取得 | High |
| **正常系** | 言語情報抽出 | valid HTML | 言語取得 | High |
| **正常系** | 説明文翻訳 | English desc | 日本語翻訳 | High |
| **異常系** | GitHub障害 | site down | ServiceError | High |
| **異常系** | HTML構造変更 | changed HTML | パースエラー | Medium |
| **境界値** | リポジトリ0件 | no repos | 空リスト | Medium |
| **境界値** | limit=1 | limit=1 | 1件のみ取得 | High |

### 3.5 HackerNews

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | トップストーリー取得 | valid API | ストーリーID一覧 | High |
| **正常系** | ストーリー詳細取得 | valid story ID | ストーリー詳細 | High |
| **正常系** | コンテンツ取得 | valid URL | 記事本文取得 | High |
| **正常系** | ブロックドメイン判定 | blocked domain | スキップ | High |
| **正常系** | スコア閾値チェック | score>=100 | 対象に含む | High |
| **異常系** | HN API障害 | API down | ServiceError | High |
| **異常系** | 記事取得失敗 | 404 error | ブロックリスト追加 | High |
| **境界値** | score=100（境界） | score=100 | 含む | High |
| **境界値** | score=99（境界） | score=99 | 除外 | High |
| **境界値** | limit=1 | limit=1 | 1件のみ | High |

### 3.6 RedditExplorer

| 観点 | テストケース | 入力 | 期待結果 | 優先度 |
|------|------------|------|---------|--------|
| **正常系** | ホット投稿取得 | valid subreddit | 投稿一覧取得 | High |
| **正常系** | コメント取得 | valid post | コメント取得 | High |
| **正常系** | 翻訳処理 | English content | 日本語翻訳 | High |
| **正常系** | subreddits.toml読込 | valid config | 設定読込 | High |
| **異常系** | Reddit API障害 | API down | ServiceError | High |
| **異常系** | OAuth認証失敗 | invalid creds | AuthError | High |
| **異常系** | subreddit不存在 | invalid sub | エラー処理 | Medium |
| **境界値** | 投稿0件 | empty sub | 空リスト | Medium |
| **境界値** | limit=1 | limit=1 | 1件のみ取得 | High |

---

## 4. エラーハンドリングテスト（全サービス共通）

| 観点 | テストケース | 期待結果 | 優先度 |
|------|------------|---------|--------|
| **例外種別** | HTTPError | ServiceError変換 | High |
| **例外種別** | TimeoutError | タイムアウト処理 | High |
| **例外種別** | ConnectionError | 接続エラー処理 | High |
| **例外種別** | JSONDecodeError | パースエラー処理 | High |
| **例外種別** | OSError | IOエラー処理 | Medium |
| **例外メッセージ** | エラー詳細含む | メッセージ検証 | High |
| **ログ出力** | エラーログ出力 | ログ検証 | Medium |
| **リトライ** | 一時エラーリトライ | 再試行確認 | High |

---

## 5. パフォーマンステスト

| 観点 | テストケース | 期待結果 | 優先度 |
|------|------------|---------|--------|
| **レート制限** | API呼出間隔 | 適切な待機 | High |
| **並行処理** | 複数データ同時処理 | 並行実行 | Medium |
| **メモリ使用** | 大量データ処理 | メモリリーク無し | Low |
| **実行時間** | タイムアウト設定 | 時間内完了 | Medium |

---

## 6. カバレッジ目標

- **行カバレッジ**: 95%以上
- **分岐カバレッジ**: 90%以上
- **関数カバレッジ**: 100%

## 7. テスト実行方法

```bash
# 全テスト実行
pytest tests/services/

# カバレッジ付き実行
pytest tests/services/ --cov=nook/services --cov-report=html --cov-report=term

# 特定サービスのみ
pytest tests/services/test_tech_feed.py -v

# 並列実行
pytest tests/services/ -n auto
```
