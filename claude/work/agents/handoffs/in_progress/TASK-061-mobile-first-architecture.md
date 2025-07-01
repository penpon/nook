# TASK-061: モバイルファーストアーキテクチャ全面転換

## タスク概要
デスクトップファーストからモバイルファーストアーキテクチャへの全面転換を実行する。CSS設計、コンポーネント設計、パフォーマンス最適化をモバイル優先で再構築し、2025年のモバイルUXスタンダードに準拠したアプリケーションを実現する。

## 変更予定ファイル
- app/globals.css（モバイルファーストCSS完全書き換え）
- tailwind.config.js（モバイルファースト設定）
- src/components/ui/（全UIコンポーネント改修）
- src/components/mobile/（モバイル専用コンポーネント作成）
- src/hooks/useMediaQuery.ts（新規作成）
- src/hooks/useTouch.ts（新規作成）
- src/hooks/useVibration.ts（新規作成）
- src/utils/performance.ts（モバイルパフォーマンス最適化）
- app/layout.tsx（モバイル最適化メタタグ）
- next.config.js（モバイル最適化設定）

## 前提タスク
TASK-060（React Server Components移行完了後）

## worktree名
worktrees/TASK-061-mobile-first-architecture

## 作業内容

### 1. モバイルファーストCSS基盤の再構築
```css
/* app/globals.css - 完全書き換え */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* モバイルファースト基本設定 */
@layer base {
  /* モバイル基準のroot設定 */
  :root {
    /* モバイル用カラーパレット */
    --primary-50: #eff6ff;
    --primary-500: #3b82f6;
    --primary-900: #1e3a8a;
    
    /* モバイル用フォントサイズ（基準） */
    --text-xs: 0.75rem;    /* 12px */
    --text-sm: 0.875rem;   /* 14px */
    --text-base: 1rem;     /* 16px - モバイル基準 */
    --text-lg: 1.125rem;   /* 18px */
    --text-xl: 1.25rem;    /* 20px */
    
    /* モバイル用スペーシング（基準） */
    --space-1: 0.25rem;    /* 4px */
    --space-2: 0.5rem;     /* 8px */
    --space-3: 0.75rem;    /* 12px */
    --space-4: 1rem;       /* 16px - モバイル基準 */
    --space-5: 1.25rem;    /* 20px */
    --space-6: 1.5rem;     /* 24px */
    
    /* タッチターゲットサイズ */
    --touch-target-min: 44px;
    --touch-target-comfortable: 48px;
    --touch-target-large: 56px;
  }
  
  /* デスクトップ用の拡張 */
  @media (min-width: 768px) {
    :root {
      /* デスクトップ用フォントサイズ（拡張） */
      --text-base: 1.125rem; /* 18px */
      --text-lg: 1.25rem;    /* 20px */
      --text-xl: 1.5rem;     /* 24px */
      --text-2xl: 2rem;      /* 32px */
      
      /* デスクトップ用スペーシング（拡張） */
      --space-4: 1.5rem;     /* 24px */
      --space-6: 2rem;       /* 32px */
      --space-8: 2.5rem;     /* 40px */
    }
  }

  /* HTML基本設定（モバイル優先） */
  html {
    font-size: 16px; /* モバイル基準 */
    line-height: 1.5;
    scroll-behavior: smooth;
    -webkit-text-size-adjust: 100%;
    -webkit-tap-highlight-color: transparent;
  }
  
  @media (min-width: 768px) {
    html {
      font-size: 18px; /* デスクトップで拡張 */
    }
  }

  body {
    @apply antialiased;
    @apply text-base text-gray-900 dark:text-white;
    @apply bg-white dark:bg-gray-900;
    /* モバイル用フォント設定 */
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    /* モバイル最適化 */
    overscroll-behavior: none;
    -webkit-overflow-scrolling: touch;
    touch-action: manipulation;
  }

  /* タッチデバイス用の調整 */
  @media (hover: none) and (pointer: coarse) {
    body {
      /* モバイルデバイス専用スタイル */
      user-select: none;
    }
    
    /* ボタンのタッチ最適化 */
    button, [role="button"] {
      @apply min-h-[44px] min-w-[44px];
      touch-action: manipulation;
      user-select: none;
    }
  }
}

@layer components {
  /* モバイルファーストコンポーネントベース */
  
  /* カード基本スタイル（モバイル基準） */
  .card {
    @apply bg-white dark:bg-gray-800;
    @apply rounded-lg shadow-sm border border-gray-200 dark:border-gray-700;
    @apply p-4; /* モバイル基準パディング */
    @apply transition-shadow duration-200;
    
    /* デスクトップでの拡張 */
    @media (min-width: 768px) {
      @apply p-6 shadow-md;
    }
    
    /* タッチデバイスでの調整 */
    @media (hover: none) {
      @apply active:scale-[0.98];
      @apply transition-transform duration-150;
    }
    
    /* ホバー可能デバイスでの調整 */
    @media (hover: hover) {
      @apply hover:shadow-lg;
    }
  }
  
  /* ボタン基本スタイル（モバイル基準） */
  .btn {
    @apply inline-flex items-center justify-center;
    @apply px-4 py-2; /* モバイル基準 */
    @apply min-h-[44px]; /* WCAG準拠 */
    @apply rounded-lg font-medium;
    @apply transition-colors duration-200;
    @apply touch-manipulation;
    @apply select-none;
    
    /* デスクトップでの拡張 */
    @media (min-width: 768px) {
      @apply px-6 py-3;
      @apply min-h-[40px]; /* デスクトップでは少し小さく */
    }
  }
  
  .btn-primary {
    @apply btn bg-blue-600 text-white;
    @apply active:bg-blue-700; /* タッチ用 */
    
    @media (hover: hover) {
      @apply hover:bg-blue-700;
    }
  }
  
  .btn-secondary {
    @apply btn bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white;
    @apply active:bg-gray-300 dark:active:bg-gray-600;
    
    @media (hover: hover) {
      @apply hover:bg-gray-300 dark:hover:bg-gray-600;
    }
  }
  
  /* 入力フィールド（モバイル基準） */
  .input {
    @apply w-full px-3 py-2;
    @apply min-h-[44px]; /* タッチフレンドリー */
    @apply border border-gray-300 dark:border-gray-600;
    @apply rounded-lg;
    @apply focus:outline-none focus:ring-2 focus:ring-blue-500;
    @apply dark:bg-gray-700 dark:text-white;
    @apply text-base; /* ズーム防止のため16px以上 */
    
    /* デスクトップでの調整 */
    @media (min-width: 768px) {
      @apply min-h-[40px];
      @apply text-sm;
    }
  }
  
  /* グリッドレイアウト（モバイルファースト） */
  .grid-responsive {
    @apply grid grid-cols-1 gap-4; /* モバイル基準 */
    
    @media (min-width: 640px) {
      @apply grid-cols-2 gap-6;
    }
    
    @media (min-width: 1024px) {
      @apply grid-cols-3;
    }
    
    @media (min-width: 1280px) {
      @apply grid-cols-4;
    }
  }
  
  /* テキストサイズ（モバイルファースト） */
  .text-responsive-sm {
    @apply text-sm; /* モバイル基準 */
    
    @media (min-width: 768px) {
      @apply text-base;
    }
  }
  
  .text-responsive-base {
    @apply text-base; /* モバイル基準 */
    
    @media (min-width: 768px) {
      @apply text-lg;
    }
  }
  
  .text-responsive-lg {
    @apply text-lg; /* モバイル基準 */
    
    @media (min-width: 768px) {
      @apply text-xl;
    }
  }
  
  /* スペーシング（モバイルファースト） */
  .spacing-responsive {
    @apply p-4; /* モバイル基準 */
    
    @media (min-width: 640px) {
      @apply p-6;
    }
    
    @media (min-width: 1024px) {
      @apply p-8;
    }
  }
}

@layer utilities {
  /* タッチ最適化ユーティリティ */
  .touch-optimized {
    @apply min-h-[44px] min-w-[44px];
    @apply touch-manipulation;
    @apply select-none;
  }
  
  /* スクロール最適化 */
  .scroll-smooth-mobile {
    -webkit-overflow-scrolling: touch;
    overscroll-behavior: contain;
  }
  
  /* フォーカス最適化 */
  .focus-visible-mobile {
    @apply focus:outline-none;
    @apply focus-visible:outline-2;
    @apply focus-visible:outline-blue-500;
    @apply focus-visible:outline-offset-2;
  }
  
  /* モバイル専用表示/非表示 */
  .mobile-only {
    @media (min-width: 768px) {
      @apply hidden;
    }
  }
  
  .desktop-only {
    @apply hidden;
    
    @media (min-width: 768px) {
      @apply block;
    }
  }
  
  /* セーフエリア対応 */
  .safe-area-inset {
    padding-top: env(safe-area-inset-top);
    padding-right: env(safe-area-inset-right);
    padding-bottom: env(safe-area-inset-bottom);
    padding-left: env(safe-area-inset-left);
  }
  
  /* Container Queries（モバイルファースト） */
  .container-mobile {
    container-type: inline-size;
    container-name: mobile;
  }
}

/* モバイル専用メディアクエリ */
@media (max-width: 767px) {
  /* モバイル専用の微調整 */
  .prose {
    @apply text-sm leading-relaxed;
  }
  
  /* モバイルでのテーブル最適化 */
  .table-mobile {
    @apply text-xs;
  }
  
  .table-mobile th,
  .table-mobile td {
    @apply px-2 py-1;
  }
}

/* タッチデバイス専用 */
@media (hover: none) and (pointer: coarse) {
  /* スクロールバーを隠す */
  ::-webkit-scrollbar {
    display: none;
  }
  
  /* タッチフィードバック */
  .touch-feedback {
    @apply active:scale-95;
    @apply transition-transform duration-150;
  }
  
  /* ボタンのタッチ最適化 */
  button:active,
  [role="button"]:active {
    transform: scale(0.95);
  }
}

/* 印刷用スタイル */
@media print {
  .no-print {
    @apply hidden;
  }
  
  body {
    @apply text-black bg-white;
  }
}
```

