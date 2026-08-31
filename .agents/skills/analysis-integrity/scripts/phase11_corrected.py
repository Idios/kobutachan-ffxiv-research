#!/usr/bin/env python3
"""
Phase 11 — バイアス補正を人口と売上の両方に一貫して適用する

【なぜ必要か】バックキャスト（完了した 7.x 周期に同じモデルを当てる検証）で、
本モデルは周期平均を **+5.0% 上振れ**させることが分かっている。
ところが v1.1 までは **その補正を人口の主指標にだけ掛けており、売上・利益の換算は
未補正の経路のまま**だった。人口を補正後で読みながら売上を未補正で読むのは基準の不整合で、
第10次査読の重大9・第11次の未解決事項 #19 として記録されていた。

【本スクリプトがやること】
  補正を **軌道そのもの** に掛ける。すなわち周期平均・FY2030.3 年度平均の両方を
  (1 + bias) で割り、その補正後の年度平均から売上・営業利益を計算し直す。
  売上は kr = FY2030.3 平均 / FY2026.3 平均 の弾力性 ε 乗で効くので、
  人口が 1/1.05 になれば **パッケージ・パルスを除く部分が (1/1.05)^ε 倍**になる。

【この適用の前提 — 明示する】
  バックキャストで測ったのは**周期平均の**上振れである。それを年度平均にも同率で適用するのは
  「上振れが軌道全体にほぼ一様に乗っている」という仮定に依存する。
  周期平均と年度平均で上振れ率が違う可能性は**検証していない**。

使い方: python3 scripts/phase11_corrected.py
"""
import sys

sys.path.insert(0, 'scripts')
import params as P
from phase7_forecast import CYC7_MEAN, build, cc_year, to_nominal, wavg

W = 92
def hdr(t): print("\n" + "=" * W); print(t); print("=" * W)

B = P.BACKCAST_BIAS_CYC          # 0.050
F = 1.0 / (1.0 + B)              # 補正係数


def main():
    r = build()
    hdr("A. 補正係数")
    print(f"  バックキャストの上振れ = {B:+.1%} → 補正係数 = 1/(1{B:+.3f}) = {F:.4f}")
    print(f"  弾力性 ε = {P.EPS_CENTRAL}（売上は人口の ε 乗で効く）")
    print(f"  → 売上のパルス以外の部分は {F ** P.EPS_CENTRAL:.4f} 倍になる"
          f"（{F ** P.EPS_CENTRAL - 1:+.1%}）")

    hdr("B. 人口 — 8.x 周期平均（すべて補正後）")
    print(f"  {'シナリオ':<10s}{'確率':>7s}{'未補正':>12s}{'**補正後**':>14s}{'7.x比(補正後)':>16s}")
    for k in ('Bear', 'Base', 'Bull'):
        c = r[k]['cyc']
        print(f"  {k:<10s}{r[k]['w']:>7.0%}{c:>12,.0f}{c*F:>14,.0f}"
              f"{c*F/CYC7_MEAN-1:>16.1%}")
    wc = wavg(r, 'cyc')
    print(f"  {'確率加重':<10s}{'':>7s}{wc:>12,.0f}{wc*F:>14,.0f}{wc*F/CYC7_MEAN-1:>16.1%}")
    print(f"\n  7.x 周期平均（実績）= {CYC7_MEAN:,.0f}")

    hdr("C. 売上・営業利益 — 補正後の人口経路から計算し直す")
    print("  ※ 営業利益は R4 適用のマージン帯（Bull を下方修正した正典版）")
    print(f"  {'シナリオ':<8s}{'FY2030.3 人口':>15s}{'CC売上':>10s}{'名目売上':>10s}{'営業利益':>16s}")
    tot_cc = tot_nom = 0.0
    lo_sum = hi_sum = 0.0
    for k in ('Bear', 'Base', 'Bull'):
        fy = r[k]['fy2030'] * F
        kr = fy / P.K1_FY_MEAN_LV80[2026]
        cc = cc_year(kr)
        nom = to_nominal(cc)
        m = P.MARGIN_R4[k]      # 正典は R4 適用版（Bull のマージン帯を下方修正した版）
        lo, hi = nom * m[0], nom * m[1]
        w = r[k]['w']
        tot_cc += w * cc; tot_nom += w * nom
        lo_sum += w * lo; hi_sum += w * hi
        print(f"  {k:<8s}{fy:>15,.0f}{cc:>9.0f}億{nom:>9.0f}億{lo:>8.0f}〜{hi:>4.0f}億")
    print(f"  {'確率加重':<8s}{'':>15s}{tot_cc:>9.0f}億{tot_nom:>9.0f}億"
          f"{lo_sum:>8.0f}〜{hi_sum:>4.0f}億")

    hdr("D. 未補正との差")
    ucc = utot = ulo = uhi = 0.0
    for k in ('Bear', 'Base', 'Bull'):
        kr = r[k]['fy2030'] / P.K1_FY_MEAN_LV80[2026]
        cc = cc_year(kr); nom = to_nominal(cc); m = P.MARGIN_R4[k]; w = r[k]['w']
        ucc += w * cc; utot += w * nom; ulo += w * nom * m[0]; uhi += w * nom * m[1]
    print(f"  {'量':<22s}{'未補正':>12s}{'補正後':>12s}{'差':>10s}")
    print(f"  {'8.x 周期平均':<22s}{wc:>12,.0f}{wc*F:>12,.0f}{wc*F/wc-1:>10.1%}")
    print(f"  {'  7.x 比':<22s}{wc/CYC7_MEAN-1:>11.1%}{wc*F/CYC7_MEAN-1:>12.1%}"
          f"{((wc*F/CYC7_MEAN-1)-(wc/CYC7_MEAN-1))*100:>+8.1f}pt")
    print(f"  {'CC売上(確率加重)':<22s}{ucc:>11.0f}億{tot_cc:>11.0f}億{tot_cc/ucc-1:>10.1%}")
    print(f"  {'名目売上(確率加重)':<22s}{utot:>11.0f}億{tot_nom:>11.0f}億{tot_nom/utot-1:>10.1%}")
    print(f"  {'営業利益(下限)':<22s}{ulo:>11.0f}億{lo_sum:>11.0f}億{lo_sum/ulo-1:>10.1%}")
    print(f"  {'営業利益(上限)':<22s}{uhi:>11.0f}億{hi_sum:>11.0f}億{hi_sum/uhi-1:>10.1%}")
    print(f"""
  → **売上の下がり幅（{tot_cc/ucc-1:.1%}）は人口の下がり幅（{F-1:.1%}）より小さい。**
     弾力性 ε={P.EPS_CENTRAL} が1未満であることと、パッケージ・パルス
     {P.PULSE_LAUNCH_Q}億が人口に依存しないことの2つによる。
     **「人口を1割下げたら売上も1割下がる」ではない。**""")

    hdr("E. この適用の前提")
    print("""  バックキャストで測ったのは**周期平均の**上振れ（+5.0%）である。
  それを FY2030.3 の**年度平均**にも同率で適用しているのは、
  「上振れが軌道全体にほぼ一様に乗っている」という仮定である。
  **周期平均と年度平均で上振れ率が違う可能性は検証していない。**
  ただし補正しないほうが基準の不整合として悪い（人口だけ補正して売上を未補正にする）ので、
  **一貫して適用するほうを採る。**""")


if __name__ == "__main__":
    main()
