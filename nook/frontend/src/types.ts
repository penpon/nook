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
}

export interface ContentResponse {
  items: ContentItem[];
}

export interface WeatherResponse {
  temperature: number;
  icon: string;
}