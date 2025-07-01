import React, { useState, useEffect } from 'react';
import { Menu, Layout } from 'lucide-react';
import { NewsHeader } from './components/NewsHeader';
import UsageDashboard from './components/UsageDashboard';
import { Sidebar } from './components/layout/Sidebar';
import { ContentRenderer } from './components/content/ContentRenderer';
import { PWAUpdateNotification } from './components/PWAUpdateNotification';
import { useSourceData } from './hooks/useSourceData';
import { useTheme } from './hooks/useTheme';
import { useMobileMenu } from './hooks/useMobileMenu';
import { isServer } from '@/utils/ssr';

const sources = ['arxiv', 'github', 'hacker-news', 'tech-news', 'business-news', 'zenn', 'qiita', 'note', 'reddit', '4chan', '5chan'];

function App() {
  // 初期ソースの取得
  const getInitialSource = () => {
    if (isServer) return 'hacker-news';
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
    if (isServer) return;
    const url = new URL(window.location.href);
    url.searchParams.set('source', selectedSource);
    window.history.replaceState({}, '', url.toString());
  }, [selectedSource]);
  
  const { processedItems, isLoading, isError, error, refetch } = useSourceData(
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
                className="min-h-touch min-w-touch flex items-center justify-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 touch-manipulation"
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
          <div className="dashboard-container">
            <UsageDashboard />
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
      
      {/* PWA更新通知 */}
      <PWAUpdateNotification />
    </div>
  );
}

export default App;