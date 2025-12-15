# TrendRadar プラットフォーム拡張計画

## 概要

TrendRadar MCP サーバー経由で複数のプラットフォームのホットトピックを取得し、nook に統合する。  
知乎（Zhihu）の実装が完了したため、以下のプラットフォームを追加する。

| 項目 | 決定事項 |
|------|----------|
| 方式 | A（TrendRadar MCP 経由） |
| 表示形式 | TrendRadar 形式 + GPT 要約（各プラットフォームに最適化） |
| グループ名 | `TrendRadar` |
| 参考実装 | `zhihu_explorer.py` |

---

## ⚠️ 作業ルール

- **Git Worktree**: 必ず worktree で作成したブランチ内で作業
- **TDD RGR サイクル**: Red → Green → Refactor の順で実装
- **実コストテスト除外**: OpenAPI 等の実コストが発生するテストは実装しない（モック使用）
- **ベース実装参照**: `zhihu_explorer.py` を継承・参考にする

---

## 📋 プラットフォーム一覧

| プラットフォーム | ID | 分類 | 言語 | 特徴 |
|------------------|-----|------|------|------|
| 掘金（Juejin） | `juejin` | 開発者コミュニティ | 中国語 | 技術記事・開発トレンド |
| IT之家（ITHome） | `ithome` | テックニュース | 中国語 | IT・デバイス・ソフトウェア |
| 36氪（36Kr） | `36kr` | スタートアップ・ビジネス | 中国語 | ビジネス・投資・スタートアップ |
| 微博（Weibo） | `weibo` | SNS | 中国語 | ホットサーチ・トレンド |
| 今日头条（Toutiao） | `toutiao` | ニュースアグリゲーター | 中国語 | 総合ニュース・AI推薦 |
| 少数派（SSPai） | `sspai` | デジタルライフ | 中国語 | 生産性・アプリ・デジタルツール |
| Product Hunt | `producthunt` | プロダクト発見 | 英語 | 新製品・スタートアップ |

---

## 🔧 実装戦略

### 共通基盤
- `ZhihuExplorer` をベースにした抽象クラス `BaseTrendRadarExplorer` を検討
- GPT プロンプトは各プラットフォームの特性に最適化
- Markdown 出力フォーマットは統一（カテゴリは各プラットフォームの特性に応じて変更）

### 実装優先順位
1. **Juejin**: 開発者向け、技術分野で zhihu と類似
2. **36Kr**: ビジネス・スタートアップ分野
3. **ITHome**: IT ニュース
4. **Sspai**: デジタルライフ・ツール
5. **Toutiao**: 総合ニュース
6. **Weibo**: SNS トレンド
7. **Product Hunt**: 英語プラットフォーム（GPTプロンプト変更）

---

## Platform 1: 掘金（Juejin）

### 概要
中国最大の開発者コミュニティプラットフォーム。技術記事、チュートリアル、オープンソースプロジェクト情報が集まる。

### 対象ファイル
- `nook/services/explorers/trendradar/juejin_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_juejin_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたは中国の開発者コミュニティ「掘金（Juejin）」のトレンドを
日本語で解説する専門のアシスタントです。日本のエンジニアに向けて、
技術的な背景やコード例の意図、開発者間での議論のポイントが
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. 技術トピックの概要 (1-2文)
[技術的な内容を簡潔に説明]

2. 技術的なポイント (箇条書き3-5点)
- [ポイント1: 使用技術・フレームワーク]
- [ポイント2: 実装のアプローチ]
- [ポイント3: パフォーマンス・最適化]

3. 開発者コミュニティの反応
[コメントでの議論やフィードバックの傾向]

4. 日本の開発者への示唆
[日本での適用可能性や類似事例]
```

### ServiceRunner 登録
```python
"trendradar-juejin": JuejinExplorer
```

### フロントエンド設定
```typescript
"trendradar-juejin": {
    title: "掘金 (Juejin)",
    subtitle: "中国最大の開発者コミュニティ",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-blue-50",
    gradientTo: "to-indigo-50",
    borderColor: "border-indigo-200",
}
```

---

## Platform 2: IT之家（ITHome）

### 概要
中国で人気の IT ニュースサイト。スマートフォン、PC、ソフトウェア、AI など幅広いテック情報を扱う。

### 対象ファイル
- `nook/services/explorers/trendradar/ithome_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_ithome_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたは中国のテックニュースサイト「IT之家（ITHome）」のトレンドを
日本語で解説する専門のアシスタントです。日本のユーザーに向けて、
製品のスペックや価格情報、中国市場での反応や比較評価が
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. ニュースの概要 (1-2文)
[製品・サービスの発表内容を簡潔に説明]

2. スペック・詳細情報 (箇条書き3-5点)
- [ポイント1: 製品スペック]
- [ポイント2: 価格・発売日]
- [ポイント3: 競合との比較]

3. 市場の反応
[中国市場での評価やユーザーの反応]

4. 日本市場への影響
[日本での発売可能性や影響の予測]
```

