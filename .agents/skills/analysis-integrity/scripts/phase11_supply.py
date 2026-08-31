#!/usr/bin/env python3
"""
Phase 11 — コンテンツ供給量の定量化（間隔だけでなく「1パッチの重さ」も測る）

【なぜ必要か】プレイヤー向けレポートは「監視すべき先行指標はパッチ間隔」と書いていたが、
**間隔だけでは足りない。** 同じ間隔でも中身が薄くなれば供給は落ちる。逆に間隔が伸びても
1本が重くなっていれば総量は保たれる。**この2つを分けて測らないと、間隔の伸びを
「薄めた」とも「重くなった」とも読めてしまう。**

【何を測るか】3つの層に分ける。
  (1) **時間あたり供給** = 世代の総量 ÷ 世代日数。プレイヤーが体感する「遊ぶものがある頻度」
  (2) **1パッチあたりの量** = 世代の総量 ÷ パッチ本数。「1本の重さ」
  (3) **パッチ間隔** = 既存の指標
  恒等式: (1) = (2) ÷ (3)。**したがって (1) の低下は (2) か (3) のどちらかに帰着する。**

【測れないもの — 先に宣言する】
  **プレイ時間は測れない。** 1コンテンツあたりの消費時間を公開している資料は存在せず、
  外部推計（HowLongToBeat 等）はパッチ単位に分解されていない。したがって本スクリプトは
  **「本数」でしか測っていない。** ダンジョン1本とメインクエスト1本を同列に足せないので、
  **種別ごとに別々に出し、合成指数は「戦闘コンテンツ」に限る**（種別が同質な範囲）。

使い方: python3 scripts/phase11_supply.py
"""
import csv
import sys
from collections import defaultdict

sys.path.insert(0, 'scripts')

W = 92
def hdr(t): print("\n" + "=" * W); print(t); print("=" * W)

SUM = 'data/ffxiv_content_generation_summary.csv'
CAD = 'data/ffxiv_patch_cadence.csv'

G = defaultdict(dict)      # generation -> metric -> row
META = {}
with open(SUM) as _f:
    for r in csv.DictReader(_f):
        G[r['generation']][r['metric']] = r
        META[r['generation']] = (int(r['gen_days']), int(r['major_patches']))

GENS = ['2.x', '3.x', '4.x', '5.x', '6.x', '7.x']
# 戦闘コンテンツのみを合成する（同質な範囲に限る）。
# ハウジング・PvP・種族・グラフィックスは性質が違うので合成しない。
BATTLE = ['dungeons', 'trials_normal', 'trials_extreme',
          'raid_tiers_normal', 'raid_tiers_savage', 'ultimate', 'alliance_raid']


def full(g, m):
    """世代の総量（マイナーパッチ込み）"""
    return float(G[g][m]['total_full_cycle'])


def battle_total(g):
    return sum(full(g, m) for m in BATTLE)


