#!/usr/bin/env python3
"""
Phase 13 — 主指標は何で動くのか。そして「バイアス補正で頑健になる」は誤りだった

【第13次の第一稿が犯した誤り — 査読で摘出、ここで撤回する】
  第一稿は「3つの基礎量（ローンチ倍率・ρ・I）を振っても補正後は 7pt しか動かない」
  を頑健性の証拠として提示した。**これは誤りである。**

  バックキャストの観測平均 co は CYC7_MEAN と**厳密に一致する**（同じ系列だから）。
  したがって
      補正後 = w/(1+bias)/CYC7_MEAN − 1 = w/(cp/co)/co − 1 = **w/cp − 1**
  ここで w = 8.x の予測平均、cp = **同じモデルが 7.x に出す予測平均**。
  つまり補正後の主指標は「モデルを 7.x 平均に in-sample で再較正した比」であり、
  **狭さは較正の定義的帰結であって、頑健性ではない。**

【第14次の訂正 — 第13次第二稿も誤っていた】
  第二稿は上の識別から「ρ・I は**定義上打ち消される**ので帯に入れても意味がない」と
  結論した。**これも誤りである。** 表の「補正後の幅」列が、実際には**生の幅**を
  印字していた（`band()` がタプルの生成分を読んでいた）ため、打ち消しの度合いを
  一度も測らないまま「打ち消される」と書いていた。実測すると:

      ρ  0.74/0.80  : 生 18.1pt → 補正後 **1.4pt**（ほぼ打ち消す）
      I  140k/200k  : 生 27.3pt → 補正後 **6.5pt**（**打ち消さない**）

  打ち消しが完全でないのは、**予測が I について1次同次でない**からである。予測は
  観測された S_0（853,595）から出発し、この初期値は I に比例しない。ρ も同様に、
  バックキャストと予測で初期条件・地平・位相が違うので比例的には通過しない。

【したがって帯は「打ち消しきらない前提」すべてで作る】
  ほぼ打ち消す（帯にほとんど寄与しない）: ρ 単独（補正後 1.4pt）
  打ち消しきらない（**これが本当の不確実性**）:
    - ρ と I の同時変動（S* 結合制約下＝群A。**一次元摂動で代用してはならない — R6-1**）
    - 8.0 後の I 倍率（設計上の選択。バックキャストの窓には存在しない）
    - シナリオ確率（主観確率。分子にしか入らない）
    - 平均化規約（等観測 / 時間加重）
    - ローンチ倍率（**第13次で予測用とバックキャスト用を分離したので、もう打ち消さない**）

使い方: python3 scripts/phase13_identification.py
"""
import sys

sys.path.insert(0, 'scripts')
import params as P
import phase7_backcast as BC
import phase7_forecast as F

W = 92
def hdr(t): print("\n" + "=" * W); print(t); print("=" * W)

BASE_SCEN = list(F.SCEN)


def measure(mult=None, rho=None, ib=None, scen=None, tw=False):
    """前提を差し替え、**その前提でバイアスを測り直してから**補正する"""
    rr = P.RHO_LV80 if rho is None else rho
    ii = P.I_BASE_LV80 if ib is None else ib
    F.LAUNCH_MULT = P.LAUNCH_MULT if mult is None else mult
    _, _, cp, co = BC.score(rr, ii)          # BC は BACKCAST_LAUNCH_MULT を使う
    bias = cp / co - 1
    sc = scen or [(l, r * rr / P.RHO_LV80, im, w) for l, r, im, w in BASE_SCEN]
    res = F.build(i_base=ii, scen=sc)
    key, base = ('cyc_tw', F.CYC7_MEAN_TW) if tw else ('cyc', F.CYC7_MEAN)
    w_ = F.wavg(res, key)
    F.LAUNCH_MULT = P.LAUNCH_MULT
    return bias, w_ / base - 1, w_ / (1 + bias) / base - 1


