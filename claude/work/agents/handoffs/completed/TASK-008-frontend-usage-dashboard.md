# TASK-008: LLM API使用状況ダッシュボードの実装

## Worktree情報
- Worktree: `worktrees/TASK-008-frontend`
- Branch: `feature/usage-dashboard-frontend`

## タスク概要
LLM APIの使用量とコストを可視化するダッシュボード画面を実装する。

## 実装要件

### 1. 新規コンポーネントの作成
- `nook/frontend/src/components/UsageDashboard.tsx`
- API使用状況を表示するダッシュボード

### 2. 表示内容
1. **サマリーカード**
   - 本日の総使用量（トークン数）
   - 本日の総コスト（USD）
   - 今月の総コスト（USD）
   - API呼び出し回数

2. **サービス別使用量テーブル**
   - サービス名
   - 呼び出し回数
   - 総トークン数（入力/出力）
   - コスト
   - 最終呼び出し時刻

3. **時系列グラフ**
   - 日別のコスト推移（過去30日）
   - サービス別の内訳（積み上げ棒グラフ）

### 3. APIエンドポイント
バックエンドに以下のエンドポイントが必要（別タスクで実装）：
- `GET /api/usage/summary` - サマリー情報取得
- `GET /api/usage/by-service` - サービス別使用量
- `GET /api/usage/daily?days=30` - 日別使用量（過去N日）

### 4. UIライブラリ
- Material-UI または Ant Design を使用
- グラフ表示には Recharts を使用

### 5. 実装詳細
```typescript
interface UsageSummary {
  todayTokens: number;
  todayCost: number;
  monthCost: number;
  totalCalls: number;
}

interface ServiceUsage {
  service: string;
  calls: number;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  lastCalled: string;
}

interface DailyUsage {
  date: string;
  services: { [key: string]: number };
  totalCost: number;
}
```

### 6. レスポンシブデザイン
- モバイル表示対応
- テーブルは横スクロール可能

### 7. 自動更新
- 5分ごとにデータを自動更新
- 手動更新ボタンも配置

## 完了条件
- [ ] UsageDashboardコンポーネントを実装
- [ ] サマリー情報の表示
- [ ] サービス別使用量テーブルの表示
- [ ] 時系列グラフの表示
- [ ] レスポンシブデザイン対応
- [ ] 自動更新機能の実装