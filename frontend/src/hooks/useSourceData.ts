import { format } from 'date-fns';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getContent } from '../api';
import type { ContentItem } from '../types';
import { getParserForSource } from '../utils/parsers';

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

    if (parser) {
      try {
        // Hacker Newsの場合は特殊処理
        if (selectedSource === 'hacker-news') {
          return parser(data.items);
        }
        // TrendRadar Zhihuの場合も特殊処理
        if (selectedSource === 'trendradar-zhihu') {
          return parser(data.items);
        }
        // TrendRadar Juejinの場合も特殊処理
        if (selectedSource === 'trendradar-juejin') {
          return parser(data.items);
        }
        // TrendRadar ITHomeの場合も特殊処理
        if (selectedSource === 'trendradar-ithome') {
          return parser(data.items);
        }
        // 他のソースはMarkdownをパース
        if (data.items[0]?.content) {
          return parser(data.items[0].content);
        }
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
