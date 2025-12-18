import React from 'react';
import ReactDOM from 'react-dom/client';
import { HydrationBoundary, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5分
    },
  },
});

// SSRからのデータをハイドレート
declare global {
  interface Window {
    __REACT_QUERY_STATE__?: unknown;
  }
}

const dehydratedState = window.__REACT_QUERY_STATE__;

ReactDOM.hydrateRoot(
  document.getElementById('root')!,
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <HydrationBoundary state={dehydratedState}>
          <App />
        </HydrationBoundary>
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
);
