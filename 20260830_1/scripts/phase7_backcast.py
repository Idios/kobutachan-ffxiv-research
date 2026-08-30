#!/usr/bin/env python3
"""
Phase 7 — 完了した 7.x 周期に対するバックキャスト検証（第4次監査 M7 で新設）

【なぜ必要か】Phase 8 §5-1（根本原因 D-7）は「検証を名乗るには (a)別のデータ /
(b)別の標本 / (c)別の識別戦略 / (d)モデルが使っていない情報 のいずれかが要る」と
書いた。**予測モデルそのものを、完了した 7.x 周期に当てて外す量を測る**のは (b) に
該当する実行可能な検証だが、第3次監査までまったく行われていなかった。

【何を測るか】7.0 発売直前の観測水準（2024-06-12）から `S_{t+1} = ρ·S_t + I` を回し、
7.x の各観測点と突き合わせる。ρ・I はシナリオが 8.x に対して使う値そのもの。

【重要な限界】ρ も I も 7.x のデータから推定されているので、これは真の
out-of-sample ではない。**モデルの関数形と初期条件の妥当性を測るだけである。**
それでもパラメータ選択（ρ の3通り、I の2通り）の間で優劣はつく。

使い方: python3 scripts/phase7_backcast.py
"""
import sys, math, csv, statistics as st
from datetime import date, timedelta
sys.path.insert(0, 'scripts')
from params import *
# 【第13次】バックキャストは**実測を再現する倍率**を使う（推定用の LAUNCH_MULT とは別物）
LAUNCH_MULT = BACKCAST_LAUNCH_MULT

E7 = date(2024, 7, 2)
STEP = 64


def load_obs():
    """7.x の観測点（norm64、足切りを Lv80超 に統一）"""
    out = []
    for r in csv.DictReader(open('data/census_normalized.csv')):
        if not r['normalized_64d']: continue
        y, m, d = map(int, r['date'].split('-')); dt = date(y, m, d)
        if dt < date(2024, 6, 1): continue
        out.append((dt, float(r['normalized_64d']) * regime_factor(r['regime'])))
    return sorted(out)


OBS = load_obs()
S_START = [v for d, v in OBS if d == date(2024, 6, 12)][0]


def sim(rho, i_base, start_v, start_d, end_d, launch=E7):
    s = start_v; t = start_d; out = [(t, s)]; since = None
    while t < end_d + timedelta(days=STEP):
        t2 = t + timedelta(days=STEP)
        I = i_base
        if t < launch <= t2: I *= LAUNCH_MULT; since = 0
        elif since is not None and since < 2: I *= UNDERSHOOT; since += 1
        s = rho * s + I; out.append((t2, s)); t = t2
    return out


def at(ser, target):
    for i in range(len(ser) - 1):
        (d0, v0), (d1, v1) = ser[i], ser[i + 1]
        if d0 <= target <= d1: return v0 + (v1 - v0) * (target - d0).days / max((d1 - d0).days, 1)
    return ser[-1][1]


def score(rho, i_base):
    ser = sim(rho, i_base, S_START, date(2024, 6, 12), date(2026, 7, 20))
    pts = [(d, v, at(ser, d)) for d, v in OBS if d > E7]
    errs = [p / v - 1 for _, v, p in pts]
    # 位相整合の周期平均（7.x の観測オフセットで再サンプル）
    cyc_pred = st.mean([at(ser, d) for d, _ in OBS if d > E7])
    cyc_obs = st.mean([v for d, v in OBS if d > E7])
    return pts, errs, cyc_pred, cyc_obs


