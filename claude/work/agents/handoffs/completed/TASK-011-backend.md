# TASK-011: Usage Dashboard APIのタイムゾーン対応

## タスク概要
Usage Dashboard APIがUTC時刻で動作しているため、日本時間のログデータが「今日」として正しく認識されない問題を修正する。

## 問題の詳細
- 現在の状況: APIの`datetime.now()`がUTCで動作（環境依存）
- 影響: 日本時間6/24のデータが、UTC時刻ではまだ6/23のため無視される
- 結果: 実データが存在するのに、Usage Dashboardに表示されない

## 実装内容

### 1. BaseConfigにタイムゾーン設定を追加
**ファイル**: `nook/common/config.py`
```python
# BaseConfigクラスに追加
TIMEZONE: str = Field(default="Asia/Tokyo", env="TIMEZONE")
```

### 2. requirements.txtにpytzを追加
**ファイル**: `requirements.txt`
```
pytz>=2023.3
```

### 3. usage.pyをタイムゾーン対応に修正
**ファイル**: `nook/api/routers/usage.py`

以下の修正を実施:
1. importにpytzとBaseConfigを追加
2. タイムゾーンオブジェクトを初期化
3. すべての`datetime.now()`をタイムゾーン付きに変更
4. ログのタイムスタンプ解析時にタイムゾーンを考慮

## 変更予定ファイル
- `nook/api/routers/usage.py`
- `nook/common/config.py`
- `requirements.txt`

## 前提タスク
なし

## テスト方法
1. `uv pip install pytz`でpytzをインストール
2. バックエンドを再起動
3. Usage Dashboardを開いて、実データが表示されることを確認
4. 環境変数`TIMEZONE=UTC`を設定して、タイムゾーン変更が機能することを確認

## 注意事項
- 既存のログファイルとの互換性を保つため、ログのタイムスタンプは変更しない
- API側でタイムゾーンを処理し、フロントエンドは変更不要