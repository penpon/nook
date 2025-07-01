import { ContentItem } from '../../types';

export function parseQiitaArticlesMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  
  // 最初に「Qiita」カテゴリヘッダーを追加
  contentItems.push({
    title: 'Qiita',
    content: '',
    source: 'qiita',
    isCategoryHeader: true
  });
  
  let articleNumber = 1;
  
  // 記事の解析
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 日付付きタイトル（# Qiita記事 (2025-06-24)）を無視
    if (line.startsWith('# Qiita記事')) {
      continue;
    }
    
    // 記事タイトル行を検出（### [タイトル](URL)）
    if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const titleMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (titleMatch) {
        const title = titleMatch[1];
        const url = titleMatch[2];
        
        // タグと要約を抽出
        let tags = '';
        let summary = '';
        
        // タグと要約を取得（次の行以降）
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          // 次のセクションまたは次の記事に到達したら終了
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.startsWith('**タグ**:')) {
            // タグ情報の行
            tags = nextLine.replace('**タグ**:', '').trim();
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
        
        // コンテンツの構築
        let content = '';
        if (tags) {
          content += `**タグ**: ${tags}\n\n`;
        }
        if (summary) {
          content += `**要約**:\n${summary}`;
        }
        
        contentItems.push({
          title: title,
          content: content,
          url: url,
          source: 'qiita',
          isArticle: true,
          metadata: {
            source: 'qiita',
            articleNumber: articleNumber++
          }
        });
      }
    }
  }
  
  return contentItems;
}