# 【第14次・査読で摘出】群Aの走査箱はどの文書にも宣言されていなかった。しかも
# 得られる両端は**常に I 格子の端**で、制約ではなく箱が縛っている。
# 第7次 F3（根本原因 D-13）が「箱は未宣言のメタパラメータで、判定は箱で反転する」と
# 認定済みなのに、第13次・第14次第一稿の §3-4 はそれを無視していた。箱を宣言し、振る。
GA_BOX_ADOPTED = (0.70, 0.84, 120_000, 220_000)
# `phase7_backcast.py` §F3 が「広大」として既に宣言・検討している箱
GA_BOX_WIDE = (0.66, 0.88, 80_000, 300_000)
GA_BOXES = [('採用', GA_BOX_ADOPTED),
            ('中間 ρ.70-.84 / I 100-240k', (0.70, 0.84, 100_000, 240_000)),
            ('拡大 ρ.66-.88 / I 100-260k', (0.66, 0.88, 100_000, 260_000)),
            ('広大（backcast §F3 が宣言済み）', GA_BOX_WIDE)]

_GA_CACHE = {}


def groupA_corrected(box=GA_BOX_ADOPTED):
    """群A（S* 結合制約下の ρ・I 同時スキャン）を**補正後**で評価する。

    【第14次】ρ・I は「定義上打ち消される」ので帯から外す、という第13次第二稿の判断は
    誤りだった。一次元摂動で代用してはならない（R6-1）ので、群Aの組でそのまま測る。
    **走査箱は引数で明示する。** 箱を書かずにこの帯を引用してはならない。
    返り値: [(名前, bias, 生, 補正後), ...]（帯に効く両端だけ）"""
    if box in _GA_CACHE:
        return _GA_CACHE[box]
    import statistics as _st
    a, b = P.SSTAR_RANGE_BY_TOL[1.5]
    r0, r1, i0, i1 = box
    rows = []
    r_ = r0
    while r_ <= r1 + 1e-9:
        ib = i0
        while ib <= i1:
            if a <= ib / (1 - r_) <= b:
                _, e, _, _ = BC.score(r_, ib)
                if _st.mean([abs(x) for x in e]) <= P.BACKCAST_MAE_BEST * 1.5:
                    rows.append((r_, ib) + measure(rho=r_, ib=ib))
            ib += 2_000
        r_ += 0.002
    lo = min(rows, key=lambda x: x[4]); hi = max(rows, key=lambda x: x[4])
    _GA_CACHE[box] = [(f'群A 下端 ρ={lo[0]:.3f} I={lo[1]:,}',) + lo[2:],
                      (f'群A 上端 ρ={hi[0]:.3f} I={hi[1]:,}',) + hi[2:]]
    return _GA_CACHE[box]


def _groups(box=GA_BOX_ADOPTED):
    """帯を作る『打ち消しきらない前提』の5群。main() と honest_band() で共有する
    （【第14次 D-1 対策】以前は帯を main() の中だけで作り、参照側がハードコードしていた）"""
    G2 = groupA_corrected(box)
    G3 = [(f'ローンチ倍率 {m:.4f}',) + measure(mult=m)
          for m in (P.LAUNCH_MULT_RANGE[0], P.LAUNCH_MULT_RANGE[1])]
    SC_LO = [(l, r_, 1.00, w_) for l, r_, im, w_ in BASE_SCEN]
    SC_HI = [(l, r_, (1.10 if l == 'Base' else 1.25 if l == 'Bull' else 1.00), w_)
             for l, r_, im, w_ in BASE_SCEN]
    G4 = [('8.0後の I 倍率 = 全て1.00',) + measure(scen=SC_LO),
          ('8.0後の I 倍率 = 上げ',) + measure(scen=SC_HI)]
    PW_LO = [(l, r_, im, w_) for (l, r_, im, _), w_ in zip(BASE_SCEN, (0.50, 0.40, 0.10))]
    PW_HI = [(l, r_, im, w_) for (l, r_, im, _), w_ in zip(BASE_SCEN, (0.10, 0.40, 0.50))]
    G5 = [('シナリオ確率 悲観寄り 50/40/10',) + measure(scen=PW_LO),
          ('シナリオ確率 楽観寄り 10/40/50',) + measure(scen=PW_HI)]
    G6 = [('平均化規約 = 等観測',) + measure(),
          ('平均化規約 = 時間加重',) + measure(tw=True)]
    return G2, G3, G4, G5, G6


_BAND_CACHE = {}


