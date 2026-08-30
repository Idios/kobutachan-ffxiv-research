#!/usr/bin/env python3
"""
正典パラメータ登録簿（Phase 8 で新設。v5 = 第8次調査を反映）

【なぜ必要か】本プロジェクトで結論を動かしてきた誤りは、係数の不確実性ではなく
**スケール・基準・定式化の取り違え**だった。各量が「どのスケールか」を宣言し、
全スクリプトがここから import する。

【3つの独立したスケール軸】必ず全て揃えること
  A. 窓長      : raw（生） / norm64（64日換算）
  B. 足切り基準 : Lv36以上 / Lv60超 / Lv70超 / Lv80超
  C. 為替      : nominal（名目） / cc（恒常為替、FY2022.3基準）

【版の履歴】
  v3 第3次監査（C1〜C6, M9）。中心 ρ を定式化②へ、I_base の単点依存を明示
  v4 第6次監査（R6-1〜R6-5）。compute_i_base() 新設、S* 許容域の格子依存を摘出、
     足切り丸めを4成分化、RHO_OBS_MAX を生成元と同期、LAUNCH_MULT の基準を明示
  v4.1 第7次監査（F1〜F4）。加法制約を実際に課す、LAUNCH_MULT の正典を 1.729 へ、
     S* 許容域の判定を「判定不能」へ、検査器に自己テストを追加
  **v5 第8次調査。記事の万表記が「切り捨て」であることを実証し、CUTOFF_STEP を再導出**
     （詳細は下の CUTOFF_STEP のコメント）。**これは監査ではなく、追加のデータ調査による訂正である。**

【第8次調査が変えたこと】
  収束しない原因を分析したところ、致命的誤りの 85% は「ρ・I・足切り」の3つの基礎量に
  集中していた（`scripts/phase8_convergence.py`）。その3つはいずれも
  「1回しか測れていない」「識別できない」というデータの弱さを抱えている。
  そこで**データ側を1段掘り直した**結果、足切り段差については弱さの一部が解消した:
  記事の万表記の規約が確定し、正確な総数を分子に使えるようになった。
"""
import datetime as _dt
import datetime
from datetime import date
import csv, statistics as _st

# ============================================================
# 足切り基準の換算係数
# ============================================================
# 出所: 2026-07-20 の同日ペア（記事に旧基準/新基準が併記された唯一の回）。
#
# 【第8次調査 — 記事の万表記の規約を実証的に確定】
# 記事は**万単位でしか報じていない**（全桁は記事に存在しない。原文確認済み）。
# 一方、ワールド別スプレッドシートには**新基準の総数の全桁 955,708** がある
# （最終更新 2026-07-22 = 再集計の当日）。この1つの正確値が万表記の規約を決める:
#
#   四捨五入だとすると: 総数「95万」の範囲 [945,000, 955,000) は 955,708 を**含まない**
#                       （四捨五入なら 96万 と書かれるはずである）。
#                       内訳の和の範囲 [925,000, 955,000) も含まない。→ **棄却**
#   切り捨てだとすると: 総数 [950,000, 960,000)、内訳の和 [940,000, 970,000) の**両方が成立**。
#                       記事の但し書き「5+28+61=94≒95万」も、各項を切り捨てた和が
#                       総数の切り捨て値より小さく出るという切り捨て特有の現象そのもの。
#   → **出典は切り捨て表記である。「x万」の真値は [x万, x+1万) を取る。**
#
# v4 までの CUTOFF_STEP は記事の万表記どうしの比（95/102 等）で、2つの誤りを抱えていた:
#   (a) 分子の正確値 955,708 を手元に持ちながら、記事の丸め値 95万 で比を取っていた
#   (b) 万表記を四捨五入とみなす対称区間（±0.5万）で不確実性を測っていた（規約が誤り）
#
# 切り捨て規約＋加法制約＋正確な総数の下で重心を取り直す:
#   制約 新基準 new'+ret'+cont' = 955,708（厳密） / 旧基準 new''+ret''+cont'' = total''
#        各項は [x万, x+1万)、旧総数は [1,020,000, 1,030,000)
#   重心（250人刻みの格子。新 1,188点 / 旧 11,480点）
#        新基準 55,167 / 285,167 / 615,375        旧基準 82,438 / 312,438 / 632,438 / 1,027,312
CUTOFF_STEP = {'total': 0.9303, 'new': 0.6692, 'ret': 0.9127, 'cont': 0.9730}
# v4 までの値。**使用禁止**（記事の丸め値どうしの比）
CUTOFF_STEP_ARTICLE = {'total': 95/102, 'new': 5/8, 'ret': 28/31, 'cont': 61/63}
# 同じ制約下での段差レンジ。**±0.5万の対称区間ではない**
CUTOFF_STEP_RANGE = {'total': (0.9281, 0.9370), 'new': (0.5571, 0.7469),
                     'ret': (0.8757, 0.9347), 'cont': (0.9538, 0.9841)}
