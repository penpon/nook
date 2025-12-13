import type { ContentItem } from '../../types';

export function parseRedditPostsMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  let currentSubreddit = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // サブレディット（## r/programming など）
    if (line.startsWith('## r/')) {
      currentSubreddit = line.substring(3).trim();
      // サブレディット名をカテゴリヘッダーとして追加
      contentItems.push({
        title: currentSubreddit,
        content: '',
        source: 'reddit',
        isCategoryHeader: true,
      });
    }
    // 投稿タイトル（### [タイトル](URL)）
    else if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const postTitle = linkMatch[1];
        const postUrl = linkMatch[2];

        // 投稿情報を取得
        let score = '';
        let content = '';
        let summary = '';
        let link = '';

        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();

          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }

          if (nextLine.startsWith('アップボート数:')) {
            score = nextLine.replace('アップボート数:', '').trim();
          } else if (nextLine.startsWith('本文:')) {
            // 本文の開始
            content = nextLine.replace('本文:', '').trim();

            // 本文の続きがある場合は次の行も読み込み
            for (let k = j + 1; k < lines.length; k++) {
              const contentLine = lines[k].trim();

              if (
                contentLine.startsWith('#') ||
                contentLine === '---' ||
                contentLine.startsWith('**') ||
                contentLine.startsWith('アップボート数:') ||
                contentLine.startsWith('リンク:')
              ) {
                break;
              }

              if (contentLine) {
                content += '\n\n' + contentLine;
              }
            }
          } else if (nextLine.startsWith('リンク:')) {
            link = nextLine.replace('リンク:', '').trim();
          } else if (nextLine.startsWith('**要約**:')) {
            // 要約セクションの開始
            summary = '';

            // 要約の内容を読み込み
            for (let k = j + 1; k < lines.length; k++) {
              const summaryLine = lines[k].trim();

              if (summaryLine.startsWith('#') || summaryLine === '---') {
                break;
              }

              if (summaryLine) {
                if (summary) {
                  summary += '\n\n' + summaryLine;
                } else {
                  summary = summaryLine;
                }
              }
            }
          }
        }

        // 投稿内容を構築（要約優先、本文はフォールバック）
        let postContent = '';
        if (score) postContent += `**アップボート数**: ${score}\n`;
        if (link) postContent += `**リンク**: ${link}\n`;

        // 要約がある場合は要約を優先、ない場合は本文を表示
        if (summary) {
          if (postContent) postContent += '\n';
          postContent += `**要約**:\n${summary}`;
        } else if (content) {
          if (postContent) postContent += '\n';
          postContent += `**本文**:\n${content}`;
        }

        // 各サブレディット内での記事番号
        const subredditItems = contentItems.filter(
          (item) => item.metadata?.subreddit === currentSubreddit && item.isArticle
        );
        const articleNumber = subredditItems.length + 1;

        contentItems.push({
          title: postTitle,
          content: postContent,
          url: postUrl,
          source: 'reddit',
          subreddit: currentSubreddit,
          isArticle: true,
          metadata: {
            source: 'reddit',
            subreddit: currentSubreddit,
            articleNumber: articleNumber,
          },
        });
      }
    }
  }

  return contentItems;
}