def main():
    hdr("A. 恒等式 — 時間あたり供給 = 1パッチの量 ÷ パッチ間隔")
    print("""  プレイヤーが体感する「遊ぶものがある頻度」は時間あたり供給である。
  それが落ちる原因は2つしかない: **1本が軽くなったか、間隔が伸びたか。**
  この2つを分けないと「間隔が伸びた」を「薄めた」とも「重くなった」とも読めてしまう。\n""")
    print("  ※ ここでの「間隔」は **世代日数 ÷ パッチ本数**（拡張と拡張のあいだの空白期を含む）。")
    print("     パッチ実装日どうしの中央値（6.x/7.x = 133日）とは別の量である。\n")
    print(f"  {'世代':<6s}{'世代日数':>9s}{'本数':>6s}{'平均間隔(日)':>13s}"
          f"{'戦闘量/世代':>13s}{'戦闘量/パッチ':>14s}{'戦闘量/年':>12s}")
    rows = {}
    for g in GENS:
        d, n = META[g]
        bt = battle_total(g)
        rows[g] = {'days': d, 'n': n, 'gap': d / n, 'total': bt,
                   'per_patch': bt / n, 'per_year': bt / d * 365.25}
        r = rows[g]
        print(f"  {g:<6s}{d:>9,}{n:>6d}{r['gap']:>10.1f}"
              f"{bt:>13.0f}{r['per_patch']:>14.2f}{r['per_year']:>12.2f}")

    b = rows['4.x']    # 基準は 4.x（2.x は新生のリブート、3.x は移行期）
    print(f"\n  {'世代':<6s}{'間隔':>10s}{'1パッチの量':>13s}{'時間あたり供給':>16s}   （4.x = 100）")
    for g in GENS:
        r = rows[g]
        print(f"  {g:<6s}{r['gap']/b['gap']*100:>10.1f}"
              f"{r['per_patch']/b['per_patch']*100:>13.1f}"
              f"{r['per_year']/b['per_year']*100:>16.1f}")
    d7 = rows['7.x']['per_year'] / b['per_year'] - 1
    g7 = rows['7.x']['gap'] / b['gap'] - 1
    p7 = rows['7.x']['per_patch'] / b['per_patch'] - 1
    print(f"""
  → **7.x の時間あたり戦闘コンテンツ供給は 4.x 比 {d7:+.1%}。**
     内訳: 間隔が {g7:+.1%} 伸び、1パッチの量は {p7:+.1%}。
     **{'間隔の伸びがほぼ全部を説明する' if abs(p7) < abs(g7)/2 else '両方が効いている'}。**
     つまり **1本の重さは保たれており、落ちているのは頻度である。**""")

    hdr("B. 種別ごと — 「本数」を足せないものは足さずに並べる")
    METRICS = [('main_scenario_quests', 'メインクエスト'),
               ('dungeons', 'ダンジョン'),
               ('trials_normal', '討滅戦(ノーマル)'),
               ('trials_extreme', '討滅戦(極)'),
               ('raid_tiers_normal', 'レイド(ノーマル)'),
               ('raid_tiers_savage', 'レイド(零式)'),
               ('ultimate', '絶'),
               ('alliance_raid', 'アライアンスレイド'),
               ('large_field_new', '大規模フィールド'),
               ('new_job', '新ジョブ')]
    print("  年あたりの本数\n")
    print(f"  {'種別':<20s}" + "".join(f"{g:>9s}" for g in GENS) + f"{'4.x比':>11s}")
    for m, name in METRICS:
        vals = [full(g, m) / META[g][0] * 365.25 for g in GENS]
        base = vals[GENS.index('4.x')]
        rel = f"{vals[-1]/base-1:+.0%}" if base else "—"
        print(f"  {name:<20s}" + "".join(f"{v:>9.2f}" for v in vals) + f"{rel:>11s}")

    print(f"""
  → **一様に減っているのではない。**
     **メインクエストの年あたり本数だけが突出して落ちている**（4.x 比
     {full('7.x','main_scenario_quests')/META['7.x'][0]/(full('4.x','main_scenario_quests')/META['4.x'][0])-1:+.0%}）。
     戦闘コンテンツは種別によっては**増えている**（絶、大規模フィールド）。
     **「薄くなった」のではなく「配分が変わった」というほうが近い。**""")

    hdr("C. マイナーパッチへのシフト — 大型パッチだけ見ると減り方を過大評価する")
    print(f"  {'世代':<6s}{'大型パッチのみ':>15s}{'マイナー込み':>14s}{'マイナー比率':>14s}")
    for g in GENS:
        mo = sum(float(G[g][m]['total_major_only']) for m in BATTLE)
        fu = battle_total(g)
        print(f"  {g:<6s}{mo:>15.0f}{fu:>14.0f}{(fu-mo)/fu if fu else 0:>14.1%}")
    print("""
  → **6.x/7.x はマイナーパッチ経由の比率が高い。** 絶シリーズは全てマイナーパッチ、
     大規模フィールドコンテンツも無人島（6.2）以外は全てマイナーパッチである。
     **「大型パッチの中身」だけを数えると、供給の減り方を過大に見積もる。**""")

    hdr("D. 監視指標としてどう使うか")
    print(f"""  §A の恒等式から、監視すべき量は2つに分かれる。

  | 指標 | 現状 | 何が分かるか | 取得しやすさ |
  |---|---|---|---|
  | パッチ間隔（実装日どうしの中央値） | 6.x/7.x とも **133日で固定**（世代日数÷本数なら {rows['7.x']['gap']:.0f}日） | 供給の頻度 | **公式の実装日だけで測れる。最も改竄されにくい** |
  | 1パッチの戦闘コンテンツ本数 | 4.x 比 **{p7:+.0%}**（ほぼ横ばい） | 1本の重さ | パッチノートの数え上げが要る |
  | メインクエスト本数 | 年あたり 4.x 比 **{full('7.x','main_scenario_quests')/META['7.x'][0]/(full('4.x','main_scenario_quests')/META['4.x'][0])-1:+.0%}** | 物語の供給 | 同上 |

  → **間隔が最も早く・確実に見える。** ただし **間隔だけを見ていると「1本が軽くなる」形の
     減速を見逃す。** 8.0 はリボーン／エヴォルヴの2系統併存で保守対象が増えるので、
     **同じ間隔のまま1本の中身が軽くなる**という減り方があり得る。**両方を見る必要がある。**

  【測れないままのもの】
  - **1コンテンツあたりのプレイ時間。** 公開資料が存在しない。したがって本節の「量」は
    すべて**本数**であり、「ダンジョン1本」と「メインクエスト1本」は足していない。
  - **難易度・作り込みの density。** 数えられない。""")


if __name__ == "__main__":
    main()