CENSUS_EXACT_TOTAL_20260720 = 955_708   # スプレッドシート（全桁）。記事の「95万」の真値
CUTOFF_ROUND_COUNTS = {'total': (95, 102), 'new': (5, 8), 'ret': (28, 31), 'cont': (61, 63)}
CUTOFF_STEP_TOTAL_RANGE = CUTOFF_STEP_RANGE['total']   # 後方互換
CUTOFF_STEP_TOTAL_ADDITIVE = 94/102                    # 由来追跡用
CUTOFF_ROUND_JOINT = None    # 第8次で規約が変わったため phase8_sensitivity.py 側で再導出

# 未測定の2段（Lv36以上→Lv60超、Lv60超→Lv70超）の仮定。
# **Phase 2 §1 は「Lv70超→Lv80超 の段差を他3段へ流用してはいけない」と明記している。**
# 既定は流用（＝実測と同じ）だが、これは仮定であって測定値ではない。
CUTOFF_STEP_UNMEASURED = CUTOFF_STEP['total']
REGIME_STEPS = {'Lv36以上': 3, 'Lv60超': 2, 'Lv70超': 1, 'Lv80超': 0}

def regime_factor(regime, unmeasured=None):
    """任意のレジームの値を Lv80超 基準へ換算する係数（総数用）"""
    u = CUTOFF_STEP_UNMEASURED if unmeasured is None else unmeasured
    n = REGIME_STEPS[regime]
    return (CUTOFF_STEP['total'] if n >= 1 else 1.0) * (u ** max(n - 1, 0))

# ============================================================
# 【第15次で新設】基準不一致（D-4）を「検出」ではなく「不可能」にするガード
# ============================================================
# 15ラウンドで D-4（尺度の不一致）は繰り返し再発している。第15次だけでも
#   - Phase 4 のファネル 133万→109万（97日窓・Lv60超 対 76日窓・Lv70超）
#   - Phase 3 の供給低下（2.x 基準 対 3.x 基準）
#   - Phase 3.5 の総アクティブ −37.9%（Lv70超 対 Lv80超）
# の3件が出た。**検査器が見つけるのでは遅い。揃っていない比較を書けなくする。**
class ScaleMismatch(AssertionError):
    """比較の基準（窓長・足切りレジーム・世代・通貨）が揃っていない"""


def census_rows(path=None):
    import csv as _csv
    return {r['date']: r for r in _csv.DictReader(open(path or CENSUS_CSV))}


