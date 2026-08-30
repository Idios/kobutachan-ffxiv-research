#!/usr/bin/env python3
"""
Phase 8 — グラフの生成（Phase 0 が要求しながら Phase 7 まで未作成だった成果物）

出力: charts/*.svg（依存ライブラリなし。SVG を直接書く）
  1. cycle-curves.svg   世代別の山→谷カーブ（位相正規化、足切り統一）
  2. forecast.svg       予測経路とシナリオ帯（観測実績と接続）
  3. tornado.svg        感度分析のトルネード
  4. backcast.svg       7.x 周期へのバックキャスト（予測 vs 実測）

使い方: python3 scripts/phase8_charts.py
"""
import sys, csv, os, math, statistics as st
from datetime import date, timedelta
sys.path.insert(0, 'scripts')
from params import *
import phase8_sensitivity as SE
_gA = SE.groupA
from phase7_forecast import (simulate, value_at, build, wavg, SCEN, CYC7, CYC7_MEAN,
                             CYC7_MEAN_TW, CYC7_X, E7)

OUT = 'charts'
os.makedirs(OUT, exist_ok=True)

# 2つのテーマで読める配色（背景を敷かず、線と文字は中間色に寄せる）
INK   = '#1f2328'
MUTED = '#6b7280'
GRID  = '#d1d5db'
C = {'Bear': '#c2410c', 'Base': '#1d4ed8', 'Bull': '#047857',
     '4.x': '#9ca3af', '5.x': '#6b7280', '6.x': '#f59e0b', '7.x': '#1d4ed8',
     'obs': '#111827', 'band': '#93c5fd'}

CSS = """
<style>
  .bg{fill:#ffffff}
  text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Hiragino Sans','Noto Sans JP',sans-serif}
  .ttl{font-size:17px;font-weight:700;fill:#1f2328}
  .sub{font-size:12px;fill:#6b7280}
  .ax{font-size:11px;fill:#6b7280}
  .lab{font-size:12px;fill:#1f2328}
  .note{font-size:11px;fill:#6b7280}
  .grid{stroke:#d1d5db;stroke-width:1}
  .axis{stroke:#9ca3af;stroke-width:1.2}
  @media (prefers-color-scheme: dark){
    .bg{fill:#0d1117}
    .ttl{fill:#e6edf3} .lab{fill:#e6edf3}
    .sub,.ax,.note{fill:#9ca3af}
    .grid{stroke:#30363d} .axis{stroke:#6b7280}
  }
</style>
"""


def svg(w, h, body, title, sub=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'{CSS}<rect class="bg" width="{w}" height="{h}"/>'
            f'<text class="ttl" x="24" y="30">{title}</text>'
            f'<text class="sub" x="24" y="50">{sub}</text>{body}</svg>')


def load_obs(unmeasured=None):
    """unmeasured: 未測定2段（Lv36以上→Lv60超、Lv60超→Lv70超）の仮定。
    既定（None）は params の −6.9% 流用。**Phase 2 §1 はこの流用を禁じている。**"""
    out = []
    for r in csv.DictReader(open('data/census_normalized.csv')):
        if not r['normalized_64d']: continue
        y, m, d = map(int, r['date'].split('-'))
        out.append((date(y, m, d),
                    float(r['normalized_64d']) * regime_factor(r['regime'], unmeasured)))
    return sorted(out)


OBS = load_obs()
# 【第5次監査 M4/M5】世代別カーブは **未測定2段 = 0%（無視）** で描く。
#   (a) `final-report.md` §1-1 と `phase4-player-dynamics.md` §1-3 が引用する谷比
#       （4.x 0.726 / 5.x 0.808 / 6.x 0.708 / 7.x 0.574）はこの仮定の行から取られている。
#   (b) −6.9% 流用の下では 5.x の最終点が 1.24 になり、Phase 4 §1-2 が
#       「仮定依存のため撤回する」と明記した「5.x は終盤に自世代ピークを超える」を復活させてしまう。
OBS_CYCLE = load_obs(unmeasured=1.0)
LAUNCH = {'4.x': date(2017, 6, 20), '5.x': date(2019, 7, 2),
          '6.x': date(2021, 12, 7), '7.x': date(2024, 7, 2)}
END_OF = {'4.x': date(2019, 7, 2), '5.x': date(2021, 12, 7),
          '6.x': date(2024, 7, 2), '7.x': E8_ASSUMED}


