/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      minHeight: {
        'touch': '44px', // WCAG推奨最小サイズ
        'touch-large': '48px', // より大きなターゲット
      },
      minWidth: {
        'touch': '44px',
        'touch-large': '48px',
      },
      spacing: {
        'touch': '44px',
        'touch-large': '48px',
      },
      // Container Queries用の設定
      containers: {
        'xs': '20rem',
        'sm': '24rem',
        'md': '28rem',
        'lg': '32rem',
        'xl': '36rem',
        '2xl': '42rem',
        '3xl': '48rem',
        '4xl': '56rem',
        '5xl': '64rem',
        '6xl': '72rem',
        '7xl': '80rem',
      },
      colors: {
        blue: {
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
        }
      },
      animation: {
        'spin': 'spin 1s linear infinite',
        'pulse': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: '100%',
            width: '100%',
            fontSize: '1.25rem',
            p: {
              fontSize: '1.25rem',
            },
            li: {
              fontSize: '1.25rem',
            },
            h1: {
              fontSize: '2.25rem',
            },
            h2: {
              fontSize: '1.875rem',
            },
            h3: {
              fontSize: '1.5rem',
            },
            img: {
              maxWidth: '100%',
            },
            pre: {
              fontSize: '1.125rem',
              overflowX: 'auto',
            },
            code: {
              fontSize: '1.125rem',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            },
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/container-queries'), // 追加
  ],
};
