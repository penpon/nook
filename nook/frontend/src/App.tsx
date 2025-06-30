import React, { useState, useEffect, useMemo } from 'react';
import { useQuery } from 'react-query';
import { format, subDays } from 'date-fns';
import { Layout, Menu, Calendar, Sun, Moon } from 'lucide-react';
import { ContentCard } from './components/ContentCard';
import { NewsHeader } from './components/NewsHeader';
import { WeatherWidget } from './components/WeatherWidget';
import UsageDashboard from './components/UsageDashboard';
import { getContent } from './api';
import { sourceDisplayInfo, defaultSourceDisplayInfo } from './config/sourceDisplayInfo';

interface ParsedRepository {
  name: string;        // "owner/repo"
  url: string;         // GitHub URL
  description: string; // 日本語の説明
  stars: string;       // スター数
  language: string;    // 所属言語
}

const sources = ['paper', 'github', 'hacker news', 'tech news', 'business news', 'zenn', 'qiita', 'note', 'reddit', '4chan', '5chan'];

// GitHub TrendingのMarkdownをパースして個別のコンテンツアイテムに変換
function parseGitHubTrendingMarkdown(markdown: string): any[] {
  const lines = markdown.split('\n');
  const contentItems: any[] = [];
  let currentLanguage = '';
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 言語セクション（## Python, ## Go, ## Rust）を検出
    if (line.startsWith('## ') && line.length > 3) {
      currentLanguage = line.substring(3).trim();
      contentItems.push({
        title: currentLanguage,
        content: '',
        source: 'github',
        isLanguageHeader: true
      });
    }
    // リポジトリ（### [owner/repo](url)）を検出
    else if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const repoName = linkMatch[1];
        const repoUrl = linkMatch[2];
        
        // 次の行から説明とスター数を取得
        let description = '';
        let stars = '';
        
        // 説明を取得（次の行以降の空行でない行）
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          if (nextLine === '' || nextLine.startsWith('#')) {
            break;
          }
          if (nextLine.includes('⭐')) {
            // スター数の行
            const starMatch = nextLine.match(/⭐\s*([0-9,]+)/);
            if (starMatch) {
              stars = starMatch[1];
            }
          } else if (!nextLine.startsWith('###')) {
            // 説明の行
            if (description) {
              description += ' ';
            }
            description += nextLine;
          }
        }
        
        contentItems.push({
          title: repoName,
          content: description + (stars ? `\n\n⭐ ${stars}` : ''),
          url: repoUrl,
          source: 'github',
          language: currentLanguage,
          isRepository: true
        });
      }
    }
  }
  
  return contentItems;
}

function App() {
  const [selectedSource, setSelectedSource] = useState('hacker news');
  const [currentPage, setCurrentPage] = useState('content'); // 'content' or 'usage-dashboard'
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    // ローカルストレージから初期値を取得、なければシステム設定を使用
    const savedTheme = localStorage.getItem('theme');
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  
  // テーマの変更を監視して適用
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);
  
  const { data, isLoading, isError, error, refetch } = useQuery(
    ['content', selectedSource, format(selectedDate, 'yyyy-MM-dd')],
    () => getContent(selectedSource, format(selectedDate, 'yyyy-MM-dd')),
    {
      retry: 2,
      enabled: currentPage === 'content', // Only fetch data when on content page
    }
  );

  // GitHub Trendingの場合のMarkdownパース処理
  const processedItems = useMemo(() => {
    if (!data?.items || data.items.length === 0) {
      return [];
    }

    // GitHub Trendingの場合は特別な処理
    if (selectedSource === 'github' && data.items[0]?.content) {
      try {
        return parseGitHubTrendingMarkdown(data.items[0].content);
      } catch (error) {
        console.error('GitHub Trending Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // 他のソースは従来通り
    return data.items;
  }, [data, selectedSource]);

  const SidebarContent = () => (
    <>
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <Layout className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          <span className="text-xl font-bold text-gray-900 dark:text-white">Dashboard</span>
        </div>
      </div>
      
      {/* 天気ウィジェット */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <WeatherWidget />
      </div>
      
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
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
        />
      </div>
      <nav className="flex-1 p-4">
        {/* Dashboard Section */}
        <div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Dashboard</div>
        <button
          onClick={() => {
            setCurrentPage('usage-dashboard');
            setIsMobileMenuOpen(false);
          }}
          className={`w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors ${
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
                setIsMobileMenuOpen(false);
              }}
              className={`w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors ${
                selectedSource === source && currentPage === 'content'
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/30'
              }`}
            >
              {sourceInfo.title}
            </button>
          );
        })}
        
        {/* テーマ切り替えボタン */}
        <div className="mt-6">
          <div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Theme</div>
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="w-full flex items-center justify-between px-4 py-2 rounded-lg font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/30"
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

  return (
    <div className={`min-h-screen bg-gray-100 dark:bg-gray-900 flex`}>
      {/* Side Navigation - Desktop */}
      <div className="hidden md:flex flex-col w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 fixed h-screen overflow-y-auto">
        <SidebarContent />
      </div>

      {/* メインコンテンツ用のスペーサー */}
      <div className="hidden md:block w-64 flex-shrink-0"></div>

      {/* Mobile Menu Button */}
      <div className="md:hidden fixed top-0 left-0 z-20 m-4">
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="p-2 rounded-lg bg-white dark:bg-gray-800 shadow-md"
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
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                ✕
              </button>
            </div>
            <div className="h-full">
              <SidebarContent />
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
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
                    <div className="space-y-3">
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
                    </div>
                  </div>
                ))
              ) : isError ? (
                <div className="col-span-full text-center py-8">
                  <p className="text-red-600 dark:text-red-400 mb-4">Error loading content: {(error as Error)?.message || 'Unknown error occurred'}</p>
                  <button
                    onClick={() => refetch()}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors dark:bg-blue-700 dark:hover:bg-blue-600"
                  >
                    Try Again
                  </button>
                </div>
              ) : processedItems && processedItems.length > 0 ? (
                (() => {
                  let repositoryCount = 0;
                  return processedItems.map((item, index) => {
                    const isRepository = (item as any).isRepository;
                    const repositoryIndex = isRepository ? repositoryCount++ : undefined;
                    return (
                      <ContentCard 
                        key={index} 
                        item={item} 
                        darkMode={darkMode} 
                        index={repositoryIndex} 
                      />
                    );
                  });
                })()
              ) : (
                <div className="col-span-full text-center py-8">
                  <p className="text-gray-500 dark:text-gray-400">No content available for this source</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