# ============================================================
# 1. 世代別カーブ
# ============================================================
def chart_cycles():
    """左: 絶対水準 / 右: 自世代ピーク基準の正規化（Phase 4 §1 の主張はこちら）"""
    W, H = 1000, 524
    T, B = 96, 86
    PW, PH = 380, H - T - B
    L1, L2 = 62, 560
    series = {}
    for g, l in LAUNCH.items():
        e = END_OF[g]
        pts = [((d - l).days / (e - l).days, v) for d, v in OBS_CYCLE if l <= d < e]
        if pts: series[g] = sorted(pts)
    norm = {g: max(v for p, v in s_ if p <= 0.25) for g, s_ in series.items()}
    ymax2 = max(v / norm[g] for g, s_ in series.items() for _, v in s_) * 1.06
    body = []

    def panel(L, ymax, getv, ylab, title):
        body.append(f'<text class="lab" x="{L}" y="{T-14}" style="font-weight:600">{title}</text>')
        n = 5
        for k in range(n + 1):
            val = ymax * k / n
            y = T + PH - (val / ymax) * PH
            body.append(f'<line class="grid" x1="{L}" y1="{y:.1f}" x2="{L+PW}" y2="{y:.1f}"/>')
            body.append(f'<text class="ax" x="{L-8}" y="{y+4:.1f}" text-anchor="end">{ylab(val)}</text>')
        for gx in range(0, 11, 2):
            x = L + gx / 10 * PW
            body.append(f'<text class="ax" x="{x:.1f}" y="{T+PH+18}" text-anchor="middle">{gx/10:.1f}</text>')
        body.append(f'<line class="axis" x1="{L}" y1="{T+PH}" x2="{L+PW}" y2="{T+PH}"/>')
        body.append(f'<line class="axis" x1="{L}" y1="{T}" x2="{L}" y2="{T+PH}"/>')
        # Phase 4 §1-1 の比較表は位相0.80までしか作られていない。それより右は次拡張前のサージ。
        xg = L + 0.8 * PW
        body.append(f'<line x1="{xg:.1f}" y1="{T}" x2="{xg:.1f}" y2="{T+PH}" '
                    f'stroke="{MUTED}" stroke-width="1" stroke-dasharray="3 3" opacity="0.8"/>')
        for g, pts in series.items():
            d = " ".join(f"{'M' if j==0 else 'L'}{L+p*PW:.1f},{T+PH-(getv(g,v)/ymax)*PH:.1f}"
                         for j, (p, v) in enumerate(pts))
            wd = 3 if g == '7.x' else 1.8
            body.append(f'<path d="{d}" fill="none" stroke="{C[g]}" stroke-width="{wd}"/>')
            for p, v in pts:
                body.append(f'<circle cx="{L+p*PW:.1f}" cy="{T+PH-(getv(g,v)/ymax)*PH:.1f}" '
                            f'r="{3 if g=="7.x" else 2.2}" fill="{C[g]}"/>')

    ymax1 = max(v for s_ in series.values() for _, v in s_) * 1.06
    panel(L1, ymax1, lambda g, v: v, lambda x: f"{x/10000:.0f}万",
          '① 絶対水準（足切りLv80超統一）')
    panel(L2, ymax2, lambda g, v: v / norm[g], lambda x: f"{x:.2f}",
          '② 自世代ピーク基準（Phase 4 §1）')
    for i, g in enumerate(['4.x', '5.x', '6.x', '7.x']):
        y = H - 34
        x = 62 + i * 150
        wd = 3 if g == '7.x' else 1.8
        body.append(f'<line x1="{x}" y1="{y}" x2="{x+24}" y2="{y}" stroke="{C[g]}" stroke-width="{wd}"/>')
        body.append(f'<text class="lab" x="{x+30}" y="{y+4}">{g}（{len(series[g])}点）</text>')
    body.append(f'<text class="note" x="{L2+PW-4}" y="{H-34+4}" text-anchor="end">'
                f'横軸=世代内の位相（0=拡張発売、1=次の拡張）</text>')
    body.append(f'<text class="note" x="{L1}" y="{H-10}">'
                f'破線=位相0.80。Phase 4 §1-1 の比較表はここまで。その右の立ち上がりは次拡張前のサージであり回復ではない</text>')
    open(f'{OUT}/cycle-curves.svg', 'w').write(svg(
        W, H, "".join(body), '世代別の活動キャラ数カーブ（位相正規化）',
        '「7.x が全位相で最低」が成り立つのは ② の自世代ピーク基準。① の絶対水準では 5.x を上回る位相もある'
        '　／　足切りの未測定2段は 0%（無視）と仮定'))


