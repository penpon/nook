# TASK-060: React 18 Server Components移行（SSR + RSC実装）

## タスク概要
React 18 Server ComponentsとNext.js App Routerへの移行を実行し、サーバーサイドレンダリングによる初期表示高速化とSEO改善を実現する。静的コンテンツの事前レンダリングとクライアント専用コンポーネントの適切な分離を行う。

## 変更予定ファイル
- nook/frontend/package.json（Next.js 14 + React 18移行）
- nook/frontend/next.config.js（新規作成）
- nook/frontend/app/layout.tsx（新規作成）
- nook/frontend/app/page.tsx（新規作成）
- nook/frontend/app/globals.css（index.css移行）
- nook/frontend/app/api/（API Routes移行）
- nook/frontend/src/components/server/（Server Components作成）
- nook/frontend/src/components/client/（Client Components作成）
- nook/frontend/src/lib/（サーバー用ユーティリティ）
- nook/frontend/public/（静的ファイル移行）

## 前提タスク
TASK-059（Container Queries導入完了後）

## worktree名
worktrees/TASK-060-react-server-components-migration

## 作業内容

### 1. 依存関係の大幅更新
```json
// package.json 完全書き換え
{
  "name": "nook-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "next": "^14.2.0",
    "axios": "^1.6.7",
    "date-fns": "^3.3.1",
    "lucide-react": "^0.344.0",
    "react-markdown": "^9.0.1",
    "recharts": "^3.0.0",
    "remark-gfm": "^4.0.0",
    "swr": "^2.2.5"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@tailwindcss/container-queries": "^0.1.1",
    "@tailwindcss/typography": "^0.5.10",
    "autoprefixer": "^10.4.18",
    "eslint": "^8.57.0",
    "eslint-config-next": "^14.2.0",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.5.3"
  }
}
```

### 2. Next.js設定ファイル
```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: true,
  },
  images: {
    domains: ['localhost'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

### 3. App Routerレイアウト構造
```typescript
// app/layout.tsx
import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '@/components/providers/ThemeProvider';

