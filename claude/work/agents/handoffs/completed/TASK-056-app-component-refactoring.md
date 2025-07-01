# TASK-056: App.tsxコンポーネント分割とリファクタリング

## タスク概要
1707行に肥大化したApp.tsxを機能別コンポーネントとカスタムフックに分割し、保守性と開発効率を向上させる。各パース関数を独立したユーティリティに移行し、TypeScript型安全性を強化する。

## 変更予定ファイル
- nook/frontend/src/App.tsx（大幅簡素化）
- nook/frontend/src/hooks/useSourceData.ts（新規作成）
- nook/frontend/src/hooks/useTheme.ts（新規作成）
- nook/frontend/src/hooks/useMobileMenu.ts（新規作成）
- nook/frontend/src/utils/parsers/index.ts（新規作成）
- nook/frontend/src/utils/parsers/githubParser.ts（新規作成）
- nook/frontend/src/utils/parsers/techNewsParser.ts（新規作成）
- nook/frontend/src/utils/parsers/businessNewsParser.ts（新規作成）
- nook/frontend/src/utils/parsers/zennParser.ts（新規作成）
- nook/frontend/src/utils/parsers/qiitaParser.ts（新規作成）
- nook/frontend/src/utils/parsers/noteParser.ts（新規作成）
- nook/frontend/src/utils/parsers/redditParser.ts（新規作成）
- nook/frontend/src/utils/parsers/arxivParser.ts（新規作成）
- nook/frontend/src/utils/parsers/fourchanParser.ts（新規作成）
- nook/frontend/src/utils/parsers/fivechanParser.ts（新規作成）
- nook/frontend/src/utils/parsers/hackerNewsParser.ts（新規作成）
- nook/frontend/src/components/layout/MainLayout.tsx（新規作成）
- nook/frontend/src/components/layout/Sidebar.tsx（新規作成）
- nook/frontend/src/components/content/ContentRenderer.tsx（新規作成）

## 前提タスク
TASK-054, TASK-055（Phase 1完了後）

## worktree名
worktrees/TASK-056-app-component-refactoring

## 作業内容

### 1. パーサーユーティリティの作成

#### utils/parsers/githubParser.ts
```typescript
import { ContentItem } from '../../types';

export function parseGitHubTrendingMarkdown(markdown: string): ContentItem[] {
  // 既存のparseGitHubTrendingMarkdown関数を移動
  // 型安全性を強化し、エラーハンドリングを追加
}
```

#### utils/parsers/index.ts
```typescript
export { parseGitHubTrendingMarkdown } from './githubParser';
export { parseTechNewsMarkdown } from './techNewsParser';
export { parseBusinessNewsMarkdown } from './businessNewsParser';
export { parseZennArticlesMarkdown } from './zennParser';
export { parseQiitaArticlesMarkdown } from './qiitaParser';
export { parseNoteArticlesMarkdown } from './noteParser';
export { parseRedditPostsMarkdown } from './redditParser';
export { parseAcademicPapersMarkdown } from './arxivParser';
export { parseFourchanThreadsMarkdown } from './fourchanParser';
export { parseFivechanThreadsMarkdown } from './fivechanParser';
export { parseHackerNewsData } from './hackerNewsParser';

// パーサー選択ロジックを統一
export function getParserForSource(source: string) {
  const parsers = {
    'github': parseGitHubTrendingMarkdown,
    'tech-news': parseTechNewsMarkdown,
    'business-news': parseBusinessNewsMarkdown,
    'zenn': parseZennArticlesMarkdown,
    'qiita': parseQiitaArticlesMarkdown,
    'note': parseNoteArticlesMarkdown,
    'reddit': parseRedditPostsMarkdown,
    'arxiv': parseAcademicPapersMarkdown,
    '4chan': parseFourchanThreadsMarkdown,
    '5chan': parseFivechanThreadsMarkdown,
    'hacker-news': parseHackerNewsData,
  };
  
  return parsers[source] || null;
}
```

### 2. カスタムフックの作成

