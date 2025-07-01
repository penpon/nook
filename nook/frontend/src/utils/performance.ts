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