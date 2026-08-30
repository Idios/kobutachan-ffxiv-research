#!/usr/bin/env python3
"""
第6次監査の指摘を、指摘者の計算を信用せずに独立に再計算する。

【なぜ必要か】監査側の指摘そのものが誤っていた例が複数ある。**指摘を採用する前に
自分で計算する。** 実際、本スクリプトの初版は 64日換算（×64/窓長）を落としており、
「I_base の5成分が互いに矛盾する」という**誤った致命的所見**を生んだ。
`new_scaled` / `returning_scaled` は**生のカテゴリ実数**であり、64日換算は別途かかる。
    I_t = (新規×新規段差 + 復帰×復帰段差) × 64/窓長
この修正で params.py の5成分は全て 0.01% 以内で再現する（§V0）。

検証項目:
  V0 I_base の再現（規約の確定）
  V1 感度分析 群A の端点が S* 許容域を満たすか
  V3 T4 の閾値 7万 は観測分布に対して到達可能か
  V4 T5 の閾値 109万 はシナリオを分割するか
  V5 足切り丸めの4成分同時摂動＋加法制約
  V6 T2 の閾値近傍で、規定される更新と正しい更新の向きが一致するか
  V7 生系列 vs norm64（Phase 2 の「暫定採用」の影響）
  V8 バックキャスト許容率・格子刻みに対する S* 許容域の感応度
  V9 phase8_retention.py §F の出力と params.py の突合
"""
import sys, csv, math, statistics as st, random
from datetime import date
sys.path.insert(0, 'scripts')
from params import *
import phase7_backcast as BC
import phase7_forecast as FC

W = 78
def hdr(t):
    print("\n" + "=" * W); print(t); print("=" * W)

ROWS = [r for r in csv.DictReader(open('data/census_normalized.csv')) if r['new_scaled']]


def flow_components(r, step=None):
    """1観測の (新規, 復帰) を Lv80超・64日換算で返す"""
    s = CUTOFF_STEP if step is None else step
    n = REGIME_STEPS[r['regime']]
    fn = (s['new'] if n >= 1 else 1.0) * (CUTOFF_STEP_UNMEASURED ** max(n - 1, 0))
    fr = (s['ret'] if n >= 1 else 1.0) * (CUTOFF_STEP_UNMEASURED ** max(n - 1, 0))
    k = 64 / float(r['window_days'])
    return float(r['new_scaled']) * fn * k, float(r['returning_scaled']) * fr * k


def inflow(r, step=None):
    a, b = flow_components(r, step); return a + b


def i_base(step=None, rows=None, n=5):
    rs = (rows or ROWS)[-n:]
    return st.mean([inflow(r, step) for r in rs])


# ------------------------------------------------------------------ V0
hdr("V0. I_base の再現（規約: (新規×段差 + 復帰×段差) × 64/窓長）")
DOC = {'2025-09-27': 196_811, '2025-11-30': 143_127, '2026-02-23': 173_757,
       '2026-04-19': 96_074, '2026-07-20': 233_402}
worst = 0
for r in ROWS[-5:]:
    got = inflow(r); exp = DOC[r['date']]
    worst = max(worst, abs(got / exp - 1))
    print(f"  {r['date']}  再計算 {got:>9,.0f}  params {exp:>9,.0f}  差 {got/exp-1:+.3%}")
print(f"  5点平均 = {i_base():,.0f}（params: {I_BASE_LV80:,}）  最大乖離 {worst:.3%}")
print("  → 規約は確定。初版の『成分が矛盾』は本スクリプトの誤りだった。")
print(f"  ただし I_BASE_LV80 は params.py の**ベタ書き定数**であり、"
      f"生成スクリプトが存在しない（根本原因 D-1）。")

# ------------------------------------------------------------------ V1
hdr("V1. 感度分析 群A の端点は S* 許容域（700,000〜770,833）を満たすか")
lo, hi = SSTAR_RANGE_BACKCAST
pts = [('ρ 低位 0.7400 / I 採用', 0.7400, I_BASE_LV80),
       (f'ρ 採用 {RHO_LV80:.4f} / I 採用', RHO_LV80, I_BASE_LV80),
       ('ρ 高位 0.8000 / I 採用', 0.8000, I_BASE_LV80),
       ('I 低位 140,000 / ρ 採用', RHO_LV80, 140_000),
       ('I 高位 200,000 / ρ 採用', RHO_LV80, 200_000)]
for name, r_, i_ in pts:
    s = i_ / (1 - r_)
    print(f"  {name:<28s} S* = {s:>10,.0f}  {'域内' if lo <= s <= hi else '**域外**'}")
print("  → 5/5 が域外。周辺レンジの端点は『相手を最適に選べば到達できる』点であり、")
print("     相手を採用値に固定して振ると結合制約を出る。")
print("     **群Aを『バックキャスト許容域で両側に振った』と呼んだのが誤り。**")

