# TASK-067: 段階的ブランチ統合戦略（修正版）

## タスク概要
`tmp-develop`の理想UI状態をベースとし、`dst-develop`への段階的統合を実行します。cherry-pick戦略によりUI品質を保持しながら全機能を統合します。

**重要**: tmp-developブランチでの安全な作業とUI確認プロセスを含みます。

## 新戦略アプローチ
**重要**: 
1. **tmp-develop (5017a80) を理想UI状態として設定**
2. **理想UI状態で最高品質のテストコードを作成**
3. **dst-developのコミットをタスクグループ単位で段階的cherry-pick**
4. **各段階でテスト実行とUI確認（スクリーンショット必須）**
5. **最終的にdst-develop (0b3a80b) 状態まで到達**

## 統合対象分析
- **理想UI状態**: tmp-develop (5017a80 "理想のUI状態")
- **統合目標**: dst-develop (0b3a80b) までの80+コミット
- **変更規模**: 93ファイル、18,652行追加、7,009行削除
- **主要変更**: PWA実装、モバイル対応、UIライブラリ統一、HTTPクライアント移行

## 変更予定ファイル
**段階的統合対象ファイル（93ファイル）**:
- `nook/frontend/src/components/ContentCard.tsx` 
- `nook/frontend/src/components/content/ContentRenderer.tsx`
- `nook/frontend/src/App.tsx`
- `nook/frontend/package.json`
- `nook/frontend/tailwind.config.js`
- `nook/frontend/vite.config.ts`
- PWA関連ファイル群
- モバイル対応コンポーネント群
- HTTPクライアント移行対象サービス群
- その他dst-developで変更された全ファイル

## 前提タスク
TASK-063～TASK-066（失敗した修正アプローチ）

## worktree名
worktrees/TASK-067-staged-integration

## 作業内容

### Phase 1: 理想UI状態の確認とテスト作成

#### 1. tmp-developブランチへの切り替え
```bash
# 理想UI状態のブランチに切り替え
git checkout tmp-develop
# 現在の状態確認
git log --oneline -5
```

#### 2. 理想UI状態の確認（スクリーンショット必須）

**重要**: tmp-develop切り替え直後は必ずスクリーンショットを撮影してユーザー確認を取る

1. **アプリケーション起動**
   ```bash
   # バックエンドとフロントエンドを起動
   # 起動方法はプロジェクトの設定に従う
   ```

2. **UI確認（スクリーンショット + MCP経由Playwright両方必須）**
   
   **A. スクリーンショット撮影**
   - **ライトモードでのスクリーンショット**
     - 記事番号「1」の青い背景表示（`bg-blue-100 text-blue-800`）
     - 丸い形状（`rounded-full`）
     - カードレイアウト（`rounded-lg shadow-md p-6`）
     - 全体的なレイアウトの美しさ

   - **ダークモードでのスクリーンショット**
     - 記事番号「1」の青い背景表示（`dark:bg-blue-900 dark:text-blue-300`）
     - ダークモード対応（`dark:bg-gray-800`）
     - カードの影とレイアウト
     - 全体的なダークモードの美しさ

   **B. MCP経由Playwrightアクセス（必須）**
   - MCP経由でPlaywrightを使用してアプリケーションにアクセス
   - UI要素の存在確認（記事番号、カードレイアウト等）
   - ライトモード・ダークモード両方での動作確認
   - DOM要素の構造とスタイル確認

3. **ユーザー確認プロセス（必須）**
   - スクリーンショットをユーザーに提示
   - 「この状態が美しいUI状態として正しいか」の確認を求める
   - **ユーザー承認取得まで後続作業は停止**
   - 承認後にPhase 2（テスト作成）に進む

4. **確認項目チェックリスト**
   - [ ] **スクリーンショット**: 記事番号「1」が青い丸いバッジで表示されている
   - [ ] **スクリーンショット**: カードに美しい影（shadow-md）と角丸（rounded-lg）が適用されている
   - [ ] **スクリーンショット**: ライトモードで適切な色合いになっている
   - [ ] **スクリーンショット**: ダークモードで適切な色合いになっている
   - [ ] **スクリーンショット**: 全体的なレイアウトが美しく整っている
   - [ ] **MCP経由Playwright**: UI要素の存在をPlaywrightで確認済み
   - [ ] **MCP経由Playwright**: ライト・ダークモード両方でのアクセス確認済み
   - [ ] **MCP経由Playwright**: DOM構造とスタイルの確認済み
   - [ ] **ユーザーからの承認を取得済み**

### Phase 2: 理想UI状態でのテスト作成（MCP経由）

**前提条件**: Phase 1でのユーザー承認が完了していること

#### ステップ1: 理想UI状態を完全に捉えるテスト作成

**重要**: UIテストはMCP経由のPlaywrightを使用

```typescript
// 理想UI状態テスト戦略
// - 記事番号「1」の表示確認
// - カードレイアウト（影、角丸、パディング）確認
// - ライトモード・ダークモード対応確認
// - 全体的なレイアウト美観確認
```

#### ステップ2: 包括的テストスイートの作成
1. **基本UI要素テスト**
   - 記事番号バッジの存在と表示確認
   - カードコンポーネントのスタイル確認
   
