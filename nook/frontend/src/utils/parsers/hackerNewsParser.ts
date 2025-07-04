import type { ContentItem } from "../../types";

export function parseHackerNewsData(items: ContentItem[]): ContentItem[] {
	// Hacker Newsの場合は構造化データをそのまま処理
	if (!items || items.length === 0) {
		return [];
	}

	// カテゴリヘッダーを追加
	const processedItems: ContentItem[] = [
		{
			title: "Hacker News",
			url: "",
			content: "",
			source: "hacker-news",
			isLanguageHeader: false,
			isCategoryHeader: true,
			isArticle: false,
		},
	];

	// 記事番号を追加
	let articleNumber = 1;
	items.forEach((item) => {
		processedItems.push({
			...item,
			isArticle: true,
			metadata: {
				...item.metadata,
				articleNumber: articleNumber++,
			},
		});
	});

	return processedItems;
}