### 2. Tailwind CSS設定の完全書き換え
```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./app/**/*.{js,ts,jsx,tsx}', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    // モバイルファーストブレークポイント
    screens: {
      'xs': '375px',   // iPhone SE
      'sm': '640px',   // タブレット縦
      'md': '768px',   // タブレット横
      'lg': '1024px',  // ラップトップ
      'xl': '1280px',  // デスクトップ
      '2xl': '1536px', // 大画面
      
      // モバイル専用ブレークポイント
      'mobile-s': {'max': '374px'}, // 小画面スマホ
      'mobile-m': {'min': '375px', 'max': '639px'}, // 中画面スマホ
      'mobile-l': {'min': '640px', 'max': '767px'}, // 大画面スマホ
      
      // タッチデバイス検出
      'touch': {'raw': '(hover: none) and (pointer: coarse)'},
      'no-touch': {'raw': '(hover: hover) and (pointer: fine)'},
    },
    
    extend: {
      // モバイルファーストフォントサイズ
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],     // 12px
        'sm': ['0.875rem', { lineHeight: '1.25rem' }], // 14px
        'base': ['1rem', { lineHeight: '1.5rem' }],    // 16px - モバイル基準
        'lg': ['1.125rem', { lineHeight: '1.75rem' }], // 18px
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],  // 20px
        '2xl': ['1.5rem', { lineHeight: '2rem' }],     // 24px
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],  // 36px
        
        // レスポンシブフォントサイズ
        'responsive-sm': ['clamp(0.875rem, 2vw, 1rem)'],
        'responsive-base': ['clamp(1rem, 2.5vw, 1.125rem)'],
        'responsive-lg': ['clamp(1.125rem, 3vw, 1.25rem)'],
        'responsive-xl': ['clamp(1.25rem, 3.5vw, 1.5rem)'],
      },
      
      // モバイルファーストスペーシング
      spacing: {
        'touch': '44px',      // 最小タッチターゲット
        'touch-lg': '48px',   // 推奨タッチターゲット
        'touch-xl': '56px',   // 大きなタッチターゲット
        'safe-top': 'env(safe-area-inset-top)',
        'safe-bottom': 'env(safe-area-inset-bottom)',
        'safe-left': 'env(safe-area-inset-left)',
        'safe-right': 'env(safe-area-inset-right)',
      },
      
      // モバイル最適化カラーパレット
      colors: {
        // 高コントラスト対応
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        
        // ダークモード最適化
        dark: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        }
      },
      
      // モバイル用アニメーション
      animation: {
        'fade-in': 'fadeIn 0.2s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'touch-feedback': 'touchFeedback 0.15s ease-out',
      },
      
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.9)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        touchFeedback: {
          '0%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(0.95)' },
          '100%': { transform: 'scale(1)' },
        },
      },
      
      // Container Queries
      containers: {
        'xs': '20rem',   // 320px
        'sm': '24rem',   // 384px
        'md': '28rem',   // 448px
        'lg': '32rem',   // 512px
        'xl': '36rem',   // 576px
        '2xl': '42rem',  // 672px
        '3xl': '48rem',  // 768px
        '4xl': '56rem',  // 896px
      },
      
      // Typography
      typography: {
        DEFAULT: {
          css: {
            maxWidth: '100%',
            // モバイル基準のタイポグラフィ
            fontSize: '1rem',
            lineHeight: '1.6',
            
            // モバイル用見出し
            h1: {
              fontSize: '1.5rem',
              lineHeight: '1.3',
              marginBottom: '1rem',
            },
            h2: {
              fontSize: '1.25rem',
              lineHeight: '1.4',
              marginBottom: '0.75rem',
            },
            h3: {
              fontSize: '1.125rem',
              lineHeight: '1.4',
              marginBottom: '0.5rem',
            },
            
            // モバイル用段落
            p: {
              marginBottom: '1rem',
              fontSize: '1rem',
              lineHeight: '1.6',
            },
            
            // リスト
            ul: {
              marginBottom: '1rem',
            },
            li: {
              marginBottom: '0.25rem',
            },
            
            // コードブロック
            pre: {
              fontSize: '0.875rem',
              overflowX: 'auto',
              padding: '1rem',
              borderRadius: '0.5rem',
            },
            
            code: {
              fontSize: '0.875rem',
              wordBreak: 'break-word',
            },
            
            // 画像
            img: {
              maxWidth: '100%',
              height: 'auto',
              borderRadius: '0.5rem',
            },
          },
        },
        
        // デスクトップ用タイポグラフィ
        lg: {
          css: {
            fontSize: '1.125rem',
            lineHeight: '1.7',
            
            h1: {
              fontSize: '2rem',
              lineHeight: '1.2',
            },
            h2: {
              fontSize: '1.5rem',
              lineHeight: '1.3',
            },
            h3: {
              fontSize: '1.25rem',
              lineHeight: '1.4',
            },
            
            p: {
              fontSize: '1.125rem',
              lineHeight: '1.7',
            },
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/container-queries'),
    
    // カスタムプラグイン
    function({ addUtilities, addComponents, theme }) {
      // モバイル専用ユーティリティ
      addUtilities({
        '.text-size-adjust-none': {
          '-webkit-text-size-adjust': 'none',
          '-moz-text-size-adjust': 'none',
          'text-size-adjust': 'none',
        },
        '.tap-highlight-transparent': {
          '-webkit-tap-highlight-color': 'transparent',
        },
        '.overscroll-none': {
          'overscroll-behavior': 'none',
        },
        '.touch-callout-none': {
          '-webkit-touch-callout': 'none',
        },
      });
      
      // モバイル専用コンポーネント
      addComponents({
        '.mobile-nav': {
          position: 'fixed',
          bottom: '0',
          left: '0',
          right: '0',
          height: 'calc(64px + env(safe-area-inset-bottom))',
          paddingBottom: 'env(safe-area-inset-bottom)',
          backgroundColor: theme('colors.white'),
          borderTop: `1px solid ${theme('colors.gray.200')}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-around',
          zIndex: '50',
        },
        
        '.mobile-header': {
          position: 'sticky',
          top: '0',
          paddingTop: 'env(safe-area-inset-top)',
          backgroundColor: theme('colors.white'),
          borderBottom: `1px solid ${theme('colors.gray.200')}`,
          zIndex: '40',
        },
      });
    },
  ],
};
```

### 3. モバイル専用フック作成

#### hooks/useMediaQuery.ts
```typescript
// src/hooks/useMediaQuery.ts
'use client';