2. **レイアウトテスト**
   - カードの影（shadow-md）確認
   - 角丸（rounded-lg）確認
   - パディング（p-6）確認
   
3. **テーマ対応テスト**
   - ライトモードでの色合い確認
   - ダークモードでの色合い確認

### Phase 3: タスクグループ別段階的統合プロセス

**前提条件**: Phase 2でのテスト作成とユーザー承認が完了していること

**重要**: タスク単位で段階的cherry-pickを実行し、各段階でテストとUI確認を繰り返す

#### ステップ1: 統合計画の作成
```bash
# dst-developとの差分確認
git diff tmp-develop..dst-develop --stat

# コミット一覧の取得とタスクグループ分析
git log --oneline tmp-develop..dst-develop
```

#### ステップ2: タスクグループ別統合戦略

**統合優先順位（UI影響度順）**:

**Stage 1: HTTPクライアント移行（UI影響: 低）**
- TASK-001～006: グローバルHTTPクライアント移行
- TASK-007: 5chanサービス修正
- TASK-020～024: エラー処理・ブロックリスト・HTTP/2対応
- **理由**: バックエンド変更中心、UI影響最小

**Stage 2: PWA基盤実装（UI影響: 中）**  
- TASK-057: PWA基本実装
- TASK-054: モバイルメニューのスクロール制御
- **理由**: 新機能追加、既存UI変更最小

**Stage 3: UIライブラリ統一（UI影響: 高）**
- TASK-058: UIライブラリ統一（Material-UI → Tailwind CSS）
- TASK-055: タッチターゲットサイズ統一
- **理由**: UI変更大、慎重な統合必要

**Stage 4: アーキテクチャ改善（UI影響: 最高）**
- TASK-056: App.tsxコンポーネント分割
- TASK-059: Container Queries導入
- TASK-060: Vite SSR最適化
- TASK-061: モバイルファーストアーキテクチャ
- TASK-062: APIプロキシ設定修正
- **理由**: 大規模構造変更、最大注意必要

#### ステップ3: 各段階でのcherry-pick統合プロセス
**各Stage毎に以下を繰り返し**:

1. **タスクグループのコミット特定**
   ```bash
   # 例：Stage 1 (HTTPクライアント移行)のコミット抽出
   git log --oneline tmp-develop..dst-develop --grep="TASK-001\|TASK-002\|TASK-003\|TASK-004\|TASK-005\|TASK-006\|TASK-007\|TASK-020\|TASK-021\|TASK-022\|TASK-024"
   ```

2. **段階的cherry-pick実行**
   ```bash
   # worktreeで安全に作業
   git worktree add -b feature/TASK-067-staged-integration worktrees/TASK-067-staged-integration
   cd worktrees/TASK-067-staged-integration
   
   # tmp-developベースでタスクグループをcherry-pick
   git cherry-pick <commit-hash-1> <commit-hash-2> ...
   ```

3. **統合後テスト実行**
   ```bash
   # MCP経由でのPlaywrightテスト実行
   # 理想UI状態テストがpassすることを確認
   ```

4. **UI確認（スクリーンショット + MCP経由Playwright両方必須）**
   
   **A. スクリーンショット撮影**
   - ライトモード・ダークモードでのUI状態確認
   - 記事番号、カードレイアウトの表示確認
   - Stage統合後の全体的なUI品質確認
   
   **B. MCP経由Playwrightアクセス**
   - MCP経由でPlaywrightを使用してUI要素確認
   - 理想UI状態テストコードがpassすることを確認
   - DOM構造とスタイルの確認
   
   **C. ユーザー確認プロセス**
   - スクリーンショットとPlaywright結果の提示
   - ユーザー承認待ち（必須）
   - 承認後に次のStageに進む

5. **cherry-pick競合時の対処**
   ```bash
   # cherry-pick競合が発生した場合
   git status  # 競合ファイル確認
   # 手動で競合解決
   git add .
   git cherry-pick --continue
   
   # 解決困難な場合は該当コミットをスキップして後で対処
   git cherry-pick --skip
   ```

#### ステップ4: 各段階の完了条件
- [ ] **MCP経由Playwright**: テストコードが全て通過
- [ ] **スクリーンショット**: UI崩れがないことを視覚的に確認
- [ ] **MCP経由Playwright**: UI要素の存在とスタイルを確認
- [ ] **ユーザー承認**: スクリーンショット + Playwright結果の承認取得
- [ ] **ビルド**: npm run buildが成功
- [ ] **品質チェック**: Biomeチェックが通過

#### ステップ5: 統合完了の最終検証
```bash
# 全段階完了後の最終確認
npm run build
npx biome check --apply .
# MCP経由での全テスト実行
```

### Phase 4: 最終統合と統合完了検証

#### 1. 全Stage統合完了後の最終検証
```bash
# 全Stage完了後、worktreeからtmp-developへ統合
cd /Users/nana/workspace/nook  # メインディレクトリに戻る
git checkout tmp-develop
git merge worktrees/TASK-067-staged-integration --no-ff
```

