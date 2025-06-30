# TASK-009: ArXiv論文要約を8つの質問形式に拡張

## タスク概要
参考コードの8つの質問形式とシステムインストラクション形式を、現在のpaper_summarizer.pyに統合する。論文の本文（HTML）を抽出して、アブストラクトだけでなく全体の内容を考慮した詳細な要約を生成する。

## 変更予定ファイル
- nook/services/paper_summarizer/paper_summarizer.py

## 前提タスク
なし

## worktree名
worktrees/TASK-009-enhance-arxiv-paper-summary

## 作業内容

### 1. ヘルパー関数の追加
ファイルの先頭（インポート後、クラス定義前）に以下の3つの関数を追加：

```python
def remove_tex_backticks(text: str) -> str:
    r"""
    文字列が TeX 形式、つまり
      `$\ldots$`
    の場合、外側のバッククォート (`) だけを削除して
      $\ldots$
    に変換します。
    それ以外の場合は、文字列を変更しません。
    """
    pattern = r"^`(\$.*?\$)`$"
    return re.sub(pattern, r"\1", text)


def remove_outer_markdown_markers(text: str) -> str:
    """
    文章中の "```markdown" で始まるブロックについて、
    最も遠くにある "```" を閉じマーカーとして認識し、
    開始の "```markdown" とその閉じマーカー "```" のみを削除します。
    """
    pattern = r"```markdown(.*)```"
    return re.sub(pattern, lambda m: m.group(1), text, flags=re.DOTALL)


def remove_outer_singlequotes(text: str) -> str:
    """
    文章中の "'''" で始まるブロックについて、
    最も遠くにある "'''" を閉じマーカーとして認識し、
    開始の "'''" とその閉じマーカー "'''" のみを削除します。
    """
    pattern = r"'''(.*)'''"
    return re.sub(pattern, lambda m: m.group(1), text, flags=re.DOTALL)
```

### 2. _is_valid_body_line メソッドの追加
PaperSummarizerクラスに以下のメソッドを追加：

```python
def _is_valid_body_line(self, line: str, min_length: int = 80):
    """本文として妥当な行かを判断するための簡易ヒューリスティック。"""
    if "@" in line:
        return False
    for kw in [
        "university",
        "lab",
        "department",
        "institute",
        "corresponding author",
    ]:
        if kw in line.lower():
            return False
    if len(line) < min_length:
        return False
    return False if "." not in line else True
```

### 3. _extract_body_text メソッドの完全な置き換え
現在の簡易実装を以下に置き換え：

```python
async def _extract_body_text(self, arxiv_id: str, min_line_length: int = 40) -> str:
    """ArXivのHTMLから本文を抽出"""
    try:
        response = await self.http_client.get(f"https://arxiv.org/html/{arxiv_id}")
        soup = BeautifulSoup(response, "html.parser")

        body = soup.body
        if body:
            for tag in body.find_all(["header", "nav", "footer", "script", "style"]):
                tag.decompose()
            full_text = body.get_text(separator="\n", strip=True)
        else:
            full_text = ""

        lines = full_text.splitlines()

        # ヒューリスティックにより、実際の論文本文の開始行を探す
        start_index = 0
        for i, line in enumerate(lines):
            clean_line = line.strip()
            # 先頭部分の空行や短すぎる行はスキップ
            if len(clean_line) < min_line_length:
                continue
            if self._is_valid_body_line(clean_line, min_length=100):
                start_index = i
                break

        # 開始行以降を本文として抽出
        body_lines = lines[start_index:]
        # ノイズ除去: 短すぎる行は除外
        filtered_lines = []
        for line in body_lines:
            if len(line.strip()) >= min_line_length:
                line = line.strip()
                line = line.replace("Â", " ")
                filtered_lines.append(line.strip())
        return "\n".join(filtered_lines)
    except Exception as e:
        self.logger.error(f"Error extracting body text: {str(e)}")
        return ""  # エラー時は空文字列を返す
```

### 4. _retrieve_paper_info メソッドの修正
219行目付近を以下のように修正：

```python
# PDFから本文を抽出
arxiv_id = paper.entry_id.split("/")[-1]  # URLからIDを抽出
contents = await self._extract_body_text(arxiv_id)
if not contents:  # HTML抽出に失敗した場合はアブストラクトを使用
    contents = paper.summary
```

### 5. _summarize_paper_info メソッドの修正
プロンプトとシステムインストラクションを以下に置き換え：

```python
async def _summarize_paper_info(self, paper_info: PaperInfo) -> None:
    """論文を要約します。"""
    prompt = """
    以下の8つの質問について、順を追って非常に詳細に、分かりやすく答えてください。

    1. 既存研究では何ができなかったのか
    2. どのようなアプローチでそれを解決しようとしたか
    3. 結果、何が達成できたのか
    4. Limitationや問題点は何か。本文で言及されているものの他、あなたが考えるものも含めて
    5. 技術的な詳細について。技術者が読むことを想定したトーンで
    6. コストや物理的な詳細について。例えばトレーニングに使用したGPUの数や時間、データセット、モデルのサイズなど
    7. 参考文献のうち、特に参照すべきもの
    8. この論文を140字以内で要約すると？

    フォーマットは以下の通りで、markdown形式で回答してください。このフォーマットに沿った文言以外の出力は不要です。
    なお、数式は表示が崩れがちで面倒なので、説明に数式を使うときは、代わりにPython風の疑似コードを書いてください。

    ## 1. 既存研究では何ができなかったのか

    ...

    ## 2. どのようなアプローチでそれを解決しようとしたか

    ...

    （以下同様）
    """

    system_instruction = f"""
    以下のテキストは、ある論文のタイトルとURL、abstract、および本文のコンテンツです。
    本文はhtmlから抽出されたもので、ノイズや不要な部分が含まれている可能性があります。
    よく読んで、ユーザーの質問に答えてください。

    title
    '''
    {paper_info.title}
    '''

    url
    '''
    {paper_info.url}
    '''

    abstract
    '''
    {paper_info.abstract}
    '''

    contents
    '''
    {paper_info.contents}
    '''
    """

    try:
        summary = await self.gpt_client.generate_async(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3,
            max_tokens=3000,  # 8つの質問に対応するため増量
            service_name=self.service_name,
        )
        
        # 出力の整形
        summary = remove_tex_backticks(summary)
        summary = remove_outer_markdown_markers(summary)
        summary = remove_outer_singlequotes(summary)
        
        paper_info.summary = summary
        await self.rate_limit()
    except Exception as e:
        # エラー処理（既存のコードと同じ）
```

### 6. 出力形式の調整
363行目付近で、タイトルの前の`##`はそのまま維持（フロントエンドのパース関数と一致させるため）：

```python
content += f"## [{paper.title}]({paper.url})\n\n"  # そのまま維持
```

### テスト確認事項
- ArXivのHTMLページから本文が正しく抽出されること
- 8つの質問形式で論文要約が生成されること
- HTMLが利用できない場合のフォールバック処理が機能すること
- 生成される要約の品質が向上していること
- エラーが発生した場合の適切なハンドリング