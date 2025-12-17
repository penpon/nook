import type { ContentItem } from '../../types';

/**
 * TrendRadar(IT之家)用のデータパーサー。
 * 構造化データを処理し、各記事を個別のカードとして表示。
 */
export function parseTrendradarIthomeData(items: ContentItem[]): ContentItem[] {
  if (!items || items.length === 0) {
    return [];
  }

  // カテゴリヘッダーを追加
  const processedItems: ContentItem[] = [
    {
      title: 'IT之家 (ITHome)',
      url: '',
      content: '',
      source: 'trendradar-ithome',
      isLanguageHeader: false,
      isCategoryHeader: true,
      isArticle: false,
    },
  ];

  // 記事番号を追加
  let articleNumber = 1;
  items.forEach((item) => {
    let title = item.title;
    let url = item.url;

    // タイトルがMarkdownリンク形式の場合の処理 [Title](URL)
    const markdownLinkMatch = title.match(/^\[(.*?)\]\((.*?)\)$/);
    if (markdownLinkMatch) {
      title = markdownLinkMatch[1];
      url = markdownLinkMatch[2];
    }

    processedItems.push({
      ...item,
      title: title,
      url: url,
      isArticle: true,
      metadata: {
        ...item.metadata,
        articleNumber: articleNumber++,
        feedName: 'ITHome',
      },
    });
  });

  return processedItems;
}
