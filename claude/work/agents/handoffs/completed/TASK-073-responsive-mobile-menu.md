# TASK-073: レスポンシブモバイルメニューの緊急修正

## タスク概要
デバイスサイズによってサイドバーの表示・操作性に重大な問題が発生している。iPhone SEでは下部コンテンツが見えず、iPhone 11ではタッチイベントが機能しない。緊急修正を実施する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/hooks/useMobileMenu.ts`
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`
- `/Users/nana/workspace/nook/nook/frontend/src/components/layout/Sidebar.tsx`
- `/Users/nana/workspace/nook/playwright-tests/responsive-mobile-menu.spec.ts`（新規作成）

## 前提タスク
TASK-071

## worktree名
worktrees/TASK-073-responsive-mobile-menu

## 作業内容

### 1. 緊急修正: useMobileMenuフックの完全修正

#### 現在の問題
```typescript
// 問題のあるコード
document.body.style.overflow = "hidden";
document.body.style.position = "fixed";
document.body.style.top = `-${currentScrollY}px`;
document.body.style.width = "100%";
```

#### 修正内容
```typescript
export function useMobileMenu() {
	const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

	useEffect(() => {
		if (isMobileMenuOpen) {
			// バックグラウンドスクロール防止（サイドバー内は許可）
			document.documentElement.style.overflow = "hidden";
			document.body.style.overflow = "hidden";
			// position: fixedは使用しない
		} else {
			// スクロール復元
			document.documentElement.style.overflow = "";
			document.body.style.overflow = "";
		}

		return () => {
			document.documentElement.style.overflow = "";
			document.body.style.overflow = "";
		};
	}, [isMobileMenuOpen]);

	const toggleMobileMenu = () => {
		setIsMobileMenuOpen(prev => !prev);
	};

	const closeMobileMenu = () => {
		setIsMobileMenuOpen(false);
	};

	const openMobileMenu = () => {
		setIsMobileMenuOpen(true);
	};

	return {
		isMobileMenuOpen,
		setIsMobileMenuOpen,
		toggleMobileMenu,
		closeMobileMenu,
		openMobileMenu,
	};
}
```

### 2. App.tsxのサイドバー表示の最適化

#### 現在のコード確認
```typescript
{/* Sidebar - Hidden on mobile, overlay when menu is open */}
<div className={`
  flex-col w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 
  fixed h-screen overflow-y-auto z-20
  ${isMobileMenuOpen ? 'flex' : 'hidden md:flex'}
`}>
```

#### 修正内容
```typescript
{/* Sidebar - レスポンシブ対応強化 */}
<div className={`
  flex-col w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 
  fixed h-screen overflow-y-auto z-20
  ${isMobileMenuOpen ? 'flex' : 'hidden md:flex'}
`}>
```

現在のコードは適切だが、サイドバー内のスクロールが確実に動作するように確認。

### 3. Sidebar.tsxの小画面対応

#### 確認すべき項目
1. サイドバーの高さが画面に収まるか
2. スクロール可能な領域が適切に設定されているか
3. タッチターゲットのサイズが適切か

#### 修正内容
```typescript
return (
  <div className="sidebar-container h-full flex flex-col">
    {/* Header - 固定 */}
    <div className="p-3 md:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
      <div className="flex items-center space-x-2">
        <Layout className="w-5 h-5 md:w-6 md:h-6 text-blue-600 dark:text-blue-400" />
        <span className="text-lg md:text-xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </span>
      </div>
    </div>

    {/* Weather Widget - 固定 */}
    <div className="p-3 md:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
      <WeatherWidget />
    </div>

    {/* Date Selector - 固定 */}
    <div className="p-3 md:p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
      {/* 日付選択UI */}
    </div>

    {/* Navigation - スクロール可能 */}
    <nav className="flex-1 p-3 md:p-4 overflow-y-auto">
      {/* ナビゲーション項目 */}
    </nav>
  </div>
);
```

### 4. 包括的なレスポンシブテストの作成

#### テストファイル: `playwright-tests/responsive-mobile-menu.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

const deviceSizes = [
  { name: 'iPhone SE', width: 375, height: 667 },
  { name: 'iPhone 11', width: 414, height: 896 },
  { name: 'iPhone 12 Pro', width: 390, height: 844 },
  { name: 'Samsung Galaxy S21', width: 360, height: 800 },
];

