# TASK-057: PWA基本実装（Progressive Web App対応）

## タスク概要
nookアプリケーションをPWA（Progressive Web App）として動作するよう基本実装を行う。manifest.json作成、Service Worker実装、オフライン機能、インストール可能な設定を含む。

## 変更予定ファイル
- nook/frontend/public/manifest.json（新規作成）
- nook/frontend/public/sw.js（新規作成）
- nook/frontend/index.html（PWA用メタタグ追加）
- nook/frontend/src/main.tsx（Service Worker登録）
- nook/frontend/vite.config.ts（PWAプラグイン設定）
- nook/frontend/package.json（PWA関連依存関係追加）
- nook/frontend/public/icons/（アイコン群作成）

## 前提タスク
TASK-056（App.tsx分割完了後）

## worktree名
worktrees/TASK-057-pwa-basic-implementation

## 作業内容

### 1. 依存関係の追加
```json
// package.jsonに追加
{
  "devDependencies": {
    "vite-plugin-pwa": "^0.17.4",
    "workbox-window": "^7.0.0"
  }
}
```

### 2. PWAアイコンの作成
```
nook/frontend/public/icons/
├── icon-72x72.png
├── icon-96x96.png
├── icon-128x128.png
├── icon-144x144.png
├── icon-152x152.png
├── icon-192x192.png
├── icon-384x384.png
├── icon-512x512.png
└── apple-touch-icon.png
```

### 3. manifest.jsonの作成
```json
{
  "name": "Nook - Tech News Dashboard",
  "short_name": "Nook",
  "description": "Comprehensive tech news dashboard aggregating content from multiple sources",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#3b82f6",
  "orientation": "portrait-primary",
  "scope": "/",
  "lang": "ja",
  "dir": "ltr",
  "categories": [
    "news",
    "productivity",
    "education"
  ],
  "icons": [
    {
      "src": "/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable any"
    }
  ],
  "shortcuts": [
    {
      "name": "Hacker News",
      "short_name": "HN",
      "description": "View Hacker News stories",
      "url": "/?source=hacker-news",
      "icons": [{ "src": "/icons/icon-96x96.png", "sizes": "96x96" }]
    },
    {
      "name": "GitHub Trending",
      "short_name": "GitHub",
      "description": "View GitHub trending repositories",
      "url": "/?source=github",
      "icons": [{ "src": "/icons/icon-96x96.png", "sizes": "96x96" }]
    },
    {
      "name": "Tech News",
      "short_name": "Tech",
      "description": "View latest tech news",
      "url": "/?source=tech-news",
      "icons": [{ "src": "/icons/icon-96x96.png", "sizes": "96x96" }]
    },
    {
      "name": "Usage Dashboard",
      "short_name": "Usage",
      "description": "View API usage dashboard",
      "url": "/?page=usage-dashboard",
      "icons": [{ "src": "/icons/icon-96x96.png", "sizes": "96x96" }]
    }
  ]
}
```

### 4. index.htmlの更新
```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    
    <!-- PWA Manifest -->
    <link rel="manifest" href="/manifest.json" />
    
    <!-- Theme color -->
    <meta name="theme-color" content="#3b82f6" />
    <meta name="theme-color" media="(prefers-color-scheme: dark)" content="#1f2937" />
    
    <!-- Apple PWA support -->
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="default" />
    <meta name="apple-mobile-web-app-title" content="Nook" />
    <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />
    
    <!-- Windows PWA support -->
    <meta name="msapplication-TileImage" content="/icons/icon-144x144.png" />
    <meta name="msapplication-TileColor" content="#3b82f6" />
    
    <!-- Description for better SEO and sharing -->
    <meta name="description" content="Comprehensive tech news dashboard aggregating content from GitHub, Hacker News, arXiv, and more" />
    
    <!-- Open Graph -->
    <meta property="og:title" content="Nook - Tech News Dashboard" />
    <meta property="og:description" content="Stay updated with the latest in tech across multiple sources" />
    <meta property="og:type" content="website" />
    <meta property="og:image" content="/icons/icon-512x512.png" />
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="Nook - Tech News Dashboard" />
    <meta name="twitter:description" content="Stay updated with the latest in tech across multiple sources" />
    <meta name="twitter:image" content="/icons/icon-512x512.png" />
    
    <title>Nook - Tech News Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### 5. Vite PWAプラグインの設定
```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'Nook - Tech News Dashboard',
        short_name: 'Nook',
        description: 'Comprehensive tech news dashboard aggregating content from multiple sources',
        theme_color: '#3b82f6',
        background_color: '#ffffff',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: 'icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            urlPattern: /^http:\/\/localhost:8000\/api\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 10,
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 // 24 hours
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'images-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 30 // 30 days
              }
            }
          },
          {
            urlPattern: /\.(?:js|css)$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'static-resources',
            }
          }
        ]
      },
      devOptions: {
        enabled: true,
        type: 'module'
      }
    })
  ],
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
  build: {
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name].[hash].js`,
        chunkFileNames: `assets/[name].[hash].js`,
        assetFileNames: `assets/[name].[hash].[ext]`
      }
    }
  }
});
```

