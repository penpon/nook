import type { ContentItem } from '../../types';
import { parseAcademicPapersMarkdown } from './arxivParser';
import { parseBusinessNewsMarkdown } from './businessNewsParser';
import { parseFivechanThreadsMarkdown } from './fivechanParser';
import { parseFourchanThreadsMarkdown } from './fourchanParser';
import { parseGitHubTrendingMarkdown } from './githubParser';
import { parseHackerNewsData } from './hackerNewsParser';
import { parseNoteArticlesMarkdown } from './noteParser';
import { parseQiitaArticlesMarkdown } from './qiitaParser';
import { parseRedditPostsMarkdown } from './redditParser';
import { parseTechNewsMarkdown } from './techNewsParser';
import { parseZennArticlesMarkdown } from './zennParser';
import { parseTrendradarZhihuData } from './trendradarZhihuParser';

export {
  parseGitHubTrendingMarkdown,
  parseTechNewsMarkdown,
  parseBusinessNewsMarkdown,
  parseZennArticlesMarkdown,
  parseQiitaArticlesMarkdown,
  parseNoteArticlesMarkdown,
  parseRedditPostsMarkdown,
  parseAcademicPapersMarkdown,
  parseFourchanThreadsMarkdown,
  parseFivechanThreadsMarkdown,
  parseHackerNewsData,
  parseTrendradarZhihuData,
};

// パーサー選択ロジックを統一
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function getParserForSource(source: string): ((input: any) => ContentItem[]) | null {
  const parsers: Record<string, (input: any) => ContentItem[]> = {
    github: parseGitHubTrendingMarkdown,
    'tech-news': parseTechNewsMarkdown,
    'business-news': parseBusinessNewsMarkdown,
    zenn: parseZennArticlesMarkdown,
    qiita: parseQiitaArticlesMarkdown,
    note: parseNoteArticlesMarkdown,
    reddit: parseRedditPostsMarkdown,
    arxiv: parseAcademicPapersMarkdown,
    '4chan': parseFourchanThreadsMarkdown,
    '5chan': parseFivechanThreadsMarkdown,
    'hacker-news': parseHackerNewsData,
    'trendradar-zhihu': parseTrendradarZhihuData,
  };

  return parsers[source] || null;
}
