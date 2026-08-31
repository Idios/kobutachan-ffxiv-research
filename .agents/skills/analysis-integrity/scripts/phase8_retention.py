#!/usr/bin/env python3
"""
Phase 8 — 再捕捉率回帰の再現スクリプト（v2。第3次監査を反映）

【なぜ作ったか】根本原因 D-1: 結論を支配する係数がどの再現スクリプトにも入って
いなかった。値だけが文書へ転記され、検証不能になっていた。

【v2 での変更】第3次監査（敵対的査読）が摘出した3件を反映:
  C1. v1 の「非パラメトリック検証」は OLS の恒等式であり証拠として空だった。
      「実測」と称した量は、③自身の窓長係数でデータを正規化したものだった。
      世代ダミー付き OLS は世代別残差和がゼロなので、世代別幾何平均＝当てはめ値が
      代数的に成立する。→ **撤回し、係数に依存しない検証に差し替えた**（§D）。
  C3. 世代ダミーが足切りレジームとほぼ同一（4.x は全てLv36以上、7.x は全てLv70超）。
      ρ の世代差と足切り段差が識別できていない。→ §C で段数を統制した推定を併記。
  M10. 「①＋fs」の2セルがスクリプトに無かった。→ specs に追加。

使い方: python3 scripts/phase8_retention.py
"""
import csv
import math
import statistics as st
from datetime import date


def D(s):
    y, m, d = map(int, s.split('-')); return date(y, m, d)

LAUNCH = [('4.x', D('2017-06-20')), ('5.x', D('2019-07-02')),
          ('6.x', D('2021-12-07')), ('7.x', D('2024-07-02')), ('8.x', D('2027-01-15'))]
GENS = ['4.x', '5.x', '6.x', '7.x']
# 足切り基準を Lv80超 まで何段階引き上げる必要があるか
REGIME_STEPS = {'Lv36以上': 3, 'Lv60超': 2, 'Lv70超': 1, 'Lv80超': 0}
with open('data/census_normalized.csv') as _f:
    CEN = [r for r in csv.DictReader(_f)]
BYD = {r['date']: r for r in CEN}


def gen_of(d):
    for j, (g, L) in enumerate(LAUNCH[:-1]):
        if L <= d < LAUNCH[j + 1][1]: return g
    return None


