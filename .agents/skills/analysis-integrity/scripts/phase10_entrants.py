#!/usr/bin/env python3
"""
Phase 10 — 新規参入 MMO の不振と、サービス終了の因果順序

【なぜ必要か】プレイヤー向けレポート v1.1 は2つの主張を置いていた。
  (1)「2024〜2026年の新規 MMO は例外なく 1〜4% まで崩壊」
  (2)「終わる直接のきっかけは運営指標の悪化ではなく意思決定主体の変更」
どちらも追加調査で成立しないことが分かった。本スクリプトは (1) を数値で作り直す。

【(1) の何が誤りだったか】
  比較していた残存率が**経過月数を揃えていない**。FFXIV は M+24、Throne and Liberty と
  New World は M+21 の値だった。しかも New World の直近値は
  **2025-10-28 の開発終了発表より後**の値で、環境要因ではなく内生イベントの結果である。
  経過月を揃えると、競合の残存率は M+9 で 5.7%〜17.9% と3倍以上ばらつく。

【(1) を揃え直しても残ること】
  FFXIV の優位は経過月を揃えても消えない。むしろ**揃えたほうが差が開く**
  （FFXIV は M+21 で 38.8%、同じ M+21 で TL 3.1% / NW 1.3%）。
  誤っていたのは「例外なく 1〜4%」という**幅の書き方**であって、桁が違うという結論ではない。

【Steam 同接そのものの限界】
  Steam の捕捉率はタイトルで 1%〜20% と桁で違う（OSRS 約1.0% / EVE 約19.8%）。
  したがって**絶対値の比較には使えない**。使えるのは同一タイトル内の時間推移だけである。

使い方: python3 scripts/phase10_entrants.py
"""
import csv
import sys
from collections import defaultdict

sys.path.insert(0, 'scripts')

W = 92
def hdr(t): print("\n" + "=" * W); print(t); print("=" * W)

MON = 'data/external/steam_ccu_monthly.csv'
CAL = 'data/external/steam_ccu_calibration.csv'

S = defaultdict(dict)
with open(MON) as _f:
    for r in csv.DictReader(_f):
        S[r['title']][r['year_month']] = int(r['peak_ccu'])

def ym(s):
    y, m = map(int, s.split('-')); return y * 12 + m

# ローンチ月（FFXIV は 7.0 = 2024-07-02。ピークはアーリーアクセスの前月に立つ）
LAUNCH = {'FFXIV': '2024-07', 'Throne and Liberty': '2024-10', 'New World': '2024-10'}
# 内生イベント（これ以降の値は「環境要因の証拠」として使ってはならない）
ENDOGENOUS = {'New World': ('2025-10', '開発終了を発表（2025-10-28）')}


def series(t):
    """(経過月, 年月, 同接, ピーク比) の列。ピークはローンチ前月以降の最大値"""
    l = LAUNCH[t]
    pts = [(ym(k) - ym(l), k, v) for k, v in sorted(S[t].items()) if ym(k) >= ym(l) - 1]
    pk = max(v for _, _, v in pts)
    return pk, [(m, k, v, v / pk) for m, k, v in pts]


