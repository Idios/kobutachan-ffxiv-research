#!/usr/bin/env python3
"""
Phase 13 — クリーンルーム再計算（既存スクリプトを一切 import しない）

【なぜ必要か】12ラウンドで致命的誤り44件、うち14件が主要な数値を動かした。
主指標は −11.4% → −21.8% → −4.7% → −2.0% → −3.4% → −11.5% → −9.6% → −6.6% と
**約20ポイントの幅を動いている。** この振れが「本当にモデルの帰結なのか」
「それとも実装のどこかに未発見の誤りがあるのか」を、
**params.py も phase7_forecast.py も読まずに、生の CSV から書き直して確かめる。**

【方針】
  - import するのは csv / math / statistics / datetime のみ
  - 定数はこのファイル内で生データから導出するか、導出元を明記して置く
  - 各段の途中結果を全部印字し、既存実装の値と突き合わせられるようにする
  - **一致しなければ、どちらかが誤っている。** 差の出た段を特定する

使い方: python3 scripts/phase13_cleanroom.py
"""
import csv
import math
import statistics as st
from datetime import date

W = 92
def hdr(t): print("\n" + "=" * W); print(t); print("=" * W)
def D(s): y, m, d = map(int, s.split('-')); return date(y, m, d)

CENSUS = 'data/census_normalized.csv'

# ---------------------------------------------------------------- 前提の宣言
# 記事の「x万」表記は**切り捨て**である（第8次で実証的に確定）。
#   四捨五入なら、内訳の和の範囲 [940,000, 970,000) と総数の範囲 [945,000, 955,000) が
#   正確な総数 955,708 を同時に満たせない。切り捨てなら両方成立する。
EXACT_TOTAL_20260720 = 955_708      # 記事が明記した正確な総数
# 2026-07-20 の同日ペア（Lv70超 基準と Lv80超 基準の両方が公表された唯一の回）
SAMEDAY = {              # (Lv70超, Lv80超) 万単位の記事表記。切り捨てなので下限。
    'total': (102, 95), 'new': (8, 5), 'ret': (31, 28), 'cont': (63, 61),
}


def cutoff_steps():
    """足切り段差（Lv70超 → Lv80超）。切り捨て表記の下限＋加法制約から点推定する。

    記事表記が切り捨てなら真値は [x万, x+1万)。総数だけは正確値を知っている。
    内訳の和は総数に一致しなければならない（加法制約）。
    その制約下で各成分の中点を取る。
    """
    lo70 = {k: v[0] * 10_000 for k, v in SAMEDAY.items()}
    lo80 = {k: v[1] * 10_000 for k, v in SAMEDAY.items()}
    # Lv70超 の総数は範囲 [1,020,000, 1,030,000)。内訳の和も同じ範囲に入る必要がある。
    parts = ['new', 'ret', 'cont']
    # 各成分を [lo, lo+10000) の一様分布と見て、和が総数範囲に入るよう中点を取る
    def solve(lo, total_lo, total_exact=None):
        base = sum(lo[k] for k in parts)
        tot_lo = total_exact if total_exact else total_lo
        slack = tot_lo - base                    # 和が総数に届くまでの不足分
        # 不足分を3成分に等分（各成分は [0,10000) の範囲内でしか動かせない）
        add = max(0.0, min(slack / 3.0, 10_000.0))
        return {k: lo[k] + add for k in parts}
    a70 = solve(lo70, lo70['total'])
    a80 = solve(lo80, lo80['total'], EXACT_TOTAL_20260720)
    step = {k: a80[k] / a70[k] for k in parts}
    step['total'] = EXACT_TOTAL_20260720 / (lo70['total'] + (sum(a70[k] for k in parts) - sum(lo70[k] for k in parts)))
    # 総数は正確値どうしの比が取れないので、Lv70超側は内訳の和で代用する
    step['total'] = EXACT_TOTAL_20260720 / sum(a70[k] for k in parts)
    return step, a70, a80


def load():
    with open(CENSUS) as _f:
        rows = [r for r in csv.DictReader(_f) if r['normalized_64d']]
    return rows


def norm64(r):
    """窓長正規化。継続はストック、新規＋復帰はフローとして扱う。
    normalized_64d = 継続 + (新規+復帰) × 64/窓長"""
    w = float(r['window_days'])
    return (float(r['continuing_scaled'])
            + (float(r['new_scaled']) + float(r['returning_scaled'])) * 64.0 / w)


REGS = ['Lv36以上', 'Lv60超', 'Lv70超', 'Lv80超']