def lstsq(X: list[list[float]], Y: list[float]):
    k = len(X[0]); n = len(X)
    A = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    B = [sum(X[i][a] * Y[i] for i in range(n)) for a in range(k)]
    M = [A[i][:] + [B[i]] for i in range(k)]
    for i in range(k):
        p = max(range(i, k), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        for r in range(k):
            if r != i:
                f = M[r][i] / M[i][i]
                for c in range(i, k + 1): M[r][c] -= f * M[i][c]
    beta = [M[i][k] / M[i][i] for i in range(k)]
    res = [Y[i] - sum(X[i][j] * beta[j] for j in range(k)) for i in range(n)]
    s2 = sum(r * r for r in res) / (n - k)
    inv = [[1.0 if i == j else 0.0 for j in range(k)] for i in range(k)]
    M = [A[i][:] + inv[i] for i in range(k)]
    for i in range(k):
        p = max(range(i, k), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        dd = M[i][i]
        for c in range(2 * k): M[i][c] /= dd
        for r in range(k):
            if r != i:
                f = M[r][i]
                for c in range(2 * k): M[r][c] -= f * M[i][c]
    se = [math.sqrt(s2 * M[i][k + i]) for i in range(k)]
    tss = sum((y - st.mean(Y)) ** 2 for y in Y)
    return beta, se, n, 1 - sum(r * r for r in res) / tss


def flow_share(r, scale):
    """当該回のフロー比率。'raw'=CSVの生列（窓長汚染あり）、'n64'=64日換算。"""
    if scale == 'raw':
        return float(r['flow_share']) if r['flow_share'] else None
    if not (r['new_scaled'] and r['returning_scaled'] and r['normalized_64d']): return None
    w = float(r['window_days'])
    I64 = (float(r['new_scaled']) + float(r['returning_scaled'])) * (64.0 / w)
    return I64 / float(r['normalized_64d'])


def sample(spec, fs_scale='n64'):
    """spec のトークン: w / pw / fs / regime / nolaunch"""
    X, Y, FS, META = [], [], [], []
    for r in CEN:
        if not r['continuing_scaled'] or not r['prev_date']: continue
        p = BYD.get(r['prev_date'])
        if not p or r['regime'] != p['regime']: continue      # 基準変更をまたぐペアは除外
        g = gen_of(D(r['date']))
        if not g: continue
        if 'nolaunch' in spec and any(D(r['prev_date']) < L <= D(r['date']) for _, L in LAUNCH):
            continue
        row = [1.0, math.log(float(r['window_days']))]
        if 'pw' in spec:
            if not r['prev_window_days']: continue
            row.append(math.log(float(r['prev_window_days'])))
        if 'fs' in spec:
            f = flow_share(p, fs_scale)
            if f is None: continue
            row.append(f); FS.append(f)
        if 'regime' in spec:
            row.append(float(REGIME_STEPS[r['regime']]))
        row += [1.0 if g == x else 0.0 for x in GENS[1:]]
        X.append(row); Y.append(math.log(float(r['continuing_scaled']) / float(p['raw_total'])))
        META.append((g, r['date'], r['regime'], float(r['window_days']),
                     float(r['prev_window_days']) if r['prev_window_days'] else None))
    return X, Y, FS, META


def names_of(spec):
    return ['切片', 'log(窓長)'] + (['log(前回窓長)'] if 'pw' in spec else []) \
           + (['前回フロー比率'] if 'fs' in spec else []) \
           + (['足切り段数'] if 'regime' in spec else []) + GENS[1:]


def run(spec, fs_scale='n64', fs_at=None, steps_at=0.0):
    """fs_at: フロー比率の評価点（None なら標本平均）。steps_at: 足切り段数の評価点。"""
    X, Y, FS, META = sample(spec, fs_scale)
    b, se, n, r2 = lstsq(X, Y)
    nm = names_of(spec)
    if fs_at is None and FS: fs_at = st.mean(FS)
    extra = b[1] * math.log(64)
    if 'pw' in spec: extra += b[nm.index('log(前回窓長)')] * math.log(64)
    if 'fs' in spec:
        assert fs_at is not None
        extra += b[nm.index('前回フロー比率')] * fs_at
    if 'regime' in spec: extra += b[nm.index('足切り段数')] * steps_at
    i0 = len(nm) - 3
    rho = {g: math.exp(b[0] + extra + (b[i0 + j - 1] if j else 0.0)) for j, g in enumerate(GENS)}
    return {'spec': spec, 'n': n, 'r2': r2, 'b': b, 'se': se, 'names': nm, 'fs_at': fs_at,
            'rho': rho, 'X': X, 'Y': Y, 'FS': FS, 'META': META}


def coef(res, name):
    i = res['names'].index(name); return res['b'][i], res['se'][i]


if __name__ == '__main__':
    W = 78
    print("=" * W)
    print("A. 定式化の一覧（フロー比率は64日換算、評価点は標本平均 fs）")
    print("=" * W)
    specs = [('w', '① 今回窓長のみ（Phase 4 v0.1。禁止事項違反）'),
             ('w+fs', '①+fs（**Phase 4 v0.2 が③と誤記していた式**）'),
             ('w+pw', '② +log(前回窓長)  ← **正典**（第3次監査 C2 で③から変更）'),
             ('w+pw+fs', '③ ②+前回フロー比率（感度用。正典ではない）'),
             ('w+pw+fs+nolaunch', '④ ③からローンチ窓ペア除外'),
             ('w+pw+fs+regime', '⑤ ③+足切り段数'),
             ('w+pw+regime', '②+足切り段数  ← C3 への対処（正典②の対照）')]
    res = {}
    print(f"{'定式化':<40s}{'n':>4s}{'R²':>7s}  " + "".join(f"{g:>8s}" for g in GENS))
    for spec, lab in specs:
        r = run(spec, 'n64'); res[spec] = r
        print(f"{lab:<40s}{r['n']:>4d}{r['r2']:>7.3f}  " + "".join(f"{r['rho'][g]:8.3f}" for g in GENS))

    r3 = res['w+pw+fs']
    print("\n--- ③（感度用。正典は②）の全係数 ---")
    for nm, bb, ss in zip(r3['names'], r3['b'], r3['se']):
        print(f"  {nm:<14s} {bb:+9.4f}  se={ss:.4f}  t={bb/ss:+6.2f}"
              f"  95%CI[{bb-1.96*ss:+.3f}, {bb+1.96*ss:+.3f}]")
    print(f"  n={r3['n']}  R²={r3['r2']:.3f}  評価点 fs = {r3['fs_at']:.4f}（標本平均、64日換算）")

    print("\n" + "=" * W)
    print("B. ρ–I 結合係数：定式化 × フロー比率スケールの 2×2＋α")
    print("=" * W)
    print(f"{'定式化':<34s}{'スケール':>8s}{'n':>4s}{'係数':>10s}{'t':>7s}{'R²':>7s}")
    for spec, lab in [('w+fs', '①+fs【Phase 4 v0.2 が使用・誤】'), ('w+pw+fs', '③（感度用）'),
                      ('w+pw+fs+nolaunch', '④ ローンチ窓ペア除外'), ('w+pw+fs+regime', '⑤ 足切り段数統制')]:
        for sc in ('raw', 'n64'):
            r = run(spec, sc); bb, ss = coef(r, '前回フロー比率')
            print(f"{lab:<34s}{sc:>8s}{r['n']:>4d}{bb:+10.4f}{bb/ss:+7.2f}{r['r2']:>7.3f}")
    print("  → **正しい定式化のもとではスケールの寄与は小さい**（−0.287 → −0.301）。")
    print("     −0.5144 → −0.0814 の大部分は『定式化欠落』の寄与であり、窓長汚染ではない。")

    print("\n" + "=" * W)
    print("C. 【第3次監査 C3】世代ダミーと足切りレジームの交絡")
    print("=" * W)
    from collections import Counter
    print("  （定式化②の標本 n=39）")
    print(f"{'世代':>5s}{'n':>4s}  " + "".join(f"{k:>10s}" for k in REGIME_STEPS) + f"{'平均段数':>10s}")
    for g in GENS:
        sub = [m for m in res['w+pw']['META'] if m[0] == g]
        c = Counter(m[2] for m in sub)
        print(f"{g:>5s}{len(sub):>4d}  " + "".join(f"{c.get(k,0):10d}" for k in REGIME_STEPS)
              + f"{st.mean([REGIME_STEPS[m[2]] for m in sub]):10.2f}")
    print("  → **世代ダミーは足切りレジームのダミーとほぼ同義**。両者は識別できない。")

    r2 = res['w+pw']; r2r = res['w+pw+regime']
    bs, ss = coef(r2r, '足切り段数')
    print(f"\n  ②+段数統制: 段数係数 {bs:+.4f} (t={bs/ss:+.2f})"
          f" → 1段あたり ρ ×{math.exp(-bs):.4f}"
          f"  95%CI [×{math.exp(-(bs+1.96*ss)):.4f}, ×{math.exp(-(bs-1.96*ss)):.4f}]   R²={r2r['r2']:.3f}")
    STEP_TOTAL, STEP_CONT = 95/102, 61/63
    K = STEP_CONT/STEP_TOTAL
    print(f"  **直接測定された1段係数（2026-07-20 同日ペア）= ×{K:.4f} はこの CI の内側**"
          f" → 回帰は測定値を棄却していない。")
    b7, s7 = coef(r2r, '7.x'); b7b, s7b = coef(r2, '7.x')
    print(f"  7.x ダミー: ② {b7b:+.4f} (t={b7b/s7b:+.2f})  →  ②+段数 {b7:+.4f} (t={b7/s7:+.2f})  **符号反転**")

    print("\n  ρ を Lv80超基準へ揃える3通り（**すべて定式化②（n=39）で統一**）:")
    print(f"{'世代':>5s}{'②(same-regime)':>16s}{'一律1段換算':>13s}{'段数整合換算':>14s}{'②+段数の直接推定':>18s}")
    steps = {g: st.mean([REGIME_STEPS[m[2]] for m in r2['META'] if m[0] == g]) for g in GENS}
    print("  平均段数（②の標本）: " + " / ".join(f"{g} {steps[g]:.2f}" for g in GENS))
    for g in GENS:
        v = r2['rho'][g]
        print(f"{g:>5s}{v:16.4f}{v*K:13.4f}{v*K**steps[g]:14.4f}{r2r['rho'][g]:18.4f}")
    print("  ※ 7.x は 8/8 が Lv70超＝ちょうど1段なので、一律1段換算と段数整合換算は恒等的に同値。")
    print("  → **一律1段換算では 7.x が最高だが、段数整合換算・段数統制推定では 4.x が上回る。**")
    print("     『7.x は観測中で最高の ρ』は識別されていない。**Bull の上限根拠として使えない。**")
    print(f"\n  Bear 用 6.x/7.x 比: 一律 {r2['rho']['6.x']/r2['rho']['7.x']:.4f}"
          f" / 段数整合 {r2['rho']['6.x']*K**steps['6.x']/(r2['rho']['7.x']*K):.4f}"
          f" / 段数統制 {r2r['rho']['6.x']/r2r['rho']['7.x']:.4f}")

    print("\n" + "=" * W)
    print("D. 【第3次監査 C1】係数に依存しない検証")
    print("=" * W)
    print("  v1 の『非パラメトリック検証』は③自身の窓長係数で正規化しており恒等式だった（撤回）。")
    print("  代わりに、**窓長が64日に近いペアだけ**を使い、無補正の生の再捕捉率を見る。")
    for tol in (10, 15, 20):
        print(f"\n  |窓長−64|≤{tol}日 かつ |前回窓長−64|≤{tol}日 のペア:")
        for g in GENS:
            v = [(math.exp(y), m) for y, m in zip(r3['Y'], r3['META'])
                 if m[3] and m[4] and abs(m[3]-64) <= tol and abs(m[4]-64) <= tol and m[0] == g]
            if not v: print(f"    {g}: 該当なし"); continue
            print(f"    {g}: n={len(v)}  生の再捕捉率 平均 {st.mean([x for x,_ in v]):.4f}"
                  f"  ({', '.join(f'{x:.3f}' for x,_ in v)})")
    print("\n  ※ この量は同一足切りレジーム内の生値であり、レジーム間の水準差は残る（C3）。")
    print("\n     【第6次監査 R6-6 で訂正】v1 はここで「7.x の水準が 0.72 ではなく 0.76 前後")
    print("     であることは確認できる」と書いていたが、**上の出力がそれを支持していない**。")
    print("     ±10日 0.7334（n=2）／±15日・±20日 0.7483（n=4）で、いずれも 0.76 に届かない。")
    print("     かつ 7.x の生値は 0.694〜0.832 に散らばり、②の 0.7603 も誤仕様の 0.740 も")
    print("     この観測域の内側にある。**この検査は両者を分離できない。**")
    print("     正しい結語: 係数非依存の生値は 0.73〜0.75 に集まるが、")
    print("     n が小さく散らばりが大きいので、定式化の優劣をここでは決められない。")

    print("\n" + "=" * W)
    print("E. 影響の大きい観測点（leave-one-out）")
    print("=" * W)
    base7 = r2['rho']['7.x']
    print(f"  【定式化②】全標本での 7.x ρ = {base7:.4f}  （7.x の same-regime ペアは {sum(1 for m in r2['META'] if m[0]=='7.x')} 組）")
    X, Y, FS, META = sample('w+pw', 'n64')
    nm = names_of('w+pw')
    for i, m in enumerate(META):
        if m[0] != '7.x': continue
        Xd = [x for j, x in enumerate(X) if j != i]; Yd = [y for j, y in enumerate(Y) if j != i]
        b, se, n, rr = lstsq(Xd, Yd)
        e = b[0] + b[1]*math.log(64) + b[2]*math.log(64) + b[nm.index('7.x')]
        print(f"  {m[1]} を除外 → 7.x ρ = {math.exp(e):.4f} ({math.exp(e)/base7-1:+.2%})"
              f"  [窓{m[3]:.0f}日/前回{m[4]:.0f}日]")

    print("\n" + "=" * W)
    print("F. params.py が持つべき正典値")
    print("=" * W)
    cf, cs = coef(r3, '前回フロー比率')
    own = {g: st.mean([f for f, m in zip(r3['FS'], r3['META']) if m[0] == g]) for g in GENS}
    print("  # 中心（定式化②、fs 項なし、n=39）")
    print("  RHO_BY_GEN     = " + "{" + ", ".join(f"'{g}': {r2['rho'][g]:.4f}" for g in GENS) + "}")
    print(f"  RHO_LV80       = {r2['rho']['7.x']*K:.4f}   RHO_BEAR_RATIO = {r2['rho']['6.x']/r2['rho']['7.x']:.4f}")
    print("  # 【第6次監査 R6-7】下は②と②+段数の**識別レンジ**であって、")
    print("  # バックキャストの許容域（params.SSTAR_RANGE_BY_TOL）ではない。混同禁止。")
    print(f"  RHO_IDENT_RANGE = ({r2['rho']['7.x']*K:.4f}, {r2r['rho']['7.x']:.4f})"
          f"   # 上端は第4次 F2 がバックキャストで棄却済み")
    print(f"  RHO_BEAR_RATIO_RANGE = ({r2['rho']['6.x']/r2['rho']['7.x']:.4f},"
          f" {r2r['rho']['6.x']/r2r['rho']['7.x']:.4f})")
    print(f"  RHO_REGIME_COEF= {bs:+.4f}")
    print("  # 感度（定式化③、fs 項あり、n=35）")
    print(f"  OPERATING_FS   = {own['7.x']:.4f}   SAMPLE_FS = {r3['fs_at']:.4f}")
    print("  RHO_BY_GEN_F3  = " + "{" + ", ".join(f"'{g}': {run('w+pw+fs','n64',fs_at=own[g])['rho'][g]:.4f}" for g in GENS) + "}")
    print(f"  FLOW_COEF      = {cf:+.4f}   FLOW_COEF_CI = ({cf-1.96*cs:+.3f}, {cf+1.96*cs:+.3f})")
    fn, _ = coef(run('w+pw+fs+nolaunch', 'n64'), '前回フロー比率')
    fr, _ = coef(run('w+pw+fs+regime', 'n64'), '前回フロー比率')
    print(f"  FLOW_COEF_NOLAUNCH = {fn:+.4f}   FLOW_COEF_REGIME = {fr:+.4f}")
    print("  # 観測された最大再捕捉率（same-regime、窓長補正なしの生値）")
    raw = [(math.exp(y), m) for y, m in zip(r2['Y'], r2['META'])]
    mx = max(raw); print(f"  RHO_OBS_MAX_SAMEREGIME = {mx[0]:.4f}  ({mx[1][1]}, {mx[1][0]}, {mx[1][2]})")
    print(f"  RHO_CAP_LV80   = {mx[0]*K:.4f}")