### 6. Service Worker登録とアップデート通知
```typescript
// src/hooks/usePWA.ts（新規作成）
import { useState, useEffect } from 'react';
import { useRegisterSW } from 'virtual:pwa-register/react';

export function usePWA() {
  const [needRefresh, setNeedRefresh] = useState(false);
  const [offlineReady, setOfflineReady] = useState(false);
  
  const {
    needRefresh: [needRefreshSW, setNeedRefreshSW],
    offlineReady: [offlineReadySW, setOfflineReadySW],
    updateServiceWorker,
  } = useRegisterSW({
    onRegistered(r) {
      console.log('SW Registered: ' + r);
    },
    onRegisterError(error) {
      console.log('SW registration error', error);
    },
  });

  useEffect(() => {
    setNeedRefresh(needRefreshSW);
  }, [needRefreshSW]);

  useEffect(() => {
    setOfflineReady(offlineReadySW);
  }, [offlineReadySW]);

  const close = () => {
    setOfflineReady(false);
    setNeedRefresh(false);
    setOfflineReadySW(false);
    setNeedRefreshSW(false);
  };

  return {
    needRefresh,
    offlineReady,
    updateServiceWorker,
    close
  };
}
```

### 7. PWA更新通知コンポーネント
```typescript
// src/components/PWAUpdateNotification.tsx（新規作成）
import React from 'react';
import { usePWA } from '../hooks/usePWA';

export const PWAUpdateNotification: React.FC = () => {
  const { needRefresh, offlineReady, updateServiceWorker, close } = usePWA();

  if (!needRefresh && !offlineReady) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 max-w-sm">
      {offlineReady && (
        <div className="mb-2">
          <p className="text-sm text-gray-700 dark:text-gray-300">
            アプリがオフラインで利用可能になりました！
          </p>
        </div>
      )}
      
      {needRefresh && (
        <div className="mb-2">
          <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
            新しいバージョンが利用可能です。更新しますか？
          </p>
          <div className="flex space-x-2">
            <button
              onClick={() => updateServiceWorker(true)}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 touch-manipulation"
            >
              更新
            </button>
            <button
              onClick={close}
              className="bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1 rounded text-sm hover:bg-gray-400 dark:hover:bg-gray-500 touch-manipulation"
            >
              後で
            </button>
          </div>
        </div>
      )}
      
      {!needRefresh && offlineReady && (
        <button
          onClick={close}
          className="bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1 rounded text-sm hover:bg-gray-400 dark:hover:bg-gray-500 touch-manipulation"
        >
          閉じる
        </button>
      )}
    </div>
  );
};
```

### 8. App.tsxに更新通知を追加
```typescript
// App.tsx
import { PWAUpdateNotification } from './components/PWAUpdateNotification';

function App() {
  // 既存のコード...

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex">
      {/* 既存のレイアウト */}
      
      {/* PWA更新通知 */}
      <PWAUpdateNotification />
    </div>
  );
}
```

### 9. オフラインページの作成
```typescript
// src/components/OfflineFallback.tsx（新規作成）
import React from 'react';
import { WifiOff } from 'lucide-react';

export const OfflineFallback: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
      <div className="text-center p-8">
        <WifiOff className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          オフラインです
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          インターネット接続を確認してください
        </p>
        <button
          onClick={() => window.location.reload()}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 touch-manipulation"
        >
          再試行
        </button>
      </div>
    </div>
  );
};
```

### 10. インストールプロンプトの実装
```typescript
// src/hooks/useInstallPrompt.ts（新規作成）
import { useState, useEffect } from 'react';

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

export function useInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isInstallable, setIsInstallable] = useState(false);

  useEffect(() => {
    const handler = (e: BeforeInstallPromptEvent) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setIsInstallable(true);
    };

    window.addEventListener('beforeinstallprompt', handler as EventListener);

    return () => {
      window.removeEventListener('beforeinstallprompt', handler as EventListener);
    };
  }, []);

  const promptInstall = async () => {
    if (!deferredPrompt) return;

    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
      setDeferredPrompt(null);
      setIsInstallable(false);
    }
  };

  return {
    isInstallable,
    promptInstall
  };
}
```

### 11. テスト項目
1. Lighthouse PWA監査で90点以上を取得
2. manifest.jsonが正しく読み込まれることを確認
3. Service Workerが正常に登録されることを確認
4. オフライン時にキャッシュされたコンテンツが表示されることを確認
5. アプリのインストールプロンプトが表示されることを確認
6. インストール後、スタンドアロンモードで動作することを確認
7. アップデート通知が適切に表示されることを確認
8. iOS/AndroidでPWAとしてインストール可能であることを確認

### 12. 注意事項
- HTTPSでのみPWA機能が有効になる（開発時は localhost では動作）
- Service Workerのキャッシュ戦略により、開発時にキャッシュクリアが必要な場合がある
- iOS SafariでのPWA機能は制限があるため、実機での確認が重要

## 完了条件
- [ ] Lighthouse PWAスコア90点以上
- [ ] manifest.jsonが有効で、アプリがインストール可能
- [ ] Service Workerによるキャッシング機能動作
- [ ] オフライン時の基本機能提供
- [ ] PWA更新通知機能実装
- [ ] iOS/Android実機でのインストール確認済み