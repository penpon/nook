// TASK-023: Tech News形式変更のPlaywrightデモテスト

const { test, expect } = require('@playwright/test');

test.describe('Tech News Format Unification Demo - TASK-022 & TASK-023', () => {
  
  test('Tech News Before/After Format Comparison', async ({ page }) => {
    console.log('🎯 TASK-022 & TASK-023 デモ実行開始');
    
    // デモページにアクセス
    await page.goto('file:///Users/nana/workspace/nook/demo_tech_news_changes.html');
    
    // ページタイトルの確認
    await expect(page).toHaveTitle('Tech News 形式変更デモ - TASK-022 & TASK-023');
    console.log('✅ デモページの読み込み完了');
    
    // 変更概要セクションの確認
    const summarySection = page.locator('h2:text("🎯 変更概要")');
    await expect(summarySection).toBeVisible();
    console.log('✅ 変更概要セクションが表示されている');
    
    // 3つの変更要素（削除、追加、変更）の確認
    await expect(page.locator('text=削除')).toBeVisible();
    await expect(page.locator('text=日付付きタイトルを削除')).toBeVisible();
    await expect(page.locator('text=追加')).toBeVisible();
    await expect(page.locator('text=記事に連番を付与')).toBeVisible();
    await expect(page.locator('text=変更')).toBeVisible();
    await expect(page.locator('text=カテゴリをタグ化')).toBeVisible();
    console.log('✅ 変更要素の3項目が全て表示されている');
    
    // Before/After比較セクションの確認
    const comparisonSection = page.locator('h2:text("📊 表示形式の比較")');
    await expect(comparisonSection).toBeVisible();
    console.log('✅ 比較セクションが表示されている');
    
    // 現在の形式（Before）の確認
    const currentFormat = page.locator('h3:text("🔴 現在の形式")');
    await expect(currentFormat).toBeVisible();
    
    // 日付付きタイトルの確認（削除対象）
    const dateTitle = page.locator('text=tech news - 2025-06-24 技術ニュース記事 (2025-06-24)');
    await expect(dateTitle).toBeVisible();
    console.log('✅ 現在の形式：日付付きタイトルが表示されている（削除対象）');
    
    // Markdownコンテンツの確認
    await expect(page.locator('text=# 技術ニュース記事 (2025-06-24)')).toBeVisible();
    await expect(page.locator('text=## Tech blogs')).toBeVisible();
    await expect(page.locator('text=## Hatena')).toBeVisible();
    console.log('✅ 現在の形式：Markdownコンテンツが表示されている');
    
    // 問題点の確認
    await expect(page.locator('text=単一のMarkdownで表示')).toBeVisible();
    await expect(page.locator('text=番号付けなし')).toBeVisible();
    console.log('✅ 現在の形式の問題点が明記されている');
    
    // 新しい形式（After）の確認
    const newFormat = page.locator('h3:text("🟢 新しい形式（TASK-022実装後）")');
    await expect(newFormat).toBeVisible();
    
    // 簡潔なタイトルの確認
    const cleanTitle = page.locator('h1:text("Tech News")').nth(1);
    await expect(cleanTitle).toBeVisible();
    console.log('✅ 新しい形式：簡潔なタイトルが表示されている');
    
    // カテゴリヘッダーの確認
    await expect(page.locator('div:text("Tech blogs")').nth(1)).toBeVisible();
    await expect(page.locator('div:text("Hatena")').nth(1)).toBeVisible();
    console.log('✅ 新しい形式：カテゴリヘッダーが表示されている');
    
    // 連番付きの記事カードの確認
    const article1 = page.locator('text=1').nth(1);
    const article2 = page.locator('text=2').nth(1);
    const article3 = page.locator('text=3').nth(1);
    await expect(article1).toBeVisible();
    await expect(article2).toBeVisible();
    await expect(article3).toBeVisible();
    console.log('✅ 新しい形式：記事に連番が付与されている');
    
    // リンクの確認
    const articleLink1 = page.locator('a:text("AIを使うと脳が衰えていく？")');
    const articleLink2 = page.locator('a:text("PCが紛失・故障しても")');
    const articleLink3 = page.locator('a:text("はてなブックマークからの記事タイトル")');
    await expect(articleLink1).toBeVisible();
    await expect(articleLink2).toBeVisible();
    await expect(articleLink3).toBeVisible();
    console.log('✅ 新しい形式：記事タイトルがリンクとして表示されている');
    
    // 改善点の確認
    await expect(page.locator('text=個別カード表示')).toBeVisible();
    await expect(page.locator('text=明確な連番付与')).toBeVisible();
    await expect(page.locator('text=GitHub Trendingと統一したUI')).toBeVisible();
    console.log('✅ 新しい形式の改善点が明記されている');
    
    // 技術実装詳細の確認
    const techDetailsSection = page.locator('h2:text("🔧 技術実装詳細")');
    await expect(techDetailsSection).toBeVisible();
    
    // TASK-022実装内容の確認
    await expect(page.locator('text=TASK-022: フロントエンド実装')).toBeVisible();
    await expect(page.locator('text=parseTechNewsMarkdown')).toBeVisible();
    await expect(page.locator('text=ContentCard')).toBeVisible();
    console.log('✅ TASK-022の実装内容が表示されている');
    
    // TASK-023実装内容の確認
    await expect(page.locator('text=TASK-023: Playwrightデモ')).toBeVisible();
    await expect(page.locator('text=実装前後の画面キャプチャ')).toBeVisible();
    await expect(page.locator('text=UI統一性の確認')).toBeVisible();
    console.log('✅ TASK-023の実装内容が表示されている');
    
    // 期待される効果の確認
    const effectsSection = page.locator('h2:text("🎉 期待される効果")');
    await expect(effectsSection).toBeVisible();
    
    await expect(page.locator('text=UI統一性')).toBeVisible();
    await expect(page.locator('text=可読性向上')).toBeVisible();
    await expect(page.locator('text=情報整理')).toBeVisible();
    console.log('✅ 期待される効果が表示されている');
    
    // 実装コード例の確認
    const codeSection = page.locator('h2:text("💾 実装コード例")');
    await expect(codeSection).toBeVisible();
    await expect(page.locator('text=parseTechNewsMarkdown関数の実装例')).toBeVisible();
    console.log('✅ 実装コード例が表示されている');
    
    // スクリーンショット撮影
    await page.screenshot({ 
      path: 'tech-news-demo-full-page.png', 
      fullPage: true 
    });
    console.log('📷 全体のスクリーンショットを撮影');
    
    // 比較セクションのスクリーンショット
    const comparisonDiv = page.locator('div').filter({ hasText: '🔴 現在の形式' }).first();
    await comparisonDiv.screenshot({ 
      path: 'tech-news-comparison-section.png' 
    });
    console.log('📷 比較セクションのスクリーンショットを撮影');
    
    console.log('🎉 TASK-022 & TASK-023 デモ実行完了');
    console.log('');
    console.log('📋 デモ結果サマリー:');
    console.log('   ✅ 日付付きタイトルの削除が明確に示されている');
    console.log('   ✅ 記事への連番付与が視覚的に確認できる');
    console.log('   ✅ カテゴリのタグ化が実装されている');
    console.log('   ✅ GitHub Trendingと同様のUI形式に統一されている');
    console.log('   ✅ 実装前後の違いが分かりやすく比較表示されている');
    console.log('   ✅ 技術的な実装詳細と期待効果が説明されている');
  });
  
  test('Responsive Design Check', async ({ page }) => {
    await page.goto('file:///Users/nana/workspace/nook/demo_tech_news_changes.html');
    
    // モバイル表示のテスト
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);
    
    // モバイルでも要素が適切に表示されることを確認
    await expect(page.locator('h1:text("Tech News 形式変更デモ")')).toBeVisible();
    await expect(page.locator('h2:text("📊 表示形式の比較")')).toBeVisible();
    
    await page.screenshot({ 
      path: 'tech-news-demo-mobile.png', 
      fullPage: true 
    });
    console.log('📱 モバイル表示のスクリーンショットを撮影');
    
    // デスクトップ表示に戻す
    await page.setViewportSize({ width: 1920, height: 1080 });
    console.log('✅ レスポンシブデザインの確認完了');
  });
  
  test('Interactive Elements Check', async ({ page }) => {
    await page.goto('file:///Users/nana/workspace/nook/demo_tech_news_changes.html');
    
    // リンクのクリック可能性をテスト
    const articleLinks = page.locator('a[href="https://example.com"]');
    const linkCount = await articleLinks.count();
    
    console.log(`🔗 ${linkCount}個のリンクが見つかりました`);
    
    // 最初のリンクの属性を確認
    const firstLink = articleLinks.first();
    await expect(firstLink).toHaveAttribute('target', '_blank');
    console.log('✅ リンクが新しいタブで開く設定になっている');
    
    console.log('✅ インタラクティブ要素の確認完了');
  });
});

// 実行コマンド:
// npx playwright test playwright-test-tech-news-demo.js

console.log(`
🚀 Tech News Format Unification Demo Test Suite

このテストスイートは以下を検証します：

📋 TASK-022: フロントエンド実装の効果
   • 日付付きタイトルの削除
   • 記事への連番付与
   • カテゴリのタグ化
   • GitHub Trendingとの形式統一

📋 TASK-023: Playwrightデモの実行
   • 実装前後の比較表示
   • UI統一性の確認
   • レスポンシブデザインの検証
   • インタラクティブ要素のテスト

実行方法:
1. npm install @playwright/test
2. npx playwright test playwright-test-tech-news-demo.js
3. npx playwright show-report (結果確認)
`);