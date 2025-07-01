# TASK-058: UIライブラリ統一（Material-UI → Tailwind CSS）

## タスク概要
現在Material-UIとTailwind CSSが混在している状態を解消し、Tailwind CSSに統一する。UsageDashboardコンポーネントをTailwind CSS + Recharts + Lucide Reactで完全に置き換え、バンドルサイズを大幅削減する。

## 変更予定ファイル
- nook/frontend/src/components/UsageDashboard.tsx（完全書き換え）
- nook/frontend/package.json（Material-UI関連削除）
- nook/frontend/src/components/dashboard/（新規ディレクトリ作成）
- nook/frontend/src/components/dashboard/SummaryCard.tsx（新規作成）
- nook/frontend/src/components/dashboard/ServiceUsageTable.tsx（新規作成）
- nook/frontend/src/components/dashboard/DailyUsageChart.tsx（新規作成）
- nook/frontend/src/hooks/useUsageData.ts（新規作成）

## 前提タスク
TASK-056（App.tsx分割完了後）

## worktree名
worktrees/TASK-058-ui-library-unification

## 作業内容

### 1. Material-UI依存関係の削除
```json
// package.json から削除
{
  "dependencies": {
    // 削除対象
    "@emotion/react": "^11.14.0",
    "@emotion/styled": "^11.14.0",
    "@mui/icons-material": "^7.1.2",
    "@mui/material": "^7.1.2"
  }
}
```

### 2. カスタムフックでデータ管理の分離
```typescript
// src/hooks/useUsageData.ts（新規作成）
import { useState, useEffect } from 'react';
import axios from 'axios';

export interface UsageSummary {
  todayTokens: number;
  todayCost: number;
  monthCost: number;
  totalCalls: number;
}

export interface ServiceUsage {
  service: string;
  calls: number;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  lastCalled: string;
}

export interface DailyUsage {
  date: string;
  services: { [key: string]: number };
  totalCost: number;
}

export function useUsageData() {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [serviceUsage, setServiceUsage] = useState<ServiceUsage[]>([]);
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [summaryResponse, serviceResponse, dailyResponse] = await Promise.all([
        axios.get('http://localhost:8000/api/usage/summary'),
        axios.get('http://localhost:8000/api/usage/by-service'),
        axios.get('http://localhost:8000/api/usage/daily?days=30')
      ]);

      setSummary(summaryResponse.data);
      setServiceUsage(serviceResponse.data);
      setDailyUsage(dailyResponse.data);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('データの取得に失敗しました:', error);
      setError('データの取得に失敗しました');
      
      // フォールバック用のモックデータ
      setSummary({
        todayTokens: 15420,
        todayCost: 0.23,
        monthCost: 12.45,
        totalCalls: 78
      });
      setServiceUsage([
        {
          service: 'OpenAI GPT-4',
          calls: 25,
          inputTokens: 8500,
          outputTokens: 3200,
          cost: 0.15,
          lastCalled: '2024-01-20T15:30:00Z'
        },
        {
          service: 'Claude-3',
          calls: 18,
          inputTokens: 6200,
          outputTokens: 2800,
          cost: 0.08,
          lastCalled: '2024-01-20T14:45:00Z'
        }
      ]);
      setDailyUsage([
        { date: '2024-01-15', services: { 'OpenAI GPT-4': 0.12, 'Claude-3': 0.08 }, totalCost: 0.20 },
        { date: '2024-01-16', services: { 'OpenAI GPT-4': 0.18, 'Claude-3': 0.06 }, totalCost: 0.24 },
        { date: '2024-01-17', services: { 'OpenAI GPT-4': 0.15, 'Claude-3': 0.09 }, totalCost: 0.24 },
        { date: '2024-01-18', services: { 'OpenAI GPT-4': 0.22, 'Claude-3': 0.07 }, totalCost: 0.29 },
        { date: '2024-01-19', services: { 'OpenAI GPT-4': 0.19, 'Claude-3': 0.11 }, totalCost: 0.30 },
        { date: '2024-01-20', services: { 'OpenAI GPT-4': 0.15, 'Claude-3': 0.08 }, totalCost: 0.23 }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // 5分ごとの自動更新
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return {
    summary,
    serviceUsage,
    dailyUsage,
    loading,
    error,
    lastUpdated,
    refetch: fetchData
  };
}
```

