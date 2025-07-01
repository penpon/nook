# TASK-006: 論文表示の番号付けとレイアウト修正

## タスク概要
BlenderFusion論文表示画面で発生している以下の問題を修正：
1. 通し番号が1から始まっていない（現在は2から開始）
2. summaryセクションが見切れている表示問題

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx` (1610-1617行目)
- `/Users/nana/workspace/nook/nook/frontend/src/components/ContentCard.tsx` (60-62行目)

## 前提タスク
なし（独立タスク）

## worktree名
worktrees/TASK-006-paper-display-fixes

## 作業内容

### 1. 番号付けロジック修正（App.tsx）

**問題分析**:
- `parseAcademicPapersMarkdown`でArXivカテゴリヘッダーが最初に追加される
- 論文表示時に配列の`index`をそのまま使用するため、カテゴリヘッダー=1、最初の論文=2になる
- 他ソース（zenn、qiita等）では`item.metadata?.articleNumber - 1`を使用して正しい番号付け

**修正方針**:
1610-1617行目の論文表示ロジックを以下に修正：

```typescript
// 修正前
else {
  return processedItems.map((item, index) => (
    <ContentCard 
      key={index} 
      item={item} 
      darkMode={darkMode} 
      index={index}  // 問題の箇所
    />
  ));
}

// 修正後
else {
  return processedItems.map((item, index) => (
    <ContentCard 
      key={index} 
      item={item} 
      darkMode={darkMode} 
      index={item.metadata?.articleNumber ? item.metadata.articleNumber - 1 : undefined}
    />
  ));
}
```

### 2. Summary表示制限実装（ContentCard.tsx）

**問題分析**:
- 60-62行目のMarkdown表示部分で縦制限がない
- 長いsummaryが画面に収まらず見切れる

**修正方針**:
以下の機能を実装：
- summary部分に初期高さ制限（例：300px）
- 「続きを読む/折りたたむ」ボタン追加
- 展開/折りたたみ状態の管理

**実装アプローチ**:
```typescript
// useState追加
const [isExpanded, setIsExpanded] = useState(false);

// Markdown表示部分の修正
<div className={`prose prose-lg max-w-none w-full overflow-x-auto ${darkMode ? 'prose-invert' : ''} ${!isExpanded ? 'max-h-[300px] overflow-hidden' : ''}`}>
  <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.content}</ReactMarkdown>
</div>

// 展開ボタン追加（長いコンテンツの場合のみ表示）
{item.content.length > 500 && (
  <button 
    onClick={() => setIsExpanded(!isExpanded)}
    className="mt-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 text-sm"
  >
    {isExpanded ? '折りたたむ' : '続きを読む'}
  </button>
)}
```

## 検証方法

### 1. 番号付け確認
- 論文一覧で最初の論文が「1」から始まることを確認
- カテゴリヘッダーに番号が表示されないことを確認

### 2. Summary表示確認
- 長いsummaryで「続きを読む」ボタンが表示されることを確認
- ボタンクリックで展開/折りたたみが正常動作することを確認

## 技術的注意点

### App.tsx修正時
- 他のソース（github、zenn、qiita等）の番号付けロジックに影響しないよう注意
- `item.metadata?.articleNumber`が存在しない場合はundefinedを渡す

### ContentCard.tsx修正時
- useStateのimportを追加
- ダークモード対応を継続
- レスポンシブデザインを維持