# TrendRadar 新規プラットフォーム拡張計画（Phase 2）

## 概要

TrendRadar MCP サーバー経由で追加の4プラットフォームを統合する。  
Phase 1 で実装済みの8プラットフォームに続き、AI技術情報収集を強化する。

| 項目 | 決定事項 |
|------|----------|
| 方式 | TrendRadar MCP 経由 |
| 表示形式 | TrendRadar 形式 + GPT 要約（各プラットフォームに最適化） |
| グループ名 | `TrendRadar` |
| 参考実装 | `sspai_explorer.py`（BaseTrendRadarExplorer 継承） |

---

## 📝 命名規則

### プラットフォーム名の表記ルール

TrendRadarプラットフォームの表示名は、以下のルールに従って統一します。

#### 中国語プラットフォーム
中国語のプラットフォームは、**中国語表記 + 英語表記（括弧内）** の形式で記載します。

**例:**
- `知乎 (Zhihu)` - Q&Aプラットフォーム
- `掘金 (Juejin)` - 開発者コミュニティ
- `IT之家 (ITHome)` - テックニュースサイト
- `36氪 (36Kr)` - スタートアップメディア
- `微博 (Weibo)` - SNSプラットフォーム
- `今日头条 (Toutiao)` - ニュースアグリゲーター
- `少数派 (SSPai)` - デジタルライフメディア
- `华尔街见闻 (Wallstreetcn)` - 金融・投資メディア
- `腾讯新闻 (Tencent News)` - 総合ニュースメディア

#### 英語プラットフォーム
英語のプラットフォームで、ブランド名として英語表記が一般的な場合は、**英語表記 + 英語表記（括弧内）** の形式で記載します。

**例:**
- `FreeBuf (FreeBuf)` - セキュリティメディア（中国語表記「飞波」もあるが、ブランド名として英語表記が一般的）
- `Product Hunt` - プロダクト発見プラットフォーム（括弧なし）

#### 適用箇所
この命名規則は以下のファイルで統一して使用します:
- `frontend/src/config/sourceDisplayInfo.ts` - `title` フィールド
- `nook/api/routers/content.py` - `_get_source_display_name()` 関数内の辞書


## ⚠️ 作業ルール

- **Git Worktree**: 必ず worktree で作成したブランチ内で作業
- **TDD RGR サイクル**: Red → Green → Refactor の順で実装
- **実コストテスト除外**: OpenAPI 等の実コストが発生するテストは実装しない（モック使用）

> [!IMPORTANT]
> **新プラットフォーム統合時のチェックリスト**
> 1. Explorer クラス実装（`BaseTrendRadarExplorer` 継承）
> 2. TDD テスト作成
> 3. `runner_impl.py` 登録（TRENDRADAR_SERVICES, trendradar_mapping）
> 4. `content.py` 登録（SOURCE_MAPPING, elif条件2箇所, _get_source_display_name）
> 5. `sourceDisplayInfo.ts` 追加
> 6. `Sidebar.tsx` グループ追加
> 7. `App.tsx` sources 追加
> 8. `config/trendradar/config.yaml` 追加

---

## 📋 プラットフォーム一覧

| プラットフォーム | ID | 分類 | 言語 | 特徴 |
|------------------|-----|------|------|------|
| Freebuf | `freebuf` | セキュリティ | 中国語 | AIセキュリティ・脅威情報 |
| 华尔街见闻（Wallstreetcn） | `wallstreetcn-hot` | 金融・投資 | 中国語 | AI投資・企業動向 |
| 腾讯新闻（Tencent News） | `tencent-hot` | 総合ニュース | 中国語 | 中国AI市場動向 |
| V2EX | `v2ex` | 開発者コミュニティ | 中国語 | 技術議論・キャリア |

---

## Platform 1: Freebuf

### 概要
中国最大のサイバーセキュリティ専門メディア。AIセキュリティ、脅威検知、脆弱性スキャン等の情報を扱う。

### チェックリスト

#### 命名規則
- [x] `sourceDisplayInfo.ts` の `title` に「FreeBuf (FreeBuf)」形式で記載
- [x] `content.py` の `_get_source_display_name()` に追加

#### 作業ルール
- [x] Git Worktree で作業
- [x] Explorer クラス実装（`BaseTrendRadarExplorer` 継承）
- [x] TDD テスト作成
- [x] `runner_impl.py` 登録（TRENDRADAR_SERVICES, trendradar_mapping）
- [x] `content.py` 登録（SOURCE_MAPPING, elif条件2箇所, _get_source_display_name）
- [x] `sourceDisplayInfo.ts` 追加
- [x] `Sidebar.tsx` グループ追加
- [x] `App.tsx` sources 追加
- [x] `config/trendradar/config.yaml` 追加

