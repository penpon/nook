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

  // パフォーマンステスト
  test.describe('Performance Tests', () => {
    test('should maintain smooth scrolling performance', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
      await page.goto('/');
      
      // ハンバーガーメニューを開く
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
  });
});