import { useState, useEffect } from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    
    if (typeof window === 'undefined') return;
    
    const mediaQuery = window.matchMedia(query);
    setMatches(mediaQuery.matches);
    
    const handler = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };
    
    mediaQuery.addEventListener('change', handler);
    
    return () => mediaQuery.removeEventListener('change', handler);
  }, [query]);
  
  // SSR中はfalseを返す
  if (!mounted) {
    return false;
  }
  
  return matches;
}

// 便利な定義済みクエリ
export function useIsMobile() {
  return useMediaQuery('(max-width: 767px)');
}

export function useIsTablet() {
  return useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
}

export function useIsDesktop() {
  return useMediaQuery('(min-width: 1024px)');
}

export function useIsTouchDevice() {
  return useMediaQuery('(hover: none) and (pointer: coarse)');
}

export function usePrefersDarkMode() {
  return useMediaQuery('(prefers-color-scheme: dark)');
}

export function usePrefersReducedMotion() {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
}
```

#### hooks/useTouch.ts
```typescript
// src/hooks/useTouch.ts
'use client';

import { useRef, useCallback, useEffect } from 'react';

interface TouchGesture {
  deltaX: number;
  deltaY: number;
  distance: number;
  direction: 'left' | 'right' | 'up' | 'down' | 'none';
  velocity: number;
  duration: number;
}

