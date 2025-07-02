import { useQuery, UseQueryResult } from 'react-query';
import { useMemo, useEffect, useCallback, useRef } from 'react';
import { format } from 'date-fns';
import { getContent } from '../api';
import { getParserForSource } from '../utils/parsers';
import { ContentItem, ContentResponse } from '../types';
import { isNetworkError, isServerError } from '../api';

const isDevelopment = import.meta.env.DEV;

// Enhanced return type with detailed state
interface UseSourceDataResult {
  data: ContentResponse | undefined;
  processedItems: ContentItem[];
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => Promise<UseQueryResult<ContentResponse, unknown>>;
  isRetrying: boolean;
  retryCount: number;
  lastSuccessTime: number | null;
  lastErrorTime: number | null;
  parsingError: Error | null;
  performanceMetrics: {
    queryDuration: number | null;
    parseDuration: number | null;
    totalDuration: number | null;
  };
}

// Error context for detailed logging
interface UseSourceDataErrorContext {
  selectedSource: string;
  selectedDate: string;
  enabled: boolean;
  timestamp: string;
  retryAttempt: number;
  queryKey: string[];
}

// Performance monitoring
interface PerformanceMetrics {
  queryStartTime: number | null;
  queryEndTime: number | null;
  parseStartTime: number | null;
  parseEndTime: number | null;
}

