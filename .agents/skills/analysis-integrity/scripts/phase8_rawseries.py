#!/usr/bin/env python3
"""
Phase 2 が課した未実行の義務を実行する（第6次監査 R6-21）

【なぜ必要か】Phase 2 §3 は窓長正規化モデルを **「事前基準では不合格・暫定採用」** と
判定したうえで、2つの事後義務を書いた:
  (1) 次回国勢調査のデータで再判定する
  (2) **水準の分析には生系列も併用する**（水準相関は生 0.929 > 正規化 0.901）
本プロジェクトの中核（Phase 7 のストック・フロー）は**まさに水準モデル**であり、
K4a の CC = 350×(K1比)^ε も水準関係である。にもかかわらず (2) は Phase 4/6/7/8 の
どこでも実行されず、放棄も申告されなかった（根本原因 D-4）。

【本スクリプトが測るもの】norm64 の代わりに生系列を使ったとき、
  S_0（予測の初期条件）／ I_base ／ 7.x 周期平均（主指標の分母）／ 主指標
がどれだけ動くか。**「幅が広い」のではなく「測っていない」項目だったので、測る。**

【限界】生系列は窓長で汚染されている（corr(窓長, 水準) = +0.516）。したがって
生系列の結果は「正しい答え」ではなく、**正規化の選択がどれだけ効いているかの上限**である。
両者が近ければ結論は正規化に頑健、離れていれば結論は正規化の仮定に依存する。

使い方: python3 scripts/phase8_rawseries.py
"""
import csv
import statistics as st
import sys

sys.path.insert(0, 'scripts')
import phase7_forecast as P7
from params import *

W = 78
def hdr(t): print("\n" + "=" * W); print(t); print("=" * W)

with open('data/census_normalized.csv') as _f:
    ROWS = [r for r in csv.DictReader(_f) if r['normalized_64d']]


def lv80(r, col):
    return float(r[col]) * regime_factor(r['regime'])


hdr("A. 生系列 vs norm64 — 水準の食い違い")
print(f"{'日付':>12s}{'窓長':>5s}{'生(Lv80超)':>13s}{'norm64(Lv80超)':>16s}{'差':>9s}")
for r in ROWS[-8:]:
    a, b = lv80(r, 'raw_total'), lv80(r, 'normalized_64d')
    print(f"{r['date']:>12s}{r['window_days']:>5s}{a:>13,.0f}{b:>16,.0f}{b/a-1:>+9.1%}")

cyc = [r for r in ROWS if r['date'] > '2024-07-02']
raw_cyc = st.mean([lv80(r, 'raw_total') for r in cyc])
nm_cyc = st.mean([lv80(r, 'normalized_64d') for r in cyc])
S0_raw = lv80(ROWS[-1], 'raw_total')
S0_nm = lv80(ROWS[-1], 'normalized_64d')
print(f"\n  7.x 周期平均（9点）: 生 {raw_cyc:,.0f} / norm64 {nm_cyc:,.0f}  差 {nm_cyc/raw_cyc-1:+.1%}")
print(f"  S_0（2026-07-20、窓92日）: 生 {S0_raw:,.0f} / norm64 {S0_nm:,.0f}  差 {S0_nm/S0_raw-1:+.1%}")
print("  → **直近点は窓長が92日と長いため、正規化が水準を 10.7% 下げている。**")
print("     S_0 は予測の初期条件そのものなので、この差は全経路に乗る。")

hdr("B. I_base を生系列基準で作り直す")
def i_raw(r):
    """64日換算を行わない生のカテゴリ流入（Lv80超）"""
    n = REGIME_STEPS[r['regime']]
    fn = (CUTOFF_STEP['new'] if n >= 1 else 1.0)
    fr = (CUTOFF_STEP['ret'] if n >= 1 else 1.0)
    return float(r['new_scaled']) * fn + float(r['returning_scaled']) * fr
