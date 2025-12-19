import { format, subDays } from 'date-fns';
import { Calendar, Layout, Moon, Sun, ChevronDown, ChevronRight } from 'lucide-react';
import type React from 'react';
import { useState } from 'react';
import { defaultSourceDisplayInfo, sourceDisplayInfo } from '../../config/sourceDisplayInfo';
import { WeatherWidget } from '../weather/WeatherWidget';

type SourceGroup = {
  key: string;
  title: string;
  sources: string[];
  defaultExpanded?: boolean;
};

interface SidebarProps {
  selectedSource: string;
  setSelectedSource: (source: string) => void;
  selectedDate: Date;
  setSelectedDate: (date: Date) => void;
  darkMode: boolean;
  setDarkMode: (dark: boolean) => void;
  onMenuItemClick: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  selectedSource,
  setSelectedSource,
  selectedDate,
  setSelectedDate,
  darkMode,
  setDarkMode,
  onMenuItemClick,
}) => {
  // グループ設定（ここに追加するだけでUI側も自動追従）
  const sourceGroups: SourceGroup[] = [
    {
      key: 'default',
      title: 'Feeds',
      sources: [
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
      ],
      defaultExpanded: true,
    },
    {
      key: 'trendradar',
      title: 'TrendRadar',
      sources: [
        'trendradar-zhihu',
        'trendradar-juejin',
        'trendradar-ithome',
        'trendradar-36kr',
        'trendradar-weibo',
        'trendradar-toutiao',
        'trendradar-sspai',
        'trendradar-producthunt',
        'trendradar-freebuf',
        'trendradar-wallstreetcn',
        'trendradar-tencent',
        'trendradar-v2ex',
      ],
      defaultExpanded: true,
    },
  ];

  // グループの開閉状態
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(() => {
    const entries = sourceGroups.map((g) => [g.key, g.defaultExpanded ?? true] as const);
    return Object.fromEntries(entries) as Record<string, boolean>;
  });

  const toggleGroup = (group: string) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [group]: !(prev[group] ?? true),
    }));
  };

  return (
    <div className="sidebar-container h-full flex flex-col">
      {/* Header - 固定 */}
      <div className="p-3 md:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
        <div className="flex items-center space-x-2">
          <Layout className="w-5 h-5 md:w-6 md:h-6 text-blue-600 dark:text-blue-400" />
          <span className="text-lg md:text-xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </span>
        </div>
      </div>

      {/* Weather Widget - 固定 */}
      <div className="p-3 md:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
        <WeatherWidget />
      </div>

      {/* Date Selector - 固定 */}
      <div className="p-3 md:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
        <div className="flex items-center space-x-2 mb-3">
          <Calendar className="w-4 h-4 md:w-5 md:h-5 text-gray-600 dark:text-gray-400" />
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

      {/* Navigation - スクロール可能 */}
      <nav className="flex-1 p-3 md:p-4 overflow-y-auto">
        {sourceGroups.map((group) => {
          const isExpanded = expandedGroups[group.key] ?? true;
          return (
            <div key={group.key} className="mb-4">
              <button
                onClick={() => toggleGroup(group.key)}
                className="w-full flex items-center justify-between px-2 py-1 mb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                <span>{group.title}</span>
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>

              {isExpanded && (
                <div className="space-y-1">
                  {group.sources.map((source) => {
                    const sourceInfo = sourceDisplayInfo[source] || defaultSourceDisplayInfo;
                    return (
                      <button
                        key={source}
                        onClick={() => {
                          setSelectedSource(source);
                          onMenuItemClick();
                        }}
                        className={`w-full text-left px-4 py-2 rounded-lg font-medium transition-colors min-h-touch touch-manipulation flex items-center ${
                          selectedSource === source
                            ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                            : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/30'
                        }`}
                      >
                        {sourceInfo.title}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
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
    </div>
  );
};