if __name__ == '__main__':
    W = 76
    print("=" * W)
    print("A. 7.x 周期のバックキャスト（2024-06-12 の Lv80超統一水準から回す）")
    print("=" * W)
    print(f"  開始値 S(2024-06-12) = {S_START:,.0f}（norm64, Lv80超統一）")
    print(f"  7.0 発売 {E7}、ローンチ窓 ×{LAUNCH_MULT}、直後2窓 ×{UNDERSHOOT}\n")

    cases = [(f'中心: ρ={RHO_LV80:.4f} / I={I_BASE_LV80:,}', RHO_LV80, I_BASE_LV80),
             (f'C4代替: ρ={RHO_LV80:.4f} / I={I_BASE_EX0720:,}', RHO_LV80, I_BASE_EX0720),
             (f'段数統制版: ρ={RHO_LV80_REGIME:.4f} / I={I_BASE_LV80:,}', RHO_LV80_REGIME, I_BASE_LV80),
             (f'段数統制版＋C4: ρ={RHO_LV80_REGIME:.4f} / I={I_BASE_EX0720:,}', RHO_LV80_REGIME, I_BASE_EX0720),
             (f'Bear: ρ={RHO_LV80*RHO_BEAR_RATIO:.4f} / I={I_BASE_LV80:,}', RHO_LV80 * RHO_BEAR_RATIO, I_BASE_LV80),
             ('【使用禁止】誤仕様 ρ=0.7693', 0.740 * CUTOFF_STEP['cont'] / CUTOFF_STEP['total'], I_BASE_LV80)]

    dates = [d for d, _ in OBS if d > E7]
    print(f"{'':>34s}" + "".join(f"{d.strftime('%y-%m'):>8s}" for d in dates) + f"{'MAE':>7s}{'周期平均誤差':>12s}")
    print(f"{'（実測）':>34s}" + "".join(f"{v/1000:8.0f}" for d, v in OBS if d > E7) + "  ※単位:千")
    best = None
    for lab, rho, ib in cases:
        pts, errs, cp, co = score(rho, ib)
        mae = st.mean([abs(e) for e in errs])
        print(f"{lab:<34s}" + "".join(f"{e:+8.1%}" for e in errs) + f"{mae:7.1%}{cp/co-1:+12.1%}")
        if best is None or mae < best[1]: best = (lab, mae)
    print(f"\n  → 最小 MAE: {best[0]}（{best[1]:.1%}）")

    print("\n" + "=" * W)
    print("B. 【第4次監査 F2】ρ の識別幅の上端 0.8303 はバックキャストで棄却される")
    print("=" * W)
    print(f"{'ρ(Lv80超)':>12s}{'出所':<34s}{'MAE':>8s}{'2026-07-20 誤差':>16s}")
    for rho, src in [(RHO_LV80, '②＋直接測定の1段係数（採用）'),
                     (0.8000, '（参考）中間'),
                     (RHO_LV80_REGIME, '②＋段数係数の点推定 ×1.0871'),
                     (RHO_LV80 * RHO_BEAR_RATIO, '②の6.x水準（Bear）')]:
        pts, errs, cp, co = score(rho, I_BASE_LV80)
        print(f"{rho:12.4f}{src:<34s}{st.mean([abs(e) for e in errs]):8.1%}{errs[-1]:+16.1%}")

    print("\n  水準恒等式から各ペアで ρ を直接解く（I はカテゴリ別段差適用済み、Lv80超）:")
    prev = None; imp = []
    for d, v in OBS:
        if prev and d > E7:
            # その回の I（norm64, Lv80超）
            row = [r for r in csv.DictReader(open('data/census_normalized.csv')) if r['date'] == d.isoformat()][0]
            w = float(row['window_days']); k = 64.0 / w
            f = 1.0 if row['regime'] == 'Lv80超' else None
            nw = float(row['new_scaled']) * k * (1.0 if f else CUTOFF_STEP['new'])
            rt = float(row['returning_scaled']) * k * (1.0 if f else CUTOFF_STEP['ret'])
            I = nw + rt
            imp.append((d, (v - I) / prev[1]))
        prev = (d, v)
    print("   " + "  ".join(f"{d.strftime('%y-%m')} {r:.4f}" for d, r in imp))
    vals = [r for _, r in imp]
    ex = [r for d, r in imp if d not in (date(2024, 8, 27), date(2026, 7, 20))]
    print(f"   中央値 {st.median(vals):.4f} / 平均 {st.mean(vals):.4f}"
          f" / ローンチ窓(24-08)と最汚染点(26-07)を除く: 中央値 {st.median(ex):.4f} 平均 {st.mean(ex):.4f}")
    print(f"   → **観測は 0.73〜0.89 に散らばるが 0.83 超は2点のみ（うち1点はローンチ窓、1点は最汚染点）。**")
    print(f"      採用値 {RHO_LV80:.4f} は平均 {st.mean(vals):.4f} とほぼ一致。**0.8303 を定常値として使う根拠はない。**")

    print(f"\n  MAE スキャン（I={I_BASE_LV80:,} 固定）:")
    row = []
    for rr in [0.70, 0.72, 0.74, 0.76, 0.78, 0.79, 0.80, 0.81, 0.82, 0.83, 0.84]:
        _, e, _, _ = score(rr, I_BASE_LV80); row.append((rr, st.mean([abs(x) for x in e])))
    print("   " + "  ".join(f"{r:.2f}:{m:.1%}" for r, m in row))
    bestr = min(row, key=lambda x: x[1])
    ok = [r for r, m in row if m <= bestr[1] * 1.5]
    print(f"   最小 MAE は ρ={bestr[0]:.2f}（{bestr[1]:.1%}）。MAE が最小の1.5倍以内に収まるのは"
          f" **ρ ∈ [{min(ok):.2f}, {max(ok):.2f}]**")

    print("\n  【重要】ρ と I はバックキャスト上でトレードオフする。2次元スキャン（MAE %）:")
    IS = [140_000, 152_442, 168_634, 185_000, 200_000]
    print("    ρ＼I  " + "".join(f"{i/1000:8.0f}k" for i in IS))
    grid = []
    for rr in [0.74, 0.76, 0.78, 0.79, 0.80, 0.82, 0.84]:
        cells = []
        for ib in IS:
            _, e, _, _ = score(rr, ib); m = st.mean([abs(x) for x in e]); cells.append(m)
            grid.append((rr, ib, m))
        print(f"    {rr:.2f}  " + "".join(f"{c:9.1%}" for c in cells))
    bg = min(grid, key=lambda x: x[2])
    print(f"    → 最小 {bg[2]:.1%} @ ρ={bg[0]:.2f}, I={bg[1]:,}")
    ok2 = [(r, i) for r, i, m in grid if m <= bg[2]*1.5]
    print(f"    → MAE 最小の1.5倍以内: ρ ∈ [{min(r for r,_ in ok2):.2f}, {max(r for r,_ in ok2):.2f}]"
          f"、I ∈ [{min(i for _,i in ok2):,}, {max(i for _,i in ok2):,}]")
    print("    **ρ の上端 0.8303 は I をどう振っても MAE 最小の1.5倍以内に入らない。**")

    print("\n  【最重要】バックキャストが実際に制約しているのは ρ でも I でもなく S* = I/(1−ρ):")
    print(f"    {'ρ':>6s}{'I':>9s}{'MAE':>8s}{'S*':>10s}{'vs FY2026.3平均':>16s}")
    for r, i, m in sorted(grid, key=lambda x: x[2])[:8]:
        ss = i/(1-r)
        print(f"    {r:6.2f}{i:9,.0f}{m:8.1%}{ss:10,.0f}{ss/K1_NOW_FY_MEAN-1:+16.1%}")
    good = [i/(1-r) for r, i, m in grid if m <= bg[2]*1.5]
    print(f"    → 粗格子（この表、{len(grid)}組）での S* レンジ: {min(good):,.0f} 〜 {max(good):,.0f}")

    # ---- 第6次監査 R6-2: 粗格子と許容率の恣意性を潰す ----
    print("\n  【第6次監査 R6-2】上のレンジは**格子ノードそのもの**（700,000=140,000/0.20、")
    print("  770,833=185,000/0.24）で、刻みと許容率（1.5倍）の選び方に依存する。")
    print("  両方を振り直す:")
    s_ad = I_BASE_LV80/(1-RHO_LV80)
    print(f"    {'格子':<10s}{'組数':>6s}{'MAE最小':>9s}   " +
          "".join(f"{'×'+str(t):>26s}" for t in (1.25, 1.5, 2.0)))
    fine_by_tol = {}
    for lab, dr, di in (('粗(採用)', 0.02, 15_000), ('中', 0.01, 5_000), ('細', 0.005, 2_500)):
        gr = [0.72 + dr*i for i in range(int(round(0.10/dr))+1)]
        gi = [130_000 + di*i for i in range(int(round(80_000/di))+1)]
        gg = []
        for r_ in gr:
            for i_ in gi:
                _, e, _, _ = score(r_, i_)
                gg.append((r_, i_, st.mean([abs(x) for x in e])))
        bb = min(m for _, _, m in gg)
        cells = []
        for tol in (1.25, 1.5, 2.0):
            sel = [i_/(1-r_) for r_, i_, m in gg if m <= bb*tol]
            cells.append((min(sel), max(sel)))
            if lab == '細': fine_by_tol[tol] = (min(sel), max(sel))
        print(f"    {lab:<10s}{len(gg):>6d}{bb:>9.2%}   " +
              "".join(f"{a:>11,.0f}〜{b:<13,.0f}" for a, b in cells))
    print(f"\n    採用パラメータの S* = {s_ad:,.0f}"
          f"（FY2026.3平均比 {s_ad/K1_NOW_FY_MEAN-1:+.1%}）の判定:")
    for tol, (a, b) in sorted(fine_by_tol.items()):
        print(f"      細格子・許容率 ×{tol}: {a:,.0f}〜{b:,.0f} → "
              f"**{'域内' if a <= s_ad <= b else '域外'}**")

    # ---- 第7次監査 F3/B2: 探索する「箱」も未宣言のメタパラメータである ----
    print("\n  【第7次監査 F3】刻みと許容率を振っても、**探索範囲（箱）自体**が未宣言だった。")
    print("  細格子の S* 下端 684,211 は I の箱の床（130,000）上のノードである。箱を振る:")
    print(f"    {'箱':<28s}{'MAE最小':>8s}   " + "".join(f"{'×'+str(t):>24s}" for t in (1.25, 1.5)))
    BOXES = [('採用 ρ.72-.82 / I 130-210k', 0.72, 0.82, 130_000, 210_000),
             ('周辺レンジ ρ.74-.80 / I 140-200k', 0.74, 0.80, 140_000, 200_000),
             ('拡大 ρ.70-.86 / I 100-250k', 0.70, 0.86, 100_000, 250_000),
             ('広大 ρ.66-.88 / I 80-300k', 0.66, 0.88, 80_000, 300_000)]
    for lab, r0, r1, i0, i1 in BOXES:
        gr = [r0 + 0.005 * k for k in range(int(round((r1 - r0) / 0.005)) + 1)]
        gi = [i0 + 2_500 * k for k in range(int(round((i1 - i0) / 2_500)) + 1)]
        gg = []
        for r_ in gr:
            for i_ in gi:
                _, e, _, _ = score(r_, i_)
                gg.append((r_, i_, st.mean([abs(x) for x in e])))
        bb = min(m for _, _, m in gg)
        cells = []
        for tol in (1.25, 1.5):
            sel = [i_ / (1 - r_) for r_, i_, m in gg if m <= bb * tol]
            cells.append(f"{min(sel):,.0f}〜{max(sel):,.0f}"
                         f"{'[内]' if min(sel) <= s_ad <= max(sel) else '[外]'}")
        print(f"    {lab:<28s}{bb:>8.2%}   " + "".join(f"{c:>24s}" for c in cells))
    print("\n    → **『採用 S* は許容域の内か外か』は well-posed な判定ではない。**")
    print("       箱を広げれば ×1.25 でも域内、周辺レンジまで狭めれば ×1.25 で域外になる。")
    print("       判定は3つの未宣言メタパラメータ（刻み・許容率・箱）で反転する。")
    print("    → **v1〜v2 の『採用 S* は許容域の外側』は撤回するが、**")
    print("       **『域内である』とも主張しない。この検証は S* の可否を決められない。**")
    print("       残るのは下の実測差（格子・箱・許容率のいずれにも依存しない）だけである。")
    _, e_ad, cp_ad, co_ad = score(RHO_LV80, I_BASE_LV80)
    mae_ad = st.mean([abs(x) for x in e_ad])
    print(f"\n    ただし**格子に依存しない事実**は残る:")
    print(f"      採用点の MAE {mae_ad:.2%} は最良点 {min(m for _,_,m in gg):.2%} の "
          f"{mae_ad/min(m for _,_,m in gg):.2f} 倍")
    print(f"      7.x 周期平均の予測 {cp_ad:,.0f} 対 実測 {co_ad:,.0f} = **{cp_ad/co_ad-1:+.1%} の上振れ**")
    print(f"      → 中心予測は上方バイアスを持つ。バイアス補正は S* 制約ではなく**この実測差**を根拠にする。")

    print("\n" + "=" * W)
    print("C. 【第4次監査 F1】周期平均の平均化規約")
    print("=" * W)
    obs7 = [(d, v) for d, v in OBS if d > E7]
    simple = st.mean([v for _, v in obs7])
    # 時間加重（台形則、観測区間 56〜748日）
    xs = [(d - E7).days for d, _ in obs7]; ys = [v for _, v in obs7]
    trap = sum((ys[i] + ys[i+1]) / 2 * (xs[i+1] - xs[i]) for i in range(len(xs)-1)) / (xs[-1] - xs[0])
    print(f"  7.x 観測9点  単純平均（等観測重み） = {simple:,.0f}")
    print(f"              時間加重平均（台形、{xs[0]}〜{xs[-1]}日） = {trap:,.0f}  （{trap/simple-1:+.1%}）")
    print(f"  観測オフセットの平均 = {st.mean(xs):.1f}日（周期927日の等間隔なら463.5日）→ **前寄りに偏る**")
    print("  → 系列は単調減少なので、単純平均は真の周期平均より高く出る＝比較の分母が持ち上がる。")

    sys.path.insert(0, 'scripts')
    from phase7_forecast import simulate, value_at, SCEN
    d9 = E8_ASSUMED + timedelta(days=927)
    print(f"\n{'':>6s}{'8.x等間隔':>11s}{'vs単純平均':>11s}{'8.x同一位相':>12s}{'vs単純平均':>11s}"
          f"{'8.x時間加重':>12s}{'vs時間加重':>11s}")
    wsum = [0.0, 0.0, 0.0]
    for lab, rho, im, w in SCEN:
        ser = simulate(rho, im, (E8_ASSUMED, d9))
        eq = st.mean([v for d, v in ser if E8_ASSUMED < d < d9])
        ph = [value_at(ser, E8_ASSUMED + timedelta(days=x)) for x in xs]
        phm = st.mean(ph)
        tw = sum((ph[i] + ph[i+1]) / 2 * (xs[i+1] - xs[i]) for i in range(len(xs)-1)) / (xs[-1] - xs[0])
        print(f"{lab:>6s}{eq:11,.0f}{eq/simple-1:+11.1%}{phm:12,.0f}{phm/simple-1:+11.1%}"
              f"{tw:12,.0f}{tw/trap-1:+11.1%}")
        wsum[0] += eq * w; wsum[1] += phm * w; wsum[2] += tw * w
    print(f"  確率加重: 等間隔 {wsum[0]/simple-1:+.1%} / 同一位相 {wsum[1]/simple-1:+.1%}"
          f" / **時間加重どうし {wsum[2]/trap-1:+.1%}**")
    print("  → **主指標は平均化規約だけで動く。両方を併記すること。**")
