# TASK-049: 記事取得数制限・番号付け動作検証

## タスク概要
TASK-047、TASK-048の修正が正しく動作することを検証し、必要に応じて調整を行う。

## 変更予定ファイル
なし（検証・調整作業）

## 前提タスク
TASK-047、TASK-048（すべて完了後）

## worktree名
`worktrees/TASK-049-article-limit-verification`

## 作業内容

### 1. バックエンド取得数制限の検証

#### 1.1 Hacker News（15記事制限）
```bash
# サービス実行
python -m nook.services.run_services --service hacker_news

# JSONファイル確認
jq '. | length' data/hacker_news/$(date +%Y-%m-%d).json
# → 15が表示されることを確認
```

#### 1.2 Tech News（5記事制限）
```bash
# サービス実行
python -m nook.services.run_services --service tech_news

# Markdownファイル確認
grep -c "^### \[" data/tech_feed/$(date +%Y-%m-%d).md
# → 5以下が表示されることを確認
```

#### 1.3 Business News（5記事制限）
```bash
# サービス実行
python -m nook.services.run_services --service business_news

# Markdownファイル確認
grep -c "^### \[" data/business_feed/$(date +%Y-%m-%d).md
# → 5以下が表示されることを確認
```

### 2. フロントエンド番号付けの検証

#### 2.1 開発サーバー起動
```bash
cd nook/frontend
npm run dev
```

#### 2.2 Playwrightを使用した自動検証
- Tech Newsページでカテゴリごとに番号がリセットされることを確認
- Business Newsページでカテゴリごとに番号がリセットされることを確認
- スクリーンショットを撮影して視覚的に確認

### 3. 総合動作確認

#### 3.1 全サービス実行
```bash
./scripts/crawl_all.sh
```

#### 3.2 各ソースの表示確認
- Hacker News: 15記事が表示され、通し番号が付いている
- Tech News: 最大5記事、カテゴリごとに番号リセット
- Business News: 最大5記事、カテゴリごとに番号リセット
- 他のソース: 従来通りの動作

### 4. パフォーマンス検証

#### 4.1 実行時間の測定
```bash
time python -m nook.services.run_services --service hacker_news
time python -m nook.services.run_services --service tech_news
time python -m nook.services.run_services --service business_news
```

#### 4.2 期待される改善
- Hacker News: 30→15記事で約50%の時間短縮
- Tech/Business News: 30→5記事で約83%の時間短縮

### 5. エッジケースの確認

#### 5.1 記事数が制限未満の場合
- フィードに5記事未満しかない場合の動作確認
- 空のフィードがある場合の動作確認

#### 5.2 エラーハンドリング
- API接続エラー時の動作確認
- 部分的な取得失敗時の動作確認

### 6. ドキュメント更新（必要に応じて）
- README.mdに取得数制限について記載
- CLAUDE.mdに実装詳細を追記

## 期待される検証結果
- 各サービスの記事取得数が指定通りに制限されている
- Tech/Business Newsでカテゴリごとに番号がリセットされる
- パフォーマンスが改善されている
- エラーケースでも適切に動作する

## 注意事項
- 検証結果はスクリーンショットやログで記録
- 問題が発見された場合は追加修正タスクを作成
- ユーザー体験の観点から最終確認を実施