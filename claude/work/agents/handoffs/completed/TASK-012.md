# TASK-012: TypeScript型定義修正（フロントエンドエラー緊急修正）

## タスク概要
フロントエンドの白い画面エラーの根本原因であるContentItem型のmetadata プロパティ未定義問題を修正

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/types.ts`

## 前提タスク
なし（最優先緊急修正）

## worktree名
worktrees/TASK-012-typescript-types-fix

## 作業内容

### 1. 現状確認
- ContentItem型定義の現在の状態を確認
- 各parserファイルでのmetadata使用状況を再確認（techNewsParser, businessNewsParser, zennParser等）
- ContentRenderer.tsx:93でのmetadata アクセス箇所を確認

### 2. 型定義修正
- ContentItem型にmetadataプロパティを追加
- metadata の型定義を以下の形式で設定：
  ```typescript
  metadata?: {
    articleNumber?: number;
    feedName?: string;
  }
  ```

### 3. 動作確認
- TypeScript コンパイルエラーが解消されることを確認
- フロントエンド開発サーバーが正常起動することを確認
- ブラウザで白い画面が解消されることを確認

### 4. 品質管理
- [ ] ビルドが成功する（`npm run build`）
- [ ] 型チェックが成功する（`npm run type-check` または `tsc --noEmit`）
- [ ] 既存テストが成功する
- [ ] ブラウザでページが正常表示される

### 技術的注意事項
- metadata プロパティはOptional（?）として定義（既存コードとの互換性確保）
- 各プロパティも Optional として定義（段階的マイグレーション対応）
- 既存のparserファイルの修正は不要（型定義のみで解決）

### 期待される結果
- フロントエンドの白い画面エラーが解消される
- TypeScript の型安全性が確保される
- すべてのparserファイルとContentRenderer.tsx の型エラーが解消される