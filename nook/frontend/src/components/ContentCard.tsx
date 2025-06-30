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
  if ((item as any).isLanguageHeader) {
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
              className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline inline-flex items-center"
            >
              {item.title}
              <ExternalLink size={16} className="ml-1 inline-block flex-shrink-0" />
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