import React, { useState, useEffect, useMemo } from 'react';
import { useQuery } from 'react-query';
import { format, subDays } from 'date-fns';
import { Layout, Menu, Calendar, Sun, Moon } from 'lucide-react';
import { ContentCard } from './components/ContentCard';
import { NewsHeader } from './components/NewsHeader';
import { WeatherWidget } from './components/WeatherWidget';
import UsageDashboard from './components/UsageDashboard';
import { getContent } from './api';
import { sourceDisplayInfo, defaultSourceDisplayInfo } from './config/sourceDisplayInfo';
import { ContentItem } from './types';

const sources = ['arxiv', 'github', 'hacker-news', 'tech-news', 'business-news', 'zenn', 'qiita', 'note', 'reddit', '4chan', '5chan'];

// GitHub TrendingのMarkdownをパースして個別のコンテンツアイテムに変換
function parseGitHubTrendingMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  let currentLanguage = '';
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 言語セクション（## Python, ## Go, ## Rust）を検出
    if (line.startsWith('## ') && line.length > 3) {
      currentLanguage = line.substring(3).trim();
      contentItems.push({
        title: currentLanguage,
        content: '',
        source: 'github',
        isLanguageHeader: true
      });
    }
    // リポジトリ（### [owner/repo](url)）を検出
    else if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const repoName = linkMatch[1];
        const repoUrl = linkMatch[2];
        
        // 次の行から説明とスター数を取得
        let description = '';
        let stars = '';
        
        // 説明を取得（次の行以降）
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          // 次のセクションまたは次のリポジトリに到達したら終了
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.includes('⭐')) {
            // スター数の行
            const starMatch = nextLine.match(/⭐\s*スター数:\s*([0-9,]+)/);
            if (starMatch) {
              stars = starMatch[1];
            }
          } else if (nextLine && !nextLine.startsWith('###')) {
            // 説明の行（空行でない場合のみ）
            if (description && nextLine) {
              description += '\n\n';
            }
            description += nextLine;
          }
        }
        
        contentItems.push({
          title: repoName,
          content: description + (stars ? `\n\n⭐ ${stars}` : ''),
          url: repoUrl,
          source: 'github',
          language: currentLanguage,
          isRepository: true
        });
      }
    }
  }
  
  return contentItems;
}

// Tech NewsのMarkdownをパースして個別のコンテンツアイテムに変換
function parseTechNewsMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  const feedGroups = new Map<string, { title: string; url: string; content: string }[]>();
  
  // まず全ての記事を解析してフィード別にグループ化
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 日付付きタイトルは無視
    if (line.startsWith('# 技術ニュース記事')) {
      continue;
    }
    
    // カテゴリセクション（## Tech_blogs, ## Hatena等）は無視
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
      source: 'tech-news',
      isCategoryHeader: true
    });
    
    // 各記事を追加
    articles.forEach((article) => {
      contentItems.push({
        title: article.title,
        content: article.content,
        url: article.url,
        source: 'tech-news',
        isArticle: true,
        metadata: {
          source: 'tech-news',
          articleNumber: articleNumber++,
          feedName: feedName
        }
      });
    });
  }
  
  return contentItems;
}

// Business NewsのMarkdownをパースして個別のコンテンツアイテムに変換
function parseBusinessNewsMarkdown(markdown: string): ContentItem[] {
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

// Zenn ArticlesのMarkdownをパースして個別のコンテンツアイテムに変換
function parseZennArticlesMarkdown(markdown: string): ContentItem[] {
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
      isLanguageHeader: false,
      isCategoryHeader: true,
      isArticle: false
    });
    
    // 記事を追加（カテゴリごとに番号をリセット）
    let articleNumber = 1;
    for (const article of articles) {
      // 記事内容を構築
      let content = '';
      // フィード情報は表示しない
      // if (article.feedInfo) {
      //   content += `**フィード**: ${article.feedInfo}\n\n`;
      // }
      if (article.content) {
        content += `**要約**:\n${article.content}`;
      }
      
      contentItems.push({
        title: article.title,
        url: article.url,
        content: content,
        isLanguageHeader: false,
        isCategoryHeader: false,
        isArticle: true,
        metadata: {
          source: 'zenn',
          feed: feedName,
          articleNumber: articleNumber++
        }
      });
    }
  }
  
  return contentItems;
}