#### hooks/useSourceData.ts
```typescript
import { useQuery } from 'react-query';
import { useMemo } from 'react';
import { format } from 'date-fns';
import { getContent } from '../api';
import { getParserForSource } from '../utils/parsers';
import { ContentItem } from '../types';

export function useSourceData(selectedSource: string, selectedDate: Date, enabled: boolean = true) {
  const { data, isLoading, isError, error, refetch } = useQuery(
    ['content', selectedSource, format(selectedDate, 'yyyy-MM-dd')],
    () => getContent(selectedSource, format(selectedDate, 'yyyy-MM-dd')),
    {
      retry: 2,
      enabled,
    }
  );

  const processedItems = useMemo((): ContentItem[] => {
    if (!data?.items || data.items.length === 0) {
      return [];
    }

    const parser = getParserForSource(selectedSource);
    if (parser && data.items[0]?.content) {
      try {
        return parser(data.items[0].content);
      } catch (error) {
        console.error(`${selectedSource} parsing error:`, error);
        return data.items;
      }
    }

    return data.items;
  }, [data, selectedSource]);

  return {
    data,
    processedItems,
    isLoading,
    isError,
    error,
    refetch,
  };
}
```

#### hooks/useTheme.ts
```typescript
import { useState, useEffect } from 'react';

export function useTheme() {
  const [darkMode, setDarkMode] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  return { darkMode, setDarkMode };
}
```

#### hooks/useMobileMenu.ts
```typescript
import { useState, useEffect } from 'react';

export function useMobileMenu() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [scrollPosition, setScrollPosition] = useState(0);

  useEffect(() => {
    if (isMobileMenuOpen) {
      const currentScrollY = window.scrollY;
      setScrollPosition(currentScrollY);
      
      document.body.style.overflow = 'hidden';
      document.body.style.position = 'fixed';
      document.body.style.top = `-${currentScrollY}px`;
      document.body.style.width = '100%';
    } else {
      document.body.style.overflow = '';
      document.body.style.position = '';
      document.body.style.top = '';
      document.body.style.width = '';
      
      window.scrollTo(0, scrollPosition);
    }
    
    return () => {
      document.body.style.overflow = '';
      document.body.style.position = '';
      document.body.style.top = '';
      document.body.style.width = '';
    };
  }, [isMobileMenuOpen, scrollPosition]);

  return {
    isMobileMenuOpen,
    setIsMobileMenuOpen,
  };
}
```

### 3. レイアウトコンポーネントの作成

#### components/layout/Sidebar.tsx
```typescript
import React from 'react';
import { Layout, Calendar, Sun, Moon } from 'lucide-react';
import { format, subDays } from 'date-fns';
import { WeatherWidget } from '../WeatherWidget';
import { sourceDisplayInfo, defaultSourceDisplayInfo } from '../../config/sourceDisplayInfo';

interface SidebarProps {
  selectedSource: string;
  setSelectedSource: (source: string) => void;
  currentPage: string;
  setCurrentPage: (page: string) => void;
  selectedDate: Date;
  setSelectedDate: (date: Date) => void;
  darkMode: boolean;
  setDarkMode: (dark: boolean) => void;
  onMenuItemClick: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  selectedSource,
  setSelectedSource,
  currentPage,
  setCurrentPage,
  selectedDate,
  setSelectedDate,
  darkMode,
  setDarkMode,
  onMenuItemClick,
}) => {
  const sources = ['arxiv', 'github', 'hacker-news', 'tech-news', 'business-news', 'zenn', 'qiita', 'note', 'reddit', '4chan', '5chan'];

  return (
    <>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <Layout className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          <span className="text-xl font-bold text-gray-900 dark:text-white">Dashboard</span>
        </div>
      </div>
      
      {/* Weather Widget */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <WeatherWidget />
      </div>
      
      {/* Date Selector */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2 mb-3">
          <Calendar className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <span className="font-medium text-gray-700 dark:text-gray-300">Select Date</span>
        </div>
        <input
          type="date"
          value={format(selectedDate, 'yyyy-MM-dd')}
          max={format(new Date(), 'yyyy-MM-dd')}
          min={format(subDays(new Date(), 30), 'yyyy-MM-dd')}
          onChange={(e) => setSelectedDate(new Date(e.target.value))}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white min-h-touch touch-manipulation"
        />
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        {/* Dashboard Section */}
        <div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Dashboard</div>
        <button
          onClick={() => {
            setCurrentPage('usage-dashboard');
            onMenuItemClick();
          }}
          className={`w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors min-h-touch touch-manipulation ${
            currentPage === 'usage-dashboard'
              ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
              : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/30'
          }`}
        >
          Usage Dashboard
        </button>
        
        {/* Sources Section */}
        <div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400 mt-6">Sources</div>
        {sources.map((source) => {
          const sourceInfo = sourceDisplayInfo[source] || defaultSourceDisplayInfo;
          return (
            <button
              key={source}
              onClick={() => {
                setSelectedSource(source);
                setCurrentPage('content');
                onMenuItemClick();
              }}
              className={`w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors min-h-touch touch-manipulation ${
                selectedSource === source && currentPage === 'content'
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/30'
              }`}
            >
              {sourceInfo.title}
            </button>
          );
        })}
        
        {/* Theme Toggle */}
        <div className="mt-6">
          <div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Theme</div>
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="w-full flex items-center justify-between px-4 py-2 rounded-lg font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/30 min-h-touch touch-manipulation"
          >
            <span>{darkMode ? 'Light Mode' : 'Dark Mode'}</span>
            {darkMode ? (
              <Sun className="w-5 h-5 text-yellow-500" />
            ) : (
              <Moon className="w-5 h-5 text-blue-600" />
            )}
          </button>
        </div>
      </nav>
    </>
  );
};
```

