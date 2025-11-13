# TASK-001: サブカテゴリ別通し番号リセット修正

## タスク概要
GitHub Trending、note、4chan、5chan、Hacker News、Academic Papersの6つのサービスで、現在カテゴリ関係なく連続した通し番号が付与されている問題を修正し、各サブカテゴリごとに番号をリセットするように実装する。

## 変更予定ファイル
- `/Users/nana/workspace/nook/nook/frontend/src/App.tsx`

## 前提タスク
なし

## worktree名
worktrees/TASK-001-subcategory-numbering-reset

## 作業内容

### 現在の問題
以下のサービスでサブカテゴリ関係なく連続番号が付与されている：

**❌ 修正対象:**
- GitHub Trending：言語別リセットなし（repositoryCount++で連続）
- note：ハッシュタグ別リセットなし（articleCount++で連続）
- 4chan：板別リセットなし（threadCount++で連続）
- 5chan：板別リセットなし（threadCount++で連続）
- Hacker News：連続番号（articleCount++で連続）
- Academic Papers：連続番号（indexで連続）

**✅ 正常動作（参考）:**
- Tech News、Business News、Zenn、Qiita、Reddit（metadata.articleNumberを使用）

### 修正方針
パース時修正方式を採用し、各パーサー関数内でmetadata.articleNumberを埋め込む実装に統一する。

### 具体的な修正内容

#### 1. parseGitHubTrendingMarkdown関数（16行目〜）
**現在:** 番号管理なし
**修正後:** 各言語（currentLanguage）別に番号をリセット
```javascript
// 言語が変わるたびにリポジトリ番号をリセット
if (line.startsWith('## ') && line.length > 3) {
  repositoryNumber = 1; // 言語別に番号をリセット
}
// リポジトリ追加時
metadata: {
  source: 'github',
  articleNumber: repositoryNumber++
}
```

#### 2. parseNoteArticlesMarkdown関数（566行目〜）
**現在:** レンダリング時にarticleCount++で連続番号
**修正後:** 既にカテゴリ別にarticleNumber管理済み（374行目）だが、レンダリングロジックを修正
```javascript
// レンダリングロジックでmetadata.articleNumberを使用するよう修正
```

#### 3. parseFourchanThreadsMarkdown関数（855行目〜）
**現在:** 番号管理なし
**修正後:** 各板（currentCategory）別に番号をリセット
```javascript
// 板が変わるたびにスレッド番号をリセット
if (line.startsWith('## /') && line.includes('/')) {
  threadNumber = 1; // 板別に番号をリセット
}
// スレッド追加時
metadata: {
  source: '4chan',
  articleNumber: threadNumber++
}
```

#### 4. parseFivechanThreadsMarkdown関数（954行目〜）
**現在:** 番号管理なし
**修正後:** 各板（currentCategory）別に番号をリセット
```javascript
// 板が変わるたびにスレッド番号をリセット
if (line.startsWith('## ') && line.includes('(/') && line.includes('/)')） {
  threadNumber = 1; // 板別に番号をリセット
}
// スレッド追加時
metadata: {
  source: '5chan',
  articleNumber: threadNumber++
}
```

#### 5. parseAcademicPapersMarkdown関数（675行目〜）
**現在:** 番号管理なし
**修正後:** 単一カテゴリで番号管理
```javascript
// 論文追加時
metadata: {
  source: 'arxiv',
  articleNumber: articleNumber++
}
```

#### 6. Hacker Newsレンダリングロジック（1187行目〜）
**現在:** 構造化データでmetadata.articleNumber未設置
**修正後:** データ変換時にarticleNumberを追加
```javascript
// 各記事を適切な形式に変換時
data.items.forEach((item, index) => {
  items.push({
    // ... 既存フィールド
    metadata: {
      source: 'hacker news',
      articleNumber: index + 1
    }
  });
});
```

#### 7. レンダリングロジック修正（1417行目〜1583行目）
全ての対象サービスのレンダリングロジックを、metadata.articleNumberを使用する方式に統一：

```javascript
// 修正前例（GitHub）
const repositoryIndex = isRepository ? repositoryCount++ : undefined;

// 修正後例（GitHub）
const repositoryIndex = isRepository && item.metadata?.articleNumber ? item.metadata.articleNumber - 1 : undefined;
```

### 完了前必須チェック
- [ ] ビルドが成功する
- [ ] 全テストが成功する  
- [ ] 各サービスでサブカテゴリ別に番号が1からリセットされることを確認
- [ ] 既存の正常動作サービス（Tech News等）に影響がないことを確認
- [ ] 新規追加したコードの警告を解消

### 検証方法
1. GitHub Trending：Python(1,2), Go(1), Rust(1,2)のように言語別リセット
2. note：各ハッシュタグごとに1からリセット
3. 4chan：各板（/g/, /sci/等）ごとに1からリセット
4. 5chan：各板ごとに1からリセット
5. Hacker News：単一カテゴリで1から連番
6. Academic Papers：単一カテゴリで1から連番

プロンプト: boss think harder. Github Trendingを確認してください 通し番号についてです。 python |- 1. sample |- 2. sample2 go |- 3. sample ■ 理想 python |- 1. sample |- 2. sample2 go |- 1. sample 上記のようにサブカテゴリごとに通し番号をリセットしてほしい いまはカテゴリ関係なく通し番号がインクリメントされている 全てのサービスをこのように修正してほしい