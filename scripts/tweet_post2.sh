#!/bin/bash

#1 ディレクトリの移動
cd /root/nook

#2 python変数変更
source venv/bin/activate

#3 ニュースの取得
python -m nook.services.run_services --service reddit

#4 ニュースの登録
python -m nook.services.run_services --service twitter_reddit

deactivate