interface UseTouchOptions {
  onSwipe?: (gesture: TouchGesture) => void;
  onTap?: (event: TouchEvent) => void;
  onLongPress?: (event: TouchEvent) => void;
  threshold?: number;
  longPressDelay?: number;
}

export function useTouch({
  onSwipe,
  onTap,
  onLongPress,
  threshold = 50,
  longPressDelay = 500,
}: UseTouchOptions = {}) {
  const touchStart = useRef<{ x: number; y: number; time: number } | null>(null);
  const longPressTimer = useRef<NodeJS.Timeout | null>(null);
  
  const handleTouchStart = useCallback((event: TouchEvent) => {
    const touch = event.touches[0];
    touchStart.current = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now(),
    };
    
    // Long press timer
    if (onLongPress) {
      longPressTimer.current = setTimeout(() => {
        onLongPress(event);
      }, longPressDelay);
    }
  }, [onLongPress, longPressDelay]);
  
  const handleTouchEnd = useCallback((event: TouchEvent) => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
    
    if (!touchStart.current) return;
    
    const touch = event.changedTouches[0];
    const deltaX = touch.clientX - touchStart.current.x;
    const deltaY = touch.clientY - touchStart.current.y;
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    const duration = Date.now() - touchStart.current.time;
    const velocity = distance / duration;
    
    // Tap detection
    if (distance < threshold && duration < 200 && onTap) {
      onTap(event);
      return;
    }
    
    // Swipe detection
    if (distance >= threshold && onSwipe) {
      let direction: TouchGesture['direction'] = 'none';
      
      if (Math.abs(deltaX) > Math.abs(deltaY)) {
        direction = deltaX > 0 ? 'right' : 'left';
      } else {
        direction = deltaY > 0 ? 'down' : 'up';
      }
      
      onSwipe({
        deltaX,
        deltaY,
        distance,
        direction,
        velocity,
        duration,
      });
    }
    
    touchStart.current = null;
  }, [onSwipe, onTap, threshold]);
  
  const handleTouchMove = useCallback(() => {
    // Clear long press on move
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  }, []);
  
  const touchHandlers = {
    onTouchStart: handleTouchStart,
    onTouchEnd: handleTouchEnd,
    onTouchMove: handleTouchMove,
  };
  
  return touchHandlers;
}
```

#### hooks/useVibration.ts
```typescript
// src/hooks/useVibration.ts
'use client';

