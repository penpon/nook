import { ContentItem } from '../../types';

// Zennのフィード情報から適切なフィード名を抽出
function extractZennFeedName(feedInfo: string): string {
  // "Frontend Weekly", "weekly-js", etc. の形式から名前を抽出
  if (feedInfo.includes('(') && feedInfo.includes(')')) {
    // カッコ内の情報を削除してフィード名を取得
    return feedInfo.split('(')[0].trim();
  }
  
  // カッコがない場合はそのまま返す
  return feedInfo || '未分類';
}

export function parseZennArticlesMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  const feedGroups = new Map<string, { title: string; url: string; content: string; feedInfo: string }[]>();
  
  // 記事の解析とフィード別グループ化
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 日付付きタイトル（# Zenn記事 (2025-06-24)）を無視
    if (line.startsWith('# Zenn記事')) {
      continue;
    }
    
    // 記事タイトル行を検出（### [タイトル](URL)）
    if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const titleMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (titleMatch) {
        const title = titleMatch[1];
        const url = titleMatch[2];
        
        // フィード情報を抽出
        let feedInfo = '';
        let summary = '';
        
        // フィード情報と要約を取得（次の行以降）
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          // 次のセクションまたは次の記事に到達したら終了
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.startsWith('**フィード**:')) {
            // フィード情報の行
            feedInfo = nextLine.replace('**フィード**:', '').trim();
          } else if (nextLine.startsWith('**要約**:')) {
            // 要約情報の開始
            summary = nextLine.replace('**要約**:', '').trim();
            
            // 要約の続きがある場合は次の行も読み込み
            for (let k = j + 1; k < lines.length; k++) {
              const summaryLine = lines[k].trim();
              
              // 次のセクション、記事、または区切り線に到達したら終了
              if (summaryLine.startsWith('#') || summaryLine === '---' || summaryLine.startsWith('**')) {
                break;
              }
              
              if (summaryLine) {
                summary += '\n\n' + summaryLine;
              }
            }
          }
        }
        
        const feedName = extractZennFeedName(feedInfo);
        
        // フィード名でグループ化
        if (!feedGroups.has(feedName)) {
          feedGroups.set(feedName, []);
        }
        
        feedGroups.get(feedName)!.push({
          title,
          url,
          content: summary,
          feedInfo
        });
      }
    }
  }
  
  // フィード名をカテゴリヘッダーとして生成
  for (const [feedName, articles] of feedGroups) {
    // フィード名をそのままカテゴリヘッダーに
    contentItems.push({
      title: feedName,
      content: '',
      source: 'zenn',
      isCategoryHeader: true
    });
    
    // 各記事を番号付きで追加
    let articleNumber = 1;
    articles.forEach((article) => {
      let content = '';
      if (article.content) {
        content = `**要約**:\n${article.content}`;
      }
      
      contentItems.push({
        title: article.title,
        content: content,
        url: article.url,
        source: 'zenn',
        isArticle: true,
        metadata: {
          source: 'zenn',
          feedName: feedName,
          articleNumber: articleNumber++
        }
      });
    });
  }
  
  return contentItems;
}