### 対象ファイル
- `nook/services/explorers/trendradar/freebuf_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_freebuf_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたは中国のサイバーセキュリティメディア「Freebuf」のトレンドを
日本語で解説する専門のアシスタントです。日本のセキュリティエンジニアに向けて、
脅威の技術的詳細、攻撃手法、防御策、影響範囲が
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. セキュリティトピックの概要 (1-2文)
[脅威・脆弱性・セキュリティ動向を簡潔に説明]

2. 技術的詳細 (箇条書き3-5点)
- [ポイント1: 攻撃手法/脆弱性タイプ]
- [ポイント2: 影響を受けるシステム]
- [ポイント3: 検知・防御方法]

3. 業界への影響
[セキュリティ業界や企業への影響]

4. 日本での対策・関連事例
[日本での類似事例や推奨される対策]
```

### ServiceRunner 登録
```python
"trendradar-freebuf": FreebufExplorer
```

### フロントエンド設定
```typescript
"trendradar-freebuf": {
    title: "Freebuf",
    subtitle: "中国最大のセキュリティメディア",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-slate-50",
    gradientTo: "to-gray-50",
    borderColor: "border-slate-300",
}
```

---

## Platform 2: 华尔街见闻（Wallstreetcn）

### 概要
中国の金融・投資ニュースメディア。「硬AI」専門セクションを持ち、AI関連企業の投資・株価動向に強い。

### チェックリスト

#### 命名規則
- [ ] `sourceDisplayInfo.ts` の `title` に「华尔街见闻 (Wallstreetcn)」形式で記載
- [ ] `content.py` の `_get_source_display_name()` に追加

#### 作業ルール
- [ ] Git Worktree で作業
- [ ] Explorer クラス実装（`BaseTrendRadarExplorer` 継承）
- [ ] TDD テスト作成
- [ ] `runner_impl.py` 登録（TRENDRADAR_SERVICES, trendradar_mapping）
- [ ] `content.py` 登録（SOURCE_MAPPING, elif条件2箇所, _get_source_display_name）
- [ ] `sourceDisplayInfo.ts` 追加
- [ ] `Sidebar.tsx` グループ追加
- [ ] `App.tsx` sources 追加
- [ ] `config/trendradar/config.yaml` 追加

### 対象ファイル
- `nook/services/explorers/trendradar/wallstreetcn_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_wallstreetcn_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたは中国の金融メディア「华尔街见闻（Wallstreetcn）」のトレンドを
日本語で解説する専門のアシスタントです。日本の投資家やビジネスパーソンに向けて、
市場動向、投資判断に影響する要因、企業業績が
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. 金融ニュースの概要 (1-2文)
[市場動向・投資情報を簡潔に説明]

2. 投資ポイント (箇条書き3-5点)
- [ポイント1: 市場インパクト]
- [ポイント2: 関連銘柄・セクター]
- [ポイント3: 数値データ（資金調達額等）]

3. 市場の反応・見通し
[アナリストの見解や市場の反応]

4. 日本市場への影響
[日本の投資家・企業への示唆]
```

### ServiceRunner 登録
```python
"trendradar-wallstreetcn": WallstreetcnExplorer
```

### フロントエンド設定
```typescript
"trendradar-wallstreetcn": {
    title: "华尔街见闻 (Wallstreetcn)",
    subtitle: "中国の金融・投資メディア",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-emerald-50",
    gradientTo: "to-teal-50",
    borderColor: "border-emerald-200",
}
```

---

## Platform 3: 腾讯新闻（Tencent News）

### 概要
中国最大のテック企業Tencentが運営する総合ニュースメディア。Hunyuan大模型を活用したAI関連報道に強み。

### チェックリスト

#### 命名規則
- [ ] `sourceDisplayInfo.ts` の `title` に「腾讯新闻 (Tencent News)」形式で記載
- [ ] `content.py` の `_get_source_display_name()` に追加

#### 作業ルール
- [ ] Git Worktree で作業
- [ ] Explorer クラス実装（`BaseTrendRadarExplorer` 継承）
- [ ] TDD テスト作成
- [ ] `runner_impl.py` 登録（TRENDRADAR_SERVICES, trendradar_mapping）
- [ ] `content.py` 登録（SOURCE_MAPPING, elif条件2箇所, _get_source_display_name）
- [ ] `sourceDisplayInfo.ts` 追加
- [ ] `Sidebar.tsx` グループ追加
- [ ] `App.tsx` sources 追加
- [ ] `config/trendradar/config.yaml` 追加

### 対象ファイル
- `nook/services/explorers/trendradar/tencent_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_tencent_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたは中国のニュースメディア「腾讯新闻（Tencent News）」のトレンドを
日本語で解説する専門のアシスタントです。日本のユーザーに向けて、
ニュースの要点、社会的背景、中国市場での影響が
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. ニュースの概要 (1-2文)
[主要なニュース内容を簡潔に説明]

2. 重要なポイント (箇条書き3-5点)
- [ポイント1: 事実関係]
- [ポイント2: 関係企業・人物]
- [ポイント3: 影響範囲]

3. 中国市場への影響
[中国国内での反応や影響]

4. 日本・国際社会との関連
[日本や国際社会への示唆]
```