export const metadata: Metadata = {
  title: 'Nook - Tech News Dashboard',
  description: 'Comprehensive tech news dashboard aggregating content from GitHub, Hacker News, arXiv, and more',
  keywords: ['tech news', 'github', 'hacker news', 'arxiv', 'dashboard'],
  authors: [{ name: 'Nook Team' }],
  manifest: '/manifest.json',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#3b82f6' },
    { media: '(prefers-color-scheme: dark)', color: '#1f2937' },
  ],
  viewport: {
    width: 'device-width',
    initialScale: 1,
  },
  icons: {
    icon: [
      { url: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: '/icons/apple-touch-icon.png',
  },
  openGraph: {
    title: 'Nook - Tech News Dashboard',
    description: 'Stay updated with the latest in tech across multiple sources',
    type: 'website',
    images: ['/icons/icon-512x512.png'],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Nook - Tech News Dashboard',
    description: 'Stay updated with the latest in tech across multiple sources',
    images: ['/icons/icon-512x512.png'],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja" suppressHydrationWarnings>
      <head />
      <body className="antialiased">
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

### 4. メインページ（Server Component）
```typescript
// app/page.tsx
import { Suspense } from 'react';
import { MainLayout } from '@/components/server/MainLayout';
import { ContentArea } from '@/components/server/ContentArea';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { getInitialSource } from '@/lib/utils';

interface PageProps {
  searchParams: {
    source?: string;
    page?: string;
  };
}

export default function HomePage({ searchParams }: PageProps) {
  const selectedSource = getInitialSource(searchParams.source);
  const currentPage = searchParams.page || 'content';

  return (
    <MainLayout 
      initialSource={selectedSource}
      initialPage={currentPage}
    >
      <Suspense fallback={<LoadingSkeleton />}>
        <ContentArea 
          source={selectedSource}
          page={currentPage}
        />
      </Suspense>
    </MainLayout>
  );
}

// Static generation for common source pages
export async function generateStaticParams() {
  const sources = ['hacker-news', 'github', 'tech-news', 'business-news'];
  
  return sources.map((source) => ({
    source,
  }));
}
```

### 5. Server Components作成

#### components/server/MainLayout.tsx
```typescript
// src/components/server/MainLayout.tsx
import React from 'react';
import { ClientSidebar } from '@/components/client/ClientSidebar';
import { MobileMenuProvider } from '@/components/providers/MobileMenuProvider';

interface MainLayoutProps {
  children: React.ReactNode;
  initialSource: string;
  initialPage: string;
}

export function MainLayout({ children, initialSource, initialPage }: MainLayoutProps) {
  return (
    <MobileMenuProvider>
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex">
        {/* Desktop Sidebar */}
        <div className="hidden md:flex flex-col w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 fixed h-screen overflow-y-auto">
          <ClientSidebar
            initialSource={initialSource}
            initialPage={initialPage}
          />
        </div>

        {/* Main Content Spacer */}
        <div className="hidden md:block w-64 flex-shrink-0"></div>

        {/* Main Content */}
        <div className="flex-1">
          {children}
        </div>
      </div>
    </MobileMenuProvider>
  );
}
```

#### components/server/ContentArea.tsx
```typescript
// src/components/server/ContentArea.tsx
import { Suspense } from 'react';
import { format } from 'date-fns';
import { NewsHeaderServer } from './NewsHeaderServer';
import { ContentListServer } from './ContentListServer';
import { UsageDashboardServer } from './UsageDashboardServer';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';

interface ContentAreaProps {
  source: string;
  page: string;
  date?: string;
}

export async function ContentArea({ 
  source, 
  page, 
  date = format(new Date(), 'yyyy-MM-dd') 
}: ContentAreaProps) {
  if (page === 'usage-dashboard') {
    return (
      <Suspense fallback={<LoadingSkeleton />}>
        <UsageDashboardServer />
      </Suspense>
    );
  }

  return (
    <div className="content-container cq-xs:p-4 cq-md:p-6 cq-lg:p-8">
      <NewsHeaderServer source={source} date={date} />
      
      <div className="cq-xs:grid cq-xs:grid-cols-1 gap-6">
        <Suspense fallback={<LoadingSkeleton />}>
          <ContentListServer source={source} date={date} />
        </Suspense>
      </div>
    </div>
  );
}
```

#### components/server/ContentListServer.tsx
```typescript
// src/components/server/ContentListServer.tsx
import { getContent } from '@/lib/api-server';
import { getParserForSource } from '@/utils/parsers';
import { ContentRenderer } from '@/components/client/ContentRenderer';

interface ContentListServerProps {
  source: string;
  date: string;
}

export async function ContentListServer({ source, date }: ContentListServerProps) {
  try {
    // Server-side data fetching
    const data = await getContent(source, date);
    
    if (!data?.items || data.items.length === 0) {
      return (
        <div className="col-span-full text-center py-8">
          <p className="text-gray-500 dark:text-gray-400">
            No content available for this source
          </p>
        </div>
      );
    }

    // Server-side parsing
    const parser = getParserForSource(source);
    let processedItems = data.items;
    
    if (parser && data.items[0]?.content) {
      try {
        processedItems = parser(data.items[0].content);
      } catch (error) {
        console.error(`${source} parsing error:`, error);
        processedItems = data.items;
      }
    }

    // Pass pre-processed data to client component
    return (
      <ContentRenderer
        processedItems={processedItems}
        selectedSource={source}
      />
    );
  } catch (error) {
    console.error('Failed to fetch content:', error);
    return (
      <div className="col-span-full text-center py-8">
        <p className="text-red-600 dark:text-red-400 mb-4">
          Error loading content
        </p>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
          Try Again
        </button>
      </div>
    );
  }
}
```

### 6. Client Components作成

#### components/client/ClientSidebar.tsx
```typescript
// src/components/client/ClientSidebar.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Sidebar } from '@/components/ui/Sidebar';
import { useTheme } from '@/components/providers/ThemeProvider';
import { useMobileMenu } from '@/components/providers/MobileMenuProvider';

interface ClientSidebarProps {
  initialSource: string;
  initialPage: string;
}

export function ClientSidebar({ initialSource, initialPage }: ClientSidebarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { darkMode, setDarkMode } = useTheme();
  const { setIsMobileMenuOpen } = useMobileMenu();
  
  const [selectedSource, setSelectedSource] = useState(initialSource);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [selectedDate, setSelectedDate] = useState(new Date());

  // URL sync
  useEffect(() => {
    const params = new URLSearchParams(searchParams.toString());
    
    if (currentPage === 'content') {
      params.set('source', selectedSource);
      params.delete('page');
    } else {
      params.set('page', currentPage);
      params.delete('source');
    }
    
    router.push(`/?${params.toString()}`, { scroll: false });
  }, [selectedSource, currentPage, router, searchParams]);

  const handleSourceChange = (source: string) => {
    setSelectedSource(source);
    setCurrentPage('content');
    setIsMobileMenuOpen(false);
  };

  const handlePageChange = (page: string) => {
    setCurrentPage(page);
    setIsMobileMenuOpen(false);
  };

  return (
    <Sidebar
      selectedSource={selectedSource}
      setSelectedSource={handleSourceChange}
      currentPage={currentPage}
      setCurrentPage={handlePageChange}
      selectedDate={selectedDate}
      setSelectedDate={setSelectedDate}
      darkMode={darkMode}
      setDarkMode={setDarkMode}
      onMenuItemClick={() => setIsMobileMenuOpen(false)}
    />
  );
}
```

#### components/client/ContentRenderer.tsx
```typescript
// src/components/client/ContentRenderer.tsx
'use client';

import React from 'react';
import { ContentCard } from '@/components/ui/ContentCard';
import { ContentItem } from '@/types';
import { useTheme } from '@/components/providers/ThemeProvider';

interface ContentRendererProps {
  processedItems: ContentItem[];
  selectedSource: string;
}

export function ContentRenderer({ processedItems, selectedSource }: ContentRendererProps) {
  const { darkMode } = useTheme();
  
  // Client-side rendering logic (번호 매기기 등)
  const renderContentItems = () => {
    // 기존의 번호 매기기 로직을 그대로 사용
    // ...
  };

  return <>{renderContentItems()}</>;
}
```

### 7. Providers作成

#### components/providers/ThemeProvider.tsx
```typescript
// src/components/providers/ThemeProvider.tsx
'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface ThemeContextType {
  darkMode: boolean;
  setDarkMode: (dark: boolean) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [darkMode, setDarkMode] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const shouldBeDark = savedTheme ? savedTheme === 'dark' : prefersDark;
    
    setDarkMode(shouldBeDark);
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted) {
      if (darkMode) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme', 'light');
      }
    }
  }, [darkMode, mounted]);

  // Prevent flash of unstyled content
  if (!mounted) {
    return <div style={{ visibility: 'hidden' }}>{children}</div>;
  }

  return (
    <ThemeContext.Provider value={{ darkMode, setDarkMode }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
```

### 8. サーバー用APIライブラリ
```typescript
// src/lib/api-server.ts
import { cache } from 'react';

// React cache()を使用してサーバーサイドでのデータフェッチを最適化
export const getContent = cache(async (source: string, date: string) => {
  const response = await fetch(`http://localhost:8000/api/content/${source}?date=${date}`, {
    next: { 
      revalidate: 300, // 5分間キャッシュ
      tags: [`content-${source}-${date}`] 
    }
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch content: ${response.statusText}`);
  }
  
  return response.json();
});

export const getUsageSummary = cache(async () => {
  const response = await fetch('http://localhost:8000/api/usage/summary', {
    next: { 
      revalidate: 60, // 1分間キャッシュ
      tags: ['usage-summary'] 
    }
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch usage summary: ${response.statusText}`);
  }
  
  return response.json();
});
```

### 9. グローバルCSS移行
```css
/* app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Container Queries設定 */
/* TASK-059で作成した設定をそのまま移行 */