### 3. サマリーカードコンポーネント
```typescript
// src/components/dashboard/SummaryCard.tsx（新規作成）
import React from 'react';

interface SummaryCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  colorClass: string;
  darkMode?: boolean;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
  title,
  value,
  icon,
  colorClass,
  darkMode = false
}) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
            {title}
          </p>
          <p className={`text-2xl font-bold ${colorClass}`}>
            {value}
          </p>
        </div>
        <div className={`p-3 rounded-full bg-opacity-10 ${colorClass.replace('text-', 'bg-')}`}>
          <div className={colorClass}>
            {icon}
          </div>
        </div>
      </div>
    </div>
  );
};
```

### 4. サービス使用量テーブルコンポーネント
```typescript
// src/components/dashboard/ServiceUsageTable.tsx（新規作成）
import React from 'react';
import { ServiceUsage } from '../../hooks/useUsageData';

interface ServiceUsageTableProps {
  serviceUsage: ServiceUsage[];
  darkMode?: boolean;
}

export const ServiceUsageTable: React.FC<ServiceUsageTableProps> = ({
  serviceUsage,
  darkMode = false
}) => {
  const formatNumber = (num: number) => num.toLocaleString();
  const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ja-JP');
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          サービス別使用量
        </h3>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                サービス名
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                呼び出し回数
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                入力トークン
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                出力トークン
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                コスト
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">
                最終呼び出し
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {serviceUsage.map((service) => (
              <tr key={service.service} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                    {service.service}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900 dark:text-white font-medium">
                  {formatNumber(service.calls)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-600 dark:text-gray-400 hidden sm:table-cell">
                  {formatNumber(service.inputTokens)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-600 dark:text-gray-400 hidden sm:table-cell">
                  {formatNumber(service.outputTokens)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-green-600 dark:text-green-400">
                  {formatCurrency(service.cost)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-600 dark:text-gray-400 hidden md:table-cell">
                  {formatDate(service.lastCalled)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
```

### 5. 日次使用量チャートコンポーネント
```typescript
// src/components/dashboard/DailyUsageChart.tsx（新規作成）
import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import { DailyUsage } from '../../hooks/useUsageData';

interface DailyUsageChartProps {
  dailyUsage: DailyUsage[];
  darkMode?: boolean;
}

export const DailyUsageChart: React.FC<DailyUsageChartProps> = ({
  dailyUsage,
  darkMode = false
}) => {
  const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          日別コスト推移（過去30日）
        </h3>
      </div>
      
      <div className="p-6">
        <div className="w-full h-80 sm:h-96">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={dailyUsage} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid 
                strokeDasharray="3 3" 
                stroke={darkMode ? '#374151' : '#e5e7eb'} 
              />
              <XAxis 
                dataKey="date" 
                tick={{ 
                  fontSize: 12, 
                  fill: darkMode ? '#9ca3af' : '#6b7280' 
                }}
                stroke={darkMode ? '#6b7280' : '#9ca3af'}
                interval="preserveStartEnd"
              />
              <YAxis 
                tick={{ 
                  fontSize: 12, 
                  fill: darkMode ? '#9ca3af' : '#6b7280' 
                }}
                stroke={darkMode ? '#6b7280' : '#9ca3af'}
              />
              <Tooltip 
                formatter={(value: number) => [formatCurrency(value), 'コスト']}
                labelFormatter={(label) => `日付: ${label}`}
                contentStyle={{
                  backgroundColor: darkMode ? '#374151' : '#ffffff',
                  border: `1px solid ${darkMode ? '#4b5563' : '#e5e7eb'}`,
                  borderRadius: '8px',
                  color: darkMode ? '#f3f4f6' : '#1f2937'
                }}
              />
              <Legend 
                wrapperStyle={{
                  color: darkMode ? '#f3f4f6' : '#1f2937'
                }}
              />
              <Bar 
                dataKey="totalCost" 
                fill="#3b82f6"
                name="総コスト"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
```

