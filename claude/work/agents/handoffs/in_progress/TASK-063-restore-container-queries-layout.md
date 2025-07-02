# TASK-063: Container Queriesベースレイアウトシステム完全復元

## タスク概要
コミット8a72b10でContainer Queriesベースの美しいカードレイアウトが削除され、UIが劣化しました。コミット0b36effの完全なContainer Queriesシステムを復元し、元の美しいUIを取り戻します。

## 変更予定ファイル
- nook/frontend/src/index.css
- nook/frontend/tailwind.config.js
- package.json（@tailwindcss/container-queriesプラグイン確認）

## 前提タスク
なし（緊急修復タスク）

## worktree名
worktrees/TASK-063-restore-container-queries-layout

## 作業内容

### 1. 問題の確認
- 現在のUIレイアウトがシンプルなリスト形式になっていることを確認
- Container Queriesシステムが削除されていることを確認

### 2. Container Queries完全復元
#### index.css復元
コミット0b36effのindex.cssを参照し、以下のContainer Queriesシステムを復元：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Container Queries基本設定 */
.container-query {
  container-type: inline-size;
}

.container-query-normal {
  container-type: normal;
}

.container-query-size {
  container-type: size;
}

/* カスタムコンテナサイズ */
.content-container {
  container-type: inline-size;
  container-name: content;
}

.card-container {
  container-type: inline-size;
  container-name: card;
}

.dashboard-container {
  container-type: inline-size;
  container-name: dashboard;
}

.sidebar-container {
  container-type: inline-size;
  container-name: sidebar;
}

/* Container Queries用のレスポンシブクラス */
@container (min-width: 320px) {
  .cq-xs\:block { display: block; }
  .cq-xs\:grid { display: grid; }
  .cq-xs\:flex { display: flex; }
  .cq-xs\:grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
  .cq-xs\:text-sm { font-size: 0.875rem; line-height: 1.25rem; }
}

@container (min-width: 384px) {
  .cq-sm\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .cq-sm\:flex-row { flex-direction: row; }
  .cq-sm\:text-base { font-size: 1rem; line-height: 1.5rem; }
  .cq-sm\:p-4 { padding: 1rem; }
}

@container (min-width: 448px) {
  .cq-md\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .cq-md\:p-6 { padding: 1.5rem; }
  .cq-md\:text-lg { font-size: 1.125rem; line-height: 1.75rem; }
}

@container (min-width: 512px) {
  .cq-lg\:grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .cq-lg\:flex-row { flex-direction: row; }
  .cq-lg\:space-x-4 > :not([hidden]) ~ :not([hidden]) { 
    margin-left: 1rem; 
  }
}

@container (min-width: 640px) {
  .cq-xl\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .cq-xl\:p-8 { padding: 2rem; }
}

@container (min-width: 768px) {
  .cq-2xl\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

/* 古いブラウザ向けフォールバック */
@supports not (container-type: inline-size) {
  .card-container {
    /* ビューポートベースのフォールバック */
  }
  
  .cq-xs\:text-lg {
    font-size: 1.125rem;
    line-height: 1.75rem;
  }
  
  .cq-md\:text-xl {
    font-size: 1.25rem;
    line-height: 1.75rem;
  }
}
```

#### tailwind.config.js復元
コミット0b36effのtailwind.config.jsを参照し、Container Queries設定を復元：

```javascript
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
    require('@tailwindcss/container-queries'), // 復元
  ],
};
```

### 3. 依存関係確認
```bash
# @tailwindcss/container-queriesプラグインがインストール済みか確認
npm list @tailwindcss/container-queries

# 未インストールの場合はインストール
npm install --save-dev @tailwindcss/container-queries
```

### 4. 動作確認
#### フロントエンド起動と確認
```bash
cd nook/frontend
npm run dev
```

#### Playwright検証
MCP経由でPlaywrightを使用し、以下を確認：
- カードレイアウトが美しく表示されること
- Container Queriesのレスポンシブ動作が機能すること
- 元のUI（Image #1のような中央寄せカード形式）が復元されること

### 5. 品質確認
- [ ] ビルドが成功する（`npm run build`）
- [ ] 全テストが成功する（存在する場合）
- [ ] Biome品質チェックが通過する（`npx biome check --apply .`）
- [ ] UIが元の美しいカード形式に復元されている
- [ ] Container Queriesのレスポンシブ動作が正常

### 6. コミットメッセージ
```
TASK-063: Container Queriesベースレイアウトシステム完全復元

実装内容：
- index.cssをContainer Queries版に復元（コミット0b36eff参照）
- tailwind.config.jsをContainer Queries設定に復元
- @tailwindcss/container-queriesプラグイン設定復元
- 美しいカードレイアウトシステム復活

技術的な判断事項：
- モバイルファーストアプローチは維持
- Container Queriesで高品質レスポンシブカード実現
- 既存コンポーネントのcq-*クラス活用
- ブラウザサポート状況良好のため安全に復元

プロンプト: 確実に前と同じUIを取り戻すことはできますか？
e6248a37b7b91b33e7c34aac417fcfc0b75ed0e6以前を参照すれば可能なはずです
```

## 重要注意事項
- **緊急修復タスク**：UIが劣化しているため最優先で実行
- **既存コンポーネント互換性**：ContentCard.tsx等は既にcq-*クラスを使用済み
- **参照コミット**：0b36eff（Container Queries導入完了時）の完全なCSSシステムを使用
- **検証必須**：復元後は元のImage #1のような美しいUIになることを確認

## 期待される結果
- 元の美しいカード形式レイアウト復元
- 中央寄せの洗練されたデザイン復活
- Container Queriesによる高品質レスポンシブ動作
- UIの劣化問題の完全解決