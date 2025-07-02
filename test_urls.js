const { chromium } = require('playwright');

async function testUrls() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  
  const urls = [
    { name: 'Hacker News', url: 'http://localhost:5173/?source=hacker-news' },
    { name: 'GitHub', url: 'http://localhost:5173/?source=github' },
    { name: 'Tech News', url: 'http://localhost:5173/?source=tech-news' }
  ];

  for (const { name, url } of urls) {
    console.log(`\n========== Testing ${name} ==========`);
    console.log(`URL: ${url}`);
    
    const page = await context.newPage();
    
    // コンソールメッセージをキャプチャ
    const consoleMessages = [];
    page.on('console', msg => {
      consoleMessages.push({
        type: msg.type(),
        text: msg.text()
      });
    });
    
    // ネットワークリクエストを監視
    const apiRequests = [];
    page.on('request', request => {
      if (request.url().includes('/api/content/')) {
        apiRequests.push({
          url: request.url(),
          method: request.method(),
          headers: request.headers()
        });
      }
    });
    
    // レスポンスを監視
    const apiResponses = [];
    page.on('response', async response => {
      if (response.url().includes('/api/content/')) {
        const contentType = response.headers()['content-type'] || '';
        let responseBody = null;
        try {
          if (contentType.includes('json')) {
            responseBody = await response.json();
          } else {
            responseBody = await response.text();
          }
        } catch (e) {
          responseBody = 'Failed to parse response body';
        }
        
        apiResponses.push({
          url: response.url(),
          status: response.status(),
          statusText: response.statusText(),
          contentType: contentType,
          body: responseBody
        });
      }
    });
    
    try {
      // ページに移動
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      
      // 少し待機
      await page.waitForTimeout(3000);
      
      // ページタイトル
      const title = await page.title();
      console.log(`Page Title: ${title}`);
      
      // "No content available" メッセージの確認
      const noContentMessage = await page.locator('text="No content available for this source"').count();
      console.log(`"No content available" message found: ${noContentMessage > 0 ? 'Yes' : 'No'}`);
      
      // コンテンツの確認
      const mainContent = await page.locator('main').textContent();
      console.log(`Main content preview: ${mainContent.substring(0, 200)}...`);
      
      // コンソールエラー
      console.log('\nConsole Messages:');
      const errors = consoleMessages.filter(msg => msg.type === 'error');
      if (errors.length > 0) {
        errors.forEach(err => console.log(`  ERROR: ${err.text}`));
      } else {
        console.log('  No console errors');
      }
      
      // APIリクエスト
      console.log('\nAPI Requests:');
      if (apiRequests.length > 0) {
        apiRequests.forEach(req => {
          console.log(`  ${req.method} ${req.url}`);
          console.log(`  Accept: ${req.headers.accept || 'not specified'}`);
        });
      } else {
        console.log('  No API requests to /api/content/');
      }
      
      // APIレスポンス
      console.log('\nAPI Responses:');
      if (apiResponses.length > 0) {
        apiResponses.forEach(res => {
          console.log(`  ${res.status} ${res.statusText} - ${res.url}`);
          console.log(`  Content-Type: ${res.contentType}`);
          console.log(`  Response body type: ${typeof res.body}`);
          if (typeof res.body === 'object' && res.body !== null) {
            console.log(`  Response structure: ${JSON.stringify(Object.keys(res.body))}`);
          } else if (typeof res.body === 'string') {
            console.log(`  Response preview: ${res.body.substring(0, 100)}...`);
          }
        });
      } else {
        console.log('  No API responses');
      }
      
      // スクリーンショット
      await page.screenshot({ path: `screenshot_${name.toLowerCase().replace(' ', '_')}.png` });
      console.log(`\nScreenshot saved: screenshot_${name.toLowerCase().replace(' ', '_')}.png`);
      
    } catch (error) {
      console.log(`\nError testing ${name}: ${error.message}`);
    }
    
    await page.close();
  }
  
  await browser.close();
}

testUrls().catch(console.error);