test.describe('Responsive Mobile Menu', () => {
  deviceSizes.forEach(({ name, width, height }) => {
    test.describe(`${name} (${width}x${height})`, () => {
      test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.setViewportSize({ width, height });
      });

      test('should display all menu items with scrolling', async ({ page }) => {
        // ハンバーガーメニューを開く
        await page.click('[aria-label="メニューを開く"]');
        
        // サイドバーが表示されることを確認
        await expect(page.locator('.sidebar-container')).toBeVisible();
        
        // 全ての重要な項目が存在することを確認
        const importantItems = [
          'Usage Dashboard',
          'ArXiv',
          'GitHub Trending', 
          'Hacker News',
          'Tech News',
          'Business News',
          'Zenn',
          'Qiita',
          'Note',
          'Reddit',
          '4ch',
          '5ch',
          'Theme' // Theme toggleボタン
        ];
        
        for (const item of importantItems) {
          // 項目が存在することを確認
          await expect(page.locator(`text=${item}`)).toBeVisible();
          
          // 必要に応じてスクロールして項目を表示
          await page.locator(`text=${item}`).scrollIntoViewIfNeeded();
          
          // 項目がクリック可能であることを確認
          await expect(page.locator(`text=${item}`)).toBeEnabled();
        }
      });

      test('should allow theme toggle to work', async ({ page }) => {
        // ハンバーガーメニューを開く
        await page.click('[aria-label="メニューを開く"]');
        
        // Themeトグルまでスクロール
        await page.locator('text=Theme').scrollIntoViewIfNeeded();
        
        // 現在のテーマ状態を確認
        const themeButton = page.locator('text=Theme').locator('xpath=..');
        const isDarkMode = await themeButton.locator('text=Light Mode').isVisible();
        
        // テーマトグルをクリック
        await themeButton.click();
        
        // テーマが変更されたことを確認
        if (isDarkMode) {
          await expect(themeButton.locator('text=Dark Mode')).toBeVisible();
        } else {
          await expect(themeButton.locator('text=Light Mode')).toBeVisible();
        }
      });

      test('should maintain scroll position during navigation', async ({ page }) => {
        // ハンバーガーメニューを開く
        await page.click('[aria-label="メニューを開く"]');
        
        // 下部までスクロール
        await page.locator('text=Theme').scrollIntoViewIfNeeded();
        
        // スクロール位置を記録
        const scrollPosition = await page.locator('.sidebar-container nav').evaluate(el => el.scrollTop);
        
        // 項目をクリック
        await page.click('text=Reddit');
        
        // メニューが閉じることを確認
        await expect(page.locator('.sidebar-container')).toBeHidden();
        
        // 再度メニューを開く
        await page.click('[aria-label="メニューを開く"]');
        
        // スクロール位置がリセットされていることを確認（通常の動作）
        const newScrollPosition = await page.locator('.sidebar-container nav').evaluate(el => el.scrollTop);
        expect(newScrollPosition).toBe(0);
      });

      test('should handle rapid open/close operations', async ({ page }) => {
        // 高速でメニューを開閉
        for (let i = 0; i < 5; i++) {
          await page.click('[aria-label="メニューを開く"]');
          await expect(page.locator('.sidebar-container')).toBeVisible();
          
          await page.click('.bg-black.bg-opacity-50');
          await expect(page.locator('.sidebar-container')).toBeHidden();
        }
        
        // 最終的に正常な状態であることを確認
        await page.click('[aria-label="メニューを開く"]');
        await expect(page.locator('.sidebar-container')).toBeVisible();
        await expect(page.locator('text=Theme')).toBeVisible();
      });
    });
  });
});
```

### 5. パフォーマンス最適化

#### スクロール性能のテスト
```typescript
test('should maintain smooth scrolling performance', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
  await page.click('[aria-label="メニューを開く"]');
  
  // スクロール性能を測定
  const sidebar = page.locator('.sidebar-container nav');
  
  const startTime = Date.now();
  
  // 複数回のスクロール操作
  for (let i = 0; i < 10; i++) {
    await sidebar.hover();
    await page.mouse.wheel(0, 50);
    await page.waitForTimeout(10);
  }
  
  const endTime = Date.now();
  const duration = endTime - startTime;
  
  // スクロール操作が500ms以内で完了することを確認
  expect(duration).toBeLessThan(500);
  
  // 最終的にTheme toggleが見えることを確認
  await page.locator('text=Theme').scrollIntoViewIfNeeded();
  await expect(page.locator('text=Theme')).toBeVisible();
});
```

## 品質チェック項目
- [ ] 全デバイスサイズでビルドが成功する
- [ ] 全レスポンシブテストが通過する
- [ ] 自動品質チェック（Biome）が通過する
- [ ] iPhone SEで全メニュー項目にアクセス可能
- [ ] iPhone 11でTheme toggleが動作する
- [ ] サイドバー内のスクロールが滑らか
- [ ] バックグラウンドスクロールが適切に防止される

## 完了条件
- [ ] iPhone SE (375x667) で全メニュー項目が表示・操作可能
- [ ] iPhone 11 (414x896) でTheme toggleが正常に動作
- [ ] 全デバイスサイズでサイドバー内スクロールが機能
- [ ] 高速な開閉操作でも安定動作
- [ ] パフォーマンステストが全て通過

## 検証方法
1. 複数デバイスサイズでの手動テスト
2. Playwrightでの自動テスト
3. 実際のデバイスでの動作確認（可能であれば）
4. パフォーマンス測定とボトルネック特定

## 緊急度
**HIGH** - 小画面デバイスでアプリケーションが部分的に使用不可能