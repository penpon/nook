const { chromium } = require('playwright');

async function testUrls() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const urls = [
    { name: 'Hacker News', url: 'http://localhost:5173/?source=hacker-news' },
    { name: 'GitHub', url: 'http://localhost:5173/?source=github' },
    { name: 'Tech News', url: 'http://localhost:5173/?source=tech-news' }
  ];

  for (const { name, url } of urls) {
    console.log(`\n========== Testing ${name} ==========`);
    console.log(`URL: ${url}`);
    
    // コンソールメッセージをキャプチャ
    const consoleMessages = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleMessages.push(msg.text());
      }
    });
    
    // APIリクエストとレスポンスを監視
    const apiInfo = [];
    
    page.on('response', async response => {
      if (response.url().includes('/api/content/')) {
        const contentType = response.headers()['content-type'] || '';
        let bodyPreview = '';
        try {
          const text = await response.text();
          bodyPreview = text.substring(0, 200);
        } catch (e) {
          bodyPreview = 'Failed to read body';
        }
        
        apiInfo.push({
          url: response.url(),
          status: response.status(),
          contentType: contentType,
          bodyPreview: bodyPreview
        });
      }
    });
    
    try {
      // ページに移動
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 10000 });
      
      // 少し待機
      await page.waitForTimeout(2000);
      
      // "No content available" メッセージの確認
      const noContentExists = await page.locator('text="No content available for this source"').count();
      console.log(`"No content available" displayed: ${noContentExists > 0 ? 'YES' : 'NO'}`);
      
      // コンソールエラー
      if (consoleMessages.length > 0) {
        console.log('Console errors:');
        consoleMessages.forEach(err => console.log(`  - ${err}`));
      } else {
        console.log('Console errors: None');
      }
      
      // API情報
      if (apiInfo.length > 0) {
        console.log('API calls to /api/content/:');
        apiInfo.forEach(info => {
          console.log(`  - ${info.status} ${info.url}`);
          console.log(`    Content-Type: ${info.contentType}`);
          console.log(`    Body preview: ${info.bodyPreview}`);
        });
      } else {
        console.log('API calls: No requests to /api/content/');
      }
      
    } catch (error) {
      console.log(`Error: ${error.message}`);
    }
    
    // クリーンアップ
    consoleMessages.length = 0;
    apiInfo.length = 0;
  }
  
  await browser.close();
}

testUrls().catch(console.error);