import { ContentItem } from '../../types';

export function parseFivechanThreadsMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  let currentCategory = '';
  let articleNumber = 0;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // カテゴリ（## プログラム技術 など）
    if (line.startsWith('## ') && !line.includes('[')) {
      currentCategory = line.substring(3).trim();
      articleNumber = 0; // カテゴリごとにリセット
      
      // カテゴリヘッダーを追加
      contentItems.push({
        title: currentCategory,
        content: '',
        source: '5chan',
        isCategoryHeader: true
      });
    }
    // スレッドタイトル（### [タイトル](URL)）
    else if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const threadTitle = linkMatch[1];
        const threadUrl = linkMatch[2];
        
        // スレッド情報を取得
        let threadNumber = '';
        let replyCount = '';
        let createdAt = '';
        let summary = '';
        
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.startsWith('**スレッド番号**:')) {
            threadNumber = nextLine.replace('**スレッド番号**:', '').trim();
          } else if (nextLine.startsWith('**レス数**:')) {
            replyCount = nextLine.replace('**レス数**:', '').trim();
          } else if (nextLine.startsWith('**作成日時**:')) {
            createdAt = nextLine.replace('**作成日時**:', '').trim();
          } else if (nextLine.startsWith('**要約**:')) {
            summary = nextLine.replace('**要約**:', '').trim();
            
            // 要約の続きがある場合は次の行も読み込み
            for (let k = j + 1; k < lines.length; k++) {
              const summaryLine = lines[k].trim();
              
              if (summaryLine.startsWith('#') || summaryLine === '---' || summaryLine.startsWith('**')) {
                break;
              }
              
              if (summaryLine) {
                summary += '\n' + summaryLine;
              }
            }
          }
        }
        
        // スレッド内容を構築
        let content = '';
        if (threadNumber) {
          content += `**スレッド番号**: ${threadNumber}\n\n`;
        }
        if (replyCount) {
          content += `**レス数**: ${replyCount}\n\n`;
        }
        if (createdAt) {
          content += `**作成日時**: ${createdAt}\n\n`;
        }
        if (summary) {
          content += `**要約**:\n${summary}`;
        }
        
        articleNumber++;
        
        contentItems.push({
          title: threadTitle,
          content: content,
          url: threadUrl,
          source: '5chan',
          category: currentCategory,
          board: currentCategory,
          threadNumber: threadNumber,
          replyCount: replyCount,
          isArticle: true,
          metadata: {
            source: '5chan',
            articleNumber: articleNumber
          }
        });
      }
    }
  }
  
  return contentItems;
}