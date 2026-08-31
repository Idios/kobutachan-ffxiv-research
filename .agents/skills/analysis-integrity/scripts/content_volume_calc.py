#!/usr/bin/env python3
"""FFXIV: content volume per patch / per generation / per unit time.

Reads data/ffxiv_content_volume.csv and emits generation aggregates.
Tests the counter-hypothesis "patches got heavier, so content did not shrink".
"""
import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ffxiv_content_volume.csv"
OUT = ROOT / "data" / "ffxiv_content_generation_summary.csv"

# Generation boundaries: x.0 launch -> next x.0 launch.
# 8.0 is the announced 2027-01 window (provisional) -> 7.x length is an estimate.
GEN_SPAN = {
    "2.x": (date(2013, 8, 27), date(2015, 6, 23)),
    "3.x": (date(2015, 6, 23), date(2017, 6, 20)),
    "4.x": (date(2017, 6, 20), date(2019, 7, 2)),
    "5.x": (date(2019, 7, 2), date(2021, 12, 7)),
    "6.x": (date(2021, 12, 7), date(2024, 7, 2)),
    "7.x": (date(2024, 7, 2), date(2027, 1, 1)),  # provisional
}
# COVID pushed 5.3 out by ~3 months; subtract to get a comparable 5.x length.
COVID_DAYS = 90

MAJOR = ["main_scenario_quests", "dungeons", "trials_normal", "trials_extreme",
         "raid_tiers_normal", "raid_tiers_savage", "ultimate", "alliance_raid",
         "new_job", "new_race", "pvp_update", "housing", "graphics_update"]
MINOR = {"minor_msq": "main_scenario_quests", "minor_dungeons": "dungeons",
         "minor_trials_normal": "trials_normal", "minor_trials_extreme": "trials_extreme",
         "minor_raid_normal": "raid_tiers_normal", "minor_raid_savage": "raid_tiers_savage",
         "minor_ultimate": "ultimate"}


def num(v):
    v = (v or "").strip()
    return int(v) if v.isdigit() else 0


rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
gens = ["2.x", "3.x", "4.x", "5.x", "6.x", "7.x"]

maj = {g: {k: 0 for k in MAJOR} for g in gens}   # major patches only
cyc = {g: {k: 0 for k in MAJOR} for g in gens}   # major + trailing minor patches
field_major = {g: [] for g in gens}
field_minor = {g: [] for g in gens}

for r in rows:
    g = r["generation"]
    for k in MAJOR:
        maj[g][k] += num(r[k])
        cyc[g][k] += num(r[k])
    for mk, tgt in MINOR.items():
        cyc[g][tgt] += num(r[mk])
    if r["large_field_content"].strip():
        field_major[g].append(f'{r["patch"]}:{r["large_field_content"].strip()}')
    if num(r["minor_large_field"]):
        field_minor[g].append(f'{r["patch"]}系マイナー x{num(r["minor_large_field"])}')

for g in gens:
    cyc[g]["large_field_new"] = len(field_major[g]) + sum(
        num(r["minor_large_field"]) for r in rows if r["generation"] == g)
    maj[g]["large_field_new"] = len(field_major[g])

KEYS = MAJOR + ["large_field_new"]
LABEL = {
    "main_scenario_quests": "メインクエスト", "dungeons": "ダンジョン",
    "trials_normal": "討滅戦(ノーマル)", "trials_extreme": "討滅戦(極)",
    "raid_tiers_normal": "レイド層(ノーマル)", "raid_tiers_savage": "レイド層(零式)",
    "ultimate": "絶シリーズ", "alliance_raid": "アライアンスレイド",
    "large_field_new": "大規模フィールド(新規/拡張)", "new_job": "新ジョブ",
    "new_race": "新種族", "pvp_update": "PvP大型更新", "housing": "ハウジング大型更新",
    "graphics_update": "グラフィックス更新",
}


def days(g):
    a, b = GEN_SPAN[g]
    d = (b - a).days
    return d - COVID_DAYS if g == "5.x" else d


print("=" * 96)
print("世代別 総量（メジャーパッチのみ / サイクル全体=メジャー+マイナー）")
print("=" * 96)
hdr = f'{"項目":<26}' + "".join(f"{g:>11}" for g in gens)
print(hdr)
for k in KEYS:
    line = f'{LABEL[k]:<24}'
    for g in gens:
        line += f'{maj[g][k]:>5}/{cyc[g][k]:<5}'
    print(line)