/* Global styles */
@layer base {
  html {
    scroll-behavior: smooth;
  }
  
  body {
    @apply antialiased;
  }
}

@layer components {
  .touch-manipulation {
    touch-action: manipulation;
  }
}
```

### 10. TypeScript設定の更新
```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@/app/*": ["./app/*"],
      "@/components/*": ["./src/components/*"],
      "@/lib/*": ["./src/lib/*"],
      "@/utils/*": ["./src/utils/*"],
      "@/hooks/*": ["./src/hooks/*"],
      "@/types": ["./src/types"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### 11. API Routes移行
```typescript
// app/api/content/[source]/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { source: string } }
) {
  const { searchParams } = new URL(request.url);
  const date = searchParams.get('date') || new Date().toISOString().split('T')[0];
  
  try {
    // Proxy to backend API
    const response = await fetch(`http://localhost:8000/api/content/${params.source}?date=${date}`);
    const data = await response.json();
    
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch content' },
      { status: 500 }
    );
  }
}
```

### 12. テスト項目
1. Server Components での初期レンダリング速度確認
2. Hydration エラーが発生しないことを確認
3. SEO メタデータが適切に設定されることを確認
4. Static Generation が正しく動作することを確認
5. ISR (Incremental Static Regeneration) の動作確認
6. Client Components の状態管理が正常に動作することを確認
7. ページ遷移時のパフォーマンス確認
8. Bundle size の削減効果確認

### 13. 段階的移行戦略
1. **Phase 1**: 基本的なSSR環境構築
2. **Phase 2**: Server Componentsの段階的移行
3. **Phase 3**: Client Componentsの最小化
4. **Phase 4**: 静的生成とISRの最適化

## 完了条件
- [ ] Next.js 14 + React 18 Server Components環境構築完了
- [ ] 主要コンポーネントのServer/Client分離完了
- [ ] 初期表示速度大幅改善（LCP < 1.2秒）
- [ ] SEOメタデータ適切設定
- [ ] Bundle sizeの削減確認（80%削減目標）
- [ ] Hydration エラー解消
- [ ] 既存機能の完全互換性確保