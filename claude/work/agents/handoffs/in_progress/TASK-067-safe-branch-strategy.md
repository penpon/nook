# TASK-067: TDDによるレイアウト問題解決（修正版）

## タスク概要
RGRCサイクル（Red, Green, Refactor, Commit）を使用して、番号表示問題とレイアウト崩れを修正します。コミット`e6248a37`の美しいUI状態を正確に再現し、最終的に`0b3a80b96358db6651fc5660334677d613441ad3`に統合します。

## 正しいTDDアプローチ
**重要**: 現在のdevelopブランチ（問題がある状態）→ コミット`e6248a37`（美しいUI状態）を再現する

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

### Phase 1: e6248a37の詳細分析

#### 1. 参考実装の完全な分析
```bash
# e6248a37の変更内容を詳細調査
git show e6248a37:nook/frontend/src/components/ContentCard.tsx
git show e6248a37:nook/frontend/src/components/content/ContentRenderer.tsx
git diff HEAD..e6248a37 -- nook/frontend/src/components/
```

#### 2. 美しいUI状態の特定
- 記事番号「1」の青い背景表示（`bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300`）
- 丸い形状（`rounded-full`）
- カードレイアウト（`rounded-lg shadow-md p-6`）
- ダークモード対応（`dark:bg-gray-800`）

### Phase 2: 正しいTDDサイクル

#### サイクル1: RED段階 - e6248a37状態を期待するテスト

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

**このテストは失敗するはず（現在の状態は美しくない）**

#### サイクル2: GREEN段階 - e6248a37の実装を適用

```typescript
// ContentCard.tsxをe6248a37の状態に修正
// 1. 記事番号バッジのスタイル修正
// 2. カードレイアウトのクラス修正
// 3. ダークモード対応の確認
```

#### サイクル3: REFACTOR段階 - コード整理

- e6248a37の実装をベースに最適化
- 重複コードの除去
- 型安全性の向上

### Phase 3: 統合と検証

#### 1. 全体テストの実行
```bash
npm run test
npm run build
npm run lint
```

#### 2. 品質チェック
- Biome自動修正
- 新規警告の解消
- パフォーマンス確認

### Phase 4: 最終統合

#### 1. 0b3a80b96358db6651fc5660334677d613441ad3への統合準備
```bash
# 目標コミットとの差分確認
git diff 0b3a80b96358db6651fc5660334677d613441ad3 -- nook/frontend/

# 必要に応じてrebase/merge戦略を決定
```

#### 2. 統合実行
- developブランチにマージ
- コンフリクト解決
- 最終検証

## 重要注意事項

### 1. 正しいTDDの理解
- **RED**: e6248a37の美しい状態を期待するテストを書く（失敗する）
- **GREEN**: e6248a37の実装をそのまま適用してテストを通す
- **REFACTOR**: コードを整理して品質向上

### 2. 参考実装の使い方
- e6248a37の実装をそのまま採用（コピペOK）
- 現在の状態との差分を正確に把握
- テストが通ることを最優先

### 3. 最終目標
- e6248a37の美しいUI状態を完全再現
- 0b3a80b96358db6651fc5660334677d613441ad3への統合
- 将来の変更に強いテストコード整備

## 期待される結果
- 全サービスで記事番号「1」が青い背景の丸で表示
- カードに美しい影（shadow-md）と角丸（rounded-lg）  
- ダークモードでの適切な背景色（gray-800）
- e6248a37と同等の美しいUI
- 0b3a80b96358db6651fc5660334677d613441ad3への正常統合