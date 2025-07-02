# TASK-067: TDDによるレイアウト問題解決

## タスク概要
RGRCサイクル（Red, Green, Refactor, Commit）を使用して、番号表示問題とレイアウト崩れを修正します。過去の美しいUIコミット（e6248a37）を参考にしながら、テストファーストで実装を進めます。

## 解決すべき問題
1. 全サービスで記事番号「1」が表示されない
2. カードレイアウトの崩れ（影、パディング、角丸）
3. ダークモードでの表示問題

## 参考コミット
- **美しいUI状態**: e6248a37b7b91b33e7c34aac417fcfc0b75ed0e6 （参考実装として確認）

## 変更予定ファイル
- `nook/frontend/tests/layout.spec.ts` (新規テストファイル)
- `nook/frontend/src/components/` 配下の各コンポーネント
- `nook/frontend/playwright.config.ts` (Playwright設定)

## 前提タスク
TASK-063～TASK-066（失敗した修正アプローチ）

## worktree名
worktrees/TASK-067-tdd-layout-fix

## 作業内容

### Phase 1: 環境準備とTODOリスト作成

#### 1. 参考実装の確認
```bash
# 美しいUIの状態を確認（参考として）
git show e6248a37b7b91b33e7c34aac417fcfc0b75ed0e6 --name-only
git show e6248a37b7b91b33e7c34aac417fcfc0b75ed0e6:nook/frontend/src/components/
```

#### 2. TODOリスト作成
以下の機能を小さく分割してリスト化：
- [ ] 記事番号「1」の表示テスト作成
- [ ] カードレイアウト（影・角丸）のテスト作成
- [ ] ダークモードでの背景色テスト作成
- [ ] サイドバー固定幅（256px）のテスト作成
- [ ] 各サービス固有のヘッダー表示テスト作成

### Phase 2: RGRCサイクルによる実装

#### サイクル1: 記事番号表示の修正

**RED段階**
```typescript
// nook/frontend/tests/article-number.spec.ts
import { test, expect } from '@playwright/test';

test.describe('記事番号表示', () => {
  test('Hacker Newsで記事番号1が青い背景で表示される', async ({ page }) => {
    await page.goto('/?source=hacker-news');
    await page.waitForLoadState('networkidle');
    
    // 記事番号「1」を含む要素を探す
    const numberBadge = page.locator('.bg-blue-100, .bg-blue-900').filter({ hasText: '1' }).first();
    await expect(numberBadge).toBeVisible();
    
    // 丸い形状（rounded-full）であることを確認
    const borderRadius = await numberBadge.evaluate(el => 
      window.getComputedStyle(el).borderRadius
    );
    expect(borderRadius).toMatch(/9999px|50%/);
  });
  
  test('Tech Newsで記事番号1が表示される', async ({ page }) => {
    await page.goto('/?source=tech-news');
    await page.waitForLoadState('networkidle');
    
    const numberBadge = page.locator('.bg-blue-100, .bg-blue-900').filter({ hasText: '1' }).first();
    await expect(numberBadge).toBeVisible();
  });
});
```
**実行して失敗を確認**

**GREEN段階**
- テストを通すための最小限の実装
- 各サービスのコンポーネントに番号表示を追加
- ベタ書きでも構わない（動くことが最優先）

**REFACTOR段階**
- 番号表示の共通コンポーネント化
- スタイルの統一
- 重複コードの除去

**COMMIT段階**
```
RED: 記事番号表示テスト追加 - TASK-067
GREEN: 記事番号表示の最小実装 - TASK-067
REFACTOR: 番号表示コンポーネント共通化 - TASK-067
```

#### サイクル2: カードレイアウトの修正

