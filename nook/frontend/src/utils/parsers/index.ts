import { ContentItem } from '../../types';
import { parseGitHubTrendingMarkdown } from './githubParser';
import { parseTechNewsMarkdown } from './techNewsParser';
import { parseBusinessNewsMarkdown } from './businessNewsParser';
import { parseZennArticlesMarkdown } from './zennParser';
import { parseQiitaArticlesMarkdown } from './qiitaParser';
import { parseNoteArticlesMarkdown } from './noteParser';
import { parseRedditPostsMarkdown } from './redditParser';
import { parseAcademicPapersMarkdown } from './arxivParser';
import { parseFourchanThreadsMarkdown } from './fourchanParser';
import { parseFivechanThreadsMarkdown } from './fivechanParser';
import { parseHackerNewsData } from './hackerNewsParser';

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
  parseHackerNewsData
};

// パーサー選択ロジックを統一
export function getParserForSource(source: string) {
  const parsers: { [key: string]: (markdown: string) => ContentItem[] } = {
    'github': parseGitHubTrendingMarkdown,
    'tech-news': parseTechNewsMarkdown,
    'business-news': parseBusinessNewsMarkdown,
    'zenn': parseZennArticlesMarkdown,
    'qiita': parseQiitaArticlesMarkdown,
    'note': parseNoteArticlesMarkdown,
    'reddit': parseRedditPostsMarkdown,
    'arxiv': parseAcademicPapersMarkdown,
    '4chan': parseFourchanThreadsMarkdown,
    '5chan': parseFivechanThreadsMarkdown,
    'hacker-news': parseHackerNewsData,
  };
  
  return parsers[source] || null;
}