# スクリプト

**すべてリポジトリのルートから実行する**（`python3 scripts/xxx.py`）。
依存パッケージは無い（図表生成の `phase8_charts.py` / `phase12_charts.py` のみ `cairosvg` を使うが、
SVG・PNG とも生成済みなので再生成しないかぎり不要）。

## 中核

| スクリプト | 役割 |
|---|---|
| **`params.py`** | **正典パラメータの登録簿。** 数値をベタ書きしないための単一の情報源。使用禁止値とその理由もここに記録。基準不一致を例外にする `compare_census()` を含む |
| **`phase8_consistency.py`** | **全成果物の機械的な横断チェック。** 16文書 × 27スクリプトを突き合わせる。自己テストと構造ガードの動作確認を内蔵 |
| `phase7_forecast.py` | 予測エンジン（ストック・フローモデル） |
| `phase7_backcast.py` | 完了した 7.x 周期への当てはめ＝答え合わせ |

## フェーズ別

| スクリプト | 対応フェーズ |
|---|---|
| `phase3_5_calc.py` | 3.5 他タイトルとの比較 |
| `phase4_calc.py` | 4 人口動態 |
| `phase5_calc.py` | 5 市場・競合 |
| `phase6_model.py` / `phase6_recalc.py` / `phase6_dqx_bounds.py` | 6 売上モデル |
| `phase7_addendum.py` | 7 分岐閾値 |
| `phase8_retention.py` | ρ（定着率）の回帰 |
| `phase8_sensitivity.py` | 感度分析。群Aの走査箱を宣言して返す `groupA()` |
| `phase8_falsification.py` | 反証テストの設計と閾値 |
| `phase8_charts.py` / `phase12_charts.py` | 図表の生成 |
| `phase8_convergence.py` / `phase8_rawseries.py` / `phase8_round6_verify.py` | 監査の補助 |
| `phase9_japan.py` | 9 日本市場 |
| `phase10_entrants.py` | 新規参入 MMO の残存率（経過月そろえ） |
| `phase11_supply.py` / `phase11_corrected.py` | コンテンツ供給の分解、バイアス補正の一貫適用 |
| `phase12_claims.py` | 個別の主張の検証（値上げリードタイム等） |
| `phase13_cleanroom.py` | **クリーンルーム再計算。** 既存スクリプトを一切 import せず生 CSV から検算 |
| `phase13_identification.py` | 主指標の識別分析。帯の生成 |
| `content_volume_calc.py` | コンテンツ量の集計 |

## 構造ガード

15ラウンドで繰り返し再発した誤りを、検出ではなく**起こせなくする**形で塞いである。

- `params.compare_census()` — 窓長・足切りレジームが揃っていない比較は `ScaleMismatch` 例外
- `phase8_sensitivity.groupA(box=...)` — 走査箱を結果に同梱して返すので、箱を宣言せずに帯を引用できない

いずれも `phase8_consistency.py` の検査 P が毎回発火を確認する。
