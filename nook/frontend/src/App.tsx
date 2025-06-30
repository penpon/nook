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
import { ContentItem } from './types';

const sources = ['paper', 'github', 'hacker news', 'tech news', 'business news', 'zenn', 'qiita', 'note', 'reddit', '4chan', '5chan'];

// GitHub TrendingのMarkdownをパースして個別のコンテンツアイテムに変換
function parseGitHubTrendingMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
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
        
        // 説明を取得（次の行以降）
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          // 次のセクションまたは次のリポジトリに到達したら終了
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.includes('⭐')) {
            // スター数の行
            const starMatch = nextLine.match(/⭐\s*スター数:\s*([0-9,]+)/);
            if (starMatch) {
              stars = starMatch[1];
            }
          } else if (nextLine && !nextLine.startsWith('###')) {
            // 説明の行（空行でない場合のみ）
            if (description && nextLine) {
              description += '\n\n';
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

// Tech NewsのMarkdownをパースして個別のコンテンツアイテムに変換
function parseTechNewsMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  let currentCategory = '';
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 日付付きタイトル（# 技術ニュース記事 (2025-06-24)）を無視
    if (line.startsWith('# 技術ニュース記事')) {
      continue;
    }
    
    // カテゴリセクション（## Tech_blogs, ## Hatena等）を検出
    if (line.startsWith('## ') && line.length > 3) {
      currentCategory = line.substring(3).trim();
      // カテゴリ名を読みやすい形式に変換
      const categoryDisplayName = currentCategory
        .replace('_', ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
      
      contentItems.push({
        title: categoryDisplayName,
        content: '',
        source: 'tech news',
        isCategoryHeader: true
      });
    }
    // 記事（### [タイトル](URL)）を検出
    else if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const articleTitle = linkMatch[1];
        const articleUrl = linkMatch[2];
        
        // 次の行からフィード情報と要約を取得
        let feedName = '';
        let summary = '';
        
        // フィード情報と要約を取得（次の行以降）
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          // 次のセクションまたは次の記事に到達したら終了
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.startsWith('**フィード**:')) {
            // フィード情報の行
            feedName = nextLine.replace('**フィード**:', '').trim();
          } else if (nextLine.startsWith('**要約**:')) {
            // 要約情報の開始
            summary = nextLine.replace('**要約**:', '').trim();
            
            // 要約の続きがある場合は次の行も読み込み
            for (let k = j + 1; k < lines.length; k++) {
              const summaryLine = lines[k].trim();
              
              // 次のセクション、記事、または区切り線に到達したら終了
              if (summaryLine.startsWith('#') || summaryLine === '---' || summaryLine.startsWith('**')) {
                break;
              }
              
              if (summaryLine) {
                summary += '\n\n' + summaryLine;
              }
            }
          }
        }
        
        // 記事内容を構築
        let content = '';
        if (feedName) {
          content += `**フィード**: ${feedName}\n\n`;
        }
        if (summary) {
          content += `**要約**:\n${summary}`;
        }
        
        contentItems.push({
          title: articleTitle,
          content: content,
          url: articleUrl,
          source: 'tech news',
          category: currentCategory,
          isArticle: true
        });
      }
    }
  }
  
  return contentItems;
}

// Business NewsのMarkdownをパースして個別のコンテンツアイテムに変換
function parseBusinessNewsMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  let currentCategory = '';
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 日付付きタイトル（# ビジネスニュース記事 (2025-06-24)）を無視
    if (line.startsWith('# ビジネスニュース記事')) {
      continue;
    }
    
    // カテゴリセクション（## Business等）を検出
    if (line.startsWith('## ') && line.length > 3) {
      currentCategory = line.substring(3).trim();
      
      contentItems.push({
        title: currentCategory,
        content: '',
        source: 'business news',
        isCategoryHeader: true
      });
    }
    // 記事（### [タイトル](URL)）を検出
    else if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const articleTitle = linkMatch[1];
        const articleUrl = linkMatch[2];
        
        // 次の行からフィード情報と要約を取得
        let feedName = '';
        let summary = '';
        
        // フィード情報と要約を取得（次の行以降）
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          // 次のセクションまたは次の記事に到達したら終了
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.startsWith('**フィード**:')) {
            // フィード情報の行
            feedName = nextLine.replace('**フィード**:', '').trim();
          } else if (nextLine.startsWith('**要約**:')) {
            // 要約情報の開始
            summary = nextLine.replace('**要約**:', '').trim();
            
            // 要約の続きがある場合は次の行も読み込み
            for (let k = j + 1; k < lines.length; k++) {
              const summaryLine = lines[k].trim();
              
              // 次のセクション、記事、または区切り線に到達したら終了
              if (summaryLine.startsWith('#') || summaryLine === '---' || summaryLine.startsWith('**')) {
                break;
              }
              
              if (summaryLine) {
                summary += '\n\n' + summaryLine;
              }
            }
          }
        }
        
        // 記事内容を構築
        let content = '';
        if (feedName) {
          content += `**フィード**: ${feedName}\n\n`;
        }
        if (summary) {
          content += `**要約**:\n${summary}`;
        }
        
        contentItems.push({
          title: articleTitle,
          content: content,
          url: articleUrl,
          source: 'business news',
          category: currentCategory,
          isArticle: true
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

  // GitHub TrendingとTech NewsのMarkdownパース処理
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

    // Tech Newsの場合は特別な処理
    if (selectedSource === 'tech news' && data.items[0]?.content) {
      try {
        return parseTechNewsMarkdown(data.items[0].content);
      } catch (error) {
        console.error('Tech News Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // Business Newsの場合は特別な処理
    if (selectedSource === 'business news' && data.items[0]?.content) {
      try {
        return parseBusinessNewsMarkdown(data.items[0].content);
      } catch (error) {
        console.error('Business News Markdown parsing error:', error);
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
                  // GitHub Trendingの場合は特別な番号付けロジック
                  if (selectedSource === 'github') {
                    let repositoryCount = 0;
                    return processedItems.map((item, index) => {
                      const isRepository = item.isRepository;
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
                  } 
                  // Tech Newsの場合も特別な番号付けロジック
                  else if (selectedSource === 'tech news') {
                    let articleCount = 0;
                    return processedItems.map((item, index) => {
                      const isArticle = item.isArticle;
                      const articleIndex = isArticle ? articleCount++ : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={articleIndex} 
                        />
                      );
                    });
                  } 
                  // Business Newsの場合も特別な番号付けロジック
                  else if (selectedSource === 'business news') {
                    let articleCount = 0;
                    return processedItems.map((item, index) => {
                      const isArticle = item.isArticle;
                      const articleIndex = isArticle ? articleCount++ : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={articleIndex} 
                        />
                      );
                    });
                  } else {
                    // 他のソースは通常の番号付け
                    return processedItems.map((item, index) => (
                      <ContentCard 
                        key={index} 
                        item={item} 
                        darkMode={darkMode} 
                        index={index} 
                      />
                    ));
                  }
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