def main():
    hdr("A. 足切り段差を生データから導出する")
    step, a70, a80 = cutoff_steps()
    print("  2026-07-20 の同日ペア（記事表記は切り捨て → 真値は [x万, x+1万)）")
    print(f"  正確な総数（記事が明記）= {EXACT_TOTAL_20260720:,}")
    print(f"\n  {'成分':<8s}{'Lv70超(推定)':>14s}{'Lv80超(推定)':>14s}{'段差':>10s}")
    for k in ('new', 'ret', 'cont'):
        print(f"  {k:<8s}{a70[k]:>14,.0f}{a80[k]:>14,.0f}{step[k]:>10.4f}")
    print(f"  {'total':<8s}{sum(a70[k] for k in ('new','ret','cont')):>14,.0f}"
          f"{EXACT_TOTAL_20260720:>14,.0f}{step['total']:>10.4f}")
    print("\n  ※ 加法制約（内訳の和＝総数）を課したうえで、各成分を切り捨て範囲の中で解いている。")
    print("     この段差は**1回の観測**からしか取れない。他の3段は測定されていない。")

    hdr("B. 窓長正規化と足切り統一 — 系列を作り直す")
    rows = load()
    # 段差の累乗でレジームを Lv80超 に揃える
    def factor(reg):
        n = REGS.index('Lv80超') - REGS.index(reg)
        # 測定できたのは Lv70超→Lv80超 の1段だけ。他の段も同じ比と仮定する（未検証の仮定）
        return step['total'] ** n
    ser = []
    for r in rows:
        v_own = norm64(r)
        ser.append((r['date'], r['regime'], v_own, v_own * factor(r['regime'])))
    # CSV の normalized_64d と自前計算が一致するか
    dmax = max(abs(norm64(r) / float(r['normalized_64d']) - 1) for r in rows)
    print(f"  自前の窓長正規化と CSV の normalized_64d の最大相対差: {dmax:.2e}")
    print(f"  → {'一致（CSV は同じ式で作られている）' if dmax < 1e-6 else '**不一致。式が違う**'}")
    print(f"\n  {'日付':<12s}{'レジーム':<10s}{'norm64':>12s}{'Lv80超統一':>13s}")
    for d, rg, a, b in ser[-5:]:
        print(f"  {d:<12s}{rg:<10s}{a:>12,.0f}{b:>13,.0f}")
    K1 = {d: b for d, _, _, b in ser}
    print(f"\n  直近（2026-07-20）= {K1['2026-07-20']:,.0f}")
    print(f"  観測最大 = {max(K1.values()):,.0f}（{max(K1, key=lambda k: K1[k])}）")

    hdr("C. 再捕捉率 ρ — 同一レジームのペアだけを使う")
    # ρ = 継続_t / 総数_{t-1}。窓長で補正する。
    # 継続は前回窓（母集団プール）と今回窓の両方に依存するので、両方を統制する。
    pairs = []
    for i in range(1, len(rows)):
        a, b = rows[i - 1], rows[i]
        if a['regime'] != b['regime']:
            continue                      # 足切り改定をまたぐペアは除外
        pairs.append((b['date'], float(b['continuing_scaled']) / float(a['raw_total']),
                      float(b['window_days']), float(a['window_days']), b['regime']))
    print(f"  同一レジームのペア n={len(pairs)}")
    X = [[1.0, math.log(w), math.log(pw)] for _, _, w, pw, _ in pairs]
    Y = [math.log(y) for _, y, _, _, _ in pairs]

    def lstsq(X: list[list[float]], Y: list[float]):
        n, k = len(X), len(X[0])
        A = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
        v = [sum(X[i][a] * Y[i] for i in range(n)) for a in range(k)]
        M = [A[i][:] + [v[i]] for i in range(k)]
        for c in range(k):
            p = max(range(c, k), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]
            for r in range(k):
                if r == c: continue
                f = M[r][c] / M[c][c]
                for j in range(c, k + 1): M[r][j] -= f * M[c][j]
        return [M[i][k] / M[i][i] for i in range(k)]
    b = lstsq(X, Y)
    rho64 = math.exp(b[0] + b[1] * math.log(64) + b[2] * math.log(64))
    print(f"  log(ρ) = {b[0]:.4f} + {b[1]:.4f}·log(今回窓) + {b[2]:.4f}·log(前回窓)")
    print(f"  → 64日換算の ρ = **{rho64:.4f}**")
    # 7.x 世代だけ
    p7 = [y for d, y, w, pw, _ in pairs if d >= '2024-07']
    print(f"  7.x 期の生の ρ（{len(p7)}点）の幾何平均 = {math.exp(st.mean(math.log(x) for x in p7)):.4f}")
    print("  ※ **足切りレジームと世代が交絡している**ので、世代別の ρ は識別できない。")

    hdr("D. 流入 I — 直近の新規＋復帰")
    inflow = []
    for r in rows[-5:]:
        w = float(r['window_days'])
        f64 = (float(r['new_scaled']) + float(r['returning_scaled'])) * 64.0 / w
        inflow.append((r['date'], r['regime'], f64, f64 * factor(r['regime'])))
    print(f"  {'日付':<12s}{'レジーム':<10s}{'流入(64日)':>13s}{'Lv80超統一':>13s}")
    for d, rg, a, bb in inflow:
        print(f"  {d:<12s}{rg:<10s}{a:>13,.0f}{bb:>13,.0f}")
    I = st.mean(x[3] for x in inflow)
    I_ex = st.mean(x[3] for x in inflow[:-1])
    print(f"\n  5点平均 I = **{I:,.0f}**")
    print(f"  直近1点を除くと I = {I_ex:,.0f}（**{I/I_ex-1:+.1%}**）")
    print(f"  → **最新の1点が平均を {I/I_ex-1:+.0%} 押し上げている。** ここが最大の弱点である。")

    hdr("E. 定常値と 8.x 周期平均")
    S0 = K1['2026-07-20']
    Sstar = I / (1 - rho64)
    print(f"  定常値 S* = I/(1−ρ) = {I:,.0f}/(1−{rho64:.4f}) = **{Sstar:,.0f}**")
    print(f"  現在 S_0 = {S0:,.0f} → S* は現在の {Sstar/S0-1:+.1%}")
    print("\n  **S* は ρ に双曲線的に効く。** ρ を ±0.01 動かすと:")
    for dr in (-0.02, -0.01, 0.0, 0.01, 0.02):
        r_ = rho64 + dr
        print(f"    ρ={r_:.4f} → S* = {I/(1-r_):>9,.0f}（{I/(1-r_)/Sstar-1:+.1%}）")

    # 8.x を素朴にシミュレートする（ローンチの山を掛けない素の再帰）
    hdr("F. 主指標 — 素の再帰式だけで 8.x 周期平均を出す")
    print("""  ここでは**ローンチ倍率も 8.0 後の I 倍率もシナリオ確率も使わない。**
  「今の ρ と今の I がこのまま続いたら」という最も素朴な経路である。
  既存モデルはここにローンチの山と3シナリオを乗せている。""")
    # 64日刻みで 8.x 周期（2027-01 〜 2029-06、約 927日）を回す
    N = round(927 / 64)
    S, path = S0, []
    for _ in range(N):
        S = rho64 * S + I
        path.append(S)
    cyc8_naive = st.mean(path)
    # 7.x 周期平均（実績、Lv80超統一・norm64）
    c7 = [v for d, v in K1.items() if '2024-07' <= d <= '2026-07-20']
    cyc7 = st.mean(c7)
    print(f"\n  7.x 周期平均（実績 {len(c7)}点）= **{cyc7:,.0f}**")
    print(f"  8.x 周期平均（素の再帰、{N}ステップ）= **{cyc8_naive:,.0f}**")
    print(f"  → 主指標（素の再帰）= **{cyc8_naive/cyc7-1:+.1%}**")
    print("""
  ※ **この素の値と、既存モデルの確率加重値（−6.6%）・バイアス補正後（−11.0%）は
     別の量である。** 素の再帰は「ローンチの山が無い世界」なので低く出る。
     既存モデルはローンチ倍率 1.7434 と 3シナリオを乗せている。""")

    hdr("G. 何が主指標を動かすか — 一次感度")
    base = cyc8_naive / cyc7 - 1
    def run(rho_=None, I_=None, S0_=None):
        r_, i_, s_ = rho_ or rho64, I_ or I, S0_ or S0
        S, p = s_, []
        for _ in range(N):
            S = r_ * S + i_; p.append(S)
        return st.mean(p) / cyc7 - 1
    print(f"  {'動かす前提':<26s}{'低位':>10s}{'高位':>10s}{'幅':>9s}")
    SENS = [('ρ ±0.02', run(rho_=rho64-0.02), run(rho_=rho64+0.02)),
            ('I ±10%', run(I_=I*0.9), run(I_=I*1.1)),
            ('I（直近1点を除く）', run(I_=I_ex), base),
            ('足切り段差 ±1%', None, None)]
    for name, lo, hi in SENS[:3]:
        print(f"  {name:<26s}{lo:>10.1%}{hi:>10.1%}{abs(hi-lo)*100:>8.1f}pt")
    print(f"\n  基準（素の再帰）= {base:+.1%}")
    print("""
  → **ρ と I の2つだけで、主指標は十数ポイント動く。**
     どちらも「1回しか測れていない」「識別できない」という弱さを抱えている。
     **主指標を1つの数字として提示するのは、この構造では妥当でない。**""")


if __name__ == "__main__":
    main()
