import type React from 'react';
import { useEffect, useState } from 'react';
import { ContentRenderer } from './components/content/ContentRenderer';
import ErrorBoundary from './components/ErrorBoundary';
import { Sidebar } from './components/layout/Sidebar';
import { MobileHeader } from './components/mobile/MobileHeader';
import { NewsHeader } from './components/NewsHeader';
import { PWAUpdateNotification } from './components/PWAUpdateNotification';
import { useMobileMenu } from './hooks/useMobileMenu';
import { useSourceData } from './hooks/useSourceData';
import { useTheme } from './hooks/useTheme';
import { isServer } from './utils/ssr';

const sources = [
  'arxiv',
  'github',
  'hacker-news',
  'tech-news',
  'business-news',
  'zenn',
  'qiita',
  'note',
  'reddit',
  '4chan',
  '5chan',
  'trendradar-zhihu',
  'trendradar-juejin',
  'trendradar-ithome',
  'trendradar-36kr',
  'trendradar-weibo',
  'trendradar-toutiao',
];

function App() {
  // 初期ソースの取得
  const getInitialSource = () => {
    if (isServer) return 'hacker-news';
    const urlParams = new URLSearchParams(window.location.search);
    const sourceParam = urlParams.get('source');
    return sourceParam && sources.includes(sourceParam) ? sourceParam : 'hacker-news';
  };

  const [selectedSource, setSelectedSource] = useState(getInitialSource());
  const [selectedDate, setSelectedDate] = useState(new Date());

  const { darkMode, setDarkMode } = useTheme();
  const { isMobileMenuOpen, toggleMobileMenu, closeMobileMenu } = useMobileMenu();

  // ソース変更時にURLを更新
  useEffect(() => {
    if (isServer) return;
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('source', selectedSource);
      window.history.replaceState({}, '', url.toString());
    } catch (error) {
      // テスト環境やセキュリティ制限がある場合は無視
      console.warn('URL更新に失敗しました:', error);
    }
  }, [selectedSource]);

  const { processedItems, isLoading, isError, error, refetch } = useSourceData(
    selectedSource,
    selectedDate
  );

  // 動的タイトル生成

  // Error handler for the main application
  const handleAppError = (error: Error, errorInfo: React.ErrorInfo) => {
    console.error('Application Error:', {
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      source: selectedSource,
    });
  };

  // Handle mobile menu item click
  const handleMobileMenuItemClick = () => {
    closeMobileMenu();
  };

  return (
    <ErrorBoundary onError={handleAppError}>
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex">
        {/* Mobile Header */}
        <MobileHeader
          title="News Dashboard"
          showWeather={false}
          showSearchButton={false}
          onMenuClick={toggleMobileMenu}
          onSearchClick={() => {}}
          rightActions={<></>}
        />

        {/* Sidebar - Hidden on mobile, overlay when menu is open */}
        <div
          className={`
					flex-col w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 fixed h-screen overflow-y-auto z-20
					${isMobileMenuOpen ? 'flex' : 'hidden md:flex'}
				`}
        >
          <Sidebar
            selectedSource={selectedSource}
            setSelectedSource={setSelectedSource}
            selectedDate={selectedDate}
            setSelectedDate={setSelectedDate}
            darkMode={darkMode}
            setDarkMode={setDarkMode}
            onMenuItemClick={handleMobileMenuItemClick}
          />
        </div>

        {/* Mobile Overlay */}
        {isMobileMenuOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-10 md:hidden"
            onClick={closeMobileMenu}
          />
        )}

        {/* Main Content Spacer - Hidden on mobile */}
        <div className="hidden md:block w-64 flex-shrink-0"></div>

        {/* Main Content */}
        <div className="flex-1 pt-16 md:pt-0">
          <div className="p-4 sm:p-6 lg:p-8 pt-4 pb-4">
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
        </div>

        {/* PWA更新通知 */}
        <PWAUpdateNotification />
      </div>
    </ErrorBoundary>
  );
}

export default App;