#### components/content/ContentRenderer.tsx
```typescript
import React from 'react';
import { ContentCard } from '../ContentCard';
import { ContentItem } from '../../types';

interface ContentRendererProps {
  processedItems: ContentItem[];
  selectedSource: string;
  darkMode: boolean;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => void;
}

export const ContentRenderer: React.FC<ContentRendererProps> = ({
  processedItems,
  selectedSource,
  darkMode,
  isLoading,
  isError,
  error,
  refetch,
}) => {
  // 番号付けロジックを統一した関数として実装
  const renderContentItems = () => {
    if (!processedItems || processedItems.length === 0) {
      return (
        <div className="col-span-full text-center py-8">
          <p className="text-gray-500 dark:text-gray-400">No content available for this source</p>
        </div>
      );
    }

    // ソース別の番号付けロジック
    const renderLogic = {
      'github': () => {
        let repositoryCount = 0;
        return processedItems.map((item, index) => {
          if (item.isLanguageHeader) {
            repositoryCount = 0;
          }
          const repositoryIndex = item.isRepository ? repositoryCount++ : undefined;
          return (
            <ContentCard 
              key={index} 
              item={item} 
              darkMode={darkMode} 
              index={repositoryIndex} 
            />
          );
        });
      },
      'tech-news': () => renderWithArticleNumbers(),
      'business-news': () => renderWithArticleNumbers(),
      'zenn': () => renderWithArticleNumbers(),
      'qiita': () => renderWithArticleNumbers(),
      'note': () => renderWithArticleNumbers(),
      'reddit': () => renderWithArticleNumbers(),
      '4chan': () => renderWithArticleNumbers(),
      '5chan': () => renderWithArticleNumbers(),
      'hacker-news': () => {
        let articleCount = 0;
        return processedItems.map((item, index) => {
          const articleIndex = item.isArticle ? articleCount++ : undefined;
          return (
            <ContentCard 
              key={index} 
              item={item} 
              darkMode={darkMode} 
              index={articleIndex} 
            />
          );
        });
      },
      'arxiv': () => renderWithArticleNumbers(),
      'default': () => processedItems.map((item, index) => (
        <ContentCard 
          key={index} 
          item={item} 
          darkMode={darkMode} 
          index={index} 
        />
      ))
    };

    const renderFunction = renderLogic[selectedSource] || renderLogic.default;
    return renderFunction();
  };

  const renderWithArticleNumbers = () => {
    return processedItems.map((item, index) => {
      const isArticle = item.isArticle;
      const articleIndex = isArticle && item.metadata?.articleNumber 
        ? item.metadata.articleNumber - 1 
        : undefined;
      return (
        <ContentCard 
          key={index} 
          item={item} 
          darkMode={darkMode} 
          index={articleIndex} 
        />
      );
    });
  };

  if (isLoading) {
    return (
      <>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
            <div className="space-y-3">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
            </div>
          </div>
        ))}
      </>
    );
  }

  if (isError) {
    return (
      <div className="col-span-full text-center py-8">
        <p className="text-red-600 dark:text-red-400 mb-4">
          Error loading content: {(error as Error)?.message || 'Unknown error occurred'}
        </p>
        <button
          onClick={() => refetch()}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors dark:bg-blue-700 dark:hover:bg-blue-600 min-h-touch min-w-touch touch-manipulation"
        >
          Try Again
        </button>
      </div>
    );
  }

  return <>{renderContentItems()}</>;
};
```

