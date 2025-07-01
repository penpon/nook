import { ContentItem } from '../../types';

export function parseBusinessNewsMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  const feedGroups = new Map<string, { title: string; url: string; content: string }[]>();
  
  // まず全ての記事を解析してフィード別にグループ化
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 日付付きタイトルは無視
    if (line.startsWith('# ビジネスニュース記事')) {
      continue;
    }
    
    // カテゴリセクション（## Business）は無視
    if (line.startsWith('## ') && line.length > 3) {
      continue;
    }
    
    // 記事を検出
    if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const articleTitle = linkMatch[1];
        const articleUrl = linkMatch[2];
        
        // フィード情報と要約を取得
        let feedName = '';
        let summary = '';
        
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.startsWith('**フィード**:')) {
            feedName = nextLine.replace('**フィード**:', '').trim();
          } else if (nextLine.startsWith('**要約**:')) {
            summary = nextLine.replace('**要約**:', '').trim();
            
            for (let k = j + 1; k < lines.length; k++) {
              const summaryLine = lines[k].trim();
              
              if (summaryLine.startsWith('#') || summaryLine === '---' || summaryLine.startsWith('**')) {
                break;
              }
              
              if (summaryLine) {
                summary += '\n\n' + summaryLine;
              }
            }
          }
        }
        
        // フィード名でグループ化
        if (feedName) {
          if (!feedGroups.has(feedName)) {
            feedGroups.set(feedName, []);
          }
          
          let content = '';
          if (summary) {
            content = `**要約**:\n${summary}`;
          }
          
          feedGroups.get(feedName)!.push({
            title: articleTitle,
            url: articleUrl,
            content: content
          });
        }
      }
    }
  }
  
  // フィードグループごとにコンテンツアイテムを作成
  for (const [feedName, articles] of feedGroups) {
    let articleNumber = 1; // フィードごとにリセット
    
    // フィード名をカテゴリヘッダーとして追加
    contentItems.push({
      title: feedName,
      content: '',
      source: 'business-news',
      isCategoryHeader: true
    });
    
    // 各記事を追加
    articles.forEach((article) => {
      contentItems.push({
        title: article.title,
        content: article.content,
        url: article.url,
        source: 'business-news',
        isArticle: true,
        metadata: {
          source: 'business-news',
          articleNumber: articleNumber++,
          feedName: feedName
        }
      });
    });
  }
  
  return contentItems;
}