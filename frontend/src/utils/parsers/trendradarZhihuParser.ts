import type { ContentItem } from '../../types';

/**
 * TrendRadar(知乎)用のデータパーサー。
 * Hacker Newsと同様に構造化データを処理し、各記事を個別のカードとして表示。
 */
export function parseTrendradarZhihuData(items: ContentItem[]): ContentItem[] {
  if (!items || items.length === 0) {
    return [];
  }

  // カテゴリヘッダーを追加
  const processedItems: ContentItem[] = [
    {
      title: '知乎 (Zhihu)',
      url: '',
      content: '',
      source: 'trendradar-zhihu',
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
      // URLが/question/を含む場合、それは質問へのリンク
      // URLが/answer/を含む場合、回答へのリンクだが、基本は質問タイトルを表示したい
    }

    processedItems.push({
      ...item,
      title: title,
      url: url,
      isArticle: true,
      metadata: {
        ...item.metadata,
        articleNumber: articleNumber++,
        feedName: 'Zhihu',
      },
    });
  });

  return processedItems;
}