import { useCallback } from 'react';

export function useVibration() {
  const vibrate = useCallback((pattern: number | number[]) => {
    if (typeof window === 'undefined') return;
    
    if ('vibrate' in navigator) {
      navigator.vibrate(pattern);
    }
  }, []);
  
  const vibrateShort = useCallback(() => {
    vibrate(50);
  }, [vibrate]);
  
  const vibrateMedium = useCallback(() => {
    vibrate(100);
  }, [vibrate]);
  
  const vibrateLong = useCallback(() => {
    vibrate(200);
  }, [vibrate]);
  
  const vibratePattern = useCallback(() => {
    vibrate([100, 50, 100]);
  }, [vibrate]);
  
  return {
    vibrate,
    vibrateShort,
    vibrateMedium,
    vibrateLong,
    vibratePattern,
  };
}
```

### 4. モバイル専用コンポーネント作成

#### components/mobile/BottomNavigation.tsx
```typescript
// src/components/mobile/BottomNavigation.tsx
'use client';

import React from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { 
  Home, 
  TrendingUp, 
  Activity, 
  User,
  Search 
} from 'lucide-react';
import { useVibration } from '@/hooks/useVibration';

interface NavItem {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  href: string;
  params?: Record<string, string>;
}

const navItems: NavItem[] = [
  { icon: Home, label: 'ホーム', href: '/', params: { source: 'hacker-news' } },
  { icon: TrendingUp, label: 'トレンド', href: '/', params: { source: 'github' } },
  { icon: Search, label: '検索', href: '/search' },
  { icon: Activity, label: 'ダッシュボード', href: '/', params: { page: 'usage-dashboard' } },
  { icon: User, label: '設定', href: '/settings' },
];

