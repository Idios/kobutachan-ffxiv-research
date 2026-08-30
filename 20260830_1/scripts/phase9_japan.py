#!/usr/bin/env python3
"""
Phase 9 — 日本国内の状況（地域別分析）

【データの制約 — 先に宣言する】
  ワールド別スプレッドシートには 49時点 × 85ワールドの**総数のみ**があり、
  **新規／復帰／継続の地域別内訳は存在しない**（記事本文にもない）。
  したがって地域別系列には Phase 2 の窓長正規化
      normalized_64d = 継続 + (新規+復帰) × 64/窓長
  を**適用できない**。地域別は生系列しか作れない。

【では何が使えるか】
  素朴には「シェアなら分子・分母の窓長汚染が相殺される」と考えたくなるが、
  §A で示す通り**これは成り立たない**（JPシェアと窓長の相関 −0.476）。
  地域ごとにフロー／ストック構成が違うため、窓が伸びるとフロー比率の高い地域が
  シェアを増やす。したがって**シェアも窓長補正が要る**。
  本スクリプトは log(シェア) を log(窓長) と足切りレジームで回帰し、
  **64日換算・レジーム統制済みのシェア**を作る。

【本スクリプトが出すもの】
  A. 窓長汚染の検査（シェアは素のままでは使えないことの実証）
  B. 窓長補正済みの地域シェア
  C. JP の水準（位相正規化。生系列であることを明示）
  D. JP のフロー／ストック構成の推定（窓長係数から逆算）
  E. 売上側の日本比率
  F. 8.x 予測の日本への含意

使い方: python3 scripts/phase9_japan.py
"""
import sys, csv, math, statistics as st
from datetime import date
sys.path.insert(0, 'scripts')
from params import *

W = 92
def hdr(t): print("\n" + "=" * W); print(t); print("=" * W)

REG = {r['date']: r for r in csv.DictReader(open('data/census_world/census_region_timeseries.csv'))}
CEN = {r['date']: r for r in csv.DictReader(open(CENSUS_CSV))}
DC = {r['date']: r for r in csv.DictReader(open('data/census_world/census_dc_timeseries.csv'))}
COM = sorted(set(REG) & set(CEN))
REGIONS = ['JP', 'NA', 'EU', 'OCE']
JP_DC = ['Elemental', 'Gaia', 'Mana', 'Meteor']


