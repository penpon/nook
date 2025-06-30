# TASK-009: ArXiv論文要約を8つの質問形式に拡張

## タスク概要
ArXiv論文要約を現在の4項目形式から、より詳細な8つの質問形式に拡張する。また、論文の本文（HTML）を抽出して、アブストラクトだけでなく全体の内容を考慮した要約を生成する。

## 変更予定ファイル
- nook/services/paper_summarizer/paper_summarizer.py

## 前提タスク
なし

## worktree名
worktrees/TASK-009-enhance-arxiv-paper-summary

## 作業内容

### 1. 本文抽出機能の実装（_extract_body_text メソッドの置き換え）
現在の簡易実装（アブストラクトを返すだけ）を、ArXivのHTMLページから本文を抽出する実装に置き換える：

```python
def _extract_body_text(self, arxiv_id: str, min_line_length: int = 40):
    response = requests.get(f"https://arxiv.org/html/{arxiv_id}")
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")
    # ... 本文抽出ロジック ...
```

### 2. _is_valid_body_line メソッドの追加
本文として妥当な行を判断するヒューリスティック関数を追加。

### 3. プロンプトの更新
299-319行目の重複したプロンプトを、8つの質問形式に統一：

```
1. 既存研究では何ができなかったのか
2. どのようなアプローチでそれを解決しようとしたか
3. 結果、何が達成できたのか
4. Limitationや問題点は何か。本文で言及されているものの他、あなたが考えるものも含めて
5. 技術的な詳細について。技術者が読むことを想定したトーンで
6. コストや物理的な詳細について。例えばトレーニングに使用したGPUの数や時間、データセット、モデルのサイズなど
7. 参考文献のうち、特に参照すべきもの
8. この論文を140字以内で要約すると？
```

### 4. システムインストラクションの更新
論文の本文（contents）を含めた新しいシステムインストラクションに更新：

```
title: {title}
url: {url}
abstract: {abstract}
contents: {contents}
```

### 5. 本文抽出の統合
- _retrieve_paper_info メソッドで、paper.summaryではなく、HTMLから抽出した本文を使用
- ArXiv IDの取得ロジックを適切に実装

### 6. トークン制限への対応
- max_tokensを適切に調整（1000 → より大きな値）
- 本文が長すぎる場合の切り詰め処理を検討

### 実装時の注意事項
- ArXivのHTML形式が利用可能でない論文の場合のフォールバック処理
- エラーハンドリングの強化
- 非同期処理との整合性を保つ

### テスト確認事項
- 新しい8つの質問形式で論文要約が生成されること
- HTML本文が正しく抽出されること
- エラーが発生した場合の適切なフォールバック
- 生成される要約の品質向上