def compare_census(d1, d2, field='normalized_64d', unify_regime=True, path=None):
    """国勢調査の2点を比較する**唯一の正規手続き**。

    生の値をそのまま割ってはならない。窓長は normalized_64d（64日換算）で、
    足切りレジームは regime_factor() で Lv80超 に揃えてから比較する。
    揃えられない要求（field を raw_total にして unify_regime=False 等）は
    **ScaleMismatch を投げる**。
    返り値: (v1_統一後, v2_統一後, 変化率, 説明文字列)
    """
    rows = census_rows(path)
    for d in (d1, d2):
        if d not in rows:
            raise KeyError(f"{d} は census_normalized.csv に無い")
    r1, r2 = rows[d1], rows[d2]
    if field == 'raw_total' and not unify_regime:
        raise ScaleMismatch(
            f"raw_total どうしの比較は窓長も足切りも揃っていない（{d1}: 窓{r1['window_days']}日"
            f"/{r1['regime']}、{d2}: 窓{r2['window_days']}日/{r2['regime']}）。"
            "normalized_64d ＋ regime 統一で比較すること。")
    if not r1.get(field) or not r2.get(field):
        raise ScaleMismatch(f"{field} が {d1} または {d2} で欠測。比較できない。")
    v1, v2 = float(r1[field]), float(r2[field])
    note = f"{field}"
    if field == 'normalized_64d':
        note = "窓長64日換算"
    else:
        raise ScaleMismatch(
            f"{field} は窓長正規化されていない。normalized_64d を使うこと。")
    if unify_regime:
        v1 *= regime_factor(r1['regime']); v2 *= regime_factor(r2['regime'])
        note += "・足切りLv80超統一"
    elif r1['regime'] != r2['regime']:
        raise ScaleMismatch(
            f"足切りレジームが違う（{d1}: {r1['regime']} / {d2}: {r2['regime']}）のに "
            "unify_regime=False が指定された。regime_factor で揃えること。")
    return v1, v2, v2 / v1 - 1, note


# ============================================================
# K1（活動キャラ数） — scale: norm64 / Lv80超
# ============================================================
CENSUS_CSV = 'data/census_normalized.csv'
K1_NOW = 853595
K1_FY2026_LV70 = 877538
# FY2026.3 の norm64 4点平均。**Lv70超 の生値 877,538 に総数段差を掛けて導出する**
# （v4 までベタ書きで、CUTOFF_STEP を変えても追随しなかった＝D-1）
# 年度平均（norm64・Lv80超統一）。**CSV から導出する**（v4 まではベタ書きで、
# CUTOFF_STEP を変えても追随しなかった。第8次で 0.1〜0.2% ずれていたことが判明）
def _fy_means(path=None):
    import csv as _csv
    rows = [r for r in _csv.DictReader(open(path or CENSUS_CSV)) if r['normalized_64d']]
    agg = {}
    for r in rows:
        y, m, _ = map(int, r['date'].split('-'))
        agg.setdefault(y + 1 if m >= 4 else y, []).append(
            float(r['normalized_64d']) * regime_factor(r['regime']))
    return {k: round(_st.mean(v)) for k, v in agg.items() if len(v) >= 3}

K1_FY_MEAN_LV80 = _fy_means()
K1_NOW_FY_MEAN = K1_FY_MEAN_LV80[2026]
FY_WITH_LAUNCH = {2018: '4.0', 2020: '5.0', 2022: '6.0', 2025: '7.0'}

# 観測系列（norm64・Lv80超統一）。**CSV から導出する**
# 【第8次監査 D-1 の再発】v5 まで K1_RANGE_OBS = (471662, 1321162) をベタ書きしており、
# CUTOFF_STEP を切り捨て基準に改めた後も追随していなかった（0.15〜0.23% ずれていた）。
def _k1_series(path=None):
    import csv as _csv
    rows = [r for r in _csv.DictReader(open(path or CENSUS_CSV)) if r['normalized_64d']]
    return [(r['date'], float(r['normalized_64d']) * regime_factor(r['regime']))
            for r in rows]

K1_SERIES_LV80 = _k1_series()
K1_RANGE_OBS = (round(min(v for _, v in K1_SERIES_LV80)),
                round(max(v for _, v in K1_SERIES_LV80)))

def k1_peak_in(lo, hi):
    """[lo, hi) の期間の K1 ピーク（norm64・Lv80超統一）を返す"""
    return max((v, d) for d, v in K1_SERIES_LV80 if lo <= d < hi)

# 拡張世代ごとのピーク（**すべて norm64・Lv80超統一**。
#  記事の「拡張進行ファネルの開始数」133万/109万 とは**別系列**なので混ぜてはならない）
K1_PEAK_60 = round(k1_peak_in('2021-11-01', '2023-07-01')[0])   # 6.0 暁月
K1_PEAK_70 = round(k1_peak_in('2023-12-01', '2025-05-01')[0])   # 7.0 黄金

