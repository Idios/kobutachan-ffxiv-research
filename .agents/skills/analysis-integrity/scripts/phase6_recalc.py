#!/usr/bin/env python3
"""
Phase 6 再推定（Phase 8 で新設。第3次監査 M1・C6 への対処）

【なぜ作ったか】Phase 8 は「Phase 6 の回帰の説明変数に足切り基準の混在があった」と
判定し、修正後の値（B=24.7 / a=87.0 / パルス40.1 / ε=0.750 / 真OOS 0/4）を文書と
params.py に載せた。**しかしその計算はアドホックに行われ、どのスクリプトにも
入っていなかった** — 根本原因 D-1 が Phase 8 自身の最重要成果物で再発していた。

【C6】足切り統一は時間の階段関数なので、**統一そのものがキャラ単価に人工的な
時間トレンドを注入する。** Phase 2 §1 は「実測できているのは Lv70超→Lv80超 の
−6.9% だけで、他3段に流用してはいけない」と明記している。
未測定2段の仮定を `--unmeasured` で振れるようにし、結論の感度を出す。

使い方:
  python3 scripts/phase6_recalc.py            # 既定（未測定2段＝実測と同じ）
  python3 scripts/phase6_recalc.py --sweep    # 仮定を振って感度を出す
"""
import csv
import math
import statistics as st
import sys
from collections import defaultdict

sys.path.insert(0, 'scripts')
from params import CUTOFF_STEP, MMO_NOMINAL, REGIME_STEPS, S_MMO, cc

LAUNCH_Q = {('FY2018.3', 'Q1'), ('FY2020.3', 'Q2'), ('FY2022.3', 'Q3'), ('FY2025.3', 'Q2')}
BACKTEST_FY = ['FY2023.3', 'FY2024.3', 'FY2025.3', 'FY2026.3']
TOL = 0.15   # PHASE6_PRECOMMIT.md で着手前に固定