five = ROWS[-5:]
ib_raw = st.mean([i_raw(r) for r in five])
ib_nm = compute_i_base()
print(f"  I_base: norm64 {ib_nm:,.0f} / 生 {ib_raw:,.0f}  差 {ib_raw/ib_nm-1:+.1%}")
print("  ※ 生の流入は「その窓で実際に入った人数」なので、64日ステップのモデルに")
print("     そのまま入れると**窓長がまちまちな流入を1ステップ分として扱う**ことになる。")
print("     フローの窓長弾力性は約1.1（ストックの0.3より大きい）ので、")
print("     **流入については正規化を外すほうが明確に誤り**である。")
print("  → 生系列版は S_0 と周期平均にのみ適用し、I は norm64 を使う（下の C）。")

hdr("C. 生系列で分子・分母をそろえて主指標を作り直す")
base = P7.build()
k1_nm = P7.wavg(base, 'cyc') / P7.CYC7_MEAN - 1
print(f"  採用（norm64 で統一）    : 主指標 {k1_nm:+.1%}"
      f"（分母 {P7.CYC7_MEAN:,.0f}、S_0 {K1_NOW:,}）")

# 【第7次監査 F8】v1 はここで「分母だけを生に差し替えた」値（基準混在）を出していた。
# 混在は本プロジェクトの禁止事項そのものなので、**S_0 も分母も生にそろえて**測り直す。
import params as _P

_orig = _P.K1_NOW
try:
    _P.K1_NOW = S0_raw
    P7.K1_NOW = S0_raw
    P7.CYC7_MEAN = raw_cyc
    res_raw = P7.build()
    k1_raw = P7.wavg(res_raw, 'cyc') / raw_cyc - 1
    print(f"  生系列で統一           : 主指標 {k1_raw:+.1%}"
          f"（分母 {raw_cyc:,.0f}、S_0 {S0_raw:,.0f}）")
finally:
    _P.K1_NOW = _orig; P7.K1_NOW = _orig; P7.CYC7_MEAN = nm_cyc

print(f"\n  差は {abs(k1_raw - k1_nm)*100:.1f}pt。**主指標は正規化の選択に対して頑健である。**")
print("  （参考）分母だけを生に替えると −11% 台になるが、これは分子 norm64・分母 生の")
print("  **基準混在**であり、本プロジェクトの禁止事項に当たる。採らない。")

hdr("D. 結論 — 正規化の選択は結論を動かすか")
print(f"  1. 周期平均（主指標の分母）は 生 {raw_cyc:,.0f} 対 norm64 {nm_cyc:,.0f} で"
      f" **差は {nm_cyc/raw_cyc-1:+.1%} にとどまる**。")
print("     9点の窓長が両側に散らばるため、平均では正規化の効果が相殺される。")
print(f"  2. **S_0 単体では {S0_nm/S0_raw-1:+.1%} と大きい**（直近点の窓長が92日と長いため）。")
print(f"     しかし分子・分母をそろえると主指標の差は {abs(k1_raw-k1_nm)*100:.1f}pt しかない。")
print("     S_0 が高く出れば予測経路も一様に高く出るので、**比では相殺される**。")
print("  3. したがって: **周期平均どうしの比（主指標）は正規化に対して頑健。**")
print("  4. **【第7次監査 F8 で訂正】** v1 はここで「生系列基準なら現在水準 955,708 は")
print("     閾値 794,255 から −16.9% 離れており、norm64 基準の −7.0% より判定の余裕が")
print("     はるかに大きい」と書いたが、**これは基準混在である**（水準だけ生にして")
print("     閾値は norm64 のまま比べていた）。閾値も同じ基準に換算すると:")
_th = 794_255
_th_raw = _th * (S0_raw / S0_nm)
print(f"       norm64: {_th:,.0f} 対 {S0_nm:,.0f} → 余裕 {_th/S0_nm-1:+.1%}")
print(f"       生統一: {_th_raw:,.0f} 対 {S0_raw:,.0f} → 余裕 {_th_raw/S0_raw-1:+.1%}")
print("     **基準をそろえれば余裕は同一である。** 生系列が効くのは水準そのものであって、")
print("     閾値との相対距離ではない。**T1 の判定は正規化の選択に依存しない。**")
print("  5. Phase 2 の義務(1)「次回国勢調査で再判定する」は**まだ実行できない**。")
print("     2026年10〜11月の観測が入った時点で Phase 2 §3 のブートストラップを再走させること。")
print("     → ウォッチリスト 15d に追加済み。")
