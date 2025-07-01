# TASK-055: タップターゲットサイズの統一（アクセシビリティ向上）

## タスク概要
WCAG 2.1 AAガイドラインに準拠し、すべてのタップ可能要素を最小44×44pxに統一する。モバイルデバイスでの操作性を向上させ、アクセシビリティを改善する。

## 変更予定ファイル
- nook/frontend/src/App.tsx
- nook/frontend/src/components/ContentCard.tsx
- nook/frontend/src/components/NewsHeader.tsx
- nook/frontend/src/components/WeatherWidget.tsx
- nook/frontend/tailwind.config.js

## 前提タスク
なし（独立したタスク）

## worktree名
worktrees/TASK-055-touch-target-size-unification

## 作業内容

### 1. Tailwind CSSカスタムクラスの追加
tailwind.config.jsにタップターゲット用のユーティリティクラスを追加：

```javascript
// tailwind.config.js の theme.extend に追加
theme: {
  extend: {
    // 既存の設定...
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
    }
  }
}
```

### 2. App.tsxのボタン要素修正

#### モバイルメニューボタン
```tsx
// 現在: line 1432-1437
<button
  onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
  className="p-2 rounded-lg bg-white dark:bg-gray-800 shadow-md"
>

// 修正後:
<button
  onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
  className="min-h-touch min-w-touch p-2 rounded-lg bg-white dark:bg-gray-800 shadow-md flex items-center justify-center touch-manipulation"
  aria-label="メニューを開く"
>
```

#### サイドバーの各ボタン
```tsx
// ダッシュボードボタン（line 1364-1376付近）
<button
  onClick={() => {
    setCurrentPage('usage-dashboard');
    setIsMobileMenuOpen(false);
  }}
  className={`w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors min-h-touch touch-manipulation ${...}`}
>

// ソース選択ボタン（line 1383-1398付近）
<button
  key={source}
  onClick={() => {
    setSelectedSource(source);
    setCurrentPage('content');
    setIsMobileMenuOpen(false);
  }}
  className={`w-full text-left px-4 py-2 rounded-lg font-medium mb-2 transition-colors min-h-touch touch-manipulation ${...}`}
>

// ダークモード切り替えボタン（line 1404-1414付近）
<button
  onClick={() => setDarkMode(!darkMode)}
  className="w-full flex items-center justify-between px-4 py-2 rounded-lg font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/30 min-h-touch touch-manipulation"
>
```

### 3. ContentCard.tsxのリンク要素修正
```tsx
// ExternalLinkアイコンのサイズ調整（line 45-57付近）
{item.url ? (
  <a
    href={item.url}
    target="_blank"
    rel="noopener noreferrer"
    className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline inline-flex items-center min-h-touch touch-manipulation"
  >
    {item.title}
    <ExternalLink size={20} className="ml-2 inline-block flex-shrink-0" />
  </a>
) : (
  <span>{item.title}</span>
)}
```

### 4. 日付入力フィールドの修正
```tsx
// App.tsx line 1352-1359付近
<input
  type="date"
  value={format(selectedDate, 'yyyy-MM-dd')}
  max={format(new Date(), 'yyyy-MM-dd')}
  min={format(subDays(new Date(), 30), 'yyyy-MM-dd')}
  onChange={(e) => setSelectedDate(new Date(e.target.value))}
  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white min-h-touch touch-manipulation"
/>
```

### 5. WeatherWidget.tsxの調整（必要に応じて）
現在は情報表示のみですが、将来的にクリック可能にする場合の準備：

```tsx
// WeatherWidget.tsx line 33-43
<div className="bg-white rounded-lg shadow-md p-4 min-h-touch">
  <div className="flex items-center space-x-4">
    {getWeatherIcon(data.icon)}
    <div>
      <div className="text-2xl font-bold">{data.temperature}°C</div>
      <div className="text-gray-500">Current Weather</div>
    </div>
  </div>
</div>
```

### 6. touch-manipulationの追加
すべてのタップ可能要素にtouch-manipulationクラスを追加してタップ遅延を除去。

### 7. フォーカス可視性の改善
```css
/* Tailwindカスタムクラスとして追加 */
.focus-visible-custom {
  @apply focus:outline-none focus-visible:outline-2 focus-visible:outline-blue-500 focus-visible:outline-offset-2;
}
```

### 8. テスト項目
1. すべてのボタンが44×44px以上であることをデベロッパーツールで確認
2. モバイルデバイス（iOS/Android）での実際のタップ操作確認
3. キーボードナビゲーションでのフォーカス可視性確認
4. タップ遅延が除去されていることを確認（300msの遅延なし）
5. アクセシビリティスキャナー（axe-core等）でのチェック

### 9. 注意事項
- デザインの一貫性を保ちながらサイズ調整する
- 既存のレイアウトを破壊しないよう慎重に実装
- hover効果はタッチデバイスでは無効になることを考慮
- :hover疑似クラスはtouch:hoverに変更を検討

## 完了条件
- [ ] すべてのタップ可能要素が44×44px以上
- [ ] touch-manipulationが適用されタップ遅延が除去
- [ ] フォーカス状態が視覚的に分かりやすい
- [ ] iOS/Androidでのタップ操作性確認済み
- [ ] アクセシビリティガイドライン準拠確認済み