// Zennフィード名を抽出
function extractZennFeedName(feedInfo: string): string {
  // 例: 'Zennの「Claude Code」のフィード' → 'Claude Code'
  const match = feedInfo.match(/Zennの「(.+?)」のフィード/);
  if (match) {
    return match[1];
  }
  
  // マッチしない場合はフィード情報全体を返す
  return feedInfo;
}

// Qiita ArticlesのMarkdownをパースして個別のコンテンツアイテムに変換
function parseQiitaArticlesMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  const tagGroups = new Map<string, { title: string; url: string; content: string; feedInfo: string }[]>();
  
  // 記事の解析とタグ別グループ化
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
        
        const tagName = extractQiitaTagName(feedInfo);
        
        // タグ名でグループ化
        if (!tagGroups.has(tagName)) {
          tagGroups.set(tagName, []);
        }
        
        tagGroups.get(tagName)!.push({
          title,
          url,
          content: summary,
          feedInfo
        });
      }
    }
  }
  
  // タグ名をカテゴリヘッダーとして生成
  for (const [tagName, articles] of tagGroups) {
    // タグ名をそのままカテゴリヘッダーに
    contentItems.push({
      title: tagName,
      content: '',
      source: 'qiita',
      isLanguageHeader: false,
      isCategoryHeader: true,
      isArticle: false
    });
    
    // 記事を追加（カテゴリごとに番号をリセット）
    let articleNumber = 1;
    for (const article of articles) {
      // 記事内容を構築
      let content = '';
      // フィード情報は表示しない
      // if (article.feedInfo) {
      //   content += `**フィード**: ${article.feedInfo}\n\n`;
      // }
      if (article.content) {
        content += `**要約**:\n${article.content}`;
      }
      
      contentItems.push({
        title: article.title,
        url: article.url,
        content: content,
        isLanguageHeader: false,
        isCategoryHeader: false,
        isArticle: true,
        metadata: {
          source: 'qiita',
          feed: tagName,
          articleNumber: articleNumber++
        }
      });
    }
  }
  
  return contentItems;
}

// Qiitaタグ名を抽出
function extractQiitaTagName(feedInfo: string): string {
  // 例: 'ChatGPTタグが付けられた新着記事 - Qiita' → 'ChatGPT'
  const tagMatch = feedInfo.match(/^(.+?)タグが付けられた/);
  if (tagMatch) {
    return tagMatch[1];
  }
  
  // 人気記事の場合
  if (feedInfo.includes('Qiita - 人気の記事')) {
    return '人気の記事';
  }
  
  // マッチしない場合はフィード情報から推測
  return feedInfo.replace(' - Qiita', '').trim();
}

