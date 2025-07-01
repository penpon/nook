# TASK-059: Container Queries導入（真のコンポーネント駆動レスポンシブ）

## タスク概要
CSS Container Queriesを導入し、ビューポートベースではなくコンテナサイズベースのレスポンシブデザインを実現する。コンポーネントの再利用性を大幅に向上させ、より柔軟なレイアウトシステムを構築する。

## 変更予定ファイル
- nook/frontend/src/index.css（Container Queries用CSS追加）
- nook/frontend/src/components/ContentCard.tsx（Container Queries対応）
- nook/frontend/src/components/layout/Sidebar.tsx（Container Queries対応）
- nook/frontend/src/components/dashboard/SummaryCard.tsx（Container Queries対応）
- nook/frontend/src/components/dashboard/ServiceUsageTable.tsx（Container Queries対応）
- nook/frontend/src/components/dashboard/DailyUsageChart.tsx（Container Queries対応）
- nook/frontend/tailwind.config.js（Container Queries プラグイン追加）
- nook/frontend/package.json（@tailwindcss/container-queries追加）

## 前提タスク
TASK-058（UIライブラリ統一完了後）

## worktree名
worktrees/TASK-059-container-queries-implementation

## 作業内容

### 1. 依存関係の追加
```json
// package.json に追加
{
  "devDependencies": {
    "@tailwindcss/container-queries": "^0.1.1"
  }
}
```

### 2. Tailwind CSS設定の更新
```javascript
// tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      // Container Queries用の設定
      containers: {
        'xs': '20rem',
        'sm': '24rem',
        'md': '28rem',
        'lg': '32rem',
        'xl': '36rem',
        '2xl': '42rem',
        '3xl': '48rem',
        '4xl': '56rem',
        '5xl': '64rem',
        '6xl': '72rem',
        '7xl': '80rem',
      },
      // 既存の設定...
      typography: {
        // 既存の設定
      }
    }
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/container-queries'), // 追加
  ],
};
```

### 3. 基本CSS設定の追加
```css
/* src/index.css に追加 */

/* Container Queries基本設定 */
.container-query {
  container-type: inline-size;
}

.container-query-normal {
  container-type: normal;
}

.container-query-size {
  container-type: size;
}

/* カスタムコンテナサイズ */
.content-container {
  container-type: inline-size;
  container-name: content;
}

.card-container {
  container-type: inline-size;
  container-name: card;
}

.dashboard-container {
  container-type: inline-size;
  container-name: dashboard;
}

.sidebar-container {
  container-type: inline-size;
  container-name: sidebar;
}

/* Container Queries用のレスポンシブクラス */
@container (min-width: 320px) {
  .cq-xs\:block { display: block; }
  .cq-xs\:grid { display: grid; }
  .cq-xs\:flex { display: flex; }
  .cq-xs\:grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
  .cq-xs\:text-sm { font-size: 0.875rem; line-height: 1.25rem; }
}

@container (min-width: 384px) {
  .cq-sm\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .cq-sm\:flex-row { flex-direction: row; }
  .cq-sm\:text-base { font-size: 1rem; line-height: 1.5rem; }
  .cq-sm\:p-4 { padding: 1rem; }
}

@container (min-width: 448px) {
  .cq-md\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .cq-md\:p-6 { padding: 1.5rem; }
  .cq-md\:text-lg { font-size: 1.125rem; line-height: 1.75rem; }
}

@container (min-width: 512px) {
  .cq-lg\:grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .cq-lg\:flex-row { flex-direction: row; }
  .cq-lg\:space-x-4 > :not([hidden]) ~ :not([hidden]) { 
    margin-left: 1rem; 
  }
}

@container (min-width: 640px) {
  .cq-xl\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .cq-xl\:p-8 { padding: 2rem; }
}

@container (min-width: 768px) {
  .cq-2xl\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
```

