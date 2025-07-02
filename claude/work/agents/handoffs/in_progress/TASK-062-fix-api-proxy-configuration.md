# TASK-062: APIプロキシ設定修正（全ソース表示問題の解決）

## タスク概要
レスポンシブデザイン変更により「No content available for this source」が全ソースで表示される問題を修正する。原因は環境変数の不一致とViteプロキシ設定の欠如。

## 変更予定ファイル
- nook/frontend/vite.config.ts（プロキシ設定追加）
- nook/frontend/.env（環境変数修正）
- nook/frontend/.env.example（ドキュメント更新）

## 前提タスク
なし（緊急修正タスク）

## worktree名
worktrees/TASK-062-fix-api-proxy-configuration

## 作業内容

### 1. 問題の詳細
#### 現在の状況
- 全ソース（ArXiv、GitHub、Hacker News等）で「No content available for this source」表示
- APIリクエストが `/api/content/xxx` に送信されるが、HTMLレスポンスが返される
- バックエンドAPI（http://localhost:8000/api）は正常に動作確認済み

#### 根本原因
1. **環境変数の不一致**：
   - フロントエンドコードは `VITE_API_URL` を参照
   - `.env` ファイルには `NEXT_PUBLIC_API_URL` として定義
   - 結果として未定義で `/api` がデフォルト使用される

2. **Viteプロキシ設定の欠如**：
   - `vite.config.ts` にプロキシ設定がない
   - `/api` リクエストがバックエンドに転送されない

### 2. 修正手順

#### Step 1: vite.config.ts にプロキシ設定を追加
```typescript
// nook/frontend/vite.config.ts に追加
export default defineConfig(({ command, mode }) => {
  const isSSR = mode === 'ssr'
  
  return {
    plugins: [
      // 既存のプラグイン設定...
    ],
    
    // プロキシ設定を追加
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path // パスをそのまま使用
        }
      }
    },
    
    resolve: {
      // 既存のresolve設定...
    },
    
    // 既存の設定を維持...
  }
})
```

#### Step 2: 環境変数の統一
```bash
# nook/frontend/.env を修正
# 削除または修正
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# 追加
VITE_API_URL=http://localhost:8000/api
```

#### Step 3: .env.example の更新
```bash
# nook/frontend/.env.example に追加
# API Configuration
VITE_API_URL=http://localhost:8000/api

# PWA Configuration (existing)
# ... 既存の設定を維持
```

### 3. 動作確認

#### 確認すべき項目
1. **各ソースでの表示確認**：
   - http://localhost:5173/?source=arxiv
   - http://localhost:5173/?source=github
   - http://localhost:5173/?source=hacker-news
   - http://localhost:5173/?source=tech-news
   - http://localhost:5173/?source=business-news

2. **APIリクエストの確認**：
   - ブラウザの開発者ツールでNetwork タブを確認
   - `/api/content/xxx` リクエストがJSONレスポンスを返すことを確認

3. **エラーログの確認**：
   - コンソールエラーがないことを確認
   - バックエンドログにエラーがないことを確認

### 4. テスト項目
- [ ] 全ソースで記事が正常に表示される
- [ ] APIリクエストがJSONレスポンスを返す
- [ ] コンソールエラーが発生しない
- [ ] 日付変更時に正しくデータが取得される
- [ ] ページリロード時に正常に動作する

### 5. 注意事項
- **緊急修正**：このタスクは最優先で実行すること
- **設定確認**：バックエンドが http://localhost:8000 で動作していることを確認
- **互換性**：既存のPWA設定やSSR設定に影響しないよう注意
- **ドキュメント**：修正後はREADME.mdの更新も検討

### 6. 完了条件
- [ ] 全ソースで「No content available for this source」が解消
- [ ] ArXiv、GitHub等の記事が正常に表示される
- [ ] APIプロキシが正常に動作する
- [ ] 環境変数が統一される
- [ ] 開発サーバーの再起動後も正常動作する

### 7. 技術的背景
- **Gemini**および**O3-high**とのコードレビューにより解決策を確定
- Viteの開発サーバープロキシ機能を活用してCORS問題を解決
- 本番環境での構成（Nginxリバースプロキシ）との整合性も考慮

## 完了後の確認
修正完了後、以下のURLで動作確認を実施：
```bash
# 各ソースのテスト
curl -s "http://localhost:5173/api/content/arxiv?date=$(date +%Y-%m-%d)" | jq .
curl -s "http://localhost:5173/api/content/github?date=$(date +%Y-%m-%d)" | jq .
```

この修正により、レスポンシブデザイン変更後の表示問題が完全に解決されます。