// noteハッシュタグを抽出
function extractNoteHashtag(feedInfo: string): string {
  // 例: '#ClaudeCodeタグ' → '#ClaudeCode'
  const hashtagMatch = feedInfo.match(/^(#.+?)タグ$/);
  if (hashtagMatch) {
    return hashtagMatch[1];
  }
  
  // マッチしない場合はフィード情報全体を返す
  return feedInfo;
}

// note ArticlesのMarkdownをパースして個別のコンテンツアイテムに変換
function parseNoteArticlesMarkdown(markdown: string): ContentItem[] {
  const items: ContentItem[] = [];
  const lines = markdown.split('\n');
  const hashtagGroups = new Map<string, { title: string; url: string; content: string; feedInfo: string }[]>();
  
  // 記事の解析とハッシュタグ別グループ化
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 記事タイトル行を検出（### [タイトル](URL)）
    const titleMatch = line.match(/^###\s*\[([^\]]+)\]\(([^)]+)\)$/);
    if (titleMatch) {
      const title = titleMatch[1];
      const url = titleMatch[2];
      
      // フィード情報と要約を取得
      let feedInfo = '';
      let summary = '';
      
      for (let j = i + 1; j < lines.length; j++) {
        const nextLine = lines[j].trim();
        
        // 次のセクションまたは次の記事に到達したら終了
        if (nextLine.startsWith('#') || nextLine === '---') {
          break;
        }
        
        if (nextLine.startsWith('**フィード**:')) {
          feedInfo = nextLine.replace('**フィード**:', '').trim();
        } else if (nextLine.startsWith('**要約**:')) {
          summary = nextLine.replace('**要約**:', '').trim();
          
          // 要約の続きがある場合は次の行も読み込み
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
      
      // ハッシュタグを抽出
      const hashtag = extractNoteHashtag(feedInfo);
      
      // ハッシュタグでグループ化
      if (!hashtagGroups.has(hashtag)) {
        hashtagGroups.set(hashtag, []);
      }
      
      // 記事内容を構築
      let content = '';
      // フィード情報は表示しない
      // if (feedInfo) {
      //   content += `**フィード**: ${feedInfo}\n\n`;
      // }
      if (summary) {
        content += `**要約**:\n${summary}`;
      }
      
      hashtagGroups.get(hashtag)!.push({
        title,
        url,
        content,
        feedInfo
      });
    }
  }
  
  // ハッシュタグをカテゴリヘッダーとして生成
  for (const [hashtag, articles] of hashtagGroups) {
    // ハッシュタグをそのままカテゴリヘッダーに
    items.push({
      title: hashtag,
      url: '',
      content: '',
      isLanguageHeader: false,
      isCategoryHeader: true,
      isArticle: false
    });
    
    // 記事を追加（カテゴリごとに番号をリセット）
    let articleNumber = 1;
    for (const article of articles) {
      items.push({
        title: article.title,
        url: article.url,
        content: article.content,
        isLanguageHeader: false,
        isCategoryHeader: false,
        isArticle: true,
        metadata: {
          source: 'note',
          feed: hashtag,
          articleNumber: articleNumber++
        }
      });
    }
  }
  
  return items;
}

// Academic PapersのMarkdownをパースして個別のコンテンツアイテムに変換
function parseAcademicPapersMarkdown(markdown: string): ContentItem[] {
  const items: ContentItem[] = [];
  const lines = markdown.split('\n');
  
  // 最初に「ArXiv」カテゴリヘッダーを追加
  items.push({
    title: 'ArXiv',
    url: '',
    content: '',
    isLanguageHeader: false,
    isCategoryHeader: true,
    isArticle: false
  });
  
  let articleNumber = 1;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 論文タイトル行を検出（## [タイトル](URL)）
    const titleMatch = line.match(/^##\s*\[([^\]]+)\]\(([^)]+)\)$/);
    if (titleMatch) {
      const title = titleMatch[1];
      const url = titleMatch[2];
      
      // 要約を次の行から取得
      let content = '';
      let collectingContent = false;
      let abstractContent = '';
      let summaryContent = '';
      let currentSection = '';
      
      for (let j = i + 1; j < lines.length; j++) {
        const nextLine = lines[j].trim();
        
        // 次の論文タイトルに到達したら終了
        if (nextLine.startsWith('## [') && nextLine.includes('](')) {
          // 最初の論文タイトル以外で終了
          if (j > i + 1) break;
        }
        
        // セクション区切り線
        if (nextLine === '---') {
          break;
        }
        
        // abstract セクション
        if (nextLine.includes('**abstract**:')) {
          currentSection = 'abstract';
          collectingContent = true;
          continue;
        }
        
        // summary セクション
        if (nextLine.includes('**summary**:')) {
          currentSection = 'summary';
          collectingContent = true;
          continue;
        }
        
        // コンテンツを収集
        if (collectingContent && nextLine) {
          if (currentSection === 'abstract') {
            if (abstractContent) abstractContent += '\n\n';
            abstractContent += nextLine;
          } else if (currentSection === 'summary') {
            if (summaryContent) summaryContent += '\n\n';
            summaryContent += nextLine;
          }
        }
      }
      
      // abstract と summary を結合
      if (abstractContent) {
        content = `**abstract**:\n\n${abstractContent}`;
      }
      if (summaryContent) {
        if (content) content += '\n\n';
        content += `**summary**:\n\n${summaryContent}`;
      }
      
      items.push({
        title: title,
        url: url,
        content: content,
        isLanguageHeader: false,
        isCategoryHeader: false,
        isArticle: true,
        metadata: {
          source: 'arxiv',
          articleNumber: articleNumber++
        }
      });
    }
  }
  
  return items;
}


// Reddit PostsのMarkdownをパースして個別のコンテンツアイテムに変換
function parseRedditPostsMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  let currentSubreddit = '';
  let articleNumber = 1;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 日付付きタイトル（# Reddit 人気投稿 (2025-06-24)）を無視
    if (line.startsWith('# Reddit 人気投稿')) {
      continue;
    }
    
    // サブレディットを直接カテゴリヘッダーとして検出（## r/xxx）
    if (line.startsWith('## r/')) {
      currentSubreddit = line.substring(5).trim(); // "## r/" を除去
      articleNumber = 1; // カテゴリごとに番号をリセット
      
      contentItems.push({
        title: currentSubreddit,
        content: '',
        source: 'reddit',
        isCategoryHeader: true,
        isLanguageHeader: false,
        isArticle: false,
        metadata: {
          source: 'reddit',
          subreddit: currentSubreddit
        }
      });
    }
    // 投稿タイトル行を検出（### [タイトル](URL)）
    else if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const titleMatch = line.match(/^###\s*\[([^\]]+)\]\(([^)]+)\)$/);
      if (titleMatch && currentSubreddit) {
        const title = titleMatch[1];
        const url = titleMatch[2];
        
        // 次の行からリンク、本文、アップボート数、要約を取得
        let linkInfo = '';
        let bodyText = '';
        let score = '';
        let summary = '';
        
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          // 次のセクション、サブレディット、または投稿に到達したら終了
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.startsWith('リンク:')) {
            linkInfo = nextLine.replace('リンク:', '').trim();
          } else if (nextLine.startsWith('本文:')) {
            bodyText = nextLine.replace('本文:', '').trim();
          } else if (nextLine.startsWith('アップボート数:')) {
            score = nextLine.replace('アップボート数:', '').trim();
          } else if (nextLine.startsWith('**要約**:')) {
            // 要約情報の開始
            summary = nextLine.replace('**要約**:', '').trim();
            
            // 要約の続きがある場合は次の行も読み込み
            for (let k = j + 1; k < lines.length; k++) {
              const summaryLine = lines[k].trim();
              
              // 次のセクション、投稿、または区切り線に到達したら終了
              if (summaryLine.startsWith('#') || summaryLine === '---' || summaryLine.startsWith('**')) {
                break;
              }
              
              if (summaryLine) {
                summary += '\n\n' + summaryLine;
              }
            }
          }
        }
        
        // 投稿内容を構築
        let content = '';
        if (linkInfo) {
          content += `**リンク**: ${linkInfo}\n\n`;
        }
        if (bodyText) {
          content += `**本文**: ${bodyText}\n\n`;
        }
        if (score) {
          content += `**アップボート数**: ${score}\n\n`;
        }
        if (summary) {
          content += `**要約**:\n${summary}`;
        }
        
        contentItems.push({
          title,
          url,
          content: content,
          isLanguageHeader: false,
          isCategoryHeader: false,
          isArticle: true,
          metadata: {
            source: 'reddit',
            subreddit: currentSubreddit,
            score: score,
            articleNumber: articleNumber++
          }
        });
      }
    }
  }
  
  return contentItems;
}