### 4. ContentCardコンポーネントの改修
```typescript
// src/components/ContentCard.tsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ExternalLink } from 'lucide-react';
import { ContentItem } from '../types';

interface ContentCardProps {
  item: ContentItem;
  darkMode: boolean;
  index?: number;
}

export const ContentCard: React.FC<ContentCardProps> = ({ item, darkMode, index }) => {
  // 言語セクションヘッダーの場合
  if (item.isLanguageHeader) {
    return (
      <div className="card-container w-full mt-8 first:mt-0 mb-4">
        <h2 className="cq-xs:text-xl cq-md:text-2xl font-bold text-gray-900 dark:text-white border-b-2 border-gray-200 dark:border-gray-700 pb-2">
          {item.title}
        </h2>
      </div>
    );
  }

  // カテゴリセクションヘッダーの場合
  if (item.isCategoryHeader) {
    return (
      <div className="card-container w-full mt-8 first:mt-0 mb-4">
        <h2 className="cq-xs:text-xl cq-md:text-2xl font-bold text-gray-900 dark:text-white border-b-2 border-gray-200 dark:border-gray-700 pb-2">
          {item.title}
        </h2>
      </div>
    );
  }

  return (
    <div className="card-container bg-white dark:bg-gray-800 rounded-lg shadow-md hover:shadow-lg transition-shadow w-full">
      {/* カードヘッダー */}
      <div className="cq-xs:p-4 cq-md:p-6">
        <div className="flex items-start justify-between mb-4">
          <h3 className="cq-xs:text-lg cq-md:text-xl font-semibold text-gray-900 dark:text-white flex-1">
            {index !== undefined && (
              <span className="inline-block bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 cq-xs:text-xs cq-md:text-sm font-medium cq-xs:px-2 cq-xs:py-1 cq-md:px-3 cq-md:py-1 rounded-full mr-3">
                {index + 1}
              </span>
            )}
            {item.url ? (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline inline-flex items-center min-h-touch touch-manipulation"
              >
                {item.title}
                <ExternalLink 
                  size={16} 
                  className="cq-xs:ml-1 cq-md:ml-2 inline-block flex-shrink-0" 
                />
              </a>
            ) : (
              <span>{item.title}</span>
            )}
          </h3>
        </div>

        {/* コンテンツ */}
        <div className={`prose prose-lg max-w-none w-full overflow-x-auto ${darkMode ? 'prose-invert' : ''}`}>
          <div className="cq-xs:text-sm cq-md:text-base">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.content}</ReactMarkdown>
          </div>
        </div>

        {/* フッター */}
        <div className="mt-4 flex items-center justify-between">
          <span className="inline-flex items-center cq-xs:px-2 cq-xs:py-1 cq-md:px-3 cq-md:py-1 rounded-full cq-xs:text-xs cq-md:text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
            {item.source}
          </span>
        </div>
      </div>
    </div>
  );
};
```

### 5. SummaryCardコンポーネントの改修
```typescript
// src/components/dashboard/SummaryCard.tsx
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
    <div className="card-container bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <div className="cq-xs:p-4 cq-md:p-6">
        {/* コンテナサイズに応じたレイアウト変更 */}
        <div className="cq-xs:flex cq-xs:flex-col cq-sm:flex-row cq-sm:items-center cq-sm:justify-between">
          <div className="flex-1">
            <p className="cq-xs:text-xs cq-md:text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              {title}
            </p>
            <p className={`cq-xs:text-lg cq-md:text-2xl cq-lg:text-3xl font-bold ${colorClass}`}>
              {value}
            </p>
          </div>
          <div className={`cq-xs:mt-2 cq-sm:mt-0 cq-xs:self-end cq-sm:self-auto cq-xs:p-2 cq-md:p-3 rounded-full bg-opacity-10 ${colorClass.replace('text-', 'bg-')}`}>
            <div className={`cq-xs:w-5 cq-xs:h-5 cq-md:w-6 cq-md:h-6 ${colorClass}`}>
              {icon}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
```