def honest_band(box=GA_BOX_ADOPTED):
    """(下限, 上限, 中心) — 打ち消しきらない前提すべてで作った補正後主指標の帯

    **box を明示せずに引用してはならない。** 下限は箱に依存する（§C）。"""
    if box not in _BAND_CACHE:
        cors = [c[3] for g in _groups(box) for c in g]
        _BAND_CACHE[box] = (min(cors), max(cors), measure()[2])
    return _BAND_CACHE[box]


def band(rows, idx):
    v = [c[idx] for c in rows]
    return (max(v) - min(v)) * 100


def main():
    hdr("A. まず、第一稿の誤りを明示する")
    _, _, cp, co = BC.score(P.RHO_LV80, P.I_BASE_LV80)
    r = F.build(); w = F.wavg(r, 'cyc'); bias = cp / co - 1
    print(f"  バックキャストの観測平均 co = {co:,.1f}")
    print(f"  7.x 周期平均 CYC7_MEAN     = {F.CYC7_MEAN:,.1f}")
    print(f"  一致するか: **{abs(co - F.CYC7_MEAN) < 1e-6}**\n")
    print(f"  補正後（定義どおり） = {w/(1+bias)/F.CYC7_MEAN-1:.6f}")
    print(f"  w / cp − 1          = {w/cp-1:.6f}")
    print("  → **恒等的に同じ。** 補正後は「モデルの 8.x 予測 ÷ 同じモデルの 7.x 予測」であり、")
    print("     **in-sample の再較正比**である。第一稿の「7pt に収まるから頑健」は**撤回する。**")
    print("     **ただし『だから ρ・I は定義上打ち消される』は言えない**（§B で実測する）。")
    print(f"     予測は観測された S_0 = {P.K1_NOW:,} から出発し、この初期値は I に比例しない。")
    print("     したがってモデルは I について1次同次ではなく、打ち消しは**部分的**である。")

    hdr("B. どれだけ打ち消すか — 生の幅と補正後の幅を並べて測る")
    print("  【第14次】第13次第二稿はこの列を『補正後の幅』と書きながら**生の幅**を印字し、")
    print("  打ち消しの度合いを一度も測らないまま『ρ・I は打ち消される』と結論していた。")
    print(f"\n  {'振る前提':<34s}{'生':>9s}{'補正後':>9s}   {'生の幅':>8s}{'補正後の幅':>12s}")
    def show(g, mark=False):
        for n, b, raw, cor in g:
            print(f"  {n:<34s}{raw:>9.1%}{cor:>9.1%}")
        star = '**' if mark else ''
        print(f"  {'':<34s}{'':>9s}{'':>9s}   {band(g,2):>6.1f}pt"
              f"{star + f'{band(g,3):.1f}pt' + star:>14s}")
    G1 = [('ρ = 0.74',) + measure(rho=0.74), ('ρ = 0.80',) + measure(rho=0.80)]
    G1b = [('I_base = 140,000',) + measure(ib=140000),
           ('I_base = 200,000',) + measure(ib=200000)]
    print("  ── 一次元摂動（**R6-1 の通り帯には使えない**。打ち消しの度合いを見るためだけ）")
    for g in (G1, G1b):
        show(g)
    print(f"  → ρ はほぼ打ち消す（{band(G1,2):.1f}pt → {band(G1,3):.1f}pt）が、")
    print(f"     **I は打ち消さない**（{band(G1b,2):.1f}pt → {band(G1b,3):.1f}pt）。S_0 が I に比例しないため。")
    print("\n  ── 帯を作る群（**これが本当の不確実性**）")
    G2, G3, G4, G5, G6 = _groups()
    for g, lab in ((G2, '群A: ρ・I 同時（S*制約下）'), (G3, 'ローンチ倍率'),
                   (G4, '8.0後の I 倍率'), (G5, 'シナリオ確率'), (G6, '平均化規約')):
        show(g, mark=True)

    hdr("C. 正直な帯 — ただし群Aの走査箱に依存する")
    ALL = G2 + G3 + G4 + G5 + G6
    lo, hi, cen = honest_band()
    print(f"""  打ち消しきらない前提（§B の5群）の包絡:

    **補正後の主指標 = {hi:.0%} 〜 {lo:.0%}（幅 {(hi-lo)*100:.0f}pt）、中心 {cen:.0%}**
    （群Aの走査箱 = ρ {GA_BOX_ADOPTED[0]}〜{GA_BOX_ADOPTED[1]} / I {GA_BOX_ADOPTED[2]:,}〜{GA_BOX_ADOPTED[3]:,}）

  第一稿が出した「−8% 〜 −15%（7pt）」は撤回する（打ち消される前提ばかりを振っていた）。""")

    print("""
  【第14次・査読で摘出 — 第14次第一稿の『帯を決めているのはシナリオ確率』は撤回する】
  群Aの両端は**常に I 格子の端**に来る。つまり縛っているのは S* 制約ではなく**走査箱**であり、
  その箱はどの文書にも宣言されていなかった。第7次 F3（D-13）が「箱は未宣言のメタパラメータで
  判定は箱で反転する」と認定済みだったのに、§3-4 はそれを無視していた。箱を振る:
""")
    print(f"  {'走査箱':<34s}{'群A 補正後':>22s}{'幅':>9s}{'組数':>7s}")
    band_by_box = {}
    for lab, bx in GA_BOXES:
        g = groupA_corrected(bx)
        v = [c[3] for c in g]
        band_by_box[lab] = (min(v), max(v))
        print(f"  {lab:<34s}{f'{min(v):+.2%} 〜 {max(v):+.2%}':>22s}"
              f"{(max(v)-min(v))*100:8.1f}pt")
    sc = band(G5, 3)
    wl, wh, _ = honest_band(GA_BOX_WIDE)
    gw = band_by_box['広大（backcast §F3 が宣言済み）']
    print(f"""
  → **シナリオ確率の補正後の幅は {sc:.1f}pt で、箱に依存しない。**
     群Aの幅は採用箱で {band(G2,3):.1f}pt、広大箱で {(gw[1]-gw[0])*100:.1f}pt。
     **広大箱では群Aがシナリオ確率を上回り、両端もシナリオ確率の外に出る。**
     したがって「帯を決めているのはシナリオ確率であって、モデルのパラメータではない」は
     **採用箱でのみ成り立つ主張である。撤回する。**

  **箱を広大まで広げた帯: {wh:.0%} 〜 {wl:.0%}（幅 {(wh-wl)*100:.0f}pt）**
     ＝ 7.x 周期平均 {F.CYC7_MEAN/10000:.1f}万 に対し **{F.CYC7_MEAN*(1+wl)/10000:.1f}万 〜 {F.CYC7_MEAN*(1+wh)/10000:.1f}万**

  → 言えるのは次の3つだけである:
     1. **上端は箱に依らず {wh:.0%} 前後で安定している**（シナリオ確率の楽観端が決めている）
     2. **下端は箱に依存し、{lo:.0%}（採用箱）〜 {wl:.0%}（広大箱）で動く**
     3. **シナリオ確率と群Aは同じ桁の不確実性源であり、どちらが最大かは箱で入れ替わる**

  なお生の主指標は、同じ前提の振り方で {min(c[2] for c in ALL):.0%} 〜 {max(c[2] for c in ALL):+.0%} に散る。
  **生 → 補正後で幅が {(max(c[2] for c in ALL)-min(c[2] for c in ALL))*100:.0f}pt → {(hi-lo)*100:.0f}pt にしか縮まないことが、
  「補正すれば頑健になる」が成り立たないことの実測である。**""")

    hdr("D. 帯にも入っていない前提 — 宣言しておく")
    print("""  **バックキャストの i_base の位相。** 予測は「周期開始前（7.x末）の水準」を定常 I に使う。
  これを 7.x に鏡映するなら、バックキャストの i_base は **6.x末** であるべきだが、
  現行は **7.x末**（＝予測対象周期の内部の情報）を使っている。
  6.x末（209,812）を使うと上振れは大きく出て、補正後の中心はさらに下がる。
  **本分析はこの規約を「7.x末」に固定している。これは未検証の選択である。**

  **バイアスが周期間に転移するという仮定。** 上振れは 7.x で1回しか測っていない（n=1）。
  「8.x でも同じ率で上振れする」は仮定であって測定ではない。

  → **したがって上の帯も下限ではない。** この分析が言えるのは
     **「8.x サイクル平均は 7.x より下がる。幅は少なくとも上の帯。方向は確か、大きさは不確か」**
     までである。""")


if __name__ == "__main__":
    main()
