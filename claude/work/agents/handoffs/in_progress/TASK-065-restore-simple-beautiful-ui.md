# TASK-065: シンプルで美しいUI復元（段階的アプローチ）

## タスク概要
Container Queriesアプローチが2回失敗したため、コミット18b6230の美しくシンプルなUIに段階的に復元します。複雑なContainer Queriesではなく、基本的なTailwindクラスで美しいカードレイアウトを実現します。

## 変更予定ファイル
- nook/frontend/src/components/ContentCard.tsx
- nook/frontend/src/App.tsx
- nook/frontend/src/index.css（シンプル化）

## 前提タスク
TASK-063、TASK-064（Container Queries試行）

## worktree名
worktrees/TASK-065-restore-simple-beautiful-ui

## 作業内容

### 1. ContentCard.tsx復元

コミット18b6230の美しいContentCard.tsxに復元：

```tsx
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
  // 言語セクションヘッダーの場合は特別なスタイルで表示
  if (item.isLanguageHeader) {
    return (
      <div className="w-full mt-8 first:mt-0 mb-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white border-b-2 border-gray-200 dark:border-gray-700 pb-2">
          {item.title}
        </h2>
      </div>
    );
  }

  // カテゴリセクションヘッダーの場合は特別なスタイルで表示
  if (item.isCategoryHeader) {
    return (
      <div className="w-full mt-8 first:mt-0 mb-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white border-b-2 border-gray-200 dark:border-gray-700 pb-2">
          {item.title}
        </h2>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow w-full">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white flex-1">
          {index !== undefined && (
            <span className="inline-block bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 text-sm font-medium px-2 py-1 rounded-full mr-3">
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
              <ExternalLink size={20} className="ml-2 inline-block flex-shrink-0" />
            </a>
          ) : (
            <span>{item.title}</span>
          )}
        </h3>
      </div>
      <div className={`prose prose-lg max-w-none w-full overflow-x-auto ${darkMode ? 'prose-invert' : ''}`}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.content}</ReactMarkdown>
      </div>
      <div className="mt-4 flex items-center justify-between">
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
          {item.source}
        </span>
      </div>
    </div>
  );
};
```

### 2. App.tsx レイアウト復元

Main Contentセクションをシンプルなレイアウトに復元：

```tsx
{/* Main Content */}
<div className="flex-1">
  {currentPage === 'usage-dashboard' ? (
    <div className="dashboard-container">
      <UsageDashboard />
    </div>
  ) : (
    <div className="p-4 sm:p-6 lg:p-8">
      <NewsHeader 
        selectedSource={selectedSource}
        selectedDate={selectedDate}
        darkMode={darkMode}
      />

      <div className="grid grid-cols-1 gap-6">
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

**重要な変更点:**
- `content-container`クラス削除
- `cq-xs:grid cq-xs:grid-cols-1 cq-xl:grid-cols-1` → `grid grid-cols-1`
- `cq-xs:p-4 cq-md:p-6 cq-lg:p-8` → `p-4 sm:p-6 lg:p-8`

### 3. index.css シンプル化

Container Queriesの複雑なシステムを削除し、基本的なTailwindのみに：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* 基本的なカスタムスタイルのみ保持 */
@layer components {
  .dashboard-container {
    container-type: inline-size;
    container-name: dashboard;
  }
}
```

### 4. tailwind.config.js シンプル化

Container Queriesプラグインを削除し、基本設定のみに：

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      minHeight: {
        'touch': '44px',
        'touch-large': '48px',
      },
      minWidth: {
        'touch': '44px',
        'touch-large': '48px',
      },
      spacing: {
        'touch': '44px',
        'touch-large': '48px',
      },
      colors: {
        blue: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        }
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: '100%',
            width: '100%',
            fontSize: '1.25rem',
            p: {
              fontSize: '1.25rem',
            },
            li: {
              fontSize: '1.25rem',
            },
            h1: {
              fontSize: '2.25rem',
            },
            h2: {
              fontSize: '1.875rem',
            },
            h3: {
              fontSize: '1.5rem',
            },
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    // @tailwindcss/container-queries を削除
  ],
};
```

### 5. package.json クリーンアップ

Container Queriesプラグインを削除：

```bash
npm uninstall @tailwindcss/container-queries
```

### 6. 完全リビルド

```bash
# キャッシュクリア
rm -rf node_modules/.cache
rm -rf dist

# 完全なリビルド
npm run build

# 開発サーバー起動
npm run dev
```

### 7. UI確認

確認項目：
- [ ] カードが美しい影付きで表示される
- [ ] `bg-white dark:bg-gray-800 rounded-lg shadow-md p-6` スタイルが適用される
- [ ] hover時に `hover:shadow-lg` が動作する
- [ ] レスポンシブレイアウトが正常（`p-4 sm:p-6 lg:p-8`）
- [ ] Image #1のような洗練されたカードレイアウトが復活する

### 8. 段階的改善（必要に応じて）

基本UIが復元された後、必要に応じて：
1. より美しいカードスタイルの追加
2. アニメーション効果の追加
3. レスポンシブ改善

### 9. 品質確認
- [ ] ビルドが成功する
- [ ] 全テストが成功する（存在する場合）
- [ ] UI が美しいカード形式で表示される
- [ ] エラーコンソールにWarningがない

### 10. コミットメッセージ
```
TASK-065: シンプルで美しいUI復元（段階的アプローチ）

実装内容：
- ContentCard.tsxをコミット18b6230の美しいバージョンに復元
- App.tsxのレイアウトをシンプルなgrid system に復元
- Container Queriesの複雑なシステムを削除
- 基本的なTailwindクラスで美しいカードレイアウトを実現

技術的な判断事項：
- 複雑さよりもシンプルさと確実性を優先
- Container Queriesではなく通常のTailwindレスポンシブクラス使用
- shadow-md, hover:shadow-lg等の基本スタイルで美しさ確保
- コミット18b6230の動作確認済みコードベースに復元

プロンプト: TASK-064を実行しましたがまだレイアウトは治っていないです
部分的に前の状態に戻すことは可能でしょうか
```

## 重要注意事項
- **段階的アプローチ**: 複雑なContainer Queriesではなくシンプルな解決策
- **実証済みコード**: コミット18b6230で美しく動作していたコードを使用
- **確実性重視**: 新しい技術よりも動作確認済みの方法を優先
- **レスポンシブ保持**: sm:, lg: 等の標準Tailwindクラスでレスポンシブ対応

## 期待される結果
- Image #1のような美しいカードレイアウトの復活
- シンプルで保守しやすいコード
- 確実に動作するレスポンシブデザイン
- Container Queriesの複雑さを排除した安定システム