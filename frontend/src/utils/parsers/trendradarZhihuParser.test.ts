import { describe, it, expect } from 'vitest';
import { parseTrendradarZhihuData } from './trendradarZhihuParser';
import type { ContentItem } from '../../types';

describe('parseTrendradarZhihuData', () => {
    it('should extract title and url from markdown link content', () => {
        const input: ContentItem[] = [
            {
                title: '[Title Here](https://www.zhihu.com/question/12345)',
                content: '',
                source: 'trendradar-zhihu',
                url: '', // input url might be empty or wrong
            },
        ];

        const result = parseTrendradarZhihuData(input);

        // First item is header, second is content
        expect(result).toHaveLength(2);
        expect(result[1].title).toBe('Title Here');
        expect(result[1].url).toBe('https://www.zhihu.com/question/12345');
        expect(result[1].isArticle).toBe(true);
        expect(result[1].metadata?.articleNumber).toBe(1);
    });

    it('should handle normal titles properly', () => {
        const input: ContentItem[] = [
            {
                title: 'Normal Title',
                content: 'Some content',
                source: 'trendradar-zhihu',
                url: 'https://existing.url',
            },
        ];

        const result = parseTrendradarZhihuData(input);

        expect(result).toHaveLength(2);
        expect(result[1].title).toBe('Normal Title');
        expect(result[1].url).toBe('https://existing.url');
    });
});
