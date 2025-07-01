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
    const renderLogic: { [key: string]: () => React.ReactElement[] } = {
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