# ============================================================
# 再捕捉率 ρ — scripts/phase8_retention.py が生成（定式化②、n=39）
# ============================================================
RHO_BY_GEN = {'4.x': 0.711, '5.x': 0.7117, '6.x': 0.677, '7.x': 0.7603}
RHO_7X_SAMEREGIME = 0.7603
RHO_REGIME_COEF = -0.0835
RHO_LV80_REGIME = 0.8303
RHO_BEAR_RATIO_RANGE = (0.8905, 0.9579)
RHO_LV80_RANGE = (0.74, 0.8)
I_BASE_RANGE = (140000, 200000)
SSTAR_RANGE_BY_TOL = {1.25: (702703, 807692), 1.5: (684211, 826531), 2.0: (662500, 857143)}
# ※ 第7次 F3 の通り、この値は格子・許容率・探索範囲に依存し well-posed ではない。参考値。
SSTAR_RANGE_BACKCAST = (684211, 826531)


def sstar_range_fine(tols=(1.25, 1.5, 2.0), dr=0.005, di=2500,
                     box=(0.72, 0.82, 130_000, 210_000)):
    """【第14次 D-1 対策】上の定数の生成器。定数を手で書き換えると必ず腐るので、
    整合チェッカ（check-M）がこの関数と定数を突き合わせる。遅いので遅延インポート。"""
    import statistics as _st
    import phase7_backcast as _BC
    r0, r1, i0, i1 = box
    gr = [r0 + dr * k for k in range(int(round((r1 - r0) / dr)) + 1)]
    gi = [i0 + di * k for k in range(int(round((i1 - i0) / di)) + 1)]
    gg = []
    for r_ in gr:
        for i_ in gi:
            _, e, _, _ = _BC.score(r_, i_)
            gg.append((r_, i_, _st.mean([abs(x) for x in e])))
    bb = min(m for _, _, m in gg)
    out = {}
    for t in tols:
        sel = [i_ / (1 - r_) for r_, i_, m in gg if m <= bb * t]
        out[t] = (round(min(sel)), round(max(sel)))
    return out
# 足切り段差の丸めが主指標に与える幅（scripts/phase8_sensitivity.py が出す値）
CUTOFF_ROUND_SENS_PT = '5.7pt'   # 第13次で再測（ローンチ倍率の訂正を反映）
BACKCAST_BIAS_CYC = 0.050   # 【第13次・査読後】バックキャストは実測を再現する倍率を使うので
                            # v5 の 0.050 に戻る。第13次第一稿の 0.022 は、バックキャストに
                            # 推定用の倍率を誤って適用した産物だった
BACKCAST_BIAS_BY_LAUNCH = {1.45: 0.002, 1.729: 0.021, 1.86: 0.03, 2.2: 0.054}
BACKCAST_MAE_ADOPTED = 0.0834
BACKCAST_MAE_BEST = 0.0427
RHO_BY_GEN_F3 = {'4.x': 0.7129, '5.x': 0.7142, '6.x': 0.6842, '7.x': 0.764}
RHO_BY_GEN_BADSPEC = {'4.x': 0.738, '5.x': 0.7, '6.x': 0.656, '7.x': 0.74}
RHO_RAW_NEAR64 = {'4.x': (0.7028, 5), '5.x': (0.7128, 4), '6.x': (0.6521, 5), '7.x': (0.7483, 4)}
RHO_OBS_MAX_SAMEREGIME = 0.8534
CYC7_MEAN_SIMPLE = 906552
CYC7_MEAN_TIME = 881460

# ============================================================
# 流入 I / ローンチ挙動
# ============================================================
I_BASE_MIXED = 191905
LAUNCH_MULT = None   # 下で導出（compute_i_base と同じ規約で分子・分母を揃える）
LAUNCH_MULT_ORIG = 1.86
LAUNCH_MULT_PHASE = 1.45
UNDERSHOOT = 0.87

