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