### ServiceRunner 登録
```python
"trendradar-ithome": IthomeExplorer
```

### フロントエンド設定
```typescript
"trendradar-ithome": {
    title: "IT之家 (ITHome)",
    subtitle: "中国のテックニュースサイト",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-red-50",
    gradientTo: "to-orange-50",
    borderColor: "border-red-200",
}
```

---

## Platform 3: 36氪（36Kr）

### 概要
中国最大のスタートアップ・ビジネスメディア。投資情報、スタートアップニュース、テック業界の動向を扱う。

### 対象ファイル
- `nook/services/explorers/trendradar/kr36_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_kr36_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたは中国のスタートアップメディア「36氪（36Kr）」のトレンドを
日本語で解説する専門のアシスタントです。日本のビジネスパーソンに向けて、
投資規模、ビジネスモデル、競争環境、成長戦略などのビジネス視点が
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. ビジネスニュースの概要 (1-2文)
[企業・投資・事業の内容を簡潔に説明]

2. ビジネスポイント (箇条書き3-5点)
- [ポイント1: 資金調達額・評価額]
- [ポイント2: ビジネスモデル・収益構造]
- [ポイント3: 市場規模・成長性]

3. 業界構造・競争環境
[競合他社や市場ポジションの分析]

4. 日本企業への示唆
[日本市場での展開可能性や参考になる戦略]
```

### ServiceRunner 登録
```python
"trendradar-36kr": Kr36Explorer
```

### フロントエンド設定
```typescript
"trendradar-36kr": {
    title: "36氪 (36Kr)",
    subtitle: "中国のスタートアップメディア",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-purple-50",
    gradientTo: "to-pink-50",
    borderColor: "border-purple-200",
}
```

---

## Platform 4: 微博（Weibo）

### 概要
中国最大の SNS プラットフォーム。リアルタイムのホットサーチで世論やトレンドを把握できる。

### 対象ファイル
- `nook/services/explorers/trendradar/weibo_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_weibo_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたは中国のSNSプラットフォーム「微博（Weibo）」のトレンドを
日本語で解説する専門のアシスタントです。日本のユーザーに向けて、
トレンドの背景、世論の反応、話題になった理由や文化的コンテキストが
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. トレンドの概要 (1-2文)
[話題になっている内容を簡潔に説明]

2. 話題のポイント (箇条書き3-5点)
- [ポイント1: 発端・きっかけ]
- [ポイント2: 主要な意見・反応]
- [ポイント3: 関連するハッシュタグ・キーワード]

3. 世論の傾向
[賛否・感情的反応・議論の方向性]

4. 文化的背景
[日本人に伝わりにくい文化的コンテキストの補足]
```

### ServiceRunner 登録
```python
"trendradar-weibo": WeiboExplorer
```

### フロントエンド設定
```typescript
"trendradar-weibo": {
    title: "微博 (Weibo)",
    subtitle: "中国最大のSNSプラットフォーム",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-red-50",
    gradientTo: "to-yellow-50",
    borderColor: "border-red-300",
}
```

---

## Platform 5: 今日头条（Toutiao）

### 概要
中国最大のニュースアグリゲーター。AI によるパーソナライズ推薦と幅広いニュースカテゴリが特徴。

### 対象ファイル
- `nook/services/explorers/trendradar/toutiao_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_toutiao_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたは中国のニュースアグリゲーター「今日头条（Toutiao）」のトレンドを
日本語で解説する専門のアシスタントです。日本のユーザーに向けて、
ニュースの要点、社会的影響、異なる視点からの分析が
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. ニュースの概要 (1-2文)
[主要なニュース内容を簡潔に説明]

2. 重要なポイント (箇条書き3-5点)
- [ポイント1: 事実関係]
- [ポイント2: 関係者・組織]
- [ポイント3: 影響範囲]

3. 社会的影響
[このニュースがもたらす影響や意味]

4. 国際的視点
[日本や国際社会との関連性]
```

### ServiceRunner 登録
```python
"trendradar-toutiao": ToutiaoExplorer
```

### フロントエンド設定
```typescript
"trendradar-toutiao": {
    title: "今日头条 (Toutiao)",
    subtitle: "中国最大のニュースアグリゲーター",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-red-50",
    gradientTo: "to-red-100",
    borderColor: "border-red-200",
}
```

---

## Platform 6: 少数派（SSPai）

### 概要
デジタルライフ・生産性向けのコミュニティ。アプリレビュー、ワークフロー、デジタルツール情報が充実。

