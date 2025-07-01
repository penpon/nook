# TASK-060: Vite SSRとパフォーマンス最適化（React Server Components代替）

## タスク概要
ViteベースでSSR（サーバーサイドレンダリング）を実装し、初期表示高速化とSEO改善を実現する。React Server Componentsの代替として、Vite SSRプラグインを使用してサーバーサイドでのデータフェッチングとレンダリングを最適化する。

## 変更予定ファイル
- nook/frontend/package.json（SSR関連パッケージ追加）
- nook/frontend/vite.config.ts（SSR設定追加）
- nook/frontend/server.ts（新規作成：SSRサーバー）
- nook/frontend/src/entry-client.tsx（新規作成）
- nook/frontend/src/entry-server.tsx（新規作成）
- nook/frontend/src/App.tsx（SSR対応に修正）
- nook/frontend/src/components/（SSR対応修正）
- nook/frontend/src/utils/ssr.ts（新規作成：SSRユーティリティ）

## 前提タスク
TASK-059（Container Queries導入完了後）

## worktree名
worktrees/TASK-060-vite-ssr-optimization

## 作業内容

### 1. 依存関係の追加
```json
// package.json に追加
{
  "dependencies": {
    "@fastify/middie": "^8.3.0",
    "fastify": "^4.26.0",
    "fastify-static": "^4.7.0"
  },
  "devDependencies": {
    "@types/node": "^20.11.0",
    "cross-env": "^7.0.3",
    "tsx": "^4.7.0"
  },
  "scripts": {
    "dev": "vite",
    "dev:ssr": "tsx server.ts",
    "build": "vite build",
    "build:client": "vite build --outDir dist/client",
    "build:server": "vite build --ssr src/entry-server.tsx --outDir dist/server",
    "build:ssr": "npm run build:client && npm run build:server",
    "preview": "vite preview",
    "serve:ssr": "cross-env NODE_ENV=production tsx server.ts"
  }
}
```

### 2. Vite SSR設定
```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig(({ command, mode }) => {
  const isSSR = mode === 'ssr'
  
  return {
    plugins: [
      react(),
      VitePWA({
        // 既存のPWA設定を維持
        registerType: 'autoUpdate',
        // SSRモードでは無効化
        disable: isSSR,
      })
    ],
    
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    
    ssr: {
      noExternal: ['react-query', 'axios'],
      target: 'node',
      format: 'esm',
    },
    
    build: {
      target: 'es2022',
      minify: !isSSR,
      sourcemap: true,
    },
    
    optimizeDeps: {
      include: ['react', 'react-dom', 'react-router-dom'],
    },
  }
})
```

### 3. SSRサーバー実装
```typescript
// server.ts
import Fastify from 'fastify'
import fastifyStatic from '@fastify/static'
import middie from '@fastify/middie'
import { createServer as createViteServer } from 'vite'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const isProduction = process.env.NODE_ENV === 'production'

async function createServer() {
  const app = Fastify({
    logger: true,
    requestTimeout: 30000,
  })

  await app.register(middie)

  let vite
  
  if (!isProduction) {
    // 開発モード
    vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'custom'
    })
    
    app.use(vite.middlewares)
  } else {
    // 本番モード
    app.register(fastifyStatic, {
      root: path.join(__dirname, 'dist/client'),
      prefix: '/',
    })
  }

  app.get('*', async (request, reply) => {
    const url = request.url

    try {
      let template, render
      
      if (!isProduction) {
        // 開発モードでテンプレートを読み込み
        template = await vite.transformIndexHtml(url, 
          `<!DOCTYPE html>
          <html lang="ja">
            <head>
              <meta charset="UTF-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1.0" />
              <title>Nook</title>
              <!--app-head-->
            </head>
            <body>
              <div id="root"><!--app-html--></div>
              <script type="module" src="/src/entry-client.tsx"></script>
            </body>
          </html>`
        )
        
        render = (await vite.ssrLoadModule('/src/entry-server.tsx')).render
      } else {
        // 本番モード
        template = await fs.readFile(
          path.join(__dirname, 'dist/client/index.html'),
          'utf-8'
        )
        
        render = (await import('./dist/server/entry-server.js')).render
      }

      // SSRレンダリング
      const { html: appHtml, head } = await render(url, {
        request,
        reply,
      })

      // HTMLテンプレートに挿入
      const html = template
        .replace('<!--app-head-->', head)
        .replace('<!--app-html-->', appHtml)

      reply.type('text/html').send(html)
    } catch (e) {
      if (!isProduction && vite) {
        vite.ssrFixStacktrace(e)
      }
      console.error(e)
      reply.code(500).send(e.message)
    }
  })

  const port = process.env.PORT || 3000
  await app.listen({ port: +port, host: '0.0.0.0' })
  
  console.log(`Server running at http://localhost:${port}`)
}

