export { parseGitHubTrendingMarkdown } from './githubParser';
export { parseTechNewsMarkdown } from './techNewsParser';
export { parseBusinessNewsMarkdown } from './businessNewsParser';
export { parseZennArticlesMarkdown } from './zennParser';
export { parseQiitaArticlesMarkdown } from './qiitaParser';
export { parseNoteArticlesMarkdown } from './noteParser';
export { parseRedditPostsMarkdown } from './redditParser';
export { parseAcademicPapersMarkdown } from './arxivParser';
export { parseFourchanThreadsMarkdown } from './fourchanParser';
export { parseFivechanThreadsMarkdown } from './fivechanParser';
export { parseHackerNewsData } from './hackerNewsParser';

// パーサー選択ロジックを統一
export function getParserForSource(source: string) {
  const parsers: { [key: string]: any } = {
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