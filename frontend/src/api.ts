import axios, { type AxiosError, type AxiosRequestConfig, type AxiosResponse } from 'axios';
import type {
  ApiErrorContext,
  ApiErrorResponse,
  ContentResponse,
  NetworkError,
  ServerError,
  WeatherResponse,
} from './types';

const isDevelopment = import.meta.env.DEV;

// Axios instance with enhanced configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 10000, // 10 seconds timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Retry configuration
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second base delay

// Type guards
const isNetworkError = (error: unknown): error is NetworkError => {
  return (
    typeof error === 'object' &&
    error !== null &&
    (error as Record<string, unknown>).isNetworkError === true
  );
};

const isServerError = (error: unknown): error is ServerError => {
  return (
    typeof error === 'object' &&
    error !== null &&
    (error as Record<string, unknown>).isServerError === true
  );
};

// Error context creation
const createErrorContext = (config: AxiosRequestConfig): ApiErrorContext => ({
  url: `${config.baseURL || ''}${config.url || ''}`,
  method: (config.method || 'GET').toUpperCase(),
  params: config.params,
  headers: config.headers as Record<string, string>,
  timestamp: new Date().toISOString(),
});

// Logging utility
const logError = (error: Error, context: ApiErrorContext) => {
  if (isDevelopment) {
    console.group('🚨 API Error');
    console.error('Error:', error.message);
    console.error('Context:', context);
    console.error('Stack:', error.stack);
    console.groupEnd();
  } else {
    // Production: log only essential information
    console.error('API Error:', {
      message: error.message,
      url: context.url,
      method: context.method,
      timestamp: context.timestamp,
    });
  }
};

const logSuccess = (response: AxiosResponse, context: ApiErrorContext) => {
  if (isDevelopment) {
    console.group('✅ API Success');
    console.log('URL:', context.url);
    console.log('Method:', context.method);
    console.log('Status:', response.status);
    console.log('Data:', response.data);
    console.groupEnd();
  }
};

// Retry utility
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const context = createErrorContext(config);
    if (isDevelopment) {
      console.group('🚀 API Request');
      console.log('URL:', context.url);
      console.log('Method:', context.method);
      console.log('Params:', context.params);
      console.groupEnd();
    }
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    const context = createErrorContext(response.config);
    logSuccess(response, context);
    return response;
  },
  async (error: AxiosError) => {
    const context = createErrorContext(error.config || {});

    // Network error (no response)
    if (!error.response) {
      const networkError: NetworkError = {
        name: 'NetworkError',
        message: error.message || 'Network error occurred',
        code: error.code,
        isNetworkError: true,
        context,
      };

      logError(networkError, context);
      return Promise.reject(networkError);
    }

    // Server error (with response)
    const apiErrorResponse: ApiErrorResponse = {
      message: error.response.data?.message || error.message || 'Server error occurred',
      status: error.response.status,
      statusText: error.response.statusText,
      url: context.url,
      timestamp: new Date().toISOString(),
    };

    const serverError: ServerError = {
      name: 'ServerError',
      message: apiErrorResponse.message,
      response: apiErrorResponse,
      isServerError: true,
      context,
    };

    logError(serverError, context);
    return Promise.reject(serverError);
  }
);

// Enhanced API functions with retry logic
const apiCallWithRetry = async <T>(
  apiCall: () => Promise<AxiosResponse<T>>,
  retries: number = MAX_RETRIES
): Promise<T> => {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await apiCall();
      return response.data;
    } catch (error) {
      // Don't retry on server errors (4xx, 5xx), only on network errors
      if (attempt === retries || isServerError(error)) {
        throw error;
      }

      // Only retry on network errors
      if (isNetworkError(error)) {
        const delayMs = RETRY_DELAY * 2 ** attempt; // Exponential backoff
        if (isDevelopment) {
          console.warn(
            `🔄 Retrying API call (attempt ${attempt + 1}/${retries + 1}) in ${delayMs}ms`
          );
        }
        await delay(delayMs);
      } else {
        throw error;
      }
    }
  }

  throw new Error('Max retries exceeded');
};

// Type-safe API response validation
const validateResponse = <T>(data: unknown, validator: (data: unknown) => data is T): T => {
  if (!validator(data)) {
    throw new Error('Invalid response format');
  }
  return data;
};

// Type guards for API responses
const isContentResponse = (data: unknown): data is ContentResponse => {
  return (
    typeof data === 'object' &&
    data !== null &&
    'items' in data &&
    Array.isArray((data as Record<string, unknown>).items)
  );
};

const isWeatherResponse = (data: unknown): data is WeatherResponse => {
  const record = data as Record<string, unknown>;
  return (
    typeof data === 'object' &&
    data !== null &&
    'temperature' in record &&
    'icon' in record &&
    typeof record.temperature === 'number' &&
    typeof record.icon === 'string'
  );
};

// Enhanced API functions
export const getContent = async (source: string, date?: string): Promise<ContentResponse> => {
  const data = await apiCallWithRetry(() =>
    api.get<ContentResponse>(`/content/${source}`, {
      params: { date },
    })
  );

  return validateResponse(data, isContentResponse);
};

export const getWeather = async (): Promise<WeatherResponse> => {
  const data = await apiCallWithRetry(() => api.get<WeatherResponse>('/weather'));

  return validateResponse(data, isWeatherResponse);
};

// Export utilities for advanced usage
export { isNetworkError, isServerError, api as apiInstance };