# ------------------------------------------------------------------ V3
hdr("V3. T4 の閾値 7万（新規・64日換算・Lv80超）は到達可能か")
sev = [(r['date'], flow_components(r)[0]) for r in ROWS if r['date'] >= '2024-06-01']
for d, v in sev:
    tag = '  ← 7.0 ローンチ窓' if d == '2024-08-27' else (
          '  ← 7.0 直前（予約期）' if d == '2024-06-12' else '')
    print(f"  {d}  新規 = {v:>8,.0f}{tag}")
mx = max(v for _, v in sev)
nl = [v for d, v in sev if d not in ('2024-08-27',)]
print(f"  7.x 最大 = {mx:,.0f}（ローンチ窓）／ローンチ窓を除く最大 = {max(nl):,.0f}")
print(f"  閾値 70,000 は 7.x 最大の {70000/mx:.2f} 倍、非ローンチ最大の {70000/max(nl):.2f} 倍")
print("  → T4 は『発売直後の1回では判定しない』と明記＝ローンチ窓を除外するので、")
print("     **7.x の全観測で一度も到達していない水準を要求している＝発火不能。**")

# ------------------------------------------------------------------ V4
hdr("V4. T5 の閾値 109万 はシナリオを分割するか")
r = FC.build(); K3 = 0.916
for k in ('Bear', 'Base', 'Bull'):
    pk = r[k]['peak']
    print(f"  {k:<5s} 8.0 ピーク K1 = {pk:>10,.0f}  ×K3プロキシ{K3} = {pk*K3:>10,.0f}")
print(f"  閾値 1,090,000 は **Lv70超期の記事値**。Lv80超 換算 = "
      f"{1_090_000*CUTOFF_STEP['total']:,.0f}")
print("  → どちらの基準で見ても3シナリオとも下回る＝分割しない。足切りも未統一。")

# ------------------------------------------------------------------ V5
hdr("V5. 足切り丸めの4成分同時摂動（加法制約あり／なし）")
CNT = {'total': (95, 102), 'new': (5, 8), 'ret': (28, 31), 'cont': (61, 63)}
print(f"  加法: 新基準 5+28+61 = 94 ≠ 95（**1万ずれる**）／旧基準 8+31+63 = 102 = 102 ✓")
print(f"  採用段差    ρ={RHO_LV80:.4f} I={i_base():>9,.0f} S*={i_base()/(1-RHO_LV80):>9,.0f}")

def outcome(step):
    rho = RHO_7X_SAMEREGIME * step['cont'] / step['total']
    ib = i_base(step)
    return rho, ib, ib / (1 - rho)

only_total = [{'total': t, 'new': 5/8, 'ret': 28/31, 'cont': 61/63}
              for t in CUTOFF_STEP_TOTAL_RANGE]
print("\n  (a) 現行の感度＝total 段差のみを振る:")
for s_ in only_total:
    rho, ib, ss = outcome(s_)
    print(f"      total={s_['total']:.4f} → ρ={rho:.4f} I={ib:>9,.0f} S*={ss:>9,.0f}")

random.seed(7)
free, cons = [], []
for _ in range(40000):
    d = {k: (random.uniform(v-.5, v+.5), random.uniform(w-.5, w+.5)) for k, (v, w) in CNT.items()}
    step = {k: d[k][0] / d[k][1] for k in d}
    rho, ib, ss = outcome(step)
    if not (0 < rho < 1): continue
    free.append((rho, ib, ss))
    if (abs(sum(d[k][0] for k in ('new', 'ret', 'cont')) - d['total'][0]) < 1e-9 or True) and \
       abs(sum(d[k][0] for k in ('new', 'ret', 'cont')) - d['total'][0]) < 0.5 and \
       abs(sum(d[k][1] for k in ('new', 'ret', 'cont')) - d['total'][1]) < 0.5:
        cons.append((rho, ib, ss))
def rng(v, i): return (min(x[i] for x in v), max(x[i] for x in v))
print(f"\n  (b) 4成分を独立に振る（制約なし, n={len(free)}）:")
print(f"      ρ  {rng(free,0)[0]:.4f}〜{rng(free,0)[1]:.4f}   "
      f"I {rng(free,1)[0]:,.0f}〜{rng(free,1)[1]:,.0f}   "
      f"S* {rng(free,2)[0]:,.0f}〜{rng(free,2)[1]:,.0f}")
print(f"  (c) 加法制約を課す（n={len(cons)}）:")
print(f"      ρ  {rng(cons,0)[0]:.4f}〜{rng(cons,0)[1]:.4f}   "
      f"I {rng(cons,1)[0]:,.0f}〜{rng(cons,1)[1]:,.0f}   "
      f"S* {rng(cons,2)[0]:,.0f}〜{rng(cons,2)[1]:,.0f}")
print(f"      採用 I={i_base():,.0f} は制約帯に "
      f"{'入る' if rng(cons,1)[0] <= i_base() <= rng(cons,1)[1] else '**入らない**'}")
print("  → total だけを振る現行感度は、I 経路（new/ret の丸め）を完全に落としている。")