### 対象ファイル
- `nook/services/explorers/trendradar/sspai_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_sspai_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたは中国のデジタルライフメディア「少数派（SSPai）」のトレンドを
日本語で解説する専門のアシスタントです。日本のユーザーに向けて、
アプリの機能、ワークフローの具体例、生産性向上のコツが
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. コンテンツの概要 (1-2文)
[紹介されているアプリ・ツール・手法を簡潔に説明]

2. 機能・特徴 (箇条書き3-5点)
- [ポイント1: 主要機能]
- [ポイント2: 対応プラットフォーム]
- [ポイント3: 価格・ライセンス]

3. 活用シーン
[具体的なユースケースや組み合わせ]

4. 日本での代替・類似ツール
[日本で入手可能な類似ツールの紹介]
```

### ServiceRunner 登録
```python
"trendradar-sspai": SspaiExplorer
```

### フロントエンド設定
```typescript
"trendradar-sspai": {
    title: "少数派 (SSPai)",
    subtitle: "デジタルライフ＆生産性メディア",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-green-50",
    gradientTo: "to-teal-50",
    borderColor: "border-green-200",
}
```

---

## Platform 7: Product Hunt

### 概要
新製品・スタートアップを発見するための英語プラットフォーム。毎日のプロダクトランキングが特徴。

### 対象ファイル
- `nook/services/explorers/trendradar/producthunt_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_producthunt_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたはプロダクト発見プラットフォーム「Product Hunt」のトレンドを
日本語で解説する専門のアシスタントです。日本のユーザーに向けて、
プロダクトの機能、ターゲット層、ビジネスモデル、類似サービスとの比較が
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. プロダクト概要 (1-2文)
[サービス・製品の内容を簡潔に説明]

2. 主要機能 (箇条書き3-5点)
- [ポイント1: コア機能]
- [ポイント2: 差別化ポイント]
- [ポイント3: 料金プラン]

3. コミュニティの評価
[Upvote数、コメントの傾向、メーカーの反応]

4. 日本での利用可能性
[日本語対応、日本市場での展開可能性]
```

### ServiceRunner 登録
```python
"trendradar-producthunt": ProductHuntExplorer
```

### フロントエンド設定
```typescript
"trendradar-producthunt": {
    title: "Product Hunt",
    subtitle: "プロダクト発見プラットフォーム",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-orange-50",
    gradientTo: "to-amber-50",
    borderColor: "border-orange-200",
}
```

---

## 🔗 フロントエンド統合

### Sidebar グループ更新

```tsx
// frontend/src/components/layout/Sidebar.tsx
const sourceGroups = {
    default: ["arxiv", "github", ...],
    trendradar: [
        "trendradar-zhihu",
        "trendradar-juejin",
        "trendradar-ithome",
        "trendradar-36kr",
        "trendradar-weibo",
        "trendradar-toutiao",
        "trendradar-sspai",
        "trendradar-producthunt",
    ],
};
```

### App.tsx sources 更新

```typescript
// frontend/src/App.tsx
const sources = [
    ...existingSources,
    "trendradar-zhihu",
    "trendradar-juejin",
    "trendradar-ithome",
    "trendradar-36kr",
    "trendradar-weibo",
    "trendradar-toutiao",
    "trendradar-sspai",
    "trendradar-producthunt",
];
```

---

## 📊 実装チェックリスト

### 各プラットフォーム共通タスク

- [ ] Explorer クラスの実装
- [ ] TDD テストの作成
- [ ] GPT プロンプトの最適化
- [ ] ServiceRunner への登録
- [ ] sourceDisplayInfo.ts への追加
- [ ] Sidebar グループへの追加
- [ ] 統合テストの実施

### 進捗状況

| プラットフォーム | Explorer | テスト | Runner | Frontend | 統合テスト |
|------------------|----------|--------|--------|----------|------------|
| 知乎（Zhihu） | ✅ | ✅ | ✅ | ✅ | ✅ |
| 掘金（Juejin） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| IT之家（ITHome） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 36氪（36Kr） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 微博（Weibo） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 今日头条（Toutiao） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 少数派（SSPai） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Product Hunt | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

---

## 前提条件

> ⚠️ **TrendRadar セットアップが必要**
>
> 各プラットフォームの実装前に TrendRadar が起動していること。
> 対象プラットフォームが TrendRadar の `config/config.yaml` で有効化されていること。
>
> ```yaml
> platforms:
>   - id: "zhihu"
>     name: "知乎热榜"
>   - id: "juejin"
>     name: "掘金"
>   - id: "ithome"
>     name: "IT之家"
>   - id: "36kr"
>     name: "36氪"
>   - id: "weibo"
>     name: "微博热搜"
>   - id: "toutiao"
>     name: "今日头条"
>   - id: "sspai"
>     name: "少数派"
>   - id: "producthunt"
>     name: "Product Hunt"
> ```

---

## 実行順序

各プラットフォームの実装は以下の順序で進める：

```
Explorer 実装 → テスト作成 → Runner 登録 → Frontend 追加 → 統合テスト
```

複数プラットフォームの並行実装も可能だが、1つずつ完了させることを推奨。
