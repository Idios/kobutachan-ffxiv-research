#!/usr/bin/env python3
"""Phase 7 予測エンジン v0.5（第3次監査を反映。params.py から正典値を import）"""
import math
import statistics as st
import sys
from datetime import date, timedelta

sys.path.insert(0, 'scripts')
from params import *

STEP = 64; START = date(2026, 7, 20); END = date(2029, 12, 31)


def simulate(rho_lv80, i_mult=1.0, launches=(), coef=FLOW_COEF_CENTRAL, bfs=BASE_FLOWSHARE,
             i_base=I_BASE_LV80, undershoot=True, e8=E8_ASSUMED, horizon=END):
    """S_{t+1}=ρ_t·S_t+I_t 。全て norm64/Lv80超。中心モデルは coef=0（ρ 一定）。"""
    n = (horizon - START).days // STEP + 2
    s = float(K1_NOW); t = START; out = [(START, s)]; fs_prev = bfs; since = None
    for _ in range(n):
        t2 = t + timedelta(days=STEP)
        I = i_base * (i_mult if t2 > e8 else 1.0)
        if any(t < L <= t2 for L in launches): I *= LAUNCH_MULT; since = 0
        elif undershoot and since is not None and since < 2: I *= UNDERSHOOT; since += 1
        rho = min(rho_lv80 * math.exp(coef * (fs_prev - bfs)), RHO_CAP_LV80)
        s2 = rho * s + I; fs_prev = I / s2 if s2 > 0 else bfs
        s = s2; out.append((t2, s)); t = t2
    return out


def value_at(ser, target):
    for i in range(len(ser) - 1):
        (d0, v0), (d1, v1) = ser[i], ser[i + 1]
        if d0 <= target <= d1: return v0 + (v1 - v0) * (target - d0).days / max((d1 - d0).days, 1)
    return ser[-1][1]


def annual_mean(ser, a, b):
    v = [x[1] for x in ser if a <= x[0] <= b]; return st.mean(v) if v else None


# シナリオは **観測された世代間変動** で定義する。
# ρ の95%CI を絶対水準に乗じると S*=I/(1−ρ) の双曲性で非現実的な値になるため使わない。
# 【第3次監査 C3】「7.x は観測中で最高の ρ」は足切りレジームとの交絡により識別されて
# いないため、Bull を ρ で作らない根拠としては使えない。それでも Bull を I で作るのは
# Phase 4 の RQ2 回答（崩れたのは新規獲得であって定着率ではない）との整合による。
SCEN = [('Bear', RHO_LV80 * RHO_BEAR_RATIO, 1.00, 0.25),   # 定着率が6.x水準へ回帰
        ('Base', RHO_LV80,                   1.05, 0.50),   # 7.x水準を維持
        ('Bull', RHO_LV80,                   1.15, 0.25)]   # 7.x維持＋流入回復

# 7.x 周期の観測9点（norm64、足切りを Lv80超 に統一済み）。位相整合比較の基準。
CYC7_RAW = [(date(2024, 8, 27), 1374616), (date(2024, 11, 4), 1139767),
            (date(2024, 12, 29), 1030585), (date(2025, 5, 25), 930807),
            (date(2025, 9, 27), 888482), (date(2025, 11, 30), 824073),
            (date(2026, 2, 23), 866791), (date(2026, 4, 19), 788546)]
CYC7 = [(d, v * CUTOFF_STEP['total']) for d, v in CYC7_RAW] + [(date(2026, 7, 20), 853595.0)]
CYC7_MEAN = st.mean([v for _, v in CYC7])          # 等観測重み（単純平均）
E7 = date(2024, 7, 2)
CYC7_X = [(d - E7).days for d, _ in CYC7]


def timewt(vals, xs=None):
    """台形則による時間加重平均（第4次監査 F1）"""
    x = xs or CYC7_X
    return sum((vals[i] + vals[i+1]) / 2 * (x[i+1] - x[i]) for i in range(len(x)-1)) / (x[-1] - x[0])