createServer()
```

### 4. エントリーポイント作成

#### entry-client.tsx
```typescript
// src/entry-client.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5分
    },
  },
})

// SSRからのデータをハイドレート
const dehydratedState = window.__REACT_QUERY_STATE__

ReactDOM.hydrateRoot(
  document.getElementById('root')!,
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
)
```

#### entry-server.tsx
```typescript
// src/entry-server.tsx
import React from 'react'
import { renderToString } from 'react-dom/server'
import { StaticRouter } from 'react-router-dom/server'
import { QueryClient, QueryClientProvider, dehydrate } from 'react-query'
import App from './App'

export async function render(url: string, context: any) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
    },
  })

  // サーバーサイドでデータフェッチング
  // TODO: URLに基づいて必要なデータを事前フェッチ
  
  const html = renderToString(
    <StaticRouter location={url}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </StaticRouter>
  )

  // React Queryの状態をシリアライズ
  const dehydratedState = dehydrate(queryClient)
  
  const head = `
    <script>
      window.__REACT_QUERY_STATE__ = ${JSON.stringify(dehydratedState)}
    </script>
  `

  return { html, head }
}
```

### 5. SSRユーティリティ
```typescript
// src/utils/ssr.ts
export const isServer = typeof window === 'undefined'
export const isClient = !isServer

// SSR対応のuseEffect
export function useIsomorphicLayoutEffect(
  effect: React.EffectCallback,
  deps?: React.DependencyList
) {
  if (isServer) {
    return
  }
  
  React.useLayoutEffect(effect, deps)
}

// SSR対応のLocalStorage
export const storage = {
  getItem: (key: string): string | null => {
    if (isServer) return null
    return localStorage.getItem(key)
  },
  
  setItem: (key: string, value: string): void => {
    if (isServer) return
    localStorage.setItem(key, value)
  },
  
  removeItem: (key: string): void => {
    if (isServer) return
    localStorage.removeItem(key)
  },
}

// SSR対応のwindowサイズ取得
export function useWindowSize() {
  const [size, setSize] = React.useState({
    width: isServer ? 1024 : window.innerWidth,
    height: isServer ? 768 : window.innerHeight,
  })

  React.useEffect(() => {
    if (isServer) return

    const handleResize = () => {
      setSize({
        width: window.innerWidth,
        height: window.innerHeight,
      })
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return size
}
```

### 6. App.tsxの修正
```typescript
// src/App.tsx
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { isServer } from '@/utils/ssr'
import MainLayout from '@/components/MainLayout'
import Dashboard from '@/pages/Dashboard'
import NotFound from '@/pages/NotFound'

// 遅延読み込みコンポーネントのSSR対応
const LazyUsageDashboard = React.lazy(() => 
  isServer 
    ? import('@/components/UsageDashboard') 
    : import('@/components/UsageDashboard')
)

function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Dashboard />} />
        <Route 
          path="usage" 
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <LazyUsageDashboard />
            </React.Suspense>
          } 
        />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default App
```

### 7. パフォーマンス最適化
```typescript
// src/utils/performance.ts
import { isServer } from './ssr'

// クリティカルCSSの抽出
export function extractCriticalCSS(html: string): string {
  // TODO: critical CSSの抽出ロジック
  return ''
}

// リソースヒントの生成
export function generateResourceHints(assets: string[]): string {
  return assets.map(asset => {
    if (asset.endsWith('.js')) {
      return `<link rel="modulepreload" href="${asset}" />`
    }
    if (asset.endsWith('.css')) {
      return `<link rel="preload" href="${asset}" as="style" />`
    }
    return ''
  }).join('\n')
}

// 画像の最適化
export function optimizeImageSrc(src: string, options?: {
  width?: number
  quality?: number
}): string {
  if (isServer) return src
  
  // TODO: 画像最適化サービスとの連携
  return src
}
```

### 8. テスト項目
1. SSRでの初期レンダリング速度確認（目標: FCP < 1.5秒）
2. ハイドレーションエラーが発生しないことを確認
3. React Queryのデータプリフェッチが機能することを確認
4. PWA機能がSSRと共存できることを確認
5. SEOメタデータが適切にレンダリングされることを確認
6. クライアントサイドルーティングが正常に動作することを確認

## 完了条件
- [ ] Vite SSR環境構築完了
- [ ] 初期表示速度改善（FCP < 1.5秒、LCP < 2.5秒）
- [ ] SEOメタデータ適切レンダリング
- [ ] ハイドレーションエラー解消
- [ ] 既存機能の完全互換性確保
- [ ] PWA機能との共存確認