// 4chan ThreadsのMarkdownをパースして個別のコンテンツアイテムに変換
function parseFourchanThreadsMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  let currentCategory = '';
  let articleNumber = 1;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 日付付きタイトル（# 4chan AI関連スレッド (2025-06-24)）を無視
    if (line.startsWith('# 4chan AI関連スレッド')) {
      continue;
    }
    
    // カテゴリセクション（## /g/等）を検出
    if (line.startsWith('## /') && line.includes('/')) {
      currentCategory = line.substring(3).trim();
      
      articleNumber = 1; // カテゴリごとに番号をリセット
      
      contentItems.push({
        title: currentCategory,
        content: '',
        source: '4chan',
        isCategoryHeader: true
      });
    }
    // スレッド（### [スレッドタイトル](URL)）を検出
    else if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const threadTitle = linkMatch[1];
        const threadUrl = linkMatch[2];
        
        // 次の行から作成日時と要約を取得
        let createdAt = '';
        let summary = '';
        
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          // 次のセクションまたは次のスレッドに到達したら終了
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.startsWith('作成日時:')) {
            // 作成日時情報の行（Discordタイムスタンプ <t:timestamp:F> の場合）
            createdAt = nextLine.replace('作成日時:', '').trim();
          } else if (nextLine.startsWith('**要約**:')) {
            // 要約情報の開始
            summary = nextLine.replace('**要約**:', '').trim();
            
            // 要約の続きがある場合は次の行も読み込み
            for (let k = j + 1; k < lines.length; k++) {
              const summaryLine = lines[k].trim();
              
              // 次のセクション、スレッド、または区切り線に到達したら終了
              if (summaryLine.startsWith('#') || summaryLine === '---' || summaryLine.startsWith('**')) {
                break;
              }
              
              if (summaryLine) {
                summary += '\n\n' + summaryLine;
              }
            }
          }
        }
        
        // スレッド内容を構築
        let content = '';
        if (createdAt) {
          content += `**作成日時**: ${createdAt}\n\n`;
        }
        if (summary) {
          content += `**要約**:\n${summary}`;
        }
        
        contentItems.push({
          title: threadTitle,
          content: content,
          url: threadUrl,
          source: '4chan',
          category: currentCategory,
          board: currentCategory,
          isArticle: true,
          metadata: {
            source: '4chan',
            articleNumber: articleNumber++
          }
        });
      }
    }
  }
  
  return contentItems;
}