export function BottomNavigation() {
  const router = useRouter();
  const pathname = usePathname();
  const { vibrateShort } = useVibration();
  
  const handleNavigation = (item: NavItem) => {
    vibrateShort();
    
    if (item.params) {
      const params = new URLSearchParams(item.params);
      router.push(`${item.href}?${params.toString()}`);
    } else {
      router.push(item.href);
    }
  };
  
  return (
    <nav className="mobile-nav dark:bg-gray-900 dark:border-gray-700">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;
        
        return (
          <button
            key={item.label}
            onClick={() => handleNavigation(item)}
            className={`
              flex flex-col items-center justify-center
              min-h-touch min-w-touch
              rounded-lg transition-colors duration-200
              touch-manipulation
              ${isActive 
                ? 'text-blue-600 dark:text-blue-400' 
                : 'text-gray-600 dark:text-gray-400'
              }
              active:scale-95 active:bg-gray-100 dark:active:bg-gray-800
            `}
            aria-label={item.label}
          >
            <Icon className="w-6 h-6 mb-1" />
            <span className="text-xs font-medium">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
```

#### components/mobile/MobileHeader.tsx
```typescript
// src/components/mobile/MobileHeader.tsx
'use client';

import React from 'react';
import { ArrowLeft, Menu, Search, MoreVertical } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface MobileHeaderProps {
  title: string;
  showBackButton?: boolean;
  showMenuButton?: boolean;
  showSearchButton?: boolean;
  onMenuClick?: () => void;
  onSearchClick?: () => void;
  rightActions?: React.ReactNode;
}

export function MobileHeader({
  title,
  showBackButton = false,
  showMenuButton = true,
  showSearchButton = true,
  onMenuClick,
  onSearchClick,
  rightActions,
}: MobileHeaderProps) {
  const router = useRouter();
  
  return (
    <header className="mobile-header dark:bg-gray-900 dark:border-gray-700">
      <div className="flex items-center justify-between px-4 py-3">
        {/* Left Section */}
        <div className="flex items-center">
          {showBackButton && (
            <button
              onClick={() => router.back()}
              className="btn-secondary p-2 mr-2"
              aria-label="戻る"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          )}
          
          {showMenuButton && !showBackButton && (
            <button
              onClick={onMenuClick}
              className="btn-secondary p-2 mr-3"
              aria-label="メニューを開く"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}
          
          <h1 className="text-responsive-lg font-bold text-gray-900 dark:text-white truncate">
            {title}
          </h1>
        </div>
        
        {/* Right Section */}
        <div className="flex items-center space-x-2">
          {showSearchButton && (
            <button
              onClick={onSearchClick}
              className="btn-secondary p-2"
              aria-label="検索"
            >
              <Search className="w-5 h-5" />
            </button>
          )}
          
          {rightActions || (
            <button
              className="btn-secondary p-2"
              aria-label="その他のオプション"
            >
              <MoreVertical className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
```

### 5. パフォーマンス最適化ユーティリティ

#### utils/performance.ts
```typescript
// src/utils/performance.ts

// 画像遅延読み込み
export function createIntersectionObserver(
  callback: (entries: IntersectionObserverEntry[]) => void,
  options?: IntersectionObserverInit
) {
  if (typeof window === 'undefined') return null;
  
  return new IntersectionObserver(callback, {
    rootMargin: '50px',
    threshold: 0.1,
    ...options,
  });
}

// バッテリー情報取得
export async function getBatteryInfo(): Promise<{
  level: number;
  charging: boolean;
  dischargingTime: number;
} | null> {
  if (typeof window === 'undefined') return null;
  
  try {
    // @ts-ignore - Battery API is experimental
    const battery = await navigator.getBattery?.();
    if (!battery) return null;
    
    return {
      level: battery.level,
      charging: battery.charging,
      dischargingTime: battery.dischargingTime,
    };
  } catch {
    return null;
  }
}

// ネットワーク状況取得
export function getNetworkInfo(): {
  effectiveType: string;
  downlink: number;
  saveData: boolean;
} | null {
  if (typeof window === 'undefined') return null;
  
  // @ts-ignore - Network Information API
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  
  if (!connection) return null;
  
  return {
    effectiveType: connection.effectiveType || 'unknown',
    downlink: connection.downlink || 0,
    saveData: connection.saveData || false,
  };
}

// 省電力モード検出
export function isPowerSaverMode(): boolean {
  const battery = getBatteryInfo();
  const network = getNetworkInfo();
  
  // バッテリー残量が少ない、または省データモード
  return (
    (battery && battery.level < 0.2 && !battery.charging) ||
    (network && network.saveData) ||
    false
  );
}

// FPS制限（省電力時）
export function requestAnimationFrameThrottled(
  callback: FrameRequestCallback,
  throttle: boolean = false
): number {
  if (throttle) {
    // 30 FPS に制限
    let lastTime = 0;
    const targetInterval = 1000 / 30;
    
    const throttledCallback: FrameRequestCallback = (time) => {
      if (time - lastTime >= targetInterval) {
        callback(time);
        lastTime = time;
      } else {
        requestAnimationFrame(throttledCallback);
      }
    };
    
    return requestAnimationFrame(throttledCallback);
  }
  
  return requestAnimationFrame(callback);
}

// メモリ使用量監視
export function getMemoryInfo(): {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
} | null {
  if (typeof window === 'undefined') return null;
  
  // @ts-ignore - performance.memory は実験的
  const memory = performance.memory;
  
  if (!memory) return null;
  
  return {
    usedJSHeapSize: memory.usedJSHeapSize,
    totalJSHeapSize: memory.totalJSHeapSize,
    jsHeapSizeLimit: memory.jsHeapSizeLimit,
  };
}

// レンダリング最適化
export function shouldReduceAnimations(): boolean {
  if (typeof window === 'undefined') return false;
  
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isPowerSaver = isPowerSaverMode();
  
  return prefersReducedMotion || isPowerSaver;
}
```

### 6. Next.js設定の最適化
```javascript
// next.config.js に追加
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 既存の設定...
  
  // モバイル最適化
  compress: true,
  poweredByHeader: false,
  
  // 画像最適化
  images: {
    domains: ['localhost'],
    formats: ['image/webp', 'image/avif'],
    deviceSizes: [375, 414, 640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },
  
  // experimental features
  experimental: {
    optimizeCss: true,
    optimizePackageImports: ['lucide-react', 'recharts'],
  },
  
  // Webpack最適化
  webpack: (config, { dev, isServer }) => {
    // モバイル用のバンドル最適化
    if (!dev && !isServer) {
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all',
          },
          common: {
            name: 'common',
            minChunks: 2,
            chunks: 'all',
            enforce: true,
          },
        },
      };
    }
    
    return config;
  },
  
  // ヘッダー最適化
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          // モバイル最適化ヘッダー
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          // 既存のセキュリティヘッダー...
        ],
      },
    ];
  },
};
```

### 7. テスト項目
1. モバイルデバイスでの初期表示速度確認（LCP < 1.5秒）
2. タッチジェスチャーの応答性確認
3. バッテリー消費量の測定
4. 省電力モードでの動作確認
5. 様々な画面サイズでのレイアウト確認
6. ネットワーク制限下でのパフォーマンス確認
7. アクセシビリティ（VoiceOver、TalkBack）確認
8. PWA としてのインストールと動作確認

### 8. 段階的移行計画
1. **Week 1**: CSS基盤とコンポーネントベースの移行
2. **Week 2**: モバイル専用フックとユーティリティの実装
3. **Week 3**: パフォーマンス最適化と微調整
4. **Week 4**: テストとデバッグ、ドキュメント化

## 完了条件
- [ ] 全コンポーネントがモバイルファーストで動作
- [ ] Lighthouse Mobile Score 95点以上
- [ ] Core Web Vitals モバイルで全指標クリア
- [ ] タッチジェスチャー完全対応
- [ ] バッテリー最適化実装
- [ ] アクセシビリティAAA準拠
- [ ] PWAとしての完璧な動作確認