def main():
    hdr("A. 経過月を揃えた残存率（ピーク同接比）")
    print("  ※ Steam 月次ピーク同接。**同一タイトル内の推移にのみ意味がある**（§C）")
    cols = [3, 6, 9, 12, 15, 18, 21]
    print(f"\n  {'タイトル':<24s}{'ピーク':>10s}" + "".join(f"{'M+'+str(c):>9s}" for c in cols))
    RET = {}
    for t in ('FFXIV', 'Throne and Liberty', 'New World'):
        pk, ser = series(t)
        d = {m: r for m, _, _, r in ser}
        RET[t] = d
        print(f"  {t:<24s}{pk:>10,}" + "".join(
            (f"{d[c]:>9.1%}" if c in d else f"{'—':>9s}") for c in cols))

    print(f"""
  → **v1.1 が並べていたのは FFXIV M+24（33.7%）と TL/NW M+21（3.1% / 1.3%）である。**
     経過月が3か月ずれていた。**揃えると差はむしろ開く**（M+21 で 38.8% 対 3.1% / 1.3%）。

  → **ただし「例外なく 1〜4%」は誤り。** 同じ M+9 で TL {RET['Throne and Liberty'][9]:.1%} に対し
     New World は {RET['New World'][9]:.1%} で、3倍以上ばらつく。""")

    hdr("B. New World の直近値は「環境要因」の証拠にならない")
    pk, ser = series('New World')
    print("  経過月  年月      同接      ピーク比")
    for m, k, v, r in ser:
        if 10 <= m <= 16:
            mark = '  ← 開発終了を発表（2025-10-28）' if k == '2025-10' else ''
            print(f"   M+{m:<3d} {k}  {v:>8,}  {r:>7.1%}{mark}")
    print("""
  → 2025-10 の 83.1% はシーズン施策による跳ね上がりで、**その同じ月に開発終了が発表され**、
     2か月後には 3.7% に落ちている。**直近の 1.3% は「新作 MMO が環境要因で死ぬ」証拠ではなく、
     「開発が打ち切られた後の値」である。** 打ち切りの結果を打ち切りの原因として使ってはならない。""")

    hdr("C. Steam 同接の捕捉率はタイトルで桁が違う — 絶対値の比較は不可")
    cal = defaultdict(dict)
    with open(CAL) as _f:
        for r in csv.DictReader(_f):
            cal[r['title']][r['year']] = int(r['steam_annual_peak_ccu'])
    OSRS_TOTAL_PEAK_2025 = 240_851   # 全プレイヤー同接の歴代最高（2025-08-03、Jagex 告知）
    osrs_steam = cal['Old School RuneScape']['2025']
    EVE_RATE = 0.198                 # phase3_5 §2-3 の実測
    print(f"  Old School RuneScape 2025: Steam 年間ピーク {osrs_steam:,} / 全体ピーク {OSRS_TOTAL_PEAK_2025:,}")
    print(f"    → Steam 捕捉率 **{osrs_steam/OSRS_TOTAL_PEAK_2025:.1%}**")
    print(f"  EVE Online: Steam 捕捉率 **{EVE_RATE:.1%}**（phase3_5 §2-3 の実測）")
    print(f"    → 同じ「Steam 同接」でも実人口に対する倍率が **{EVE_RATE/(osrs_steam/OSRS_TOTAL_PEAK_2025):.0f}倍** 違う。")
    print("""
  → FFXIV もランチャー直起動・PS5・Switch 2 が入らない。
     **Steam 同接は絶対値の比較にも、タイトル間のシェアの計算にも使えない。**
     使えるのは同一タイトル内の時間推移（＝残存率の形）だけである。""")

    hdr("D. 残存率の低さは「事業の失敗」と同じではない")
    print("""  Throne and Liberty は残存率 3.1%（M+21）だが、NCSoft 共同CEO は 2025 Q3 決算コールで
  **初年度売上を約2億ドルと述べている**。買い切り型（New World、Dune: Awakening）にとっては
  そもそも同接の維持は収益条件ではない。
  → **残存率は「継続的に遊ばれているか」の指標であって「儲かったか」の指標ではない。**
     サブスク型の FFXIV では両者がほぼ一致するが、**他モデルのタイトルには当てはまらない。**""")

    hdr("E. まとめ — v1.1 から何を変えるか")
    print("""  維持する: **FFXIV の残存率は競合と桁が違う**（経過月を揃えても、揃えたほうがむしろ開く）
  訂正する: 「例外なく 1〜4%」→ **M+9 で 5.7%〜17.9% とばらつく**。幅の書き方が誤り
  訂正する: New World の 1.2〜1.3% は**開発終了発表後の値**であり、環境要因の証拠に使えない
  追加する: Steam 捕捉率は 1%〜20% と桁で違うので**絶対値の比較には使えない**
  追加する: 残存率の低さは事業の失敗と同義ではない（TL は初年度売上 約2億ドル）""")


if __name__ == "__main__":
    main()