### 6. ServiceUsageTableコンポーネントの改修
```typescript
// src/components/dashboard/ServiceUsageTable.tsx
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
    <div className="dashboard-container bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <div className="cq-xs:p-4 cq-md:p-6 border-b border-gray-200 dark:border-gray-700">
        <h3 className="cq-xs:text-base cq-md:text-lg font-semibold text-gray-900 dark:text-white">
          サービス別使用量
        </h3>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="cq-xs:px-3 cq-xs:py-2 cq-md:px-6 cq-md:py-3 text-left cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                サービス名
              </th>
              <th className="cq-xs:px-3 cq-xs:py-2 cq-md:px-6 cq-md:py-3 text-right cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                呼び出し
              </th>
              <th className="cq-md:px-6 cq-md:py-3 text-right cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cq-xs:hidden cq-md:table-cell">
                入力トークン
              </th>
              <th className="cq-md:px-6 cq-md:py-3 text-right cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cq-xs:hidden cq-md:table-cell">
                出力トークン
              </th>
              <th className="cq-xs:px-3 cq-xs:py-2 cq-md:px-6 cq-md:py-3 text-right cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                コスト
              </th>
              <th className="cq-lg:px-6 cq-lg:py-3 text-right cq-xs:text-xs cq-md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cq-xs:hidden cq-lg:table-cell">
                最終呼び出し
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {serviceUsage.map((service) => (
              <tr key={service.service} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                <td className="cq-xs:px-3 cq-xs:py-3 cq-md:px-6 cq-md:py-4 whitespace-nowrap">
                  <span className="inline-flex items-center cq-xs:px-2 cq-xs:py-0.5 cq-md:px-2.5 cq-md:py-0.5 rounded-full cq-xs:text-xs cq-md:text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                    {service.service}
                  </span>
                </td>
                <td className="cq-xs:px-3 cq-xs:py-3 cq-md:px-6 cq-md:py-4 whitespace-nowrap text-right cq-xs:text-sm cq-md:text-sm text-gray-900 dark:text-white font-medium">
                  {formatNumber(service.calls)}
                </td>
                <td className="cq-md:px-6 cq-md:py-4 whitespace-nowrap text-right cq-xs:text-sm cq-md:text-sm text-gray-600 dark:text-gray-400 cq-xs:hidden cq-md:table-cell">
                  {formatNumber(service.inputTokens)}
                </td>
                <td className="cq-md:px-6 cq-md:py-4 whitespace-nowrap text-right cq-xs:text-sm cq-md:text-sm text-gray-600 dark:text-gray-400 cq-xs:hidden cq-md:table-cell">
                  {formatNumber(service.outputTokens)}
                </td>
                <td className="cq-xs:px-3 cq-xs:py-3 cq-md:px-6 cq-md:py-4 whitespace-nowrap text-right cq-xs:text-sm cq-md:text-sm font-medium text-green-600 dark:text-green-400">
                  {formatCurrency(service.cost)}
                </td>
                <td className="cq-lg:px-6 cq-lg:py-4 whitespace-nowrap text-right cq-xs:text-sm cq-md:text-sm text-gray-600 dark:text-gray-400 cq-xs:hidden cq-lg:table-cell">
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

### 7. メインレイアウトの改修
```typescript
// src/App.tsx のメインコンテンツ部分を修正
<div className="flex-1">
  {currentPage === 'usage-dashboard' ? (
    <div className="dashboard-container">
      <UsageDashboard darkMode={darkMode} />
    </div>
  ) : (
    <div className="content-container cq-xs:p-4 cq-md:p-6 cq-lg:p-8">
      <NewsHeader 
        selectedSource={selectedSource}
        selectedDate={selectedDate}
        darkMode={darkMode}
      />

      <div className="cq-xs:grid cq-xs:grid-cols-1 cq-xl:grid-cols-1 gap-6">
        <ContentRenderer
          processedItems={processedItems}
          selectedSource={selectedSource}
          darkMode={darkMode}
          isLoading={isLoading}
          isError={isError}
          error={error}
          refetch={refetch}
        />
      </div>
    </div>
  )}
</div>
```

### 8. サイドバーの改修
```typescript
// src/components/layout/Sidebar.tsx のコンテナ設定
export const Sidebar: React.FC<SidebarProps> = ({...props}) => {
  return (
    <div className="sidebar-container h-full">
      {/* Header */}
      <div className="cq-xs:p-3 cq-md:p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <Layout className="cq-xs:w-5 cq-xs:h-5 cq-md:w-6 cq-md:h-6 text-blue-600 dark:text-blue-400" />
          <span className="cq-xs:text-lg cq-md:text-xl font-bold text-gray-900 dark:text-white">Dashboard</span>
        </div>
      </div>
      
      {/* 以下、既存の内容にContainer Queriesクラスを適用 */}
    </div>
  );
};
```

### 9. ダッシュボードのグリッドレイアウト改修
```typescript
// src/components/UsageDashboard.tsx のグリッド部分
{/* サマリーカード */}
<div className="dashboard-container cq-xs:grid cq-xs:grid-cols-1 cq-sm:grid-cols-2 cq-lg:grid-cols-4 cq-xs:gap-4 cq-md:gap-6 mb-8">
  <SummaryCard... />
</div>
```

### 10. テスト項目
1. 各コンポーネントがContainer Queriesに応じて適切にレイアウト変更することを確認
2. ビューポートサイズと独立してコンテナサイズでレスポンシブ動作することを確認
3. サイドバーの幅変更時にコンテンツが適切に調整されることを確認
4. ダッシュボードのカード配置がコンテナサイズに応じて変化することを確認
5. モバイル/デスクトップでの表示確認
6. 異なるブラウザでのContainer Queries対応確認（Chrome 105+, Firefox 110+, Safari 16+）
7. フォールバック表示の確認（古いブラウザ）

### 11. パフォーマンス最適化
- Container Queriesの計算頻度を最適化
- 不要なレイアウト再計算を防ぐため、container-typeを適切に設定
- CSSのカスケードを効率化

### 12. ブラウザ対応フォールバック
```css
/* 古いブラウザ向けフォールバック */
@supports not (container-type: inline-size) {
  .card-container {
    /* ビューポートベースのフォールバック */
  }
  
  .cq-xs\:text-lg {
    font-size: 1.125rem;
    line-height: 1.75rem;
  }
  
  .cq-md\:text-xl {
    font-size: 1.25rem;
    line-height: 1.75rem;
  }
}
```

## 完了条件
- [ ] 全コンポーネントでContainer Queries対応完了
- [ ] ビューポートと独立したレスポンシブ動作確認
- [ ] コンテナサイズに応じた適切なレイアウト変更確認
- [ ] モダンブラウザでの動作確認済み
- [ ] 古いブラウザでのフォールバック動作確認済み
- [ ] パフォーマンス劣化がないことを確認
- [ ] 再利用性の向上確認（異なるコンテキストでの動作）