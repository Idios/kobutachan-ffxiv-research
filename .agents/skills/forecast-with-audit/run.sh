#!/bin/sh
# 予測・監査スクリプトを UTF-8 モードで実行するラッパー。
# 使い方: ./run.sh phase7_backcast.py
set -eu
export PYTHONUTF8=1
cd "$(dirname "$0")"
exec python3 "scripts/$1"
