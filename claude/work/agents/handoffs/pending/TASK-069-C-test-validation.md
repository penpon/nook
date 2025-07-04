# TASK-069-C: 実装テストと動作検証

## タスク概要
TASK-069-AとTASK-069-Bで実装した403エラー対策の動作を検証し、5chan DAT取得が正常に機能することを確認する。

## 変更予定ファイル
なし（テストと検証のみ）

## 前提タスク
- TASK-069-A（Cookie・ヘッダー強化）
- TASK-069-B（403対策統合）

## worktree名
`worktrees/TASK-069-C-test-validation`

## 作業内容

### 1. 単体テストの実施

以下のテストスクリプトを作成して実行：

```python
# test_5chan_dat.py
import asyncio
import sys
sys.path.append('/home/ubuntu/nook')

from nook.services.fivechan_explorer.fivechan_explorer import FiveChanExplorer

async def test_dat_retrieval():
    """DAT取得機能のテスト"""
    explorer = FiveChanExplorer()
    
    test_cases = [
        {
            'board': 'prog',
            'name': 'プログラミング板',
            'expected_threads': ['AI', 'Python', 'Cursor', 'Copilot']
        },
        {
            'board': 'tech',
            'name': 'プログラム技術板',
            'expected_threads': ['機械学習', 'ChatGPT', 'LLM']
        }
    ]
    
    for test in test_cases:
        print(f"\n=== {test['name']}のテスト開始 ===")
        
        # subject.txt取得テスト
        threads = await explorer._get_subject_txt_data(test['board'])
        print(f"スレッド一覧取得: {len(threads)}件")
        
        # AI関連スレッドの検索
        ai_threads = [t for t in threads if any(kw in t['title'] for kw in test['expected_threads'])]
        print(f"AI関連スレッド: {len(ai_threads)}件")
        
        # 最初のAIスレッドでDAT取得テスト
        if ai_threads:
            thread = ai_threads[0]
            print(f"\nテストスレッド: {thread['title']}")
            
            dat_url = f"https://medaka.5ch.net/{test['board']}/dat/{thread['key']}.dat"
            posts = await explorer._get_thread_posts_from_dat(dat_url, test['board'])
            
            if posts:
                print(f"✓ DAT取得成功: {len(posts)}件の投稿")
                print(f"  最初の投稿: {posts[0]['com'][:50]}...")
            else:
                print("✗ DAT取得失敗")
    
    await explorer.close()

# テスト実行
asyncio.run(test_dat_retrieval())
```

### 2. 統合テストの実施

実際のサービスとして動作確認：

```bash
# 1. ログレベルをDEBUGに設定して詳細ログを確認
export LOG_LEVEL=DEBUG

# 2. 5chanサービスを実行
python -m nook.services.run_services --service 5chan

# 3. ログを監視して以下を確認：
# - subject.txt取得の成功
# - DAT取得時の戦略ログ
# - 成功した戦略の記録
# - 取得した投稿データ
```

### 3. 成功判定基準

以下の条件を満たした場合、修正成功とする：

1. **基本動作**
   - subject.txtが正常に取得できる（既に成功）
   - DAT取得で403エラーが発生しない
   - 少なくとも1つのAI関連スレッドの内容が取得できる

2. **パフォーマンス**
   - DAT取得成功率: 80%以上
   - 平均レスポンス時間: 10秒以内
   - リトライ回数: 平均3回以内

3. **ログ分析**
   - どの戦略で成功したかを記録
   - Cookie設定の効果を確認
   - User-Agent戦略の有効性を評価

### 4. 結果レポートの作成

テスト結果をまとめたレポートを作成：

```markdown
# 5chan DAT取得403エラー対策 実装結果レポート

## 実装内容
- Cookie設定（READJS='on'）の追加
- 完全なブラウザヘッダーの実装
- 403対策メソッドの統合
- 複数戦略によるリトライ機構

## テスト結果
- テスト日時: [日時]
- テスト環境: [環境]

### 成功率
- subject.txt取得: 100% (XXX/XXX)
- DAT取得: XX% (XXX/XXX)

### 成功した戦略
1. [最も成功した戦略]
2. [次に成功した戦略]

### パフォーマンス
- 平均レスポンス時間: XX秒
- 平均リトライ回数: XX回

## 結論
[実装の成功/失敗と今後の改善点]
```

### 5. 追加検証項目

必要に応じて以下も確認：

1. **エンコーディングテスト**
   - 日本語の文字化けがないか
   - 絵文字や特殊文字の処理

2. **エラーハンドリング**
   - ネットワークエラー時の挙動
   - タイムアウト処理

3. **長期安定性**
   - 1時間連続実行テスト
   - メモリリークの確認

## 注意事項

- テスト時はサーバーに負荷をかけないよう適切な間隔を設定
- ログは詳細に記録し、問題発生時の分析に使用
- 成功した戦略は文書化して今後の参考にする