CYC7_MEAN_TW = timewt([v for _, v in CYC7])        # 時間加重（−2.8%）


def build(coef=FLOW_COEF_CENTRAL, bfs=BASE_FLOWSHARE, i_base=I_BASE_LV80, g9=927,
          e8=E8_ASSUMED, scen=None):
    d9 = e8 + timedelta(days=g9); res = {}
    for lab, rho, im, w in (scen or SCEN):
        ser = simulate(rho, im, (e8, d9), coef=coef, bfs=bfs, i_base=i_base, e8=e8)
        ser_h = simulate(rho, im, tuple(L for L in (e8, d9) if L <= END),
                         coef=coef, bfs=bfs, i_base=i_base, e8=e8)
        cyc = [x[1] for x in ser if e8 < x[0] < d9]
        # 【第3次監査・軽微】7.x と同一位相（発売後日数）でサンプリングし直した平均も出す
        cyc_ph = [value_at(ser, e8 + timedelta(days=x)) for x in CYC7_X]
        res[lab] = {'w': w, 'rho': rho, 'im': im, 'd9': d9,
                    'trough': min(cyc), 'peak': max(x[1] for x in ser
                                                  if e8 < x[0] < e8 + timedelta(days=200)),
                    'end': value_at(ser_h, END), 'cyc': st.mean(cyc), 'cyc_ph': st.mean(cyc_ph),
                    'cyc_tw': timewt(cyc_ph),
                    'fy2030': annual_mean(ser, date(2029, 4, 1), date(2030, 3, 31))}
    return res


def wavg(r, k): return sum(r[x][k] * r[x]['w'] for x in r)


def cc_year(kr, eps=None, drift=None, pulse=True):
    """FY2026.3 の実績 CC 350億にアンカーした年度CC売上"""
    e = EPS_CENTRAL if eps is None else eps
    d = REV_DRIFT_4Y if drift is None else drift
    return 350 * kr ** e * d + (PULSE_LAUNCH_Q if pulse else 0.0)


def to_nominal(ccv, usd=150.0, s=S_MMO):
    I = usd / 112.38
    return ccv / ((1 - s) + s / I)


