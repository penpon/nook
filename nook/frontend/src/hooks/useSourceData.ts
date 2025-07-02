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
    console.log('useSourceData debug:', { selectedSource, dataItems: data?.items?.length });
    
    if (!data?.items || data.items.length === 0) {
      console.log('No data items available');
      return [];
    }

    const parser = getParserForSource(selectedSource);
    console.log('Parser found:', !!parser);
    
    if (parser && data.items[0]?.content) {
      try {
        // Hacker Newsの場合は特殊処理
        if (selectedSource === 'hacker-news') {
          console.log('Processing Hacker News data...');
          return parser(data.items);
        }
        // 他のソースはMarkdownをパース
        return parser(data.items[0].content);
      } catch (error) {
        console.error(`${selectedSource} parsing error:`, error);
        return data.items;
      }
    }

    console.log('Returning raw data items');
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