# ============================================================
# ρ–I 結合 — 中心モデルでは使わない
# ============================================================
FLOW_COEF_CENTRAL = 0.0
FLOW_COEF = -0.301
FLOW_COEF_CI = (-0.919, 0.317)
FLOW_COEF_NOLAUNCH = -0.7832
FLOW_COEF_REGIME = -0.1595
FLOW_COEF_BADSPEC = -0.5144
OPERATING_FS = 0.2182
SAMPLE_FS = 0.2912
BASE_FLOWSHARE = 0.2182

# ============================================================
# 為替 — FY2022.3 基準
# ============================================================
FX_INDEX = {2018: 0.988, 2020: 0.9571, 2021: 0.9447, 2022: 1.0, 2023: 1.1741, 2024: 1.2654, 2025: 1.3318, 2026: 1.3409}
S_MMO = 0.58
S_MMO_RANGE = (0.55, 0.62)

# ============================================================
# K4（売上・利益） — scripts/phase6_recalc.py が生成
# ============================================================
MMO_NOMINAL = {2023: 533, 2024: 473, 2025: 555, 2026: 410}
REV_B_PER_Q = 24.7
REV_A_PER_CH = 8.693e-05
PULSE_LAUNCH_Q = 40.1
REV_A_OOS = 0.00011231
EPS = {'level': 0.751, 'loglog': 0.736, 'loglog_trend': 0.845, 'inertia': 1.0}
EPS_CENTRAL = 0.845
REV_DRIFT_4Y = 0.9131
REV_DRIFT_SENS = {1.0: (0.9781, 3), 0.98: (0.9591, 1), 0.96: (0.9401, 1), 0.94: (0.9212, 0), 0.93137: (0.9131, 0), 0.9: (0.8837, 0)}
REV_PER_CH_BY_ERA = {'FY2015-19': 13297, 'FY2020-22': 12571, 'FY2023-26': 10582}
MARGIN = {'Bear': (0.26, 0.31), 'Base': (0.31, 0.38), 'Bull': (0.38, 0.45)}
MARGIN_R4 = {'Bear': (0.26, 0.31), 'Base': (0.31, 0.38), 'Bull': (0.31, 0.38)}

# ============================================================
# カレンダー
# ============================================================
EXPANSIONS = {'2.0': datetime.date(2013, 8, 27), '3.0': datetime.date(2015, 6, 23), '4.0': datetime.date(2017, 6, 20), '5.0': datetime.date(2019, 7, 2), '6.0': datetime.date(2021, 12, 7), '7.0': datetime.date(2024, 7, 2)}
E8_ASSUMED = datetime.date(2027, 1, 15)

# 派生量（生成規則をここに置く。ベタ書きにしない）
RHO_LV80       = RHO_7X_SAMEREGIME * CUTOFF_STEP['cont'] / CUTOFF_STEP['total']
RHO_BEAR_RATIO = RHO_BY_GEN['6.x'] / RHO_BY_GEN['7.x']
RHO_CAP_LV80   = RHO_OBS_MAX_SAMEREGIME * CUTOFF_STEP['cont'] / CUTOFF_STEP['total']

def cc(nominal_oku, fy, s=S_MMO):
    I = FX_INDEX[fy]
    return nominal_oku * ((1 - s) + s / I)

# ============================================================
# 流入 I_base — **生成関数を正典とする**（第6次監査 R6-4。ベタ書き禁止）
# ============================================================
# 規約: I_t = (新規 × 新規段差 + 復帰 × 復帰段差) × 64/窓長
#   - new_scaled / returning_scaled は**生のカテゴリ実数**（64日換算済みではない）
#   - 段差は Lv70超 の回にのみ適用（2026-07-20 は既に Lv80超）
I_BASE_DATES = ['2025-09-27', '2025-11-30', '2026-02-23', '2026-04-19', '2026-07-20']

def _census_rows(path=None):
    return {r['date']: r for r in csv.DictReader(open(path or CENSUS_CSV))}

def inflow_lv80(row, step=None):
    s = CUTOFF_STEP if step is None else step
    n = REGIME_STEPS[row['regime']]
    u = CUTOFF_STEP_UNMEASURED ** max(n - 1, 0)
    fn = (s['new'] if n >= 1 else 1.0) * u
    fr = (s['ret'] if n >= 1 else 1.0) * u
    k = 64 / float(row['window_days'])
    return float(row['new_scaled']) * fn * k, float(row['returning_scaled']) * fr * k