print()
print("=" * 96)
print("1メジャーパッチあたり平均（サイクル全体の総量 ÷ 6本）")
print("=" * 96)
print(f'{"項目":<26}' + "".join(f"{g:>11}" for g in gens))
for k in KEYS:
    line = f'{LABEL[k]:<24}'
    for g in gens:
        line += f"{cyc[g][k] / 6:>10.2f} "
    print(line)

print()
print("=" * 96)
print("単位時間あたり供給量（サイクル全体の総量 ÷ 世代日数 × 365 = 年あたり）")
print("=" * 96)
print(f'{"項目":<26}' + "".join(f"{g:>11}" for g in gens))
for k in KEYS:
    line = f'{LABEL[k]:<24}'
    for g in gens:
        line += f"{cyc[g][k] / days(g) * 365:>10.2f} "
    print(line)

print()
print("世代日数:", {g: days(g) for g in gens}, "(5.xはCOVID -90日補正、7.xは8.0=2027-01暫定)")

# --- composite index: battle content only, ARR-relaunch distortion excluded ---
print()
print("=" * 96)
print("複合指標: バトルコンテンツ総量（ID+討滅N+討滅極+レイド層N+レイド層S+絶+アラレ）")
print("=" * 96)
BATTLE = ["dungeons", "trials_normal", "trials_extreme", "raid_tiers_normal",
          "raid_tiers_savage", "ultimate", "alliance_raid"]
base_pp = base_pd = 0.0
first = True
for g in gens:
    tot = sum(cyc[g][k] for k in BATTLE)
    pp, pd_ = tot / 6, tot / days(g) * 365
    if first:
        base_pp, base_pd = pp, pd_
        first = False
    print(f"{g}: 総量={tot:>4}  1パッチ={pp:>6.2f} ({pp/base_pp*100:>6.1f}%)"
          f"  年あたり={pd_:>6.2f} ({pd_/base_pd*100:>6.1f}%)")

print()
print("同上、2.0(リブート一括投入)を除いた 2.1-2.5 基準:")
tot2 = sum(cyc["2.x"][k] for k in BATTLE) - (16 + 4 + 3 + 5)
print(f"2.x(2.1-2.5, 5本): 総量={tot2}  1パッチ={tot2/5:.2f}")
for g in gens[1:]:
    tot = sum(cyc[g][k] for k in BATTLE)
    print(f"{g}: 1パッチ={tot/6:>6.2f} ({tot/6/(tot2/5)*100:>6.1f}%)")

with OUT.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["generation", "gen_days", "major_patches", "metric",
                "total_major_only", "total_full_cycle",
                "per_major_patch", "per_year"])
    for g in gens:
        for k in KEYS:
            w.writerow([g, days(g), 6, k, maj[g][k], cyc[g][k],
                        round(cyc[g][k] / 6, 3),
                        round(cyc[g][k] / days(g) * 365, 3)])
print(f"\n-> {OUT}")


# --- supplementary cuts (x.1-x.5 only, x.0 only, major/minor split) ---
def supplementary():
    print("\n" + "=" * 88)
    print("x.1〜x.5 のみ（x.0 除外）— 運営パッチ1本の重さ")
    print("=" * 88)
    MINK = {"minor_dungeons": 1, "minor_trials_normal": 1, "minor_trials_extreme": 1,
            "minor_raid_normal": 1, "minor_raid_savage": 1, "minor_ultimate": 1}
    for g in gens:
        rs = [r for r in rows if r["generation"] == g and not r["patch"].endswith(".0")]
        tot = sum(num(r[k]) for r in rs for k in BATTLE) + sum(num(r[mk]) for r in rs for mk in MINK)
        msq = sum(num(r["main_scenario_quests"]) + num(r["minor_msq"]) for r in rs)
        print(f"{g}: バトル総量={tot:>3} 1パッチ={tot/5:>5.2f}  MSQ={msq:>3} ({msq/5:>4.1f}/本)")

    print("\n" + "=" * 88)
    print("メジャーパッチ本体 vs マイナーパッチ への配分（バトルコンテンツ）")
    print("=" * 88)
    for g in gens:
        rs = [r for r in rows if r["generation"] == g]
        mj = sum(num(r[k]) for r in rs for k in BATTLE)
        mn = sum(num(r[mk]) for r in rs for mk in MINK)
        print(f"{g}: メジャー{mj:>3} / マイナー{mn:>3} → マイナー比率 {mn/(mj+mn)*100:>5.1f}%")


supplementary()