# ------------------------------------------------------------------ V6
hdr(f"V6. T2（新規＋復帰が {I_BASE_LV80:,} を下回る）の閾値近傍の挙動")
five = [(r['date'], inflow(r)) for r in ROWS[-5:]]
for d, v in five: print(f"  {d}  {v:>9,.0f}")
cur = st.mean([v for _, v in five])
print(f"  現在の5点平均 = {cur:,.0f}／規定される撤回先 = {I_BASE_EX0720:,}")
print(f"  {'次回観測':>10s} {'T2':>6s} {'正しい5点平均':>14s} {'規定値との差':>14s}")
for nxt in (120_000, 150_000, 167_000, 168_000, 169_000, 200_000):
    upd = st.mean([v for _, v in five[1:]] + [nxt])
    print(f"  {nxt:>10,} {'発火' if nxt < I_BASE_LV80 else '不発火':>6s} "
          f"{upd:>14,.0f} {upd - I_BASE_EX0720:>+14,.0f}")
print("  → 閾値ちょうどで発火しても、正しい更新（5点平均の再計算）は")
print("     規定の撤回先 152,442 まで下がらない。閾値と撤回内容が対応していない。")

# ------------------------------------------------------------------ V7
hdr("V7. 生系列 vs norm64（Phase 2 の『暫定採用・水準は生も併用』）")
rr = [r for r in csv.DictReader(open('data/census_normalized.csv')) if r['normalized_64d']]
def pair(r_):
    f = regime_factor(r_['regime'])
    return float(r_['raw_total']) * f, float(r_['normalized_64d']) * f
last = [x for x in rr if x['date'] == '2026-07-20'][0]
a, b = pair(last)
print(f"  2026-07-20（窓{last['window_days']}日）: 生 {a:,.0f} / norm64 {b:,.0f}  差 {b/a-1:+.1%}")
cyc = [pair(x) for x in rr if x['date'] > '2024-07-02']
ra, rb = st.mean([x for x, _ in cyc]), st.mean([y for _, y in cyc])
print(f"  7.x 周期平均: 生 {ra:,.0f} / norm64 {rb:,.0f}  差 {rb/ra-1:+.1%}")
wd = [float(x['window_days']) for x in rr]
print(f"  窓長: 最小 {min(wd):.0f} / 中央 {st.median(wd):.0f} / 最大 {max(wd):.0f} 日")
print("  → 直近点の窓長が92日と長いため、生と norm64 は水準で 10.7% 食い違う。")
print("     S_0（予測の初期条件）に直接効く。Phase 2 の『水準は生も併用』は未実行。")

# ------------------------------------------------------------------ V8
hdr("V8. バックキャスト S* 許容域の、格子刻みと許容率に対する感応度")
def scan(dr, di):
    gr = [0.72 + dr * i for i in range(int(0.10 / dr) + 1)]
    gi = [130_000 + di * i for i in range(int(80_000 / di) + 1)]
    out = []
    for r_ in gr:
        for i_ in gi:
            _, errs, _, _ = BC.score(r_, i_)
            out.append((r_, i_, st.mean([abs(e) for e in errs])))
    return out
for lab, dr, di in (('粗（採用）', 0.02, 15_000), ('中', 0.01, 5_000), ('細', 0.005, 2_500)):
    res = scan(dr, di); best = min(m for _, _, m in res)
    print(f"  格子 {lab:<8s}(Δρ={dr}, ΔI={di:,})  組数 {len(res):>4}  MAE最小 {best:.4f}")
    for mult in (1.25, 1.5, 2.0):
        sel = [i_ / (1 - r_) for r_, i_, m in res if m <= best * mult]
        inside = min(sel) <= 804_579 <= max(sel)
        print(f"      ×{mult:<5}: S* {min(sel):>9,.0f}〜{max(sel):>9,.0f}"
              f"   採用 804,579 は {'域内' if inside else '**域外**'}")
_, e0, cp, co = BC.score(RHO_LV80, I_BASE_LV80)
print(f"\n  採用点そのもの: MAE {st.mean([abs(x) for x in e0]):.4f}、"
      f"周期平均 予測 {cp:,.0f} / 実測 {co:,.0f}（{cp/co-1:+.1%}）")
print("  → 『採用 S* は許容域の外側』は**格子の粗さの産物**。刻みを細かくすると域内に入る。")
print("     一方、採用点の当てはまりが最良点より悪く +3.0% 上振れする事実は残る。")

# ------------------------------------------------------------------ V9
hdr("V9. phase8_retention.py §F の出力と params.py の突合")
import subprocess
out = subprocess.run(['python3', 'scripts/phase8_retention.py'],
                     capture_output=True, text=True).stdout
for key, pv in (('RHO_LV80_RANGE', str(RHO_LV80_RANGE)),
                ('RHO_OBS_MAX_SAMEREGIME', f"{RHO_OBS_MAX_SAMEREGIME}"),
                ('RHO_CAP_LV80', f"{RHO_CAP_LV80:.4f}")):
    ls = [l.strip() for l in out.splitlines() if key in l]
    print(f"  {key}\n    スクリプト: {ls[0] if ls else '（なし）'}\n    params.py : {pv}")
print("\n  §D（係数非依存）の 7.x:")
for l in out.splitlines():
    if l.strip().startswith('7.x:'): print("    " + l.strip())
print("  → 文書の「0.76前後であることは確認できる」は自スクリプトに支持されていない。")