### 6. 新しいUsageDashboardコンポーネント
```typescript
// src/components/UsageDashboard.tsx（完全書き換え）
import React from 'react';
import { 
  RefreshCw, 
  TrendingUp, 
  DollarSign, 
  Activity, 
  Calendar,
  AlertCircle
} from 'lucide-react';
import { SummaryCard } from './dashboard/SummaryCard';
import { ServiceUsageTable } from './dashboard/ServiceUsageTable';
import { DailyUsageChart } from './dashboard/DailyUsageChart';
import { useUsageData } from '../hooks/useUsageData';

interface UsageDashboardProps {
  darkMode?: boolean;
}

const UsageDashboard: React.FC<UsageDashboardProps> = ({ darkMode = false }) => {
  const {
    summary,
    serviceUsage,
    dailyUsage,
    loading,
    error,
    lastUpdated,
    refetch
  } = useUsageData();

  const formatNumber = (num: number) => num.toLocaleString();
  const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;

  if (loading && !summary) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4 sm:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="flex items-center space-x-2">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
              <span className="text-lg text-gray-600 dark:text-gray-400">
                データを読み込み中...
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* ヘッダー */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              LLM API 使用状況ダッシュボード
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              APIの使用状況とコストを監視します
            </p>
          </div>
          
          <div className="mt-4 sm:mt-0 flex flex-col sm:flex-row items-start sm:items-center space-y-2 sm:space-y-0 sm:space-x-4">
            {error && (
              <div className="flex items-center space-x-2 text-amber-600 dark:text-amber-400">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">モックデータ表示中</span>
              </div>
            )}
            <div className="text-sm text-gray-600 dark:text-gray-400">
              最終更新: {lastUpdated.toLocaleTimeString('ja-JP')}
            </div>
            <button
              onClick={refetch}
              disabled={loading}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors min-h-touch touch-manipulation"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>更新</span>
            </button>
          </div>
        </div>

        {/* サマリーカード */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <SummaryCard
            title="今日のトークン数"
            value={formatNumber(summary?.todayTokens || 0)}
            icon={<Activity className="w-6 h-6" />}
            colorClass="text-blue-600"
            darkMode={darkMode}
          />
          <SummaryCard
            title="今日のコスト"
            value={formatCurrency(summary?.todayCost || 0)}
            icon={<DollarSign className="w-6 h-6" />}
            colorClass="text-green-600"
            darkMode={darkMode}
          />
          <SummaryCard
            title="今月のコスト"
            value={formatCurrency(summary?.monthCost || 0)}
            icon={<Calendar className="w-6 h-6" />}
            colorClass="text-orange-600"
            darkMode={darkMode}
          />
          <SummaryCard
            title="API呼び出し回数"
            value={formatNumber(summary?.totalCalls || 0)}
            icon={<TrendingUp className="w-6 h-6" />}
            colorClass="text-purple-600"
            darkMode={darkMode}
          />
        </div>

        {/* サービス別使用量テーブル */}
        <div className="mb-8">
          <ServiceUsageTable 
            serviceUsage={serviceUsage} 
            darkMode={darkMode} 
          />
        </div>

        {/* 日次使用量グラフ */}
        <DailyUsageChart 
          dailyUsage={dailyUsage} 
          darkMode={darkMode} 
        />
      </div>
    </div>
  );
};

export default UsageDashboard;
```

### 7. Tailwind CSSの拡張設定
```javascript
// tailwind.config.js に追加
theme: {
  extend: {
    colors: {
      blue: {
        50: '#eff6ff',
        100: '#dbeafe',
        // ... 既存の色設定
      }
    },
    animation: {
      'spin': 'spin 1s linear infinite',
      'pulse': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
    }
  }
}
```

### 8. テスト項目
1. バンドルサイズの削減確認（~90KB削減予想）
2. 全ての機能が Material-UI 版と同等に動作することを確認
3. レスポンシブデザインが適切に動作することを確認
4. ダークモードでの表示確認
5. タッチデバイスでの操作性確認
6. データ取得エラー時のフォールバック動作確認
7. 自動更新機能の動作確認

### 9. 注意事項
- Rechartsのテーマ設定はダークモード対応が必要
- テーブルのレスポンシブ対応で重要な情報の優先順位を考慮
- Material-UIの削除後は未使用の型定義も確認して削除
- パフォーマンス改善の効果測定を実施

## 完了条件
- [ ] Material-UI完全削除（package.jsonから依存関係削除）
- [ ] UsageDashboard完全置き換え完了
- [ ] 既存機能の動作確認済み
- [ ] バンドルサイズ削減確認済み
- [ ] レスポンシブデザイン動作確認済み
- [ ] ダークモード対応確認済み