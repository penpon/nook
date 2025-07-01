# TASK-053: Docker構成の修正と最適化
## タスク概要: Docker関連ファイルの問題点を修正し、本番環境に適した構成に最適化する
## 変更予定ファイル: 
- Dockerfile.backend
- Dockerfile.frontend  
- docker-compose.yaml
- nginx/.htpasswd (新規作成)
- docker-rebuild.sh
## 前提タスク: なし
## worktree名: worktrees/TASK-053-docker-configuration-fixes
## 作業内容:

### 1. nginx/.htpasswdファイルの作成
- nginx/ディレクトリに.htpasswdファイルを作成
- 初期認証情報を設定（例: admin/password）
- ファイル内容の例:
  ```
  admin:$apr1$xxxxx$xxxxxxxxxxxxxxxxx
  ```
- 注: 実際のパスワードハッシュはhtpasswdコマンドで生成

### 2. Dockerfile.backendの修正
- `COPY data ./data`行を削除（dataはvolumeマウントで管理）
- 必要に応じてディレクトリ作成コマンドを追加:
  ```dockerfile
  RUN mkdir -p /app/data /app/logs
  ```

### 3. Dockerfile.frontendの最適化
- マルチステージビルドを活用してnginxイメージに直接含める構成に変更
- 例:
  ```dockerfile
  FROM node:18-alpine AS builder
  # ... ビルド処理 ...
  
  FROM nginx:alpine
  COPY --from=builder /app/dist /usr/share/nginx/html
  COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
  ```

### 4. docker-compose.yamlの更新
- frontendサービスを削除（nginxに統合）
- nginxサービスの設定を更新:
  - frontendのビルドコンテキストを削除
  - frontend-distボリュームを削除
  - depends_onからfrontendを削除

### 5. docker-rebuild.shの更新
- 変更されたサービス構成に合わせてスクリプトを調整
- 不要なボリューム削除処理を追加

### 6. .env.production.exampleの作成
- 実際の.env.productionファイルをテンプレート化
- 機密情報をプレースホルダに置き換えて、設定例を提供

## 注意事項:
- 既存のデータやログが失われないように注意
- nginxの設定変更時は構文チェックを実施
- 認証情報は適切に管理し、本番環境では強固なパスワードを使用