# ============================================================
# 2. 予測経路
# ============================================================
def chart_forecast():
    W, H = 980, 500
    L, R, T, B = 70, 180, 78, 60
    pw, ph = W - L - R, H - T - B
    d9 = E8_ASSUMED + timedelta(days=927)
    ser = {lab: simulate(rho, im, (E8_ASSUMED, d9)) for lab, rho, im, w in SCEN}
    x0, x1 = date(2021, 12, 7), date(2029, 12, 31)
    span = (x1 - x0).days
    ymax = 1_450_000
    fx = lambda d: L + max(0, min(1, (d - x0).days / span)) * pw
    fy = lambda v: T + ph - (v / ymax) * ph
    body = []
    for gy in range(0, 15, 2):
        y = fy(gy * 100000)
        body.append(f'<line class="grid" x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}"/>')
        body.append(f'<text class="ax" x="{L-8}" y="{y+4:.1f}" text-anchor="end">{gy*10}万</text>')
    for yr in range(2022, 2030):
        x = fx(date(yr, 1, 1))
        body.append(f'<text class="ax" x="{x:.1f}" y="{T+ph+18}" text-anchor="middle">{yr}</text>')
    # 拡張の発売線
    for lab, d in [('6.0', date(2021, 12, 7)), ('7.0', E7), ('8.0', E8_ASSUMED), ('9.0', d9)]:
        x = fx(d)
        dash = '' if d <= date(2026, 7, 20) else ' stroke-dasharray="4 3"'
        body.append(f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{T+ph}" stroke="{MUTED}" stroke-width="1"{dash} opacity="0.7"/>')
        body.append(f'<text class="ax" x="{x+4:.1f}" y="{T+12}">{lab}</text>')
    # Bear–Bull の帯
    pts_hi = [(d, v) for d, v in ser['Bull'] if d >= date(2026, 7, 20)]
    pts_lo = [(d, v) for d, v in ser['Bear'] if d >= date(2026, 7, 20)]
    poly = " ".join(f"{fx(d):.1f},{fy(v):.1f}" for d, v in pts_hi) + " " + \
           " ".join(f"{fx(d):.1f},{fy(v):.1f}" for d, v in reversed(pts_lo))
    body.append(f'<polygon points="{poly}" fill="{C["band"]}" opacity="0.28"/>')
    for lab in ['Bear', 'Base', 'Bull']:
        p = [(d, v) for d, v in ser[lab] if d >= date(2026, 7, 20)]
        dd = " ".join(f"{'M' if j==0 else 'L'}{fx(d):.1f},{fy(v):.1f}" for j, (d, v) in enumerate(p))
        body.append(f'<path d="{dd}" fill="none" stroke="{C[lab]}" stroke-width="{2.6 if lab=="Base" else 1.8}" stroke-dasharray="6 3"/>')
    # 観測
    ob = [(d, v) for d, v in OBS if d >= x0]
    dd = " ".join(f"{'M' if j==0 else 'L'}{fx(d):.1f},{fy(v):.1f}" for j, (d, v) in enumerate(ob))
    body.append(f'<path d="{dd}" fill="none" stroke="{C["obs"]}" stroke-width="2.4"/>')
    for d, v in ob:
        body.append(f'<circle cx="{fx(d):.1f}" cy="{fy(v):.1f}" r="2.6" fill="{C["obs"]}"/>')
    # 凡例
    items = [('観測（実績）', C['obs'], ''), ('Bull 25%', C['Bull'], ' stroke-dasharray="6 3"'),
             ('Base 50%', C['Base'], ' stroke-dasharray="6 3"'), ('Bear 25%', C['Bear'], ' stroke-dasharray="6 3"')]
    for i, (t, col, dsh) in enumerate(items):
        y = T + 16 + i * 22
        body.append(f'<line x1="{L+pw+18}" y1="{y}" x2="{L+pw+44}" y2="{y}" stroke="{col}" stroke-width="2.4"{dsh}/>')
        body.append(f'<text class="lab" x="{L+pw+50}" y="{y+4}">{t}</text>')
    r = build()
    body.append(f'<text class="note" x="{L+pw+18}" y="{T+16+4*22+16}">FY2030.3 平均</text>')
    for i, lab in enumerate(['Bull', 'Base', 'Bear']):
        body.append(f'<text class="note" x="{L+pw+18}" y="{T+16+4*22+32+i*16}">'
                    f'{lab} {r[lab]["fy2030"]/10000:.0f}万</text>')
    body.append(f'<text class="ax" x="{L+pw/2}" y="{H-16}" text-anchor="middle">'
                f'活動キャラ数（窓長64日換算・足切りLv80超統一）。破線は予測</text>')
    open(f'{OUT}/forecast.svg', 'w').write(svg(
        W, H, "".join(body), '3年予測 — 観測実績とシナリオ帯',
        '6.0ピーク132万からの下落は概ね完了。以後は拡張サイクルの周期変動が主になる'
        f'　／　ただし採用点はバックキャストで {BACKCAST_BIAS_CYC:+.1%} 上振れし、'
        f'S*制約下の主指標は {_gA()[2]:.1%}〜{_gA()[3]:.1%}'.replace('-', '−')))


# ============================================================
# 3. トルネード
# ============================================================
def chart_tornado():
    import phase8_sensitivity as S
    rows = []
    for grp, name, lo, hi, lodesc, hidesc in S.CASES:
        if '別途' in lodesc: continue
        a = S.case(**lo); b = S.case(**hi)
        if abs(a[0] - b[0]) < 0.002: continue
        rows.append((name, a[0], b[0], abs(a[0] - b[0]), grp))
    # 【第5次監査 M6】降順＝上が太い漏斗。
    # 【第6次監査 R6-14】ただし**群をまたいで1本に並べると較正基準の違う行が順位で混ざる**。
    # 群ごとにブロック化し、ブロック内でのみ降順に並べる。
    GORDER = {'B': 0, 'C': 1, 'D': 2, 'E': 3}
    rows.sort(key=lambda x: (GORDER.get(x[4], 9), -x[3]))
    base = S.BASE[0]
    W, H = 900, 90 + len(rows) * 34 + 60
    L, R, T = 250, 60, 86
    pw = W - L - R
    lo = min(min(r[1], r[2]) for r in rows) - 0.02
    hi = max(max(r[1], r[2]) for r in rows) + 0.02
    fx = lambda v: L + (v - lo) / (hi - lo) * pw
    body = []
    for t in [-0.30, -0.25, -0.20, -0.15, -0.10, -0.05, 0.0]:
        if not (lo <= t <= hi): continue
        x = fx(t)
        body.append(f'<line class="grid" x1="{x:.1f}" y1="{T-10}" x2="{x:.1f}" y2="{T+len(rows)*34}"/>')
        body.append(f'<text class="ax" x="{x:.1f}" y="{T-16}" text-anchor="middle">{t:+.0%}</text>')
    xb = fx(base)
    body.append(f'<line x1="{xb:.1f}" y1="{T-10}" x2="{xb:.1f}" y2="{T+len(rows)*34}" stroke="{INK}" stroke-width="1.6"/>')
    body.append(f'<text class="note" x="{xb:.1f}" y="{T+len(rows)*34+18}" text-anchor="middle">基準 {base:+.1%}</text>')
    for i, r in enumerate(rows):
        name, a, b, sp = r[0], r[1], r[2], r[3]
        y = T + i * 34 + 10
        x1_, x2_ = sorted([fx(a), fx(b)])
        GCOL = {'B': C['Base'], 'C': C['Bear'], 'D': MUTED, 'E': MUTED}
        col = GCOL.get(r[4], MUTED)
        if i == 0 or rows[i-1][4] != r[4]:
            GNAME = {'B': '群B 測定・規約由来（両側）', 'C': '群C 周辺レンジの一次元摂動（分散分解ではない）',
                     'D': '群D 設計選択（アドホック）', 'E': '群E K4のみ'}
            body.append(f'<line class="grid" x1="{L-240}" y1="{y-8}" x2="{W-R}" y2="{y-8}"/>')
            body.append(f'<text class="note" x="{L-240}" y="{y-12}">{GNAME.get(r[4], "")}</text>')
        _op = 0.32 if r[4] == 'C' else 0.8
        _dash = ' stroke-dasharray="4 3" stroke="%s" stroke-width="1"' % col if r[4] == 'C' else ''
        body.append(f'<rect x="{x1_:.1f}" y="{y}" width="{max(x2_-x1_,2):.1f}" height="18" '
                    f'rx="3" fill="{col}" opacity="{_op}"{_dash}/>')
        body.append(f'<text class="lab" x="{L-12}" y="{y+14}" text-anchor="end">{name}</text>')
        body.append(f'<text class="note" x="{x2_+8:.1f}" y="{y+14}">{sp*100:.1f}pt</text>')
    open(f'{OUT}/tornado.svg', 'w').write(svg(
        W, H, "".join(body), '感度分析 — 群ごとの前提の振れ幅',
        '群ごとに較正基準が違うので、群をまたいだ長さの比較は無意味。'
        '群Cは結合制約を外れた一次元摂動であり、答えの不確実性ではない。'
        f'答えの不確実性は群A（S*制約下の同時スキャン、'
        f'{_gA()[2]:.1%}〜{_gA()[3]:.1%}、'
        f'{(_gA()[3]-_gA()[2])*100:.1f}pt）'.replace('-', '−')))


# ============================================================
# 4. バックキャスト
# ============================================================
def chart_backcast():
    import phase7_backcast as BC
    W, H = 900, 460
    L, R, T, B = 70, 200, 78, 56
    pw, ph = W - L - R, H - T - B
    obs = [(d, v) for d, v in BC.OBS if d >= date(2024, 6, 1)]
    x0, x1 = date(2024, 6, 1), date(2026, 9, 1)
    span = (x1 - x0).days
    ymax = 1_450_000
    fx = lambda d: L + (d - x0).days / span * pw
    fy = lambda v: T + ph - (v / ymax) * ph
    body = []
    for gy in range(0, 15, 2):
        y = fy(gy * 100000)
        body.append(f'<line class="grid" x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}"/>')
        body.append(f'<text class="ax" x="{L-8}" y="{y+4:.1f}" text-anchor="end">{gy*10}万</text>')
    for lab, d in [('2024-07\n7.0発売', E7), ('2025-01', date(2025, 1, 1)),
                   ('2026-01', date(2026, 1, 1)), ('2026-07', date(2026, 7, 1))]:
        x = fx(d)
        body.append(f'<text class="ax" x="{x:.1f}" y="{T+ph+18}" text-anchor="middle">{lab.splitlines()[0]}</text>')
    cases = [(f'ρ={RHO_LV80:.4f} / I={I_BASE_LV80:,}（採用）', RHO_LV80, I_BASE_LV80, C['Base']),
             (f'ρ={RHO_LV80:.4f} / I={I_BASE_EX0720:,}', RHO_LV80, I_BASE_EX0720, C['Bull']),
             ('ρ=0.8303（棄却）', RHO_LV80_REGIME, I_BASE_LV80, C['Bear'])]
    for i, (lab, rho, ib, col) in enumerate(cases):
        ser = BC.sim(rho, ib, BC.S_START, date(2024, 6, 12), date(2026, 7, 20))
        p = [(d, v) for d, v in ser if x0 <= d <= x1]
        dd = " ".join(f"{'M' if j==0 else 'L'}{fx(d):.1f},{fy(v):.1f}" for j, (d, v) in enumerate(p))
        body.append(f'<path d="{dd}" fill="none" stroke="{col}" stroke-width="2" stroke-dasharray="6 3"/>')
        _, errs, _, _ = BC.score(rho, ib)
        mae = st.mean([abs(e) for e in errs])
        y = T + 16 + i * 34
        body.append(f'<line x1="{L+pw+16}" y1="{y}" x2="{L+pw+42}" y2="{y}" stroke="{col}" stroke-width="2" stroke-dasharray="6 3"/>')
        body.append(f'<text class="lab" x="{L+pw+48}" y="{y+4}" style="font-size:11px">{lab}</text>')
        body.append(f'<text class="note" x="{L+pw+48}" y="{y+19}">MAE {mae:.1%}</text>')
    dd = " ".join(f"{'M' if j==0 else 'L'}{fx(d):.1f},{fy(v):.1f}" for j, (d, v) in enumerate(obs))
    body.append(f'<path d="{dd}" fill="none" stroke="{C["obs"]}" stroke-width="2.6"/>')
    for d, v in obs:
        body.append(f'<circle cx="{fx(d):.1f}" cy="{fy(v):.1f}" r="3" fill="{C["obs"]}"/>')
    y = T + 16 + 3 * 34
    body.append(f'<line x1="{L+pw+16}" y1="{y}" x2="{L+pw+42}" y2="{y}" stroke="{C["obs"]}" stroke-width="2.6"/>')
    body.append(f'<text class="lab" x="{L+pw+48}" y="{y+4}" style="font-size:11px">観測（実績）</text>')
    body.append(f'<text class="ax" x="{L+pw/2}" y="{H-16}" text-anchor="middle">'
                f'2024-06-12 の水準から予測モデルを回し、7.x の観測9点と突き合わせる</text>')
    open(f'{OUT}/backcast.svg', 'w').write(svg(
        W, H, "".join(body), 'バックキャスト — 完了した 7.x 周期にモデルを当てる',
        'ρ=0.8303 は 2026-07-20 を +19.2% 外す。採用値は +3.0% の上方バイアスを持つ'))


if __name__ == '__main__':
    chart_cycles(); print('charts/cycle-curves.svg')
    chart_forecast(); print('charts/forecast.svg')
    chart_tornado(); print('charts/tornado.svg')
    chart_backcast(); print('charts/backcast.svg')