def compute_i_base(dates=None, step=None, path=None):
    rows = _census_rows(path)
    return _st.mean([sum(inflow_lv80(rows[d], step)) for d in (dates or I_BASE_DATES)])

I_BASE_LV80   = round(compute_i_base())
I_BASE_EX0720 = round(compute_i_base(I_BASE_DATES[:-1]))

# ============================================================
# ローンチ倍率 — **【第13次で全面訂正】分母の位相が2年ずれていた**
# ============================================================
# モデルは `I_launch = LAUNCH_MULT × i_base` を計算する。i_base は**直近（周期末）**の
# 流入水準である。したがって推定すべき量は
#     「ローンチ時の流入は、**その直前の周期末**の流入の何倍か」
# である。
#
# v5 までは 7.0 ローンチ窓（2024-08-27）の流入を **I_BASE_LV80（2025-09〜2026-07 の5点）**
# で割って 1.7434 としていた。**分子は 7.0 直後、分母はその1〜2年後**で、
# **周期上の位相が2年ずれている。** 分母はその間に減衰しているので、倍率は系統的に
# **過大**に出る。これは本プロジェクトが D-4（尺度・基準の不一致）として何度も
# 摘出してきた誤りの、位相方向での再発である。
#
# 正しい推定: 各ローンチ窓の流入 ÷ **その直前の周期末5点**の平均。
# 観測できるローンチは 5.0 / 6.0 / 7.0 の3回（4.0 は直前5点が取れない）。
LAUNCH_WINDOW_DATE = '2024-08-27'
LAUNCH_EVENTS = [('5.0', '2019-07-02', '2019-07-29'),
                 ('6.0', '2021-12-07', '2022-01-03'),
                 ('7.0', '2024-07-02', '2024-08-27')]

def launch_mults(step=None, path=None):
    """(拡張, ローンチ窓, 発売からの日数, 倍率) の列。**位相を揃えて測る**"""
    rows = _census_rows(path)
    ds = sorted(d for d in rows if rows[d]['new_scaled'])
    out = []
    for name, ld, lw in LAUNCH_EVENTS:
        pre = [d for d in ds if d <= ld][-5:]
        if len(pre) < 5:
            continue
        base = _st.mean([sum(inflow_lv80(rows[d], step)) for d in pre])
        num = sum(inflow_lv80(rows[lw], step))
        out.append((name, lw, (_dt.date(*map(int, lw.split('-')))
                               - _dt.date(*map(int, ld.split('-')))).days, num / base))
    return out

def compute_launch_mult(step=None, path=None):
    """3回のローンチの平均。**n=3 であり、幅は LAUNCH_MULT_RANGE を見ること**"""
    return _st.mean([m for *_, m in launch_mults(step, path)])

LAUNCH_MULT = round(compute_launch_mult(), 4)

# 【第13次・査読で摘出】**推定対象が2つある。混ぜてはならない。**
#   予測側: 「8.0 でどれだけ跳ねるか」= 未知。→ 3回のローンチの平均 LAUNCH_MULT
#   バックキャスト側: 「7.0 でどれだけ跳ねたか」= **既知・実測**。
#     バックキャストの i_base は 7.x 末なので、実測流入を再現する倍率は
#     実測流入 / I_BASE_LV80 であり、これは 1.7434 に一致する。
#   v6 の第一稿は予測側の訂正をバックキャストにも機械的に適用してしまい、
#   バックキャストがローンチ窓を 22.5% 過小に予測 → 上振れが小さく見える、という
#   **新しい誤りを作っていた**（訂正が次の誤りを作る、の再発）。
def backcast_launch_mult(step=None, path=None):
    """バックキャスト用。**7.0 の実測流入を再現する倍率**（推定ではない）"""
    rows = _census_rows(path)
    return sum(inflow_lv80(rows[LAUNCH_WINDOW_DATE], step)) / compute_i_base(step=step, path=path)