// 5ch ThreadsのMarkdownをパースして個別のコンテンツアイテムに変換
function parseFivechanThreadsMarkdown(markdown: string): ContentItem[] {
  const lines = markdown.split('\n');
  const contentItems: ContentItem[] = [];
  let currentCategory = '';
  let articleNumber = 1;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 日付付きタイトル（# 5chan AI関連スレッド (2025-06-24)）を無視
    if (line.startsWith('# 5chan AI関連スレッド')) {
      continue;
    }
    
    // カテゴリセクション（## 板名 (/板名/)）を検出
    if (line.startsWith('## ') && line.includes('(/') && line.includes('/)')) {
      currentCategory = line.substring(3).trim();
      
      articleNumber = 1; // カテゴリごとに番号をリセット
      
      contentItems.push({
        title: currentCategory,
        content: '',
        source: '5chan',
        isCategoryHeader: true
      });
    }
    // スレッド（### [番号: スレッドタイトル (レス数)](URL)）を検出
    else if (line.startsWith('### ') && line.includes('[') && line.includes('](')) {
      const linkMatch = line.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const threadInfo = linkMatch[1];
        const threadUrl = linkMatch[2];
        
        // スレッド情報をパース（番号: タイトル (レス数)）
        const threadInfoMatch = threadInfo.match(/^(\d+):\s*(.+?)\s*\((\d+)\)$/);
        let threadNumber = '';
        let threadTitle = threadInfo; // フォールバック
        let replyCount = '';
        
        if (threadInfoMatch) {
          threadNumber = threadInfoMatch[1];
          threadTitle = threadInfoMatch[2];
          replyCount = threadInfoMatch[3];
        }
        
        // 次の行から作成日時と要約を取得
        let createdAt = '';
        let summary = '';
        
        for (let j = i + 1; j < lines.length; j++) {
          const nextLine = lines[j].trim();
          
          // 次のセクションまたは次のスレッドに到達したら終了
          if (nextLine.startsWith('#') || nextLine === '---') {
            break;
          }
          
          if (nextLine.startsWith('作成日時:')) {
            // 作成日時情報の行
            createdAt = nextLine.replace('作成日時:', '').trim();
          } else if (nextLine.startsWith('**要約**:')) {
            // 要約情報の開始
            summary = nextLine.replace('**要約**:', '').trim();
            
            // 要約の続きがある場合は次の行も読み込み
            for (let k = j + 1; k < lines.length; k++) {
              const summaryLine = lines[k].trim();
              
              // 次のセクション、スレッド、または区切り線に到達したら終了
              if (summaryLine.startsWith('#') || summaryLine === '---' || summaryLine.startsWith('**')) {
                break;
              }
              
              if (summaryLine) {
                summary += '\n\n' + summaryLine;
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
            articleNumber: articleNumber++
          }
        });
      }
    }
  }
  
  return contentItems;
}

