# Nook プロキシ設定テスト結果

## テスト実施日: 2025-07-02

## 問題の概要

フロントエンド（Vite開発サーバー、ポート5173）がバックエンドAPI（FastAPIサーバー、ポート8000）にアクセスできず、以下のような症状が発生していました：

1. 全てのソース（hacker-news、github、tech-news）で「No content available for this source」が表示される
2. APIリクエストが`http://localhost:5173/api/content/xxx`に送信され、Viteの開発サーバーがHTMLを返す
3. フロントエンドはJSONを期待しているが、HTMLが返されるためパースエラーが発生

## 原因分析

### 1. 環境変数の不一致
- フロントエンドのコード（`api.ts`）は`VITE_API_URL`環境変数を探している
- しかし、`.env`ファイルには`NEXT_PUBLIC_API_URL`として定義されている
- 結果として、`VITE_API_URL`が未定義となり、デフォルトの`/api`が使用される

### 2. Viteプロキシ設定の欠如
- `vite.config.ts`にプロキシ設定が存在しない
- フロントエンドからの`/api`リクエストがバックエンド（ポート8000）に転送されない
- 代わりにVite開発サーバー（ポート5173）が処理し、HTMLを返す

## バックエンドAPIの動作確認

以下のコマンドで各APIエンドポイントが正常に動作していることを確認：

```bash
# Hacker News API
curl -s "http://localhost:8000/api/content/hacker-news?date=2025-07-02"
# → 正常なJSONレスポンスを返す（15件の記事）

# GitHub API  
curl -s "http://localhost:8000/api/content/github?date=2025-07-02"
# → 正常なJSONレスポンスを返す（GitHubトレンドリポジトリ）

# Tech News API
curl -s "http://localhost:8000/api/content/tech-news?date=2025-07-02"
# → 正常なJSONレスポンスを返す（技術ニュース記事）
```

## 解決策

### 1. 環境変数の追加（短期的解決）
`.env`ファイルに以下を追加：
```env
VITE_API_URL=http://localhost:8000/api
```

### 2. Viteプロキシ設定の追加（推奨される解決策）
`vite.config.ts`に以下のプロキシ設定を追加：

```typescript
export default defineConfig({
  // ... 既存の設定
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

この設定により、開発時に`/api`へのリクエストが自動的にバックエンドサーバー（ポート8000）に転送されます。

## 推奨アクション

1. **即座の修正**: `.env`ファイルに`VITE_API_URL=http://localhost:8000/api`を追加
2. **恒久的な修正**: `vite.config.ts`にプロキシ設定を追加し、開発環境での自動プロキシを有効化
3. **ドキュメント更新**: 開発環境のセットアップ手順に環境変数の設定について明記

## テスト確認項目

修正後、以下を確認：
- [ ] 各ソースページ（hacker-news、github、tech-news）でコンテンツが表示される
- [ ] ブラウザのコンソールにエラーが表示されない
- [ ] ネットワークタブで`/api/content/xxx`への正しいレスポンスが確認できる