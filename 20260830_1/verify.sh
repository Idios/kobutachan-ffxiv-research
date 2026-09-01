#!/usr/bin/env sh
# 全成果物の機械的な横断チェック。**リポジトリのルートから実行すること。**
# 期待される出力: 致命 0 / 要修正 0
#   （「要確認」は監査記録が旧値を引用している箇所で、これは正常）
#
# ただし **クローンしたままの状態では 致命 3 が出る**。国勢調査のワールド粒度 CSV
# （data/census_world/*.csv）は第三者著作物のため同梱しておらず、phase6_model.py と
# phase9_japan.py が実行できない。これは想定どおりで、合否の基準は
# 「この3件以外に指摘が出ないこと」である。詳細と復元手順は
# README.md 「クローン直後の期待値」節 および data/census_world/SOURCE.txt を参照。
set -e
cd "$(dirname "$0")"
python3 scripts/phase8_consistency.py
