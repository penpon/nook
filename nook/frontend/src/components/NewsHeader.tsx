import React from 'react';
import { format } from 'date-fns';

interface NewsHeaderProps {
  selectedSource: string;
  selectedDate: Date;
  darkMode: boolean;
}

export const NewsHeader: React.FC<NewsHeaderProps> = ({ selectedSource, selectedDate, darkMode }) => {
  const formatSourceTitle = (source: string): string => {
    if (source === 'hacker news') {
      return `Hacker News - ${format(selectedDate, 'yyyy-MM-dd')}`;
    }
    return `${source.charAt(0).toUpperCase() + source.slice(1)} Feed`;
  };

  const formatSubtitle = (source: string, date: Date): string => {
    if (source === 'hacker news') {
      return `Hacker News トップ記事 (${format(date, 'yyyy-MM-dd')})`;
    }
    return format(date, 'MMMM d, yyyy');
  };

  return (
    <div className="mb-8">
      <div className={`
        rounded-xl shadow-lg p-8
        ${darkMode 
          ? 'bg-gradient-to-r from-gray-800 to-gray-900 border border-gray-700' 
          : 'bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200'}
        transition-all duration-300 hover:shadow-xl
      `}>
        <h1 className={`
          text-4xl sm:text-5xl lg:text-6xl font-bold text-center mb-3
          ${darkMode ? 'text-white' : 'text-gray-900'}
        `}>
          {formatSourceTitle(selectedSource)}
        </h1>
        <p className={`
          text-lg sm:text-xl text-center
          ${darkMode ? 'text-gray-300' : 'text-gray-600'}
        `}>
          {formatSubtitle(selectedSource, selectedDate)}
        </p>
      </div>
    </div>
  );
};