def lstsq(X, Y):
    n, k = len(X), len(X[0])
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    XtY = [sum(X[i][a] * Y[i] for i in range(n)) for a in range(k)]
    M = [row[:] + [XtY[i]] for i, row in enumerate(XtX)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12: continue
        for r in range(k):
            if r == c: continue
            f = M[r][c] / M[c][c]
            for j in range(c, k + 1): M[r][j] -= f * M[c][j]
    b = [M[i][k] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(k)]
    yh = [sum(b[a] * X[i][a] for a in range(k)) for i in range(n)]
    res = [Y[i] - yh[i] for i in range(n)]
    s2 = sum(r * r for r in res) / max(n - k, 1)
    inv = []
    A = [row[:] for row in XtX]
    I = [[1.0 if i == j else 0.0 for j in range(k)] for i in range(k)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(A[r][c]))
        A[c], A[p] = A[p], A[c]; I[c], I[p] = I[p], I[c]
        d = A[c][c]
        if abs(d) < 1e-12: continue
        A[c] = [x / d for x in A[c]]; I[c] = [x / d for x in I[c]]
        for r in range(k):
            if r == c: continue
            f = A[r][c]
            A[r] = [A[r][j] - f * A[c][j] for j in range(k)]
            I[r] = [I[r][j] - f * I[c][j] for j in range(k)]
    inv = I
    se = [math.sqrt(max(s2 * inv[i][i], 0)) for i in range(k)]
    my = st.mean(Y)
    r2 = 1 - sum(r * r for r in res) / max(sum((y - my) ** 2 for y in Y), 1e-12)
    return b, se, n, r2


def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return num / den if den else 0.0


def share(d, reg):
    return float(REG[d][reg]) / float(REG[d]['sheet_total'])


# ------------------------------------------------------------------ A
hdr("A. 地域別シェアは素のままでは使えない（窓長汚染の検査）")
w = [float(CEN[d]['window_days']) for d in COM]
print(f"  観測 {len(COM)} 点、窓長 {min(w):.0f}〜{max(w):.0f} 日（中央 {st.median(w):.0f}）\n")
print(f"  {'量':<22s}{'窓長との相関':>14s}")
print(f"  {'全体の水準':<22s}{corr(w, [float(REG[d]['sheet_total']) for d in COM]):>14.3f}")
for r in REGIONS:
    print(f"  {r + ' の水準':<22s}{corr(w, [float(REG[d][r]) for d in COM]):>14.3f}")
for r in REGIONS:
    print(f"  {r + ' のシェア':<22s}{corr(w, [share(d, r) for d in COM]):>14.3f}")
print("""
  → **シェアでも相殺されない。** JP シェアは窓長と **−0.48**、NA は **+0.44**。
     地域ごとにフロー（新規＋復帰）／ストック（継続）の構成が違うため、
     窓が伸びると**フロー比率の高い地域がシェアを取る**。
     **地域別の議論は、必ず窓長を統制してから行う。**""")

# ------------------------------------------------------------------ B
hdr("B. 窓長補正済みの地域シェア")
print("  模型: log(シェア) ~ log(窓長) + 足切りレジーム ダミー")
print("  （レジームは水準シフトを吸収する。世代と交絡するので世代ダミーは入れない）\n")
REGS = ['Lv36以上', 'Lv60超', 'Lv70超', 'Lv80超']
adj = {}
print(f"  {'地域':<6s}{'log(窓長)係数':>14s}{'t':>7s}{'R²':>7s}   64日換算シェア（基準レジーム=Lv70超, n=13）")
for r in REGIONS:
    X, Y = [], []
    for d in COM:
        if float(REG[d][r]) <= 0: continue
        rg = CEN[d]['regime']
        X.append([1.0, math.log(float(CEN[d]['window_days']))] +
                 [1.0 if rg == g else 0.0 for g in REGS[1:]])
        Y.append(math.log(share(d, r)))
    b, se, n, r2 = lstsq(X, Y)
    # 64日・Lv80超 に揃えた各時点のシェア（残差 + 基準点の予測）
    # 【第9次 F7】Lv80超 は標本中 n=1（2026-07-20 のみ）。基準に使うと情報量ゼロなので
    # 基準は Lv70超（n=13）に置き、必要なら最後に Lv80段差を1回掛ける。
    base = b[0] + b[1] * math.log(64) + b[3]
    fit = {}
    i = 0
    for d in COM:
        if float(REG[d][r]) <= 0: continue
        yh = sum(b[a] * X[i][a] for a in range(len(b)))
        fit[d] = math.exp(base + (Y[i] - yh))
        i += 1
    adj[r] = fit
    print(f"  {r:<6s}{b[1]:>14.3f}{b[1]/se[1]:>7.2f}{r2:>7.3f}   n={n}")

print("\n  窓長・レジームを揃えたシェアの推移（拡張ごとの平均）:")
GENS = [('4.x', date(2017, 6, 20), date(2019, 7, 2)), ('5.x', date(2019, 7, 2), date(2021, 12, 7)),
        ('6.x', date(2021, 12, 7), date(2024, 7, 2)), ('7.x', date(2024, 7, 2), date(2027, 1, 15))]
def D(s): y, m, dd = map(int, s.split('-')); return date(y, m, dd)
print(f"  {'世代':<6s}" + "".join(f"{r:>10s}" for r in REGIONS) + f"{'n':>5s}")
for g, a, bb in GENS:
    ds = [d for d in COM if a <= D(d) < bb and d in adj['JP']]
    if not ds: continue
    row = f"  {g:<6s}"
    for r in REGIONS:
        v = [adj[r][d] for d in ds if d in adj[r]]
        row += f"{st.mean(v)*100:>9.1f}%" if v else f"{'—':>10s}"
    print(row + f"{len(ds):>5d}")

first = [d for d in COM if d in adj['JP']][:3]
last = [d for d in COM if d in adj['JP']][-3:]
print()
for r in REGIONS:
    a0 = [adj[r][d] for d in first if d in adj[r]]
    a1 = [adj[r][d] for d in last if d in adj[r]]
    if not a0 or not a1:
        print(f"  {r:<4s} 初期に観測なし（OCE の初出は 2022-04-10、Materia 開設 2022-01-25）"); continue
    f0, f1 = st.mean(a0), st.mean(a1)
    print(f"  {r:<4s} 初期3点 {f0*100:5.1f}% → 直近3点 {f1*100:5.1f}%   {(f1-f0)*100:+5.1f}pt")
raw0 = st.mean([share(d, 'JP') for d in COM[:3]]); raw1 = st.mean([share(d, 'JP') for d in COM[-3:]])
print(f"\n  【対照】補正**前**の JP シェア: 初期3点 {raw0*100:.1f}% → 直近3点 {raw1*100:.1f}%"
      f"   {(raw1-raw0)*100:+.1f}pt")
print(f"  → 生のシェアが示す下落 {(raw1-raw0)*100:+.1f}pt のうち、"
      f"窓長と足切りで説明される分を除くと **{(st.mean([adj['JP'][d] for d in last])-st.mean([adj['JP'][d] for d in first]))*100:+.1f}pt** しか残らない。")

# --------------------------------------------------------------- B-3
# 【第10次監査 重大1】v1.1 は「非公開補正 +0.53pt は残差 −0.5pt とほぼ同額」と書いて
# 相殺していた。**これは誤りである。** +0.53pt は**水準**の補正であり、残差 −0.5pt は
# **初期3点→直近3点の変化**である。水準補正は基準（レジームダミー）も同時に押し上げる
# ので、そのまま差し引けない。**データ側に補正を入れて回帰をやり直すのが正しい手順**で、
# そうすると残差は −0.51pt → −0.40pt にしか動かない（縮小は 0.11pt であって 0.53pt ではない）。
# --------------------------------------------------------------- B-4
# 【第11次】2026年の反発を地域別に分解する。
# 生データでは JP +14.4% / NA +29.9% で「日本には反発が来ていない」ように見えるが、
# **2026-04-19 → 2026-07-20 は窓長が 55日 → 92日（+67%）に伸びている**。
# §A の通り窓長弾力性は地域で違う（JP 0.375 / NA 0.519）ので、
# **窓が伸びるだけで NA のほうが大きく伸びる。** 補正しないと比較にならない。
hdr("B-4. 2026年の反発は地域でどう違うか（窓長を地域別に補正する）")
_A, _B = '2026-04-19', '2026-07-20'
print(f"  {_A}（窓 {CEN[_A]['window_days']}日・{CEN[_A]['regime']}）"
      f" → {_B}（窓 {CEN[_B]['window_days']}日・{CEN[_B]['regime']}）")
_lw = math.log(float(CEN[_B]['window_days']) / float(CEN[_A]['window_days']))
print(f"  窓長は log で {_lw:+.3f}（+{math.exp(_lw)-1:.0%}）伸びている\n")
_BET = {}
for _r in REGIONS + ['sheet_total']:
    _X, _Y = [], []
    for d in COM:
        v = float(REG[d][_r])
        if v <= 0: continue
        rg = CEN[d]['regime']
        _X.append([1.0, math.log(float(CEN[d]['window_days']))] +
                  [1.0 if rg == g else 0.0 for g in REGS[1:]])
        _Y.append(math.log(v))
    _b, _, _, _ = lstsq(_X, _Y)
    _BET[_r] = _b[1]
print(f"  {'地域':<6s}{'水準のβ':>9s}{'生の反発':>10s}{'窓長のみ補正':>14s}{'窓長+段差':>12s}")
for _r in REGIONS:
    _a = float(REG[_A][_r]); _bv = float(REG[_B][_r])
    _raw = _bv / _a - 1
    _win = (_bv / _a) / math.exp(_BET[_r] * _lw) - 1
    _both = (_bv / _a) / math.exp(_BET[_r] * _lw) / CUTOFF_STEP['total'] - 1
    print(f"  {_r:<6s}{_BET[_r]:>9.3f}{_raw:>10.1%}{_win:>14.1%}{_both:>12.1%}")
print(f"""
  → **生データの「日本だけ反発していない」（JP +14.4% 対 NA +29.9%、差 15.5pt）は、
     大半が窓長の産物である。** 窓が 55→92日 に伸びると、フロー比率の高い NA/EU が
     機械的に大きく伸びる。地域別の β で補正すると **差は 5.5pt まで縮む**。
  → **窓長だけを補正すると、全地域で反発は消える**（JP −5.7% / NA −0.6% / EU −5.1%）。
     見えていた「反発」のほとんどは、**より長い窓でより多くのキャラを拾っただけ**である。
  → 3列目は足切り段差を**全地域共通と仮定**した場合。§7 の通り**地域別の段差は測定不能**
     （Lv80超 は地域データで n=1）なので、**3列目は仮定に依存する。**
  → **結論: 2026年の反発は地域別に分解できない。** ただし
     **「日本には反発が来ていない」という生データの読みは、窓長の産物として棄却される。**""")

hdr("B-3. 非公開機能の補正を『データに入れて回帰しなおす』とどうなるか")
def _refit(adjust):
    out = {}
    for r in REGIONS:
        X, Y = [], []
        for d in COM:
            if float(REG[d][r]) <= 0: continue
            rg = CEN[d]['regime']
            X.append([1.0, math.log(float(CEN[d]['window_days']))] +
                     [1.0 if rg == g else 0.0 for g in REGS[1:]])
            num = float(REG[d][r]); den = float(REG[d]['sheet_total'])
            if adjust and D(d) >= date(2024, 11, 1):
                fac = lambda q: (1 / (1 - NONDISC_JP) if q == 'JP' else 1 / (1 - NONDISC_OTHER))
                num *= fac(r)
                den = sum(float(REG[d][q]) * fac(q) for q in REGIONS if float(REG[d][q]) > 0)
            Y.append(math.log(num / den))
        b, se, n, r2 = lstsq(X, Y)
        base = b[0] + b[1] * math.log(64) + b[3]
        fit = {}; i = 0
        for d in COM:
            if float(REG[d][r]) <= 0: continue
            yh = sum(b[a] * X[i][a] for a in range(len(b)))
            fit[d] = math.exp(base + (Y[i] - yh)); i += 1
        out[r] = fit
    return out

NONDISC_JP, NONDISC_OTHER = 0.03, 0.007
print(f"  非公開率: JP {NONDISC_JP:.1%} / JP以外 {NONDISC_OTHER:.1%}（Phase 2 §1-2）、導入 2024-08〜11")
print(f"\n  {'手順':<30s}{'初期3点':>10s}{'直近3点':>10s}{'変化':>9s}")
for lab, ad in (('補正なし（v1.1 の系列）', _refit(False)),
                ('データに補正を入れて再回帰', _refit(True))):
    a = ad['JP']; ds = [d for d in COM if d in a]
    f_ = st.mean([a[d] for d in ds[:3]]); l_ = st.mean([a[d] for d in ds[-3:]])
    print(f"  {lab:<30s}{f_:>10.2%}{l_:>10.2%}{(l_-f_)*100:>+8.2f}pt")
_a0 = _refit(False)['JP']; _ds = [d for d in COM if d in _a0]
_ex = st.mean([_a0[d] for d in _ds[-4:-1]]) - st.mean([_a0[d] for d in _ds[:3]])
print(f"""
  → **縮小は 0.11pt であって 0.53pt ではない。** v1.1 の「残差 −0.5pt とほぼ同額」は誤り。
     +0.53pt は**水準**の補正で、レジームダミー（基準）も同時に押し上げるため、
     **変化量である残差からそのまま差し引くことはできない。**
     実勢低下の下限が狭まるのは事実だが、狭まる幅は 1/5 である。

  【第10次監査 軽微7】直近3点のうち 2026-07-20 は Lv80超 n=1 で、その補正値は
     ダミーが残差を全吸収するため**モデルの当てはめ定数**であり観測情報を持たない。
     この点を外すと変化は {_ex*100:+.2f}pt（3点版は {(st.mean([_a0[d] for d in _ds[-3:]])-st.mean([_a0[d] for d in _ds[:3]]))*100:+.2f}pt）。""")

hdr("B-2. 【重要】レジームダミーと時間トレンドは交絡している")
tt = [(D(d) - date(2017, 6, 6)).days / 365.25 for d in COM]
Xr = [[1.0] + [1.0 if CEN[d]['regime'] == g else 0.0 for g in REGS[1:]] for d in COM]
_, _, _, r2t = lstsq(Xr, tt)
print(f"  time を レジームダミーだけに回帰した R² = {r2t:.3f}")
print("  **足切り改定は時間とともに起きているので、ダミーはほぼ時間ブロックそのものである。**")
print("  したがって『ダミーで吸収してから残差のトレンドを見る』という手順は、")
print("  **構造的に「トレンドなし」側へ倒れる。** 3通りの定式化を並べる:\n")
lw = [math.log(float(CEN[d]['window_days'])) for d in COM]
Yj = [math.log(share(d, 'JP')) for d in COM]
Xa = [[1.0, lw[i]] + [1.0 if CEN[COM[i]]['regime'] == g else 0.0 for g in REGS[1:]]
      for i in range(len(COM))]
ba, _, _, _ = lstsq(Xa, Yj)
res = [Yj[i] - sum(ba[k] * Xa[i][k] for k in range(len(ba))) for i in range(len(COM))]
bb, seb, _, _ = lstsq([[1.0, tt[i]] for i in range(len(COM))], res)
Xb = [[1.0, lw[i], tt[i]] for i in range(len(COM))]
b2, se2, _, _ = lstsq(Xb, Yj)
Xc = [[1.0, lw[i], tt[i]] + [1.0 if CEN[COM[i]]['regime'] == g else 0.0 for g in REGS[1:]]
      for i in range(len(COM))]
b3, se3, _, _ = lstsq(Xc, Yj)
print(f"  {'定式化':<40s}{'JPシェアのトレンド':>18s}{'t':>8s}")
print(f"  {'A ダミーで吸収 → 残差にトレンド（v1.0 の手順）':<40s}"
      f"{math.exp(bb[1])-1:>17.2%}{bb[1]/seb[1]:>8.2f}")
print(f"  {'B トレンドのみ（ダミーなし）':<40s}{math.exp(b2[2])-1:>17.2%}{b2[2]/se2[2]:>8.2f}")
print(f"  {'C トレンドとダミーを同時に投入':<40s}{math.exp(b3[2])-1:>17.2%}{b3[2]/se3[2]:>8.2f}")
print("""
  → **どれが正しいかはデータで決められない。** A は「足切り改定が全部説明する」、
     C は「実勢が落ちていてダミーは効いていない」という、正反対の識別である。
     **v1.0 は A だけを示して『シェアは落ちていない（確度高）』と書いた。これは撤回する。**

  −3.9pt の分解:
     窓長由来          約 −1.0pt  … 機構（フロー/ストック構成の差）で説明でき、頑健
     レジーム／時間由来  約 −2.4pt  … **測定（足切り改定）か実勢かを分離できない**
     残差              約 −0.5pt

  ただし**日本固有の測定要因が1つ既知である**（Phase 2 §1-2、v1.0 は落としていた）:""")
NDJ, NDO = 0.03, 0.007
s0 = st.mean([adj['JP'][d] for d in COM[-3:] if d in adj['JP']])
s_adj = (s0/(1-NDJ)) / ((s0/(1-NDJ)) + (1-s0)/(1-NDO))
print(f"     2024-08〜11 に Lodestone のキャラ情報非公開機能が入り、"
      f"**非公開率は JP {NDJ:.0%} / JP以外 {NDO:.1%}**。")
print(f"     観測 JPシェア {s0:.1%} → 非公開分を戻すと {s_adj:.1%}（{(s_adj-s0)*100:+.2f}pt）。")
print(f"     **これは残差 −0.5pt とほぼ同額であり、機構が既知の分だけ下限を狭める。**")

# ------------------------------------------------------------------ C
hdr("C. JP の水準 — 位相正規化（**生系列**であることに注意）")
print("  地域別は窓長正規化できないので、**水準の比較は生系列で行う**。")
print("  Phase 2 の禁止事項に触れるため、**同じ窓長帯の点だけ**を使って緩和する。")
band = [d for d in COM if 55 <= float(CEN[d]['window_days']) <= 75]
print(f"  窓長 55〜75日 に限定: {len(band)}/{len(COM)} 点\n")
print(f"  {'世代':<6s}{'JP 平均':>12s}{'全体 平均':>12s}{'JP比率':>9s}{'n':>4s}")
for g, a, bb in GENS:
    ds = [d for d in band if a <= D(d) < bb]
    if not ds: continue
    jp = st.mean([float(REG[d]['JP']) for d in ds])
    tt = st.mean([float(REG[d]['sheet_total']) for d in ds])
    print(f"  {g:<6s}{jp:>12,.0f}{tt:>12,.0f}{jp/tt*100:>8.1f}%{len(ds):>4d}")
pk = max(band, key=lambda d: float(REG[d]['JP']))
lt = band[-1]
print(f"\n  JP のピーク: {pk}  {float(REG[pk]['JP']):,.0f}")
print(f"  直近（同帯）: {lt}  {float(REG[lt]['JP']):,.0f}  ピーク比 {float(REG[lt]['JP'])/float(REG[pk]['JP'])-1:+.1%}")
tpk = max(band, key=lambda d: float(REG[d]['sheet_total']))
print(f"  全体のピーク: {tpk}  {float(REG[tpk]['sheet_total']):,.0f}")
print(f"  直近（同帯）: {float(REG[lt]['sheet_total']):,.0f}  ピーク比 "
      f"{float(REG[lt]['sheet_total'])/float(REG[tpk]['sheet_total'])-1:+.1%}")

# ------------------------------------------------------------------ D
hdr("D. JP のフロー／ストック構成 — 窓長係数からの逆算")
print("""  地域別内訳は存在しないが、**窓長係数がその代理になる**。
  総数 = 継続 + (新規+復帰) で、継続の窓長弾力性 ≈ 0.28、フロー ≈ 1.1〜1.3（Phase 2 §2-1）。
  地域 r の総数の窓長弾力性 β_r は、フロー比率 φ_r のほぼ線形関数になる:
      β_r ≈ 0.28·(1−φ_r) + 1.2·φ_r  →  φ_r ≈ (β_r − 0.28) / 0.92""")
# 【第9次 F3】この方法は**真値が分かる場所で検証できる**（全体のフロー比率は
# census_normalized.csv の flow_share 列に直接ある）。v1.0 はその検証をしていなかった。
Xt = [[1.0, math.log(float(CEN[d]['window_days']))] +
      [1.0 if CEN[d]['regime'] == g else 0.0 for g in REGS[1:]] for d in COM]
Yt = [math.log(float(REG[d]['sheet_total'])) for d in COM]
bt, _, _, _ = lstsq(Xt, Yt)
FS = [float(r['flow_share']) for r in csv.DictReader(open(CENSUS_CSV)) if r['flow_share']]
phi_true = st.mean(FS)
phi_naive = (bt[1] - 0.28) / 0.92
print(f"\n  【検証】全体で試すと: 逆算 φ={phi_naive:.1%} 対 "
      f"**直接測定 {phi_true:.1%}**（flow_share 列, n={len(FS)}）")
print(f"     → 逆算法は真値が分かる場所で {(phi_naive-phi_true)*100:+.1f}pt ずれる"
      f"（相対 {phi_naive/phi_true-1:+.0%}）。**v1.0 はこの検証を行っていなかった。**")
f_cal = (bt[1] - 0.28 * (1 - phi_true)) / phi_true
print(f"     ずれの原因はフロー弾力性の仮定。全体を再現する値は f={f_cal:.3f}"
      f"（仮定していた 1.2 ではない）。**これで較正する。**\n")
print(f"  {'地域':<6s}{'β（窓長弾力性）':>18s}{'φ（v1.0・未較正）':>18s}{'φ（較正後）':>14s}")
for r in REGIONS:
    X, Y = [], []
    for d in COM:
        if float(REG[d][r]) <= 0: continue
        rg = CEN[d]['regime']
        X.append([1.0, math.log(float(CEN[d]['window_days']))] +
                 [1.0 if rg == g else 0.0 for g in REGS[1:]])
        Y.append(math.log(float(REG[d][r])))
    b, se, n, r2 = lstsq(X, Y)
    phi_raw = (b[1] - 0.28) / 0.92
    phi_c = (b[1] - 0.28) / (f_cal - 0.28)
    print(f"  {r:<6s}{b[1]:>14.3f} (t={b[1]/se[1]:+.1f}){phi_raw:>18.1%}{phi_c:>14.1%}")
# 【第10次監査 重大5】ずれ −8.1pt を全額 f に帰すのは**識別上の選択**である。
# ストック側に帰す代替較正を併記しないと、φ が選択に依存することが見えない。
s_cal = (bt[1] - 1.2 * phi_true) / (1 - phi_true)
print(f"\n  【代替較正】ずれをストック弾力性に帰すと s={s_cal:.3f}（f=1.2 のまま）:")
print(f"  {'地域':<6s}{'φ（f 側較正・採用）':>20s}{'φ（s 側較正）':>16s}{'差':>9s}")
_mx = 0.0
for r in REGIONS:
    X, Y = [], []
    for d in COM:
        if float(REG[d][r]) <= 0: continue
        rg = CEN[d]['regime']
        X.append([1.0, math.log(float(CEN[d]['window_days']))] +
                 [1.0 if rg == g else 0.0 for g in REGS[1:]])
        Y.append(math.log(float(REG[d][r])))
    b, _, _, _ = lstsq(X, Y)
    pf = (b[1] - 0.28) / (f_cal - 0.28); ps = (b[1] - s_cal) / (1.2 - s_cal)
    _mx = max(_mx, abs(ps - pf))
    print(f"  {r:<6s}{pf:>20.1%}{ps:>16.1%}{(ps-pf)*100:>+8.1f}pt")
print(f"  → **どちらの較正でも順序は変わらないが、水準は最大 {_mx*100:.1f}pt 動く。**")
print(f"     f={f_cal:.3f} は Phase 2 の直接測定 1.1〜1.3 と整合しない。**ずれの真因が")
print(f"     f でない可能性は排除できていない。**")
print(f"     なお φ_true は census_normalized 全点（n={len(FS)}）、β は共通時点（n={len(COM)}）で標本が違う。")

print("""
  **【精度】t 値は「β≠0」の検定であって φ の精度ではない。**
  Phase 2 の弾力性は幅が広く（フロー 1.2±0.33、継続 0.28±0.16）、これを伝播させると
  φ_JP の区間は 0 を含む。**地域間の序列（JP が最低）も統計的には有意でない。**
  したがって φ は**小数1桁で読んではならない。** 言えるのは順序の向きだけである。""")
print("""
  → **JP はフロー比率が最も低い＝最も「定着した」市場である**（順序の向きのみ。`[Estimate]` 低）。
     2017-12-01 の記事が伝える地域別の継続課金率（JP 69% / NA 55% / EU 51%）と同じ向き。
     含意: **日本は新規流入が細っても水準が落ちにくいが、いったん落ちると戻りにくい。**
     Phase 4 の「毀損しているのは定着ではなく新規獲得」は、**日本では最も緩やかに効く。**""")

# ------------------------------------------------------------------ E
hdr("E. 売上側の日本比率")
print(f"""  MMO サブセグメントの実効海外売上比率 s^MMO = {S_MMO}（Phase 6 §2、レンジ {S_MMO_RANGE}）
  → **MMO 売上の国内比率は約 {1-S_MMO:.0%}**。ただしこれは DQX（ほぼ100%国内）を含む。

  FY2026.3 の MMO 名目売上 {MMO_NOMINAL[2026]}億円 に対して:""")
dom = MMO_NOMINAL[2026] * (1 - S_MMO)
print(f"    国内 約 {dom:.0f}億円 / 海外 約 {MMO_NOMINAL[2026]-dom:.0f}億円")
print(f"""  DQX+FFXI が MMO に占める比率を 15% とすると（Phase 6 §2-3 の中心）、
    DQX+FFXI（ほぼ国内） 約 {MMO_NOMINAL[2026]*0.15:.0f}億円
    → **FFXIV の国内売上は 約 {dom - MMO_NOMINAL[2026]*0.15:.0f}億円**（MMO 全体の {(dom-MMO_NOMINAL[2026]*0.15)/MMO_NOMINAL[2026]:.0%}）
       FFXIV 全体（約 {MMO_NOMINAL[2026]*0.85:.0f}億円）に占める国内比率は
       **約 {(dom-MMO_NOMINAL[2026]*0.15)/(MMO_NOMINAL[2026]*0.85):.0%}**

  【第9次 F4 — これは独立した検証ではない】
  **この 32% は、そもそもキャラ数シェアから構築された値である。** Phase 6 の s^MMO は
  「キャラ数シェア × 地域別月額 × 継続課金率」で作られており、上の分解はそれを逆算しただけで、
  実際 (0.42−0.15)/0.85 = 31.8% = 1−0.684 とほぼ恒等式になる。
  **売上側にキャラ数シェアと独立な情報は入っていない。「一致した」を裏づけとして読んではならない。**
  実質的な中身は下の「相殺の機構」だけである。

  【感度】この 32% は2つの仮定に依存する:
    s^MMO を 0.55〜0.62 で振ると  国内比率 27.1〜35.3%
    DQX+FFXI 比率を 10〜17% で振ると 30.1〜35.6%
  → **「約32%」は ±4pt 程度の幅を持つ。** 111億円も同じ幅を持つ（約95〜125億円）。

  【なぜこの水準に落ち着くのか — 2つの効果が相殺している】
  Phase 6 §2-3 の3段階推定を追うと:
    ① キャラ数シェア × 地域別月額のみ  → FFXIV 海外比率 0.735（**国内 26.5%**）
    ② ＋地域別の継続課金率で補正       → FFXIV 海外比率 0.684（**国内 31.6%**）
  **日本の月額が北米の 64〜68% しかないこと（下押し）を、日本の継続課金率の高さ
  （JP 69% / NA 55% / EU 51%、2017-12 の記事注記）が打ち返している。**
  差し引きで、売上シェアはキャラ数シェアとほぼ同じ水準に落ち着く。

  【弱い裏づけ】§D の窓長弾力性から逆算した JP のフロー比率（較正後 14.3%、NA 35.8% / EU 41.2%）は、
  上の継続課金率とは別のデータ・別の方法から出ており、**順序の向きは一致する**。
  ただし §D の通り φ の区間は広く、序列は統計的に有意でない。**方向の一致以上には使えない。**
  **「日本は価格が安いが、定着している」** —— これが日本市場の基本性質である。

  【この推定の弱点】継続課金率 69/55/51% は **2017-12 の記事注記1回きり**で、9年前の値である。
  Phase 6 の s^MMO はこの1点に依存しており、更新も検証もできていない。""")

# ------------------------------------------------------------------ G
hdr("G. 日本のデータセンター別の内訳")
band2 = [d for d in COM if 55 <= float(CEN[d]['window_days']) <= 75]
print(f"  窓長 55〜75日 の点のみ（n={len(band2)}）。**日本のDCは4つで、2017年以降増えていない。**")
print(f"  （北米は **2022-11**（パッチ6.28）に Dynamis を追加して4DC化した。国勢調査での初出は 2022-12-31。**増設は北米に向かった。**）\n")
print(f"  {'DC':<11s}{'ピーク日':>12s}{'ピーク値':>11s}{'直近':>11s}{'ピーク比':>10s}")
lt2 = band2[-1]
for k in JP_DC:
    pk2 = max(band2, key=lambda d: int(DC[d][k]))
    print(f"  {k:<11s}{pk2:>12s}{int(DC[pk2][k]):>11,}{int(DC[lt2][k]):>11,}"
          f"{int(DC[lt2][k])/int(DC[pk2][k])-1:>+10.1%}")
print("""
  → **4DC すべてが 2022-10-16 に同時ピークを打ち、41〜50% 下げている。**
     特定のDC・コミュニティが崩れたのではなく、**日本全体が一様に縮んでいる。**
     「特定サーバーの過疎化」という説明は、このデータでは支持されない。""")

# ------------------------------------------------------------------ F
hdr("F. 8.x 予測の日本への含意")
import phase7_forecast as P7
r_ = P7.build()
jp_share_now = st.mean([adj['JP'][d] for d in last])
print(f"  全体の 8.x 周期平均（確率加重）= {P7.wavg(r_, 'cyc'):,.0f}（norm64・Lv80超統一）")
print(f"""
  【JP シェアをどの足切り基準で取るか — 第9次 F7】
  基準を Lv70超（n=13）に置くと {jp_share_now:.1%}。
  唯一の Lv80超 観測（2026-07-20）を基準にすると 31.9% だが、**n=1 なので
  その1点の残差と足切り段差を分離できない**。
  なお**足切り段差が地域で共通なら、シェアは足切り改定で変わらないはず**である
  （分子・分母に同じ係数が掛かるため）。その場合 {jp_share_now:.1%} が正しい。
  地域別の段差は測定不能（§7）なので、**31.9%〜{jp_share_now:.1%} をレンジとして扱う。**""")
JPS = (0.319, jp_share_now)
print(f"\n  {'前提':<34s}{'JP 8.x 周期平均':>18s}")
for lab, s_ in (('シェアが横ばい', jp_share_now),
                ('シェアが過去10年のトレンド継続', None),
                ('シェアが 4.x 期の水準へ回帰', None)):
    pass
# シェアのトレンド外挿（窓長補正後の系列に対する年次トレンド）
xs, ys = [], []
for d in sorted(adj['JP']):
    t = (D(d) - date(2017, 6, 6)).days / 365.25
    xs.append([1.0, t]); ys.append(math.log(adj['JP'][d]))
b, se, n, r2 = lstsq(xs, ys)
per_yr = math.exp(b[1]) - 1
t8 = (date(2028, 8, 1) - date(2017, 6, 6)).days / 365.25   # 8.x 周期の中央付近
trend_share = math.exp(b[0] + b[1] * t8)
# 【第10次監査 重大2】v1.1 は外挿年数を 3.5 とベタ書きしていた。由来がどこにも
# 書かれておらず、実際にはシェア推定の基準時点（直近3点の平均日）から 8.x 周期
# 中央（2028-08-01）までであり、**2.3年**である。3.5年は下限を約0.9万過小に見せていた。
_anchor = [D(d) for d in sorted(adj['JP'])[-3:]]
_anchor_mid = date.fromordinal(round(st.mean(x.toordinal() for x in _anchor)))
EXTRAP_YEARS = (date(2028, 8, 1) - _anchor_mid).days / 365.25
g4 = st.mean([adj['JP'][d] for d in adj['JP'] if date(2017,6,20) <= D(d) < date(2019,7,2)])
print(f"  {'シェア横ばい ' + f'{JPS[0]:.1%}〜{JPS[1]:.1%}':<34s}"
      f"{P7.wavg(r_,'cyc')*JPS[0]:>9,.0f}〜{P7.wavg(r_,'cyc')*JPS[1]:>9,.0f}")
_cdecay = (1 - 0.0229) ** EXTRAP_YEARS
print(f"  基準時点 {_anchor_mid} → 8.x 中央 2028-08-01 = {EXTRAP_YEARS:.2f}年"
      f"（減衰係数 {_cdecay:.4f}）")
print(f"  {'定式化C（−2.29%/年）が正しい場合':<34s}"
      f"{P7.wavg(r_,'cyc')*JPS[0]*_cdecay:>9,.0f}〜{P7.wavg(r_,'cyc')*JPS[1]*_cdecay:>9,.0f}")
print(f"  {'4.x 期の水準 ' + f'{g4:.1%}' + ' へ回帰':<34s}{P7.wavg(r_,'cyc')*g4:>19,.0f}")
_bc = P7.wavg(r_, 'cyc') / (1 + BACKCAST_BIAS_CYC)
print(f"  {'【推奨】バイアス補正後 × 上のシェア帯':<34s}"
      f"{_bc*JPS[0]:>9,.0f}〜{_bc*JPS[1]:>9,.0f}")
print(f"\n  【第9次 F5 / 第10次 重大3で出典訂正 → 第11次で採用規約を確定 → 第15次で帯へ】")
print(f"  補正後を採るのは phase8b の判定（『バイアス補正後のほうが足切り規約の変更に頑健』）による。")
print(f"  **第11次で「補正後に統一」をプロジェクトの採用規約として確定した**ので、")
print(f"  『2文書で採用規約が食い違う』という v1.2〜v1.4 の記述は**解消済み**である。")
print(f"  補正後の点推定を日本に適用すると **{_bc*JPS[0]:,.0f}〜{_bc*JPS[1]:,.0f}**。")

# 【第15次】全体の結論が点推定から帯に変わった（第13次）のに、日本レポートだけ点推定のままだった。
import phase13_identification as ID
_lo, _hi, _cen = ID.honest_band()
_wlo, _whi, _ = ID.honest_band(ID.GA_BOX_WIDE)
_c7 = P7.CYC7_MEAN
print(f"""
  ============================================================================
  【第15次で追加】**日本も点推定ではなく帯で出す**
  ============================================================================
  全体の採用値は第13次以降**帯**である（補正後 {_hi:.0%} 〜 {_lo:.0%}、中心 {_cen:.0%}）。
  日本レポートだけ点推定のままだったので揃える。

  全体の 8.x 周期平均の帯: {_c7*(1+_lo):>9,.0f} 〜 {_c7*(1+_hi):>9,.0f}
    × JP シェア {JPS[0]:.1%}〜{JPS[1]:.1%}
  → **JP の 8.x 周期平均 = {_c7*(1+_lo)*JPS[0]:,.0f} 〜 {_c7*(1+_hi)*JPS[1]:,.0f}**
     （中心 {_c7*(1+_cen)*JPS[0]:,.0f}〜{_c7*(1+_cen)*JPS[1]:,.0f}）

  走査箱を宣言済みの最も広いものに広げると全体の帯は {_whi:.0%} 〜 {_wlo:.0%} となり、
  → JP は **{_c7*(1+_wlo)*JPS[0]:,.0f} 〜 {_c7*(1+_whi)*JPS[1]:,.0f}** まで広がる。

  **この帯の幅は、シェアの前提（{JPS[0]:.1%}〜{JPS[1]:.1%}）よりも全体の帯のほうが効いている。**
  日本固有の施策より全体の流入 I が効く、という §B-4 の結論は帯にしても変わらない。""")
print(f"\n  シナリオ別（**未補正 / 補正後 を併記。v1.1 は未補正だけを出していた**）:")
for lab, k in (('Bear', 'Bear'), ('Base', 'Base'), ('Bull', 'Bull')):
    _c = r_[k]['cyc']; _cb = _c / (1 + BACKCAST_BIAS_CYC)
    print(f"    全体が {lab:<5s}（{_c:>9,.0f}）なら JP = "
          f"{_c*JPS[0]:>9,.0f}〜{_c*JPS[1]:>9,.0f}"
          f"  ／補正後 {_cb*JPS[0]:>9,.0f}〜{_cb*JPS[1]:>9,.0f}")
print(f"""
  ※ **§B-2 の通り、JP シェアのトレンドは識別されていない**（定式化Aなら −0.23%/年で
     有意でない、定式化Cなら −2.29%/年で有意）。上の2行目はCが正しい場合である。
     シェアの前提を振っても JP の 8.x 周期平均は **約 25.6万〜30.2万** に収まるのに対し、
     **全体のシナリオを振ると 19.0万〜32.7万 と幅が倍以上になる。**
     **シェアの想定より全体の水準のほうが効く。**
     → **日本固有の施策より、全体の新規流入 I が効く。**""")
