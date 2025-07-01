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