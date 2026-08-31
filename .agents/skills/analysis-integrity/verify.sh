#!/usr/bin/env sh
# 全成果物の機械的な横断チェック。**リポジトリのルートから実行すること。**
# 期待される出力: 致命 0 / 要修正 0
#   （「要確認」は監査記録が旧値を引用している箇所で、これは正常）
set -e
export PYTHONUTF8=1
cd "$(dirname "$0")"
python3 scripts/phase8_consistency.py
