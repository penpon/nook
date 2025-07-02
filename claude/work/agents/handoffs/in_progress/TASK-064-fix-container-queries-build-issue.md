# TASK-064: Container Queries ビルド問題修正（緊急）

## タスク概要
TASK-063でContainer QueriesのCSSを復元しましたが、TailwindCSSビルドプロセスで@containerルールが除去される問題が判明。@containerルールを@layer utilities内で再定義し、確実にCSSに出力させます。

## 変更予定ファイル
- nook/frontend/src/index.css
- nook/frontend/package.json（プラグイン更新の可能性）

## 前提タスク
TASK-063（Container Queries基本システム復元完了）

## worktree名
worktrees/TASK-064-fix-container-queries-build

## 作業内容

### 1. 問題確認
現在の状況確認：
```bash
cd nook/frontend
npm run build
# dist/assets/index.*.cssで@containerルールが出力されていないことを確認
```

### 2. index.css修正

現在の@containerルールを@layer utilities内で再定義：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Container Queries基本設定 */
.container-query {
  container-type: inline-size;
}

.container-query-normal {
  container-type: normal;
}

.container-query-size {
  container-type: size;
}

/* カスタムコンテナサイズ */
.content-container {
  container-type: inline-size;
  container-name: content;
}

.card-container {
  container-type: inline-size;
  container-name: card;
}

.dashboard-container {
  container-type: inline-size;
  container-name: dashboard;
}

.sidebar-container {
  container-type: inline-size;
  container-name: sidebar;
}

/* Container Queries用のレスポンシブクラス - @layer utilities内で定義 */
@layer utilities {
  @container (min-width: 320px) {
    .cq-xs\:block { display: block; }
    .cq-xs\:grid { display: grid; }
    .cq-xs\:flex { display: flex; }
    .cq-xs\:grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
    .cq-xs\:text-sm { 
      font-size: 0.875rem; 
      line-height: 1.25rem; 
    }
    .cq-xs\:text-lg { 
      font-size: 1.125rem; 
      line-height: 1.75rem; 
    }
    .cq-xs\:text-xl { 
      font-size: 1.25rem; 
      line-height: 1.75rem; 
    }
    .cq-xs\:p-4 { 
      padding: 1rem; 
    }
  }

  @container (min-width: 384px) {
    .cq-sm\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .cq-sm\:flex-row { flex-direction: row; }
    .cq-sm\:text-base { 
      font-size: 1rem; 
      line-height: 1.5rem; 
    }
    .cq-sm\:p-4 { 
      padding: 1rem; 
    }
  }

  @container (min-width: 448px) {
    .cq-md\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .cq-md\:p-6 { 
      padding: 1.5rem; 
    }
    .cq-md\:text-lg { 
      font-size: 1.125rem; 
      line-height: 1.75rem; 
    }
    .cq-md\:text-xl { 
      font-size: 1.25rem; 
      line-height: 1.75rem; 
    }
    .cq-md\:text-2xl { 
      font-size: 1.5rem; 
      line-height: 2rem; 
    }
  }

  @container (min-width: 512px) {
    .cq-lg\:grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .cq-lg\:flex-row { flex-direction: row; }
    .cq-lg\:space-x-4 > :not([hidden]) ~ :not([hidden]) { 
      margin-left: 1rem; 
    }
  }

  @container (min-width: 640px) {
    .cq-xl\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .cq-xl\:p-8 { 
      padding: 2rem; 
    }
  }

  @container (min-width: 768px) {
    .cq-2xl\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  }
}

/* 古いブラウザ向けフォールバック */
@supports not (container-type: inline-size) {
  .card-container {
    /* ビューポートベースのフォールバック */
  }
  
  .cq-xs\:text-lg {
    font-size: 1.125rem;
    line-height: 1.75rem;
  }
  
  .cq-md\:text-xl {
    font-size: 1.25rem;
    line-height: 1.75rem;
  }
}
```

### 3. パッケージ更新（必要に応じて）
```bash
# Container Queriesプラグインを最新版に更新
npm update @tailwindcss/container-queries

# 依存関係確認
npm list @tailwindcss/container-queries
```

### 4. ビルド検証
```bash
# 完全なリビルド（キャッシュクリア含む）
rm -rf node_modules/.cache
rm -rf dist
npm run build

# 出力CSSで@containerルールの存在確認
grep -n "@container" dist/assets/index.*.css

# 開発サーバー再起動
npm run dev
```

### 5. 動作確認
#### ブラウザ開発者ツールでの確認
1. Elements タブでContainer Queriesクラスが適用されていることを確認
2. Computed styles でcontainer-typeプロパティが認識されていることを確認
3. cq-xs:*, cq-md:* クラスが実際にスタイルを適用していることを確認

#### UI確認
- カードが美しく表示されること
- レスポンシブ動作が正常であること
- 元のImage #1のような洗練されたレイアウトが復元されること

### 6. 追加修正（必要に応じて）
#### カード基本スタイル追加
@layer utilities内でカードの基本スタイルも定義：

```css
@layer utilities {
  /* 上記のContainer Queriesルール */
  
  /* カード基本スタイル */
  .card-base {
    @apply bg-white dark:bg-gray-800;
    @apply rounded-lg shadow-md;
    @apply border border-gray-200 dark:border-gray-700;
    @apply transition-shadow duration-200;
  }
  
  .card-hover {
    @apply hover:shadow-lg;
  }
}
```

### 7. 品質確認
- [ ] ビルドが成功する（`npm run build`）
- [ ] 出力CSSに@containerルールが含まれている
- [ ] ブラウザでContainer Queriesクラスが機能している
- [ ] UIが美しいカードレイアウトに復元されている
- [ ] レスポンシブ動作が正常

### 8. コミットメッセージ
```
TASK-064: Container Queries ビルド問題修正（緊急）

実装内容：
- @containerルールを@layer utilities内で再定義
- TailwindCSSビルドプロセスでの除去問題を解決
- Container Queriesクラス（cq-xs:*, cq-md:*）が正常に機能することを確認
- 美しいカードレイアウトの確実な復元

技術的な判断事項：
- @layer utilities使用でTailwindCSS処理パイプラインとの整合性確保
- カスタムContainer Queriesブレークポイント（320px, 384px等）を保持
- @tailwindcss/container-queriesプラグインとの併用で安定動作

プロンプト: TASK-063を実施しましたが相変わらずレイアウトは崩れています
原因を調査してください
```

## 重要注意事項
- **緊急修正**: Container Queriesが機能していない状態のため最優先
- **@layer utilities必須**: TailwindCSS 3.x系でカスタム@containerルールを確実に出力するため
- **完全リビルド必要**: キャッシュクリアを含む完全な再ビルドを実行
- **UI検証必須**: 修正後は必ず元の美しいレイアウトが復元されることを確認

## 期待される結果
- @containerルールがCSSに正しく出力される
- Container Queriesクラスが機能する
- カードレイアウトが美しく表示される
- Image #1のような洗練されたUIが復元される