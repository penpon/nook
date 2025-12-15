import { describe, it, expect } from 'vitest';
import { parseTrendradarJuejinData } from './trendradarJuejinParser';
import type { ContentItem } from '../../types';

describe('parseTrendradarJuejinData', () => {
  it('should add Juejin header and extract title/url from markdown link title', () => {
    const input: ContentItem[] = [
      {
        title: '[Title Here](https://juejin.cn/post/12345)',
        content: '',
        source: 'trendradar-juejin',
        url: '',
      },
    ];

    const result = parseTrendradarJuejinData(input);

    expect(result).toHaveLength(2);
    expect(result[0].isCategoryHeader).toBe(true);
    expect(result[0].title).toBe('掘金 (Juejin)');
    expect(result[0].source).toBe('trendradar-juejin');

    expect(result[1].title).toBe('Title Here');
    expect(result[1].url).toBe('https://juejin.cn/post/12345');
    expect(result[1].isArticle).toBe(true);
    expect(result[1].metadata?.articleNumber).toBe(1);
    expect(result[1].metadata?.feedName).toBe('Juejin');
  });

  it('should handle normal titles and preserve url', () => {
    const input: ContentItem[] = [
      {
        title: 'Normal Title',
        content: 'Some content',
        source: 'trendradar-juejin',
        url: 'https://existing.url',
      },
    ];

    const result = parseTrendradarJuejinData(input);

    expect(result).toHaveLength(2);
    expect(result[1].title).toBe('Normal Title');
    expect(result[1].url).toBe('https://existing.url');
    expect(result[1].metadata?.articleNumber).toBe(1);
  });
});
