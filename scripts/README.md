# Nook スクリプト

## logs-jst.sh

DockerコンテナのログをJST（日本標準時）で表示するスクリプトです。

### 使用方法

```bash
# 基本的な使い方（すべてのログを表示）
./scripts/logs-jst.sh -t

# リアルタイムでログを追跡
./scripts/logs-jst.sh -f -t

# 特定のサービスのログのみ表示
./scripts/logs-jst.sh -f -t backend

# 最新の20行を表示
./scripts/logs-jst.sh --tail 20 -t

# ヘルプを表示
./scripts/logs-jst.sh -h
```

### エイリアスの設定（推奨）

以下のコマンドを実行して、便利なエイリアスを設定できます：

```bash
echo "alias nook-logs='/home/ubuntu/nook/scripts/logs-jst.sh'" >> ~/.bashrc
source ~/.bashrc
```

エイリアス設定後は以下のように使用できます：

```bash
nook-logs -f -t
nook-logs --tail 50 -t backend
```