#### 2. 最終UI確認プロセス（必須）
**重要**: 最終統合後は必ずスクリーンショットを取りユーザーが最終確認

1. **統合完了スクリーンショット撮影**
   - ライトモードでの最終UI状態
   - ダークモードでの最終UI状態  
   - 記事番号「1」の表示確認
   - カードレイアウトの最終確認
   - 全体的なUI品質の確認

2. **dst-develop状態との比較確認**
   - dst-develop (0b3a80b) 状態と同等機能を持つことの確認
   - 理想UI状態が保持されていることの確認

3. **最終ユーザー承認**
   - 統合完了スクリーンショットをユーザーに提示
   - dst-developへの全機能統合完了の確認
   - 理想UI状態維持の確認
   - 最終承認完了まで作業停止

#### 3. 統合完了条件チェック
- [ ] **全4Stage（HTTPクライアント、PWA、UIライブラリ、アーキテクチャ）の統合完了**
- [ ] MCP経由でのPlaywrightテストが全て通過
- [ ] 理想UI状態テストが全て通過  
- [ ] dst-develop (0b3a80b) と同等機能の実現
- [ ] ビルドが成功
- [ ] Biomeチェックが通過
- [ ] **最終スクリーンショット確認完了（ユーザー承認済み）**

#### 4. 最終検証と作業完了
- [ ] tmp-developブランチでの全テスト通過
- [ ] 理想UI状態の完全保持確認
- [ ] dst-develop機能の完全統合確認
- [ ] 品質チェック完了
- [ ] **最終UI確認プロセス完了**
- [ ] **統合戦略成功の確認**

## 重要注意事項

### 1. 段階的統合戦略
- **理想ベース**: tmp-develop (5017a80) を理想UI状態として設定
- **統合方法**: cherry-pick戦略による段階的統合
- **UI確認**: Stage統合毎にスクリーンショット撮影・ユーザー確認必須
- **作業停止**: ユーザー確認完了まで後続作業は実行しない
- **Stage毎の承認**: 各Stage完了前にユーザー承認が必要

### 2. cherry-pick統合の詳細
- **タスクグループ**: UI影響度別に4つのStageに分割
- **競合対処**: cherry-pick競合時は手動解決またはスキップ
- **コミット選択**: タスク関連コミットのみを選択的に統合
- **順次実行**: Stage 1→2→3→4の順で実行（並行実行禁止）

### 3. テスト実行方法
- **UIテスト**: MCP経由のPlaywrightのみ使用
- **理想状態テスト**: tmp-developの理想UI状態を基準とするテスト作成
- **品質チェック**: Biome使用（`npx biome check --apply .`）

### 4. UI確認プロセスの詳細
- **タイミング**: tmp-develop切り替え直後・Stage統合毎・最終統合後に必須
- **方法**: スクリーンショット撮影 + MCP経由Playwrightアクセス（両方必須）
- **内容**: ライト/ダークモード両方での確認
- **確認項目**: 記事番号表示、カードレイアウト、DOM構造、全体的なUI崩れ
- **承認**: スクリーンショット + Playwright結果でのユーザー承認が必要

### 5. 新戦略アプローチの理解
- **Phase 1**: tmp-developの理想UI状態を確認・承認取得
- **Phase 2**: 理想UI状態でMCP経由テストコード作成
- **Phase 3**: **4段階cherry-pick統合** - タスクグループ毎にStage統合実行
- **Phase 4**: 最終統合とdst-develop同等機能の実現確認

### 6. 段階的cherry-pick統合の重要性
- **一気統合の禁止**: 80+コミットを一度に統合することは禁止
- **Stage分割**: HTTPクライアント→PWA→UIライブラリ→アーキテクチャの順番
- **各Stage確認**: 統合毎にMCP経由Playwright + スクリーンショット + ユーザー承認
- **理想UI保持**: 各Stage統合後も理想UI状態テストがpassすることを確認
- **競合時対処**: cherry-pick競合は手動解決、困難な場合はスキップして後で対処
- **安全第一**: 確実性を優先し、時間がかかっても段階的に進める

### 7. 最終目標
- tmp-develop (5017a80) の理想UI状態を完全保持
- dst-develop (0b3a80b) の全機能を安全に統合
- UI崩れを防ぐスクリーンショット確認プロセスの確立
- cherry-pick戦略による段階的統合の成功実現

## 期待される結果

### UI品質の保持
- 全サービスで記事番号「1」が青い背景の丸で表示
- カードに美しい影（shadow-md）と角丸（rounded-lg）  
- ダークモードでの適切な背景色（gray-800）
- tmp-develop (5017a80) と同等の理想UI状態

### 機能統合の完了
- dst-develop (0b3a80b) の全機能を正常統合
- PWA機能の完全実装
- モバイルファーストアーキテクチャの実現
- UIライブラリ統一（Tailwind CSS）の完了
- HTTPクライアント移行の完了

### 統合戦略の成功
- **UI崩れのないtmp-developブランチ状態**
- cherry-pick戦略による段階的統合の成功
- 理想UI状態の完全保持
- 4つのStage統合プロセスの完遂
- MCP経由テストによる品質保証の確立