function App() {
  // URLパラメータから初期ソースを取得
  const getInitialSource = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const sourceParam = urlParams.get('source');
    
    // パラメータが存在し、有効なソースの場合はそれを返す
    if (sourceParam && sources.includes(sourceParam)) {
      return sourceParam;
    }
    
    // デフォルトはhacker-news
    return 'hacker-news';
  };

  const [selectedSource, setSelectedSource] = useState(getInitialSource());
  const [currentPage, setCurrentPage] = useState('content'); // 'content' or 'usage-dashboard'
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    // ローカルストレージから初期値を取得、なければシステム設定を使用
    const savedTheme = localStorage.getItem('theme');
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  
  // テーマの変更を監視して適用
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  // ソース変更時にURLを更新
  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('source', selectedSource);
    window.history.replaceState({}, '', url.toString());
  }, [selectedSource]);
  
  const { data, isLoading, isError, error, refetch } = useQuery(
    ['content', selectedSource, format(selectedDate, 'yyyy-MM-dd')],
    () => getContent(selectedSource, format(selectedDate, 'yyyy-MM-dd')),
    {
      retry: 2,
      enabled: currentPage === 'content', // Only fetch data when on content page
    }
  );

  // GitHub TrendingとTech NewsのMarkdownパース処理
  const processedItems = useMemo(() => {
    if (!data?.items || data.items.length === 0) {
      return [];
    }

    // GitHub Trendingの場合は特別な処理
    if (selectedSource === 'github' && data.items[0]?.content) {
      try {
        return parseGitHubTrendingMarkdown(data.items[0].content);
      } catch (error) {
        console.error('GitHub Trending Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // Tech Newsの場合は特別な処理
    if (selectedSource === 'tech-news' && data.items[0]?.content) {
      try {
        return parseTechNewsMarkdown(data.items[0].content);
      } catch (error) {
        console.error('Tech News Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // Business Newsの場合は特別な処理
    if (selectedSource === 'business-news' && data.items[0]?.content) {
      try {
        return parseBusinessNewsMarkdown(data.items[0].content);
      } catch (error) {
        console.error('Business News Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // Zenn Articlesの場合は特別な処理
    if (selectedSource === 'zenn' && data.items[0]?.content) {
      try {
        return parseZennArticlesMarkdown(data.items[0].content);
      } catch (error) {
        console.error('Zenn Articles Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // Qiita Articlesの場合は特別な処理
    if (selectedSource === 'qiita' && data.items[0]?.content) {
      try {
        return parseQiitaArticlesMarkdown(data.items[0].content);
      } catch (error) {
        console.error('Qiita Articles Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // note Articlesの場合は特別な処理
    if (selectedSource === 'note' && data.items[0]?.content) {
      try {
        return parseNoteArticlesMarkdown(data.items[0].content);
      } catch (error) {
        console.error('note Articles Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // Reddit Postsの場合は特別な処理
    if (selectedSource === 'reddit' && data.items[0]?.content) {
      try {
        return parseRedditPostsMarkdown(data.items[0].content);
      } catch (error) {
        console.error('Reddit Posts Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // Hacker Newsの場合は構造化データをそのまま処理
    if (selectedSource === 'hacker-news' && data.items && data.items.length > 0) {
      // カテゴリヘッダーを追加
      const items: ContentItem[] = [{
        title: 'Hacker News',
        url: '',
        content: '',
        source: 'hacker-news',
        isLanguageHeader: false,
        isCategoryHeader: true,
        isArticle: false
      }];
      
      // 各記事を適切な形式に変換
      data.items.forEach((item) => {
        items.push({
          title: item.title,
          url: item.url || '',
          content: item.content,
          source: 'hacker-news',
          isLanguageHeader: false,
          isCategoryHeader: false,
          isArticle: true
        });
      });
      
      return items;
    }

    // Academic Papersの場合は特別な処理
    if (selectedSource === 'arxiv' && data.items[0]?.content) {
      try {
        return parseAcademicPapersMarkdown(data.items[0].content);
      } catch (error) {
        console.error('Academic Papers Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // 4chan Threadsの場合は特別な処理
    if (selectedSource === '4chan' && data.items[0]?.content) {
      try {
        return parseFourchanThreadsMarkdown(data.items[0].content);
      } catch (error) {
        console.error('4chan Threads Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // 5ch Threadsの場合は特別な処理
    if (selectedSource === '5chan' && data.items[0]?.content) {
      try {
        return parseFivechanThreadsMarkdown(data.items[0].content);
      } catch (error) {
        console.error('5ch Threads Markdown parsing error:', error);
        // フォールバック: 元のアイテムをそのまま返す
        return data.items;
      }
    }

    // 他のソースは従来通り
    return data.items;
  }, [data, selectedSource]);

  const SidebarContent = () => (
    <>
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <Layout className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          <span className="text-xl font-bold text-gray-900 dark:text-white">Dashboard</span>
        </div>
      </div>
      
      {/* 天気ウィジェット */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <WeatherWidget />
      </div>
      
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2 mb-3">
          <Calendar className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <span className="font-medium text-gray-700 dark:text-gray-300">Select Date</span>
        </div>
        <input
          type="date"
          value={format(selectedDate, 'yyyy-MM-dd')}
          max={format(new Date(), 'yyyy-MM-dd')}
          min={format(subDays(new Date(), 30), 'yyyy-MM-dd')}
          onChange={(e) => setSelectedDate(new Date(e.target.value))}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
        />
      </div>
      <nav className="flex-1 p-4">
        {/* Dashboard Section */}
        <div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Dashboard</div>
        <button
          onClick={() => {
            setCurrentPage('usage-dashboard');
            setIsMobileMenuOpen(false);
          }}
          className={`w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors ${
            currentPage === 'usage-dashboard'
              ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
              : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/30'
          }`}
        >
          Usage Dashboard
        </button>
        
        {/* Sources Section */}
        <div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400 mt-6">Sources</div>
        {sources.map((source) => {
          const sourceInfo = sourceDisplayInfo[source] || defaultSourceDisplayInfo;
          return (
            <button
              key={source}
              onClick={() => {
                setSelectedSource(source);
                setCurrentPage('content');
                setIsMobileMenuOpen(false);
              }}
              className={`w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors ${
                selectedSource === source && currentPage === 'content'
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/30'
              }`}
            >
              {sourceInfo.title}
            </button>
          );
        })}
        
        {/* テーマ切り替えボタン */}
        <div className="mt-6">
          <div className="mb-3 text-sm font-medium text-gray-500 dark:text-gray-400">Theme</div>
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="w-full flex items-center justify-between px-4 py-2 rounded-lg font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/30"
          >
            <span>{darkMode ? 'Light Mode' : 'Dark Mode'}</span>
            {darkMode ? (
              <Sun className="w-5 h-5 text-yellow-500" />
            ) : (
              <Moon className="w-5 h-5 text-blue-600" />
            )}
          </button>
        </div>
      </nav>
    </>
  );

  return (
    <div className={`min-h-screen bg-gray-100 dark:bg-gray-900 flex`}>
      {/* Side Navigation - Desktop */}
      <div className="hidden md:flex flex-col w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 fixed h-screen overflow-y-auto">
        <SidebarContent />
      </div>

      {/* メインコンテンツ用のスペーサー */}
      <div className="hidden md:block w-64 flex-shrink-0"></div>

      {/* Mobile Menu Button */}
      <div className="md:hidden fixed top-0 left-0 z-20 m-4">
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="p-2 rounded-lg bg-white dark:bg-gray-800 shadow-md"
        >
          <Menu className="w-6 h-6 text-gray-700 dark:text-gray-300" />
        </button>
      </div>

      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-10 bg-gray-800 bg-opacity-75 dark:bg-black dark:bg-opacity-75">
          <div className="fixed inset-y-0 left-0 w-64 bg-white dark:bg-gray-800 overflow-y-auto">
            <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-2">
                <Layout className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                <span className="text-xl font-bold text-gray-900 dark:text-white">Dashboard</span>
              </div>
              <button
                onClick={() => setIsMobileMenuOpen(false)}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                ✕
              </button>
            </div>
            <div className="h-full">
              <SidebarContent />
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1">
        {currentPage === 'usage-dashboard' ? (
          <UsageDashboard darkMode={darkMode} />
        ) : (
          <div className="p-4 sm:p-6 lg:p-8">
            <NewsHeader 
              selectedSource={selectedSource}
              selectedDate={selectedDate}
              darkMode={darkMode}
            />

            <div className="grid grid-cols-1 gap-6">
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
                    <div className="space-y-3">
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
                    </div>
                  </div>
                ))
              ) : isError ? (
                <div className="col-span-full text-center py-8">
                  <p className="text-red-600 dark:text-red-400 mb-4">Error loading content: {(error as Error)?.message || 'Unknown error occurred'}</p>
                  <button
                    onClick={() => refetch()}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors dark:bg-blue-700 dark:hover:bg-blue-600"
                  >
                    Try Again
                  </button>
                </div>
              ) : processedItems && processedItems.length > 0 ? (
                (() => {
                  // GitHub Trendingの場合は特別な番号付けロジック
                  if (selectedSource === 'github') {
                    let repositoryCount = 0;
                    return processedItems.map((item, index) => {
                      // 言語ヘッダーを検出したらカウンターをリセット
                      if (item.isLanguageHeader) {
                        repositoryCount = 0;
                      }
                      
                      const isRepository = item.isRepository;
                      const repositoryIndex = isRepository ? repositoryCount++ : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={repositoryIndex} 
                        />
                      );
                    });
                  } 
                  // Tech Newsの場合も特別な番号付けロジック
                  else if (selectedSource === 'tech-news') {
                    return processedItems.map((item, index) => {
                      const isArticle = item.isArticle;
                      // metadata.articleNumberを使用してフィードごとにリセット
                      const articleIndex = isArticle && item.metadata?.articleNumber 
                        ? item.metadata.articleNumber - 1 
                        : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={articleIndex} 
                        />
                      );
                    });
                  } 
                  // Business Newsの場合も特別な番号付けロジック
                  else if (selectedSource === 'business-news') {
                    return processedItems.map((item, index) => {
                      const isArticle = item.isArticle;
                      // metadata.articleNumberを使用してフィードごとにリセット
                      const articleIndex = isArticle && item.metadata?.articleNumber 
                        ? item.metadata.articleNumber - 1 
                        : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={articleIndex} 
                        />
                      );
                    });
                  } 
                  // Zenn Articlesの場合も特別な番号付けロジック
                  else if (selectedSource === 'zenn') {
                    return processedItems.map((item, index) => {
                      const isArticle = item.isArticle;
                      const articleIndex = isArticle && item.metadata?.articleNumber ? item.metadata.articleNumber - 1 : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={articleIndex} 
                        />
                      );
                    });
                  } 
                  // Qiita Articlesの場合も特別な番号付けロジック
                  else if (selectedSource === 'qiita') {
                    return processedItems.map((item, index) => {
                      const isArticle = item.isArticle;
                      const articleIndex = isArticle && item.metadata?.articleNumber ? item.metadata.articleNumber - 1 : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={articleIndex} 
                        />
                      );
                    });
                  } 
                  // note Articlesの場合も特別な番号付けロジック
                  else if (selectedSource === 'note') {
                    return processedItems.map((item, index) => {
                      const isArticle = item.isArticle;
                      const articleIndex = isArticle && item.metadata?.articleNumber 
                        ? item.metadata.articleNumber - 1 
                        : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={articleIndex} 
                        />
                      );
                    });
                  } 
                  // Reddit Postsの場合も特別な番号付けロジック
                  else if (selectedSource === 'reddit') {
                    return processedItems.map((item, index) => {
                      const isPost = item.isArticle;
                      const postIndex = isPost && item.metadata?.articleNumber ? item.metadata.articleNumber - 1 : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={postIndex} 
                        />
                      );
                    });
                  } 
                  // 4chan Threadsの場合も特別な番号付けロジック
                  else if (selectedSource === '4chan') {
                    return processedItems.map((item, index) => {
                      const isArticle = item.isArticle;
                      const threadIndex = isArticle && item.metadata?.articleNumber 
                        ? item.metadata.articleNumber - 1 
                        : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={threadIndex} 
                        />
                      );
                    });
                  } 
                  // 5ch Threadsの場合も特別な番号付けロジック
                  else if (selectedSource === '5chan') {
                    return processedItems.map((item, index) => {
                      const isArticle = item.isArticle;
                      const threadIndex = isArticle && item.metadata?.articleNumber 
                        ? item.metadata.articleNumber - 1 
                        : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={threadIndex} 
                        />
                      );
                    });
                  } 
                  // Hacker Newsの場合も特別な番号付けロジック
                  else if (selectedSource === 'hacker-news') {
                    let articleCount = 0;
                    return processedItems.map((item, index) => {
                      const isArticle = item.isArticle;
                      const articleIndex = isArticle ? articleCount++ : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={articleIndex} 
                        />
                      );
                    });
                  } 
                  // Academic Papersの場合も特別な番号付けロジック
                  else if (selectedSource === 'arxiv') {
                    return processedItems.map((item, index) => {
                      const isPaper = item.isArticle;
                      const paperIndex = isPaper && item.metadata?.articleNumber ? item.metadata.articleNumber - 1 : undefined;
                      return (
                        <ContentCard 
                          key={index} 
                          item={item} 
                          darkMode={darkMode} 
                          index={paperIndex} 
                        />
                      );
                    });
                  } else {
                    // 他のソースは通常の番号付け
                    return processedItems.map((item, index) => (
                      <ContentCard 
                        key={index} 
                        item={item} 
                        darkMode={darkMode} 
                        index={index} 
                      />
                    ));
                  }
                })()
              ) : (
                <div className="col-span-full text-center py-8">
                  <p className="text-gray-500 dark:text-gray-400">No content available for this source</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
