# TASK-007: ContentCardのタイトルをクリック可能なリンクに変更

## タスク概要: ContentCardコンポーネントでタイトル全体をクリック可能なリンクにし、UXを改善する

## 変更予定ファイル:
- /Users/nana/workspace/nook/nook/frontend/src/components/ContentCard.tsx

## 前提タスク: なし

## worktree名: worktrees/TASK-007-title-link-implementation

## 作業内容:

### 1. ContentCardコンポーネントの修正

タイトル部分（行16-35）を以下のように変更：

```tsx
<div className="flex items-start justify-between mb-4">
  <h3 className="text-xl font-semibold text-gray-900 dark:text-white flex-1">
    {index !== undefined && (
      <span className="inline-block bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 text-sm font-medium px-2 py-1 rounded-full mr-3">
        {index + 1}
      </span>
    )}
    {item.url ? (
      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline inline-flex items-center"
      >
        {item.title}
        <ExternalLink size={16} className="ml-1 inline-block flex-shrink-0" />
      </a>
    ) : (
      <span>{item.title}</span>
    )}
  </h3>
</div>
```

### 2. 主な変更点

1. **条件分岐の追加**
   - `item.url`が存在する場合：タイトル全体をリンクにする
   - URLがない場合：通常のテキストとして表示

2. **リンクの実装**
   - タイトルテキスト全体を`<a>`タグで囲む
   - 外部リンクアイコンをタイトルの右側に統合（サイズを16pxに縮小）
   - `inline-flex items-center`でアイコンとテキストを適切に配置

3. **スタイリング**
   - リンクカラー：`text-blue-600 hover:text-blue-800`（ライトモード）
   - ダークモード：`dark:text-blue-400 dark:hover:text-blue-300`
   - ホバー時にアンダーライン表示：`hover:underline`
   - アイコンの余白：`ml-1`（左マージン1単位）
   - アイコンの収縮防止：`flex-shrink-0`

4. **右側の独立したリンクアイコンの削除**
   - 行25-34の独立したリンクアイコンを削除（タイトルに統合されたため不要）

### 3. テスト確認項目

1. **URLがある記事**
   - タイトル全体がクリック可能
   - ホバー時に適切なスタイル変更
   - 新しいタブで開く（target="_blank"）
   - 外部リンクアイコンが表示される

2. **URLがない記事**
   - タイトルは通常のテキスト
   - リンクアイコンが表示されない
   - クリックできない

3. **レスポンシブ対応**
   - モバイルデバイスでタップしやすい
   - 長いタイトルの折り返し処理

4. **ダークモード**
   - 適切な色の切り替え
   - 視認性の確保

### 4. 実装後の確認

1. フロントエンドの開発サーバーを起動：`npm run dev`
2. Hacker Newsセクションで実際の記事表示を確認
3. URLありとなしの両方の記事で動作確認
4. ダークモードとライトモードの両方でテスト