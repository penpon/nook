import type { ContentItem } from "../../types";
import { parseAcademicPapersMarkdown } from "./arxivParser";
import { parseBusinessNewsMarkdown } from "./businessNewsParser";
import { parseFivechanThreadsMarkdown } from "./fivechanParser";
import { parseFourchanThreadsMarkdown } from "./fourchanParser";
import { parseGitHubTrendingMarkdown } from "./githubParser";
import { parseHackerNewsData } from "./hackerNewsParser";
import { parseNoteArticlesMarkdown } from "./noteParser";
import { parseQiitaArticlesMarkdown } from "./qiitaParser";
import { parseRedditPostsMarkdown } from "./redditParser";
import { parseTechNewsMarkdown } from "./techNewsParser";
import { parseZennArticlesMarkdown } from "./zennParser";

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
};

// パーサー選択ロジックを統一
export function getParserForSource(source: string) {
	const parsers: { [key: string]: (markdown: string) => ContentItem[] } = {
		github: parseGitHubTrendingMarkdown,
		"tech-news": parseTechNewsMarkdown,
		"business-news": parseBusinessNewsMarkdown,
		zenn: parseZennArticlesMarkdown,
		qiita: parseQiitaArticlesMarkdown,
		note: parseNoteArticlesMarkdown,
		reddit: parseRedditPostsMarkdown,
		arxiv: parseAcademicPapersMarkdown,
		"4chan": parseFourchanThreadsMarkdown,
		"5chan": parseFivechanThreadsMarkdown,
		"hacker-news": parseHackerNewsData,
	};

	return parsers[source] || null;
}