### ServiceRunner 登録
```python
"trendradar-tencent": TencentExplorer
```

### フロントエンド設定
```typescript
"trendradar-tencent": {
    title: "腾讯新闻 (Tencent News)",
    subtitle: "Tencentの総合ニュースメディア",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-blue-50",
    gradientTo: "to-indigo-50",
    borderColor: "border-blue-300",
}
```

---

## Platform 4: V2EX

### 概要
中国の開発者・テック愛好者向けコミュニティ。プログラミング、キャリア、テクノロジーに関する議論が活発。Hacker News の中国版とも言われる。

### チェックリスト

#### 命名規則
- [ ] `sourceDisplayInfo.ts` の `title` に「V2EX」形式で記載
- [ ] `content.py` の `_get_source_display_name()` に追加

#### 作業ルール
- [ ] Git Worktree で作業
- [ ] Explorer クラス実装（`BaseTrendRadarExplorer` 継承）
- [ ] TDD テスト作成
- [ ] `runner_impl.py` 登録（TRENDRADAR_SERVICES, trendradar_mapping）
- [ ] `content.py` 登録（SOURCE_MAPPING, elif条件2箇所, _get_source_display_name）
- [ ] `sourceDisplayInfo.ts` 追加
- [ ] `Sidebar.tsx` グループ追加
- [ ] `App.tsx` sources 追加
- [ ] `config/trendradar/config.yaml` 追加

### 対象ファイル
- `nook/services/explorers/trendradar/v2ex_explorer.py` [NEW]
- `tests/services/explorers/trendradar/test_v2ex_explorer.py` [NEW]

### GPT プロンプト設計

```
あなたは中国の開発者コミュニティ「V2EX」のトレンドを
日本語で解説する専門のアシスタントです。日本のエンジニアに向けて、
技術的な議論のポイント、開発者の意見、キャリアに関する洞察が
伝わるような具体的で情報量の多い要約を作成してください。
```

### 要約フォーマット

```markdown
1. トピックの概要 (1-2文)
[議論されている技術やトピックを簡潔に説明]

2. 議論のポイント (箇条書き3-5点)
- [ポイント1: 主要な意見・提案]
- [ポイント2: 技術的な詳細]
- [ポイント3: コミュニティの反応]

3. 開発者コミュニティの動向
[トレンドや共通の関心事]

4. 日本の開発者への示唆
[日本での適用可能性や参考になる点]
```

### ServiceRunner 登録
```python
"trendradar-v2ex": V2exExplorer
```

### フロントエンド設定
```typescript
"trendradar-v2ex": {
    title: "V2EX",
    subtitle: "中国の開発者コミュニティ",
    dateFormat: "yyyy年MM月dd日",
    gradientFrom: "from-gray-50",
    gradientTo: "to-zinc-50",
    borderColor: "border-gray-300",
}
```

---

## 🔧 共通変更ファイル

### バックエンド

| ファイル | 変更内容 |
|----------|----------|
| `runner_impl.py` | TRENDRADAR_SERVICES, trendradar_mapping に追加 |
| `content.py` | SOURCE_MAPPING, elif条件, display_name に追加 |
| `__init__.py` | export 追加 |

### フロントエンド

| ファイル | 変更内容 |
|----------|----------|
| `sourceDisplayInfo.ts` | 4プラットフォームのエントリ追加 |
| `Sidebar.tsx` | trendradar グループに追加 |
| `App.tsx` | sources 配列に追加 |

### 設定

```yaml
# config/trendradar/config.yaml
platforms:
  - id: "freebuf"
    name: "Freebuf"
  - id: "wallstreetcn-hot"
    name: "华尔街见闻"
  - id: "tencent-hot"
    name: "腾讯新闻"
  - id: "v2ex"
    name: "V2EX"
```

---

## 📊 検証計画

### 自動テスト
```bash
# 単体テスト
uv run pytest tests/services/explorers/trendradar/test_freebuf_explorer.py -v
uv run pytest tests/services/explorers/trendradar/test_wallstreetcn_explorer.py -v
uv run pytest tests/services/explorers/trendradar/test_tencent_explorer.py -v
uv run pytest tests/services/explorers/trendradar/test_v2ex_explorer.py -v

# 品質チェック
uv run ruff check nook/services/explorers/trendradar/
cd frontend && npm run lint
```

### 手動検証
1. TrendRadar Docker コンテナ起動
2. 各サービス実行: `uv run python -m nook.services.runner.run_services --service trendradar-freebuf`
3. フロントエンド表示確認

---

## 📅 実装順序

1. **Freebuf** - AIセキュリティ
2. **Wallstreetcn** - AI投資・ビジネス  
3. **Tencent News** - 中国AI市場
4. **V2EX** - 開発者コミュニティ