### 4. 新しいApp.tsxの作成
```typescript
import React, { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import { NewsHeader } from './components/NewsHeader';
import UsageDashboard from './components/UsageDashboard';
import { Sidebar } from './components/layout/Sidebar';
import { ContentRenderer } from './components/content/ContentRenderer';
import { useSourceData } from './hooks/useSourceData';
import { useTheme } from './hooks/useTheme';
import { useMobileMenu } from './hooks/useMobileMenu';

const sources = ['arxiv', 'github', 'hacker-news', 'tech-news', 'business-news', 'zenn', 'qiita', 'note', 'reddit', '4chan', '5chan'];

function App() {
  // 初期ソースの取得
  const getInitialSource = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const sourceParam = urlParams.get('source');
    return (sourceParam && sources.includes(sourceParam)) ? sourceParam : 'hacker-news';
  };

  const [selectedSource, setSelectedSource] = useState(getInitialSource());
  const [currentPage, setCurrentPage] = useState('content');
  const [selectedDate, setSelectedDate] = useState(new Date());
  
  const { darkMode, setDarkMode } = useTheme();
  const { isMobileMenuOpen, setIsMobileMenuOpen } = useMobileMenu();
  
  // ソース変更時にURLを更新
  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('source', selectedSource);
    window.history.replaceState({}, '', url.toString());
  }, [selectedSource]);
  
  const { data, processedItems, isLoading, isError, error, refetch } = useSourceData(
    selectedSource, 
    selectedDate, 
    currentPage === 'content'
  );

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex flex-col w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 fixed h-screen overflow-y-auto">
        <Sidebar
          selectedSource={selectedSource}
          setSelectedSource={setSelectedSource}
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          selectedDate={selectedDate}
          setSelectedDate={setSelectedDate}
          darkMode={darkMode}
          setDarkMode={setDarkMode}
          onMenuItemClick={() => {}}
        />
      </div>

      {/* Main Content Spacer */}
      <div className="hidden md:block w-64 flex-shrink-0"></div>

      {/* Mobile Menu Button */}
      <div className="md:hidden fixed top-0 left-0 z-20 m-4">
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="min-h-touch min-w-touch p-2 rounded-lg bg-white dark:bg-gray-800 shadow-md flex items-center justify-center touch-manipulation"
          aria-label="メニューを開く"
        >
          <Menu className="w-6 h-6 text-gray-700 dark:text-gray-300" />
        </button>
      </div>

      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-10 bg-gray-800 bg-opacity-75 dark:bg-black dark:bg-opacity-75">
          <div className="fixed inset-y-0 left-0 w-64 bg-white dark:bg-gray-800 overflow-y-auto">
            <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-2">
                <Layout className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                <span className="text-xl font-bold text-gray-900 dark:text-white">Dashboard</span>
              </div>
              <button
                onClick={() => setIsMobileMenuOpen(false)}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 min-h-touch min-w-touch touch-manipulation"
                aria-label="メニューを閉じる"
              >
                ✕
              </button>
            </div>
            <div className="h-full">
              <Sidebar
                selectedSource={selectedSource}
                setSelectedSource={setSelectedSource}
                currentPage={currentPage}
                setCurrentPage={setCurrentPage}
                selectedDate={selectedDate}
                setSelectedDate={setSelectedDate}
                darkMode={darkMode}
                setDarkMode={setDarkMode}
                onMenuItemClick={() => setIsMobileMenuOpen(false)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1">
        {currentPage === 'usage-dashboard' ? (
          <UsageDashboard darkMode={darkMode} />
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
    </div>
  );
}

export default App;
```

### 5. テスト項目
1. 各パーサーが正常に動作することを確認
2. カスタムフックがstate管理を適切に行うことを確認
3. 分割後のコンポーネントが既存の機能を全て保持していることを確認
4. モバイルメニューの動作確認
5. パフォーマンス改善（ホットリロード速度等）を確認
6. TypeScript型エラーがないことを確認

### 6. 完了条件
- [ ] App.tsxが200行以下に簡素化
- [ ] 全てのパーサー関数が独立ファイルに移行
- [ ] カスタムフックによる状態管理の分離完了
- [ ] 既存機能の動作確認済み
- [ ] TypeScript型エラー解消
- [ ] ホットリロード速度の改善確認