BACKCAST_LAUNCH_MULT = round(backcast_launch_mult(), 4)
_lm = [m for *_, m in launch_mults()]
LAUNCH_MULT_RANGE = (round(min(_lm), 4), round(max(_lm), 4))
LAUNCH_MULT_N = len(_lm)

# 【使用禁止】v5 までの採用値。分子は 7.0 直後、分母はその1〜2年後で位相が2年ずれている
LAUNCH_MULT_PHASEMISMATCH = 1.7434
LAUNCH_MULT_ORIG = 1.86        # 使用禁止（分母がさらに別基準）

# 7.0 だけを直前3点比で見た値（参考。LAUNCH_MULT の 7.0 成分に近い）
def compute_launch_mult_phase(path=None):
    rows = _census_rows(path)
    pre = [d for d in sorted(rows) if '2023-12-01' <= d < '2024-07-02' and rows[d]['new_scaled']]
    base = _st.mean([sum(inflow_lv80(rows[d])) for d in pre])
    return sum(inflow_lv80(rows[LAUNCH_WINDOW_DATE])) / base
LAUNCH_MULT_PHASE = round(compute_launch_mult_phase(), 4)


if __name__ == '__main__':
    print("=== 正典パラメータ v5（第8次調査：万表記＝切り捨てを実証）===")
    print(f"K1_NOW         = {K1_NOW:,} (norm64, Lv80超)")
    print(f"K1_NOW_FY_MEAN = {K1_NOW_FY_MEAN:,} (FY2026.3)")
    print("\n--- 足切り段差（第8次で再導出）---")
    print(f"{'成分':<8s}{'v5（切捨・加法制約・正確な総数）':>26s}{'v4まで（記事の万表記の比）':>24s}{'レンジ':>22s}")
    for k in ('total', 'new', 'ret', 'cont'):
        lo, hi = CUTOFF_STEP_RANGE[k]
        print(f"{k:<8s}{CUTOFF_STEP[k]:>26.4f}{CUTOFF_STEP_ARTICLE[k]:>24.4f}"
              f"{f'{lo:.4f}〜{hi:.4f}':>22s}")
    print(f"  正確な総数（スプレッドシート）= {CENSUS_EXACT_TOTAL_20260720:,}")
    print(f"\nρ(7.x)         = {RHO_7X_SAMEREGIME:.4f} → Lv80超 {RHO_LV80:.4f}"
          f"（v4 では 0.7904）")
    print(f"Bear 比        = {RHO_BEAR_RATIO:.4f}")
    print(f"I_BASE_LV80    = {I_BASE_LV80:,}（v4 では 168,634）／除外版 {I_BASE_EX0720:,}")
    print(f"LAUNCH_MULT    = {LAUNCH_MULT}（正典）／旧 {LAUNCH_MULT_ORIG}／位相整合 {LAUNCH_MULT_PHASE}")
    print(f"S* = I/(1-ρ)   = {I_BASE_LV80/(1-RHO_LV80):,.0f}")

    print("\n--- I_base の内訳 ---")
    _rows = _census_rows()
    for _d in I_BASE_DATES:
        _r = _rows[_d]; _n, _rt = inflow_lv80(_r)
        print(f"  {_d} ({_r['regime']:>6s}, 窓{_r['window_days']:>2s}日): "
              f"新規 {_n:>8,.0f} + 復帰 {_rt:>9,.0f} = {_n+_rt:>9,.0f}")

    print("\n--- バックキャストが制約する S* ---")
    _s = I_BASE_LV80/(1-RHO_LV80)
    for tol, (a, b) in sorted(SSTAR_RANGE_BY_TOL.items()):
        print(f"  許容率 ×{tol:<5}: {a:,}〜{b:,}  採用 S*={_s:,.0f} は "
              f"{'域内' if a <= _s <= b else '域外'}")
    print("  ※ 第7次 F3: この判定は格子・許容率・探索範囲の3つに依存し well-posed ではない。")
    print(f"  格子非依存の事実: 採用点の MAE {BACKCAST_MAE_ADOPTED:.2%}（最良点 {BACKCAST_MAE_BEST:.2%}）、"
          f"周期平均を {BACKCAST_BIAS_CYC:+.1%} 上振れ")
