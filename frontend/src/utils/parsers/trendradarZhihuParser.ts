import type { ContentItem } from '../../types';

const SOURCE = 'trendradar-zhihu';

/**
 * TrendRadar(知乎)用の緩やかなMarkdownパーサー。
 * 箇条書きや番号付きリストの `[title](url) - summary` 形式を主に想定しつつ、
 * 見出しレベルの区切りがあればカテゴリヘッダーとして扱う。
 */
export function parseTrendradarZhihuMarkdown(markdown: string): ContentItem[] {
  if (!markdown?.trim()) return [];

  const lines = markdown.split('\n');
  const items: ContentItem[] = [];
  let currentCategory: string | null = null;
  let articleNumber = 0;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    // 見出しをカテゴリとして扱う
    const headingMatch = /^(#{1,6})\s+(.*)$/.exec(line);
    if (headingMatch) {
      currentCategory = headingMatch[2].trim();
      items.push({
        title: currentCategory,
        content: '',
        source: SOURCE,
        isCategoryHeader: true,
      });
      continue;
    }

    // 箇条書き / 番号付きリストのリンク行
    // ReDoS脆弱性を避けるため、段階的にマッチング
    const listPrefixMatch = /^(?:[-*]|\d+\.)\s*(.+)$/.exec(line);
    if (listPrefixMatch) {
      const content = listPrefixMatch[1];
      const linkPattern = /^\[([^\]]+)\]\(([^)]*)\)(.*)$/;
      const linkMatch = linkPattern.exec(content);

      if (linkMatch) {
        const [, title, url, rest] = linkMatch;
        // サマリー部分の抽出（ダッシュ記号の後）
        const summaryMatch = /^\s*[-–—]\s*(.*)$/.exec(rest);
        const summary = summaryMatch ? summaryMatch[1] : '';

        articleNumber += 1;
        items.push({
          title: title.trim(),
          url: url.trim(),
          content: summary.trim(),
          source: SOURCE,
          isArticle: true,
          metadata: {
            articleNumber,
            feedName: 'Zhihu',
            source: currentCategory ?? undefined,
          },
        });
        continue;
      }
    }

    // その他の行は前項目の本文に追記（シンプルな結合）
    const last = items.at(-1);
    if (last && last.isArticle) {
      last.content = last.content ? `${last.content}\n${line}` : line;
    } else {
      // パース不能行は汎用記事として扱う
      console.warn('[trendradarZhihuParser] Unparseable line:', line);
      articleNumber += 1;
      items.push({
        title: line.slice(0, 80),
        content: line,
        source: SOURCE,
        isArticle: true,
        metadata: { articleNumber, feedName: 'Zhihu' },
      });
    }
  }

  return items;
}