def ols(X: list[list[float]], Y: list[float]):
    k = len(X[0]); n = len(X)
    A = [[sum(X[i][a]*X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    B = [sum(X[i][a]*Y[i] for i in range(n)) for a in range(k)]
    M = [A[i][:] + [B[i]] for i in range(k)]
    for i in range(k):
        p = max(range(i, k), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        for r in range(k):
            if r != i:
                f = M[r][i]/M[i][i]
                for c in range(i, k+1): M[r][c] -= f*M[i][c]
    b = [M[i][k]/M[i][i] for i in range(k)]
    res = [Y[i] - sum(X[i][j]*b[j] for j in range(k)) for i in range(n)]
    s2 = sum(x*x for x in res)/(n-k)
    inv = [[1.0 if i == j else 0.0 for j in range(k)] for i in range(k)]
    M = [A[i][:] + inv[i] for i in range(k)]
    for i in range(k):
        p = max(range(i, k), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        d = M[i][i]
        for c in range(2*k): M[i][c] /= d
        for r in range(k):
            if r != i:
                f = M[r][i]
                for c in range(2*k): M[r][c] -= f*M[i][c]
    se = [math.sqrt(s2*M[i][k+i]) for i in range(k)]
    tss = sum((y - st.mean(Y))**2 for y in Y)
    return b, se, n, 1 - sum(x*x for x in res)/tss


def load(unmeasured, unify=True):
    """unify=False で Phase 6 v0.4 までの挙動（足切り混在）を再現できる"""
    with open('data/census_normalized.csv') as _f:
        cen = {r['date']: r for r in csv.DictReader(_f)}
    out = []
    with open('data/census_vs_revenue.csv') as _f:
        for r in csv.DictReader(_f):
            if not r['mmo_rev_nominal_oku'] or not r['census']:
                continue
            cd = r['census_date']
            if cd not in cen or not cen[cd]['normalized_64d']:
                continue
            c = float(cen[cd]['normalized_64d'])
            if unify:
                n = REGIME_STEPS[cen[cd]['regime']]
                c *= (CUTOFF_STEP['total'] if n >= 1 else 1.0) * (unmeasured ** max(n-1, 0))
            nom = float(r['mmo_rev_nominal_oku'])
            I = float(r['fx_index'])
            out.append({'d': cd, 'fy': r['assigned_fy'], 'q': r['assigned_q'], 'c': c,
                        'nom': nom, 'I': I,
                        'cc': nom*((1-S_MMO) + S_MMO/I),
                        'exp': r['is_expansion_quarter'].strip().upper() in ('TRUE', '1', 'YES'),
                        'launch': (r['assigned_fy'], r['assigned_q']) in LAUNCH_Q,
                        'y': int(r['assigned_fy'][2:6])})
    return out


def fit(d):
    """水準モデル・log-logモデル・年トレンド付きモデルを一括で推定"""
    non = [x for x in d if not x['exp']]
    b, se, n, r2 = ols([[1.0, x['c']] for x in non], [x['cc'] for x in non])
    pulse = st.median([x['cc'] - (b[0] + b[1]*x['c']) for x in d if x['launch']])
    y0 = min(x['y'] for x in non)
    bt, st_, _, _ = ols([[1.0, x['c']*1e6, float(x['y']-y0)] for x in non], [x['cc'] for x in non])
    bl, sl, _, r2l = ols([[1.0, math.log(x['c']), float(x['y']-y0)] for x in non],
                         [math.log(x['cc']) for x in non])
    bll, _, _, r2ll = ols([[1.0, math.log(x['c'])] for x in non], [math.log(x['cc']) for x in non])
    C = 853595.0
    return {'B': b[0], 'a': b[1], 'a_t': b[1]/se[1], 'r2': r2, 'n': n, 'pulse': pulse,
            'eps_level': (b[1]*C)/(b[0]+b[1]*C), 'eps_loglog': bll[1], 'r2_loglog': r2ll,
            'trend_lin': bt[2], 'trend_lin_t': bt[2]/st_[2],
            'eps_lt': bl[1], 'eps_lt_t': bl[1]/sl[1], 'trend_log': bl[2], 'trend_log_t': bl[2]/sl[2],
            'r2_lt': r2l, 'drift4': math.exp(bl[2]*4)}


def backtest(d, f, train_pre2023=False):
    byq = defaultdict(list)
    for x in d: byq[(x['fy'], x['q'])].append(x)
    if train_pre2023:
        tr = [x for x in d if not x['exp'] and x['fy'] not in BACKTEST_FY]
        b, _, _, _ = ols([[1.0, x['c']] for x in tr], [x['cc'] for x in tr])
        A, Bc = b[1], b[0]
    else:
        A, Bc = f['a'], f['B']
    ok = 0; errs = []
    for fy in BACKTEST_FY:
        qs = [k for k in byq if k[0] == fy]
        if len(qs) < 3: continue
        pv = []
        for k in qs:
            c = st.mean([x['c'] for x in byq[k]]); v = Bc + A*c
            if k in LAUNCH_Q: v += f['pulse']
            pv.append(v)
        pred = st.mean(pv)*4
        act = cc(MMO_NOMINAL[int(fy[2:6])], int(fy[2:6]))
        e = pred/act - 1; errs.append(e); ok += abs(e) <= TOL
    return ok, len(errs), errs, A


def eps_backtest(d, unmeasured):
    """弾力性版（FY2023.3 実績を起点に他年度を予測）"""
    K = {}
    for fy in BACKTEST_FY:
        y = int(fy[2:6])
        v = [x['c'] for x in d if x['fy'] == fy]
        K[y] = st.mean(v) if v else None
    base = cc(MMO_NOMINAL[2023], 2023)
    out = {}
    for eps in (0.750, 0.811, 0.845, 1.0):
        es = []
        for y in (2024, 2025, 2026):
            pred = base*(K[y]/K[2023])**eps
            if y == 2025: pred += PULSE_HOLD[0]
            act = cc(MMO_NOMINAL[y], y); es.append(pred/act - 1)
        out[eps] = es
    return out


if __name__ == '__main__':
    U0 = CUTOFF_STEP['total']
    sweep = '--sweep' in sys.argv
    print("=" * 76)
    print("A. 足切り統一の有無（未測定2段＝実測と同じ −6.9% を仮定）")
    print("=" * 76)
    print(f"{'':>18s}{'n':>4s}{'B(億/Q)':>9s}{'a(円/キャラ/Q)':>15s}{'t':>7s}{'R²':>7s}"
          f"{'パルス':>8s}{'ε@85万':>9s}")
    for lab, uni in [('v0.4（混在）', False), ('v0.5（Lv80超統一）', True)]:
        d = load(U0, unify=uni); f = fit(d)
        print(f"{lab:>18s}{f['n']:>4d}{f['B']:9.1f}{f['a']*1e8:15,.0f}{f['a_t']:7.2f}{f['r2']:7.3f}"
              f"{f['pulse']:8.1f}{f['eps_level']:9.4f}")
    print("  ※ a の単位は **円/キャラ/四半期**。Phase 6 v0.4 の「80.1円」は 100倍ずれた表記だった。")

    d = load(U0); f = fit(d)
    PULSE_HOLD = (f['pulse'],)
    print("\n" + "=" * 76)
    print("B. 弾力性とキャラ単価の年次ドリフト（Lv80超統一）")
    print("=" * 76)
    print(f"  水準モデルの点弾力性 @85万 : {f['eps_level']:.4f}")
    print(f"  log-log（年トレンドなし）    : {f['eps_loglog']:.4f}   R²={f['r2_loglog']:.3f}")
    print(f"  log-log＋年トレンド         : ε={f['eps_lt']:.4f} (t={f['eps_lt_t']:+.2f})"
          f"  年トレンド {math.exp(f['trend_log'])-1:+.2%}/年 (t={f['trend_log_t']:+.2f})  R²={f['r2_lt']:.3f}")
    print(f"  線形＋年トレンド（水準統制）  : 年トレンド {f['trend_lin']:+.2f}億/Q/年 (t={f['trend_lin_t']:+.2f})")
    print(f"  → 4年（FY2026.3→FY2030.3）の逓減係数 = {f['drift4']:.4f}")
    print("  ※ 2つの関数形が一致するのは同一データに関数形を2つ当てただけであり独立の検証ではない。")

    print("\n  期間別の平均キャラ単価（CC売上 ÷ キャラ数、非拡張四半期のみ）:")
    for lo, hi in [(2015, 2019), (2020, 2022), (2023, 2026)]:
        sub = [x for x in d if not x['exp'] and lo <= x['y'] <= hi]
        if sub:
            print(f"    FY{lo}-{hi%100:02d}  n={len(sub):2d}  {st.mean([x['cc']/x['c'] for x in sub])*1e8:8,.0f} 円/Q")

    print("\n" + "=" * 76)
    print("C. バックテスト（precommit: 年次CC、許容 ±15%）")
    print("=" * 76)
    ok, tot, errs, _ = backtest(d, f)
    print(f"  水準モデル in-sample     : {ok}/{tot} 合格  誤差 "
          + " / ".join(f"{e:+.1%}" for e in errs))
    ok2, tot2, errs2, a2 = backtest(d, f, train_pre2023=True)
    print(f"  水準モデル **真のOOS**    : {ok2}/{tot2} 合格  誤差 "
          + " / ".join(f"{e:+.1%}" for e in errs2))
    print(f"    係数ドリフト: {a2*1e8:,.0f} → {f['a']*1e8:,.0f} 円/キャラ/Q ({f['a']/a2-1:+.1%})")
    print("    → **水準モデルは3年外挿に使えない。**")
    eb = eps_backtest(d, U0)
    print("\n  弾力性版（FY2023.3 実績を起点に FY2024〜26 を予測、FY2025.3 にはパルスを加算）:")
    for eps, es in eb.items():
        print(f"    ε={eps:<6}: " + " / ".join(f"{e:+.1%}" for e in es)
              + f"   平均絶対 {st.mean([abs(e) for e in es]):.1%}"
              + f"  {sum(abs(e)<=TOL for e in es)}/3 合格")

    if sweep:
        print("\n" + "=" * 76)
        print("D. 【C6】未測定2段の仮定を振る — 足切り統一は人工トレンドを注入しうる")
        print("=" * 76)
        print(f"{'未測定段差':>10s}{'a(円/Q)':>10s}{'ε@85万':>9s}{'年トレンド':>11s}{'t':>7s}"
              f"{'4年係数':>9s}{'真OOS':>7s}")
        for u in (1.00, 0.98, 0.96, 0.94, U0, 0.90):
            dd = load(u); ff = fit(dd)
            PULSE_HOLD = (ff['pulse'],)
            o, t, _, _ = backtest(dd, ff, train_pre2023=True)
            print(f"{u:10.5f}{ff['a']*1e8:10,.0f}{ff['eps_level']:9.4f}"
                  f"{math.exp(ff['trend_log'])-1:+11.2%}{ff['trend_log_t']:7.2f}"
                  f"{ff['drift4']:9.4f}{f'{o}/{t}':>7s}")
        print("\n  → **年トレンドの有意性も水準モデルの合否も、この仮定に依存する。**")
        print("     Phase 2 §1 の禁止事項（−6.9% を他3段に流用しない）に照らせば、")
        print("     『キャラ単価が −2.3%/年 で逓減』は測定値ではなく仮定付きの推定である。")
