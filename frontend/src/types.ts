export interface ContentItem {
  title: string;
  content: string;
  url?: string;
  source: string;
  language?: string;
  category?: string;
  isLanguageHeader?: boolean;
  isCategoryHeader?: boolean;
  isRepository?: boolean;
  isArticle?: boolean;
  metadata?: {
    articleNumber?: number;
    feedName?: string;
    subreddit?: string;
    source?: string;
    /** 4chan固有: 掲示板名（例: "g", "sci"） */
    board?: string;
    /** 4chan固有: スレッド番号 */
    threadNumber?: string;
    /** 4chan固有: 返信数 */
    replyCount?: string;
    /** 4chan固有: 画像数 */
    imageCount?: string;
  };
}

export interface ContentResponse {
  items: ContentItem[];
}

export interface WeatherResponse {
  temperature: number;
  icon: string;
}

export interface ApiErrorResponse {
  message: string;
  status: number;
  statusText: string;
  url?: string;
  timestamp: string;
}

export interface ApiErrorContext {
  url: string;
  method: string;
  params?: Record<string, unknown>;
  headers?: Record<string, string>;
  timestamp: string;
}

export interface NetworkError extends Error {
  code?: string;
  isNetworkError: true;
  context: ApiErrorContext;
}

export interface ServerError extends Error {
  response: ApiErrorResponse;
  isServerError: true;
  context: ApiErrorContext;
}
