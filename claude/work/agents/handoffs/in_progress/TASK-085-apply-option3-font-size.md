# TASK-085: Option3文字サイズ適用実装

## タスク概要
モバイル版文字サイズのOption3（30%減）をtailwind.config.jsに適用し、プロジェクト全体の文字サイズを調整する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/tailwind.config.js`

## 前提タスク
- TASK-084（文字サイズ調整検討）完了

## worktree名
`worktrees/TASK-085-apply-option3-font-size`

## 作業内容

### 1. 現在の設定確認
tailwind.config.jsのtypographyセクションの現在の設定：
```javascript
typography: {
  DEFAULT: {
    css: {
      fontSize: "1.25rem",      // 20px
      p: {
        fontSize: "1.25rem",    // 20px
      },
      li: {
        fontSize: "1.25rem",    // 20px
      },
      h1: {
        fontSize: "2.25rem",    // 36px
      },
      h2: {
        fontSize: "1.875rem",   // 30px
      },
      h3: {
        fontSize: "1.5rem",     // 24px
      },
    },
  },
},
```

### 2. Option3設定への変更
以下の設定に変更する：
```javascript
typography: {
  DEFAULT: {
    css: {
      fontSize: "0.875rem",    // 14px (30%減)
      p: {
        fontSize: "0.875rem",  // 14px (30%減)
      },
      li: {
        fontSize: "0.875rem",  // 14px (30%減)
      },
      h1: {
        fontSize: "1.5rem",    // 24px (30%減)
      },
      h2: {
        fontSize: "1.25rem",   // 20px (30%減)
      },
      h3: {
        fontSize: "1.0rem",    // 16px (30%減)
      },
    },
  },
},
```

### 3. 実装手順

#### Step 1: 作業環境準備
1. developブランチでタスクファイルをpending/→in_progress/へ移動
2. 変更をコミット
3. worktreeを作成：`git worktree add -b feature/TASK-085-apply-option3-font-size worktrees/TASK-085-apply-option3-font-size`
4. 作業ディレクトリに移動：`cd worktrees/TASK-085-apply-option3-font-size`

#### Step 2: 実装作業
1. `tailwind.config.js`を開く
2. `typography.DEFAULT.css`セクションを確認
3. 各文字サイズをOption3の設定に変更
4. ファイルを保存

#### Step 3: 動作確認
1. 開発サーバーを起動：`npm run dev`
2. モバイル版での表示を確認
3. 主要な記事表示エリア（ContentCard）の文字サイズを確認
4. 各種コンテンツ（ニュース記事、GitHub情報、ArXiv要約）の表示を確認

#### Step 4: 品質確認
1. ビルドテスト：`npm run build`
2. 型チェック：`npm run type-check`（存在する場合）
3. リント：`npx biome check --apply .`
4. 全体的な表示の一貫性確認

### 4. 影響確認ポイント

#### 主要影響箇所
- **ContentCard.tsx**: 記事本文エリアの文字サイズ変更
- **ReactMarkdown**: Markdown形式コンテンツの表示変更

#### 確認すべき項目
1. **可読性**: 文字が小さくなっても読みやすさが保たれているか
2. **レイアウト**: 文字サイズ変更による行間やスペースの調整が必要か
3. **一貫性**: 全体的なデザインの統一性が保たれているか
4. **モバイル対応**: 特に小さなスマートフォンでの表示問題がないか

### 5. 完了条件
- [ ] tailwind.config.jsの文字サイズがOption3の設定に変更されている
- [ ] 開発サーバーで正常に動作する
- [ ] ビルドが成功する
- [ ] 全体的な表示に問題がない
- [ ] モバイル版での可読性が確保されている

### 6. 技術的な注意点
- **キャッシュクリア**: 変更後はブラウザのキャッシュクリアが必要な場合がある
- **hot reload**: 開発サーバーが自動的にリロードされることを確認
- **CSS再生成**: TailwindのCSS再生成が正しく行われることを確認

### 7. 変更詳細
以下の6つの値を変更：
1. `fontSize: "1.25rem"` → `"0.875rem"`
2. `p.fontSize: "1.25rem"` → `"0.875rem"`
3. `li.fontSize: "1.25rem"` → `"0.875rem"`
4. `h1.fontSize: "2.25rem"` → `"1.5rem"`
5. `h2.fontSize: "1.875rem"` → `"1.25rem"`
6. `h3.fontSize: "1.5rem"` → `"1.0rem"`

### 8. 品質管理
- 新規追加コードの警告をゼロに維持
- 既存の警告は対象外
- テストコードは変更しない
- 可読性を重視した実装

### 9. 完了後の確認
- developブランチにマージ
- worktreeの削除
- タスクファイルをcompleted/に移動