**RED段階**
```typescript
// nook/frontend/tests/card-layout.spec.ts
import { test, expect } from '@playwright/test';

test.describe('カードレイアウト', () => {
  test('カードに適切な影と角丸が適用される', async ({ page }) => {
    await page.goto('/?source=hacker-news');
    await page.waitForLoadState('networkidle');
    
    const card = page.locator('.bg-gray-800').first();
    
    // shadow-mdが適用されていることを確認
    const shadow = await card.evaluate(el => 
      window.getComputedStyle(el).boxShadow
    );
    expect(shadow).not.toBe('none');
    expect(shadow).toMatch(/rgba?\(/);
    
    // rounded-lg (8px)が適用されていることを確認
    const borderRadius = await card.evaluate(el => 
      window.getComputedStyle(el).borderRadius
    );
    expect(borderRadius).toBe('8px');
    
    // パディング p-6 (24px)が適用されていることを確認
    const padding = await card.evaluate(el => 
      window.getComputedStyle(el).padding
    );
    expect(padding).toBe('24px');
  });
});
```

**GREEN段階**
- カードコンポーネントにTailwindクラスを追加
- `rounded-lg shadow-md p-6` の適用

**REFACTOR段階**
- カードスタイルの統一
- 共通スタイルの抽出

**COMMIT段階**
```
RED: カードレイアウトテスト追加 - TASK-067
GREEN: カードスタイルの最小実装 - TASK-067
REFACTOR: カードスタイル統一 - TASK-067
```

#### サイクル3: ダークモード対応

**RED段階**
```typescript
// nook/frontend/tests/dark-mode.spec.ts
import { test, expect } from '@playwright/test';

test.describe('ダークモード', () => {
  test.beforeEach(async ({ page }) => {
    await page.evaluate(() => {
      document.documentElement.classList.add('dark');
    });
  });
  
  test('ダークモードでカード背景がgray-800になる', async ({ page }) => {
    await page.goto('/?source=hacker-news');
    await page.waitForLoadState('networkidle');
    
    const card = page.locator('.dark\\:bg-gray-800').first();
    const bgColor = await card.evaluate(el => 
      window.getComputedStyle(el).backgroundColor
    );
    expect(bgColor).toBe('rgb(31, 41, 55)'); // gray-800
  });
});
```

**以降、同様のサイクルで実装**

### Phase 3: 統合テストの作成

全体レイアウトが正しく表示されることを確認する統合テストを作成：

```typescript
// nook/frontend/tests/integration-layout.spec.ts
import { test, expect } from '@playwright/test';

test.describe('統合レイアウトテスト', () => {
  test('全体レイアウトが正しく表示される', async ({ page }) => {
    await page.goto('/');
    
    // サイドバー
    const sidebar = page.locator('.w-64');
    await expect(sidebar).toBeVisible();
    const width = await sidebar.evaluate(el => 
      window.getComputedStyle(el).width
    );
    expect(width).toBe('256px');
    
    // メインコンテンツ
    const mainContent = page.locator('.flex-1');
    await expect(mainContent).toBeVisible();
    
    // ナビゲーション項目
    const navItems = ['Hacker News', 'Tech News', 'Business News', 'Zenn'];
    for (const item of navItems) {
      await expect(page.locator(`text=${item}`)).toBeVisible();
    }
  });
});
```

### Phase 4: 品質確認

#### 完了前必須チェック
- [ ] ビルドが成功する
- [ ] 全テストが成功する
- [ ] 自動品質チェック（Biome）が通過する
- [ ] 新規追加したコードの警告を解消した

#### テスト実行コマンド
```bash
# Playwrightインストール
npm install -D @playwright/test
npx playwright install

# テスト実行
npm run test:layout

# ヘッドフルモードで確認
npx playwright test --headed
```

## 重要注意事項

### TDD原則の厳守
1. **必ずテストを先に書く**（RED）
2. **テストを通す最小限の実装**（GREEN）
3. **動作を保ちながらリファクタリング**（REFACTOR）
4. **各段階でコミット**（COMMIT）

### 三角測量の活用
- 2つ以上のテストケースから一般化を導く
- 例：Hacker NewsとTech Newsの番号表示テストから共通コンポーネントを抽出

### 参考実装の使い方
- 過去のコミット（e6248a37）は「どう動くべきか」の参考
- コピペではなく、テストが要求する実装を行う

## 期待される結果
- 全サービスで記事番号「1」が青い背景の丸で表示
- カードに美しい影（shadow-md）と角丸（rounded-lg）
- ダークモードでの適切な背景色（gray-800）
- 左サイドバーの固定幅（256px）
- RGRCサイクルによる品質の高い実装
- 将来の変更に強いテストコード