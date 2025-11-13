# TASK-054: モバイルデバイスでのNetwork Error修正

## タスク概要: モバイルデバイスからアクセス時に発生する「Error loading content: Network Error」を修正

## 変更予定ファイル: /home/ubuntu/nook/nook/frontend/src/api.ts

## 前提タスク: なし

## worktree名: worktrees/TASK-054-mobile-network-error-fix

## 作業内容:

### 1. 問題の原因
- フロントエンドのapi.tsで `baseURL: 'http://localhost:8001/api'` がハードコードされている
- モバイルデバイスからアクセスすると、localhostはそのデバイス自身を指すため、サーバーに接続できない
- Dockerfile.frontendでは既に `ENV VITE_API_URL=/api` が設定されているが、コードがこれを使用していない

### 2. 修正内容
api.tsを以下のように修正：

```typescript
import axios from 'axios';
import { ContentResponse, WeatherResponse } from './types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api'
});

export const getContent = async (source: string, date?: string) => {
  const { data } = await api.get<ContentResponse>(`/content/${source}`, {
    params: { date }
  });
  return data;
};

export const getWeather = async () => {
  const { data } = await api.get<WeatherResponse>('/weather');
  return data;
};
```

### 3. 修正の効果
- 本番環境（Docker）: 環境変数VITE_API_URL（`/api`）が使用され、相対URLでアクセス
- 開発環境: 必要に応じて異なるURLを環境変数で設定可能
- モバイルデバイス: 相対URLによりpenpon.jpドメイン配下の/apiにアクセスするため、正常に動作

### 4. テスト方法
1. ビルドが成功することを確認
2. ローカルでDockerを起動し、PCとモバイルデバイスの両方からアクセスして動作確認
3. エラーメッセージが表示されず、コンテンツが正常に表示されることを確認