if __name__ == '__main__':
    r = build(); d9 = E8_ASSUMED + timedelta(days=927)

    print("=== §0 シナリオ（中心モデル: ρ 一定、結合なし）===")
    print(f"{'':>6s}{'ρ(Lv80)':>9s}{'I倍率':>7s}{'8.x周期平均':>12s}{'vs7.x(等観測)':>13s}"
          f"{'vs7.x(時間加重)':>15s}{'FY2030.3':>10s}{'vs FY25':>9s}{'vs FY26':>9s}")
    for lab in ['Bear', 'Base', 'Bull']:
        d = r[lab]
        print(f"{lab:>6s}{d['rho']:9.4f}{d['im']:7.2f}{d['cyc']:12,.0f}{d['cyc']/CYC7_MEAN-1:+13.1%}"
              f"{d['cyc_tw']/CYC7_MEAN_TW-1:+15.1%}{d['fy2030']:10,.0f}"
              f"{d['fy2030']/K1_FY_MEAN_LV80[2025]-1:+9.1%}{d['fy2030']/K1_FY_MEAN_LV80[2026]-1:+9.1%}")
    print(f"  確率加重: 8.x周期平均 {wavg(r,'cyc'):,.0f}"
          f" (**等観測 {wavg(r,'cyc')/CYC7_MEAN-1:+.1%} / 時間加重 {wavg(r,'cyc_tw')/CYC7_MEAN_TW-1:+.1%}**)"
          f" / FY2030.3 {wavg(r,'fy2030'):,.0f} ({wavg(r,'fy2030')/K1_FY_MEAN_LV80[2025]-1:+.1%} vs FY2025.3)")
    print(f"  基準: 7.x周期平均(観測9点) 等観測 {CYC7_MEAN:,.0f} / 時間加重 {CYC7_MEAN_TW:,.0f}"
          f" / FY2025.3 {K1_FY_MEAN_LV80[2025]:,} / FY2026.3 {K1_FY_MEAN_LV80[2026]:,}")
    print(f"  【第4次監査】バックキャストによる上方バイアス補正後の目安:"
          f" 等観測 {wavg(r,'cyc')/(1+BACKCAST_BIAS_CYC)/CYC7_MEAN-1:+.1%}"
          f" / 時間加重 {wavg(r,'cyc_tw')/(1+BACKCAST_BIAS_CYC)/CYC7_MEAN_TW-1:+.1%}")
    print("  谷/ピーク: " + " ".join(f"{k} {r[k]['trough']:,.0f}/{r[k]['peak']:,.0f}"
                                    for k in ['Bear', 'Base', 'Bull']))

    print("\n=== §1 感度: ρ の推定（周辺レンジの一次元摂動。第6次監査 R6-1 で「最大の分散源」の格付けは撤回）===")
    print(f"{'':>34s}{'ρ(Lv80)':>9s}{'Base 8.x周期':>13s}{'vs7.x':>8s}{'加重':>8s}")
    for lab, rho, ratio in [('中心: ②, 一律1段換算', RHO_LV80, RHO_BEAR_RATIO),
                            ('【棄却】②+足切り段数統制', RHO_LV80_REGIME, RHO_BEAR_RATIO_RANGE[1]),
                            ('バックキャスト下端 ρ=0.74', 0.74, RHO_BEAR_RATIO),
                            ('バックキャスト上端 ρ=0.80', 0.80, RHO_BEAR_RATIO),
                            ('③（fs項あり）@運転点', 0.7640*CUTOFF_STEP['cont']/CUTOFF_STEP['total'],
                             RHO_BY_GEN_F3['6.x']/RHO_BY_GEN_F3['7.x']),
                            ('【使用禁止】誤仕様①+生fs', 0.740*CUTOFF_STEP['cont']/CUTOFF_STEP['total'],
                             RHO_BY_GEN_BADSPEC['6.x']/RHO_BY_GEN_BADSPEC['7.x'])]:
        sc = [('Bear', rho*ratio, 1.00, 0.25), ('Base', rho, 1.05, 0.50), ('Bull', rho, 1.15, 0.25)]
        rr = build(scen=sc)
        print(f"  {lab:<32s}{rho:9.4f}{rr['Base']['cyc']:13,.0f}"
              f"{rr['Base']['cyc']/CYC7_MEAN-1:+8.1%}{wavg(rr,'cyc')/CYC7_MEAN-1:+8.1%}")

    print("\n=== §2 感度: I_base（**第3次監査 C4**）===")
    for lab, ib in [(f'直近5回平均 {I_BASE_LV80:,}（中心）', I_BASE_LV80),
                    (f'2026-07-20 を除く4回 {I_BASE_EX0720:,}', I_BASE_EX0720),
                    ('【使用禁止】足切り混在 191,905', I_BASE_MIXED)]:
        rr = build(i_base=ib)
        print(f"  {lab:<30s}: Base 8.x周期 {rr['Base']['cyc']:,.0f} ({rr['Base']['cyc']/CYC7_MEAN-1:+.1%})"
              f"  加重 {wavg(rr,'cyc')/CYC7_MEAN-1:+.1%}")

    print("\n=== §3 感度: ρ–I 結合（中心では 0。構造方程式として使わない）===")
    for lab, c in [('中心（結合なし） 0', FLOW_COEF_CENTRAL), ('③ -0.301', FLOW_COEF),
                   ('CI上端 +0.317', FLOW_COEF_CI[1]), ('④ -0.783', FLOW_COEF_NOLAUNCH),
                   ('CI下端 -0.919', FLOW_COEF_CI[0]), ('⑤ -0.160', FLOW_COEF_REGIME)]:
        rr = build(coef=c)
        print(f"  {lab:<20s}: Base 8.x周期 {rr['Base']['cyc']:,.0f} ({rr['Base']['cyc']/CYC7_MEAN-1:+.1%})")
    print(f"  ※ ρ は観測実測最大 {RHO_CAP_LV80:.4f}(Lv80超) で頭打ち。採用パラメータでは発散しない。")

    print("\n=== §4 感度: 9.0 の時期（Base 固定）===")
    for g9, lab in [(760, '2029-02'), (852, '2029-05'), (927, '2029-07'),
                    (1035, '2029-11'), (1096, '2030-01'), (1250, '2030-06')]:
        rr = build(g9=g9); d = rr['Base']; dd9 = E8_ASSUMED + timedelta(days=g9)
        ph = f"9.0後{(END-dd9).days/30.44:.1f}ヶ月" if END >= dd9 else f"8.x位相{(END-E8_ASSUMED).days/g9:.2f}"
        kr = d['fy2030'] / K1_FY_MEAN_LV80[2026]
        inhz = date(2029, 4, 1) <= dd9 <= date(2030, 3, 31)
        print(f"  9.0={lab}: 2029-12 {d['end']:,.0f}  FY2030.3平均 {d['fy2030']:,.0f}"
              f"  CC {cc_year(kr, pulse=inhz):.0f}億{'' if inhz else '（パルス無し）'}  {ph}")

    print("\n=== §5 K4a（売上）===")
    print("  CC = 350億 × (K1比 vs FY2026.3)^0.845 × 0.913（キャラ単価4年逓減） + 9.0パルス40.1億")
    print(f"\n{'':>6s}{'K1比':>8s}{'CC':>8s}{'vs350億':>9s}{'名目@150':>10s}"
          f"{'営利(Phase6原案)':>20s}{'営利(R4適用)':>17s}")
    tl = th = tl4 = th4 = 0
    for lab in ['Bear', 'Base', 'Bull']:
        kr = r[lab]['fy2030'] / K1_FY_MEAN_LV80[2026]
        v = cc_year(kr); nom = to_nominal(v); m, m4 = MARGIN[lab], MARGIN_R4[lab]; w = r[lab]['w']
        tl += nom*m[0]*w; th += nom*m[1]*w; tl4 += nom*m4[0]*w; th4 += nom*m4[1]*w
        print(f"{lab:>6s}{kr:8.3f}{v:8.0f}{v/350-1:+9.1%}{nom:10.0f}"
              f"{f'{nom*m[0]:.0f}〜{nom*m[1]:.0f}億':>20s}{f'{nom*m4[0]:.0f}〜{nom*m4[1]:.0f}億':>17s}")
    print(f"  確率加重 営業利益: Phase6原案 {tl:.0f}〜{th:.0f}億 / **R4適用 {tl4:.0f}〜{th4:.0f}億**"
          f"   （FY2026.3 実績 151億）")

    print("\n  --- 感度: 弾力性とキャラ単価ドリフト（Base）---")
    kr = r['Base']['fy2030'] / K1_FY_MEAN_LV80[2026]
    for nm, e in EPS.items():
        print(f"    ε={e:<5} ({nm:12s}) ドリフト有 {cc_year(kr,eps=e):5.0f}億"
              f" / 無 {cc_year(kr,eps=e,drift=1.0):5.0f}億")
    print("  --- 感度: 足切り未測定2段の仮定がドリフトに与える影響（C6）---")
    for u in sorted(REV_DRIFT_SENS, reverse=True):
        dr, oos = REV_DRIFT_SENS[u]
        print(f"    未測定段差={u:.5f} → 4年ドリフト {dr:.4f}  水準モデル真OOS {oos}/4"
              f"  → Base CC {cc_year(kr,drift=dr):.0f}億")

    print("\n=== §6 K3 下限プロキシ（拡張『開始』数 = 0.916 × K1）===")
    for lab in ['Bear', 'Base', 'Bull']:
        print(f"  {lab:5s}: FY2030.3 {r[lab]['fy2030']*0.916:,.0f}")
