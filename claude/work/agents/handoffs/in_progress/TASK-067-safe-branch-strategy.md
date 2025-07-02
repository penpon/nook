# TASK-067: TDDによるレイアウト問題解決（修正版）

## タスク概要
RGRCサイクル（Red, Green, Refactor, Commit）を使用して、番号表示問題とレイアウト崩れを修正します。コミット`e6248a37`の美しいUI状態を正確に再現し、最終的に`0b3a80b96358db6651fc5660334677d613441ad3`に統合します。

## 正しいTDDアプローチ
**重要**: 
1. **まずe6248a37b7b91b33e7c34aac417fcfc0b75ed0e6にgit reset**
2. **その状態（美しいUI）でテストコードを書く**
3. **テストが通ることを確認**
4. **そのテストコードを保持しながら0b3a80b96358db6651fc5660334677d613441ad3に向けて統合**

## 解決すべき問題
1. 全サービスで記事番号「1」が表示されない
2. カードレイアウトの崩れ（影、パディング、角丸）
3. ダークモードでの表示問題

## 参考コミット
- **目標状態**: e6248a37b7b91b33e7c34aac417fcfc0b75ed0e6 （美しいUI状態を正確に再現）
- **最終統合先**: 0b3a80b96358db6651fc5660334677d613441ad3

## 変更予定ファイル
- `nook/frontend/tests/` 配下の新規テストファイル
- `nook/frontend/src/components/ContentCard.tsx` 
- `nook/frontend/src/components/content/ContentRenderer.tsx`
- その他e6248a37で変更されたファイル

## 前提タスク
TASK-063～TASK-066（失敗した修正アプローチ）

## worktree名
worktrees/TASK-067-tdd-layout-fix

## 作業内容

### Phase 1: 美しいUI状態へのリセット

#### 1. e6248a37への完全リセット
```bash
# 美しいUI状態にリセット
git reset --hard e6248a37b7b91b33e7c34aac417fcfc0b75ed0e6
```

#### 2. 美しいUI状態の確認
- 記事番号「1」の青い背景表示（`bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300`）
- 丸い形状（`rounded-full`）
- カードレイアウト（`rounded-lg shadow-md p-6`）
- ダークモード対応（`dark:bg-gray-800`）

### Phase 2: 美しい状態でのテスト作成

#### ステップ1: 美しいUI状態を捉えるテスト作成

```typescript
// nook/frontend/tests/beautiful-ui.spec.ts
import { test, expect } from '@playwright/test';

test.describe('美しいUI状態の再現（e6248a37）', () => {
  test.beforeEach(async ({ page }) => {
    // 実際のAPIを使用（バックエンド起動が必要）
    await page.goto('/?source=hacker-news');
    await page.waitForLoadState('networkidle');
  });

  test('記事番号1が青い丸いバッジで表示される', async ({ page }) => {
    // e6248a37の美しい状態を期待
    const numberBadge = page.locator('span.bg-blue-100.text-blue-800.rounded-full').filter({ hasText: '1' }).first();
    await expect(numberBadge).toBeVisible();
    
    // 丸い形状を確認
    const borderRadius = await numberBadge.evaluate(el => 
      window.getComputedStyle(el).borderRadius
    );
    expect(borderRadius).toMatch(/9999px|50%/);
  });

  test('カードに美しい影と角丸が適用される', async ({ page }) => {
    const card = page.locator('.bg-white.dark\\:bg-gray-800.rounded-lg.shadow-md').first();
    await expect(card).toBeVisible();
    
    // shadow-mdの確認
    const boxShadow = await card.evaluate(el => 
      window.getComputedStyle(el).boxShadow
    );
    expect(boxShadow).not.toBe('none');
    
    // rounded-lgの確認
    const borderRadius = await card.evaluate(el => 
      window.getComputedStyle(el).borderRadius
    );
    expect(borderRadius).toBe('8px');
  });
});
```

**このテストは通るはず（美しい状態）**

#### ステップ2: テスト実行と確認
```bash
# テストが通ることを確認
npm run test
```

### Phase 3: テスト駆動統合プロセス

#### ステップ1: 目標コミットとの差分確認
```bash
# 0b3a80b96358db6651fc5660334677d613441ad3との差分確認
git diff 0b3a80b96358db6651fc5660334677d613441ad3 -- nook/frontend/
```

#### ステップ2: テスト保護統合
```bash
# テストを保持しながら統合コミットに向けてrebase
git rebase 0b3a80b96358db6651fc5660334677d613441ad3
```

#### ステップ3: 統合後の検証
```bash
# 統合後もテストが通ることを確認
npm run test
npm run build
npm run lint
```

### Phase 4: 最終確認と完了

#### 1. 統合完了条件チェック
- [ ] beautiful-ui.spec.tsが全て通過
- [ ] 既存テストが全て通過  
- [ ] 0b3a80b96358db6651fc5660334677d613441ad3への統合完了
- [ ] ビルドが成功
- [ ] Lintが通過

#### 2. developブランチへのマージ
```bash
# developブランチにマージ
git checkout develop
git merge feature/TASK-067-tdd-layout-fix --no-ff
```

#### 3. 最終検証
- [ ] developブランチでの全テスト通過
- [ ] 美しいUI状態の保持確認
- [ ] 品質チェック完了

## 重要注意事項

### 1. 修正されたアプローチの理解
- **Phase 1**: e6248a37にリセットして美しい状態を確保
- **Phase 2**: 美しい状態でテストコードを作成（テスト通過を確認）
- **Phase 3**: テストを保持しながら0b3a80b96358db6651fc5660334677d613441ad3に統合
- **Phase 4**: 最終確認と完了

### 2. テスト駆動統合の重要性
- テストコードが美しいUI状態の保護者として機能
- 統合時にUIが破綻しないことを保証
- 将来の変更に対する回帰テストとして機能

### 3. 最終目標
- e6248a37の美しいUI状態を正確に捉えたテスト作成
- 0b3a80b96358db6651fc5660334677d613441ad3への安全な統合
- 美しいUI状態を保護するテストコード整備

## 期待される結果
- 全サービスで記事番号「1」が青い背景の丸で表示
- カードに美しい影（shadow-md）と角丸（rounded-lg）  
- ダークモードでの適切な背景色（gray-800）
- e6248a37と同等の美しいUI
- 0b3a80b96358db6651fc5660334677d613441ad3への正常統合