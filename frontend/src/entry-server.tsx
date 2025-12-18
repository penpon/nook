import { renderToString } from 'react-dom/server';
import { dehydrate, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StaticRouter } from 'react-router-dom/server';
import App from './App';

export async function render(url: string, context: unknown) {
  void context;

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
    },
  });

  // サーバーサイドでデータフェッチング
  // TODO: URLに基づいて必要なデータを事前フェッチ

  const html = renderToString(
    <StaticRouter location={url}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </StaticRouter>
  );

  // React Queryの状態をシリアライズ
  const dehydratedState = dehydrate(queryClient);
  const dehydratedStateJson = JSON.stringify(dehydratedState).replace(/</g, '\\u003c');

  const head = `
    <script>
      window.__REACT_QUERY_STATE__ = ${dehydratedStateJson}
    </script>
  `;

  return { html, head };
}