export function useSourceData(
  selectedSource: string, 
  selectedDate: Date, 
  enabled: boolean = true
): UseSourceDataResult {
  const performanceRef = useRef<PerformanceMetrics>({
    queryStartTime: null,
    queryEndTime: null,
    parseStartTime: null,
    parseEndTime: null,
  });
  
  const retryCountRef = useRef(0);
  const lastSuccessTimeRef = useRef<number | null>(null);
  const lastErrorTimeRef = useRef<number | null>(null);
  const parsingErrorRef = useRef<Error | null>(null);

  // Format date for consistency
  const formattedDate = useMemo(() => format(selectedDate, 'yyyy-MM-dd'), [selectedDate]);
  
  // Query key for caching
  const queryKey = useMemo(() => ['content', selectedSource, formattedDate], [selectedSource, formattedDate]);

  // Log hook invocation
  useEffect(() => {
    if (isDevelopment) {
      console.group('🔍 useSourceData Hook Called');
      console.log('Parameters:', {
        selectedSource,
        selectedDate: formattedDate,
        enabled,
        timestamp: new Date().toISOString()
      });
      console.log('Query Key:', queryKey);
      console.groupEnd();
    }
  }, [selectedSource, formattedDate, enabled, queryKey]);

  // Enhanced error context creation
  const createErrorContext = useCallback((retryAttempt = 0): UseSourceDataErrorContext => ({
    selectedSource,
    selectedDate: formattedDate,
    enabled,
    timestamp: new Date().toISOString(),
    retryAttempt,
    queryKey,
  }), [selectedSource, formattedDate, enabled, queryKey]);

  // Detailed error logging
  const logError = useCallback((error: unknown, context: UseSourceDataErrorContext, phase: 'query' | 'parsing') => {
    lastErrorTimeRef.current = Date.now();
    
    if (isDevelopment) {
      console.group(`🚨 useSourceData ${phase} Error`);
      console.error('Error:', error);
      console.error('Context:', context);
      
      if (isNetworkError(error)) {
        console.error('Error Type: Network Error');
        console.error('Network Details:', {
          code: error.code,
          context: error.context,
        });
      } else if (isServerError(error)) {
        console.error('Error Type: Server Error');
        console.error('Server Details:', {
          status: error.response.status,
          statusText: error.response.statusText,
          message: error.response.message,
        });
      } else if (error instanceof Error) {
        console.error('Error Type: Generic Error');
        console.error('Stack:', error.stack);
      }
      
      console.groupEnd();
    } else {
      // Production: minimal logging
      console.error('useSourceData Error:', {
        phase,
        message: error instanceof Error ? error.message : 'Unknown error',
        source: selectedSource,
        timestamp: context.timestamp,
      });
    }
  }, [selectedSource]);

  // Success logging
  const logSuccess = useCallback((data: ContentResponse) => {
    lastSuccessTimeRef.current = Date.now();
    
    if (isDevelopment) {
      console.group('✅ useSourceData Success');
      console.log('Data received:', {
        itemCount: data.items?.length || 0,
        source: selectedSource,
        timestamp: new Date().toISOString()
      });
      console.log('Performance:', {
        queryDuration: performanceRef.current.queryEndTime && performanceRef.current.queryStartTime 
          ? performanceRef.current.queryEndTime - performanceRef.current.queryStartTime 
          : null,
      });
      console.groupEnd();
    }
  }, [selectedSource]);

  // Enhanced query with performance monitoring
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
    failureCount,
  } = useQuery<ContentResponse, unknown>(
    queryKey,
    async () => {
      try {
        performanceRef.current.queryStartTime = performance.now();
        
        if (isDevelopment) {
          console.log('🚀 API call started:', {
            source: selectedSource,
            date: formattedDate,
            timestamp: new Date().toISOString()
          });
        }
        
        const result = await getContent(selectedSource, formattedDate);
        
        performanceRef.current.queryEndTime = performance.now();
        
        if (isDevelopment) {
          console.log('📦 API call completed:', {
            source: selectedSource,
            itemCount: result.items?.length || 0,
            duration: performanceRef.current.queryEndTime - (performanceRef.current.queryStartTime || 0),
            timestamp: new Date().toISOString()
          });
        }
        
        logSuccess(result);
        retryCountRef.current = 0; // Reset retry count on success
        return result;
        
      } catch (error) {
        performanceRef.current.queryEndTime = performance.now();
        retryCountRef.current = failureCount + 1;
        
        const errorContext = createErrorContext(retryCountRef.current);
        logError(error, errorContext, 'query');
        
        throw error;
      }
    },
    {
      enabled,
      // Use QueryClient's advanced settings
      onError: (error) => {
        const errorContext = createErrorContext(failureCount);
        logError(error, errorContext, 'query');
      },
      onSuccess: (data) => {
        logSuccess(data);
      },
    }
  );

  // Enhanced processing with error handling and performance monitoring
  const processedItems = useMemo((): ContentItem[] => {
    parsingErrorRef.current = null; // Reset parsing error
    
    if (!data?.items || data.items.length === 0) {
      if (isDevelopment) {
        console.log('📝 No data to process:', { source: selectedSource });
      }
      return [];
    }

    try {
      performanceRef.current.parseStartTime = performance.now();
      
      const parser = getParserForSource(selectedSource);
      
      if (!parser) {
        if (isDevelopment) {
          console.log('📝 No parser found, returning raw data:', { source: selectedSource });
        }
        return data.items;
      }

      if (!data.items[0]?.content) {
        if (isDevelopment) {
          console.log('📝 No content to parse, returning raw data:', { source: selectedSource });
        }
        return data.items;
      }

      let result: ContentItem[];
      
      // Enhanced parsing with error handling
      if (selectedSource === 'hacker-news') {
        result = parser(data.items);
      } else {
        result = parser(data.items[0].content);
      }
      
      performanceRef.current.parseEndTime = performance.now();
      
      if (isDevelopment) {
        console.group('🔄 Data Processing Completed');
        console.log('Source:', selectedSource);
        console.log('Input items:', data.items.length);
        console.log('Processed items:', result.length);
        console.log('Parse duration:', 
          performanceRef.current.parseEndTime - (performanceRef.current.parseStartTime || 0), 'ms'
        );
        console.groupEnd();
      }
      
      return result;
      
    } catch (error) {
      performanceRef.current.parseEndTime = performance.now();
      
      const parseError = error instanceof Error ? error : new Error('Unknown parsing error');
      parsingErrorRef.current = parseError;
      
      const errorContext = createErrorContext();
      logError(parseError, errorContext, 'parsing');
      
      // Return raw data as fallback
      if (isDevelopment) {
        console.warn('📝 Parsing failed, returning raw data:', { 
          source: selectedSource, 
          error: parseError.message 
        });
      }
      
      return data.items;
    }
  }, [data, selectedSource, createErrorContext, logError]);

  // Performance metrics calculation
  const performanceMetrics = useMemo(() => ({
    queryDuration: performanceRef.current.queryEndTime && performanceRef.current.queryStartTime
      ? performanceRef.current.queryEndTime - performanceRef.current.queryStartTime
      : null,
    parseDuration: performanceRef.current.parseEndTime && performanceRef.current.parseStartTime
      ? performanceRef.current.parseEndTime - performanceRef.current.parseStartTime
      : null,
    totalDuration: performanceRef.current.queryEndTime && performanceRef.current.queryStartTime && 
                   performanceRef.current.parseEndTime && performanceRef.current.parseStartTime
      ? (performanceRef.current.queryEndTime - performanceRef.current.queryStartTime) +
        (performanceRef.current.parseEndTime - performanceRef.current.parseStartTime)
      : null,
  }), []); // Static calculation based on refs

  // Enhanced refetch with logging
  const enhancedRefetch = useCallback(async () => {
    if (isDevelopment) {
      console.log('🔄 Manual refetch triggered:', {
        source: selectedSource,
        timestamp: new Date().toISOString()
      });
    }
    
    return refetch();
  }, [refetch, selectedSource]);

  return {
    data,
    processedItems,
    isLoading,
    isError,
    error,
    refetch: enhancedRefetch,
    isRetrying: isFetching && !isLoading,
    retryCount: retryCountRef.current,
    lastSuccessTime: lastSuccessTimeRef.current,
    lastErrorTime: lastErrorTimeRef.current,
    parsingError: parsingErrorRef.current,
    performanceMetrics,
  };
}