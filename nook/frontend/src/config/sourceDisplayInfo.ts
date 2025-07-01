export interface SourceDisplayInfo {
  title: string;
  subtitle: string;
  dateFormat: string;
  gradientFrom?: string;
  gradientTo?: string;
  borderColor?: string;
}

export const sourceDisplayInfo: Record<string, SourceDisplayInfo> = {
  'hacker-news': {
    title: 'Hacker News',
    subtitle: 'ハッカーニュース トップ記事',
    dateFormat: 'yyyy-MM-dd',
    gradientFrom: 'from-orange-50',
    gradientTo: 'to-amber-50',
    borderColor: 'border-orange-200'
  },
  'tech-news': {
    title: 'Tech News',
    subtitle: '技術ニュース記事',
    dateFormat: 'yyyy年MM月dd日',
    gradientFrom: 'from-blue-50',
    gradientTo: 'to-cyan-50',
    borderColor: 'border-blue-200'
  },
  'business-news': {
    title: 'Business News',
    subtitle: 'ビジネスニュース記事',
    dateFormat: 'yyyy年MM月dd日',
    gradientFrom: 'from-gray-50',
    gradientTo: 'to-slate-50',
    borderColor: 'border-gray-200'
  },
  'arxiv': {
    title: 'ArXiv',
    subtitle: '学術論文・研究レポート',
    dateFormat: 'yyyy年MM月dd日',
    gradientFrom: 'from-purple-50',
    gradientTo: 'to-indigo-50',
    borderColor: 'border-purple-200'
  },
  'github': {
    title: 'GitHub Trending',
    subtitle: 'GitHub トレンドリポジトリ',
    dateFormat: 'yyyy-MM-dd',
    gradientFrom: 'from-gray-50',
    gradientTo: 'to-zinc-50',
    borderColor: 'border-gray-300'
  },
  'zenn': {
    title: 'Zenn',
    subtitle: 'Zenn 技術記事',
    dateFormat: 'yyyy年MM月dd日',
    gradientFrom: 'from-sky-50',
    gradientTo: 'to-blue-50',
    borderColor: 'border-sky-200'
  },
  'qiita': {
    title: 'Qiita',
    subtitle: 'Qiita 技術記事',
    dateFormat: 'yyyy年MM月dd日',
    gradientFrom: 'from-green-50',
    gradientTo: 'to-emerald-50',
    borderColor: 'border-green-200'
  },
  'note': {
    title: 'Note',
    subtitle: 'note 記事・コラム',
    dateFormat: 'yyyy年MM月dd日',
    gradientFrom: 'from-teal-50',
    gradientTo: 'to-cyan-50',
    borderColor: 'border-teal-200'
  },
  'reddit': {
    title: 'Reddit',
    subtitle: 'Reddit 人気投稿',
    dateFormat: 'MMM dd, yyyy',
    gradientFrom: 'from-red-50',
    gradientTo: 'to-orange-50',
    borderColor: 'border-red-200'
  },
  '4chan': {
    title: '4ch',
    subtitle: '4ちゃんねる スレッド',
    dateFormat: 'MM/dd/yyyy',
    gradientFrom: 'from-green-50',
    gradientTo: 'to-lime-50',
    borderColor: 'border-green-300'
  },
  '5chan': {
    title: '5ch',
    subtitle: '5ちゃんねる スレッド',
    dateFormat: 'yyyy年MM月dd日',
    gradientFrom: 'from-amber-50',
    gradientTo: 'to-yellow-50',
    borderColor: 'border-amber-200'
  }
};

// デフォルト設定
export const defaultSourceDisplayInfo: SourceDisplayInfo = {
  title: 'News Feed',
  subtitle: 'ニュースフィード',
  dateFormat: 'yyyy-MM-dd',
  gradientFrom: 'from-blue-50',
  gradientTo: 'to-indigo-50',
  borderColor: 'border-blue-200'
};
