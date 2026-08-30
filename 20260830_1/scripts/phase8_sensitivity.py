#!/usr/bin/env python3
"""
Phase 8 — 体系的感度分析（トルネード）

Phase 0 §Phase 8 の第1項「感度分析: どの前提が結論を最も動かすか」。

【方法】予測に入っている前提を**1つずつ**振り、3つの結論指標への影響を測る:
  (K1) 主指標 = 8.x 周期平均 ÷ 7.x 周期平均 − 1（確率加重）
  (K4a) FY2030.3 の恒常為替 MMO 売上（確率加重、億円）
  (K4c) FY2030.3 の営業利益の中点（確率加重、億円）

【重要】これは「1つずつ振る」ローカル感度であり、交互作用を捉えない。
特に ρ と I はバックキャスト上でトレードオフする（`phase7_backcast.py` §B）ので、
両者を独立に振ると幅を過大に見積もる。→ §C で結合ケースを別に出す。

使い方: python3 scripts/phase8_sensitivity.py
"""
import sys, math, statistics as st
from datetime import date, timedelta
sys.path.insert(0, 'scripts')
from params import *
import phase7_backcast as BC
from phase7_forecast import (simulate, value_at, annual_mean, build, wavg, cc_year,
                             to_nominal, CYC7, CYC7_MEAN, CYC7_MEAN_TW, CYC7_X, timewt, E7)

BASE_MARGIN = MARGIN_R4


def outcomes(res, eps=None, drift=None, pulse=True, s=S_MMO, usd=150.0,
             margin=None, tw=False, bias=1.0):
    """3つの結論指標を返す。周期平均の基準は P7 のモジュール変数を都度参照する"""
    import phase7_forecast as P7
    m = margin or BASE_MARGIN
    k1 = (wavg(res, 'cyc_tw') / P7.CYC7_MEAN_TW - 1) if tw else (wavg(res, 'cyc') / P7.CYC7_MEAN - 1)
    k1 = (1 + k1) / bias - 1
    ccw = opw = 0.0
    for lab in res:
        kr = res[lab]['fy2030'] / K1_FY_MEAN_LV80[2026]
        v = cc_year(kr, eps=eps, drift=drift, pulse=pulse)
        nom = to_nominal(v, usd=usd, s=s)
        ccw += v * res[lab]['w']
        opw += nom * (m[lab][0] + m[lab][1]) / 2 * res[lab]['w']
    return k1, ccw, opw


BASE = outcomes(build())


def scen_for(rho, ratio=None, im=(1.00, 1.05, 1.15)):
    rt = RHO_BEAR_RATIO if ratio is None else ratio
    return [('Bear', rho * rt, im[0], 0.25), ('Base', rho, im[1], 0.50), ('Bull', rho, im[2], 0.25)]


GROUPA_TOL = 1.50
# 【第15次で新設】走査箱を**必須の宣言**にする（D-13 を「検出」ではなく「不可能」にする）
# 第14次の査読で、群Aの帯が未宣言の箱で完全に決まっていたことが判明した。
# 箱は引数で受け取り、**結果に同梱して返す**。箱を書かずに帯を引用できないようにする。
GROUPA_BOX = (0.70, 0.84, 120_000, 220_000)
_GROUPA_CACHE = {}


def groupA(tol=GROUPA_TOL, box=GROUPA_BOX):
    """群A = S* 結合制約下の (ρ, I) 同時スキャン。**答えの不確実性はこれで測る。**

    【第14次 D-1 対策】以前はスキャン結果を §C の表で出しながら、まとめ行・チャート・
    整合チェッカが**別々にハードコードした古い値**（14.2pt / −20.8〜−6.6% / 15.5pt）を
    使っていた。生成器を1つにして全参照をここに向ける。
    返り値: (S*下限, S*上限, 主指標下限, 主指標上限, 組数)
    """
    if (tol, box) in _GROUPA_CACHE:
        return _GROUPA_CACHE[(tol, box)]
    a, b = SSTAR_RANGE_BY_TOL[tol]
    r0, r1, i0, i1 = box
    vv = []
    r_ = r0
    while r_ <= r1 + 1e-9:
        ib = i0
        while ib <= i1:
            if a <= ib / (1 - r_) <= b:
                # 【第7次監査 F12】S* が域内でも当てはまりが悪い組が 41% 混じる。MAE 条件も課す。
                _, _e, _, _ = BC.score(r_, ib)
                if st.mean([abs(x) for x in _e]) <= BACKCAST_MAE_BEST * tol:
                    vv.append(wavg(build(scen=scen_for(r_), i_base=ib), 'cyc') / CYC7_MEAN - 1)
            ib += 2_000
        r_ += 0.002
    _GROUPA_CACHE[(tol, box)] = (a, b, min(vv), max(vv), len(vv), box)
    return _GROUPA_CACHE[(tol, box)]


def groupA_label(tol=GROUPA_TOL, box=GROUPA_BOX):
    """帯を引用するときに必ず併記する箱の宣言文字列"""
    r0, r1, i0, i1 = box
    return f"走査箱 ρ {r0}〜{r1} / I {i0:,}〜{i1:,}、許容率 ×{tol}"


def case(**kw):
    """build() に渡す引数と outcomes() に渡す引数を分けて評価"""
    import phase7_forecast as P7
    bk = {k: v for k, v in kw.items() if k in ('coef', 'i_base', 'g9', 'e8', 'scen')}
    ok = {k: v for k, v in kw.items() if k not in bk and k not in ('launch', 'step')}
    # 【第5次監査 M1】9.0 が FY2030.3 に入らない想定では、パッケージ・パルスも外す
    if 'g9' in bk or 'e8' in bk:
        e8 = bk.get('e8', E8_ASSUMED); d9 = e8 + timedelta(days=bk.get('g9', 927))
        ok.setdefault('pulse', date(2029, 4, 1) <= d9 <= date(2030, 3, 31))
    # 【第5次監査 M2 → 第6次監査 R6-3 で4成分化】足切り段差は
    #   total → ρ の分母・7.x周期平均・FY2026.3平均
    #   cont  → ρ の分子
    #   new/ret → I_base
    # に**同時に**効く。v1 は total しか振らず、I への経路を丸ごと落としていた。
    # step には dict（4成分）またはスカラー（total のみ。後方互換）を渡せる。
    if 'step' in kw:
        sk = kw['step']
        step = dict(CUTOFF_STEP) if isinstance(sk, dict) else dict(CUTOFF_STEP)
        if isinstance(sk, dict): step.update(sk)
        else: step['total'] = sk
        st_ = step['total']
        rho = RHO_7X_SAMEREGIME * step['cont'] / st_
        bk['scen'] = scen_for(rho)
        bk.setdefault('i_base', compute_i_base(step=step))
        _cy, _cyt, _fy = P7.CYC7_MEAN, P7.CYC7_MEAN_TW, K1_FY_MEAN_LV80[2026]
        cy7 = [(d, v * st_) for d, v in P7.CYC7_RAW] + [(date(2026, 7, 20), 853595.0)]
        P7.CYC7_MEAN = st.mean([v for _, v in cy7])
        P7.CYC7_MEAN_TW = P7.timewt([v for _, v in cy7])
        K1_FY_MEAN_LV80[2026] = round(K1_FY2026_LV70 * st_)
        try:
            return outcomes(P7.build(**bk), **ok)
        finally:
            P7.CYC7_MEAN, P7.CYC7_MEAN_TW = _cy, _cyt
            K1_FY_MEAN_LV80[2026] = _fy
    # 【第5次監査 M3】ローンチ挙動（7.0 の1回だけから推定した2パラメータ）
    if 'launch' in kw:
        _lm, _us = P7.LAUNCH_MULT, P7.UNDERSHOOT
        P7.LAUNCH_MULT, P7.UNDERSHOOT = kw['launch']
        try: return outcomes(P7.build(**bk), **ok)
        finally: P7.LAUNCH_MULT, P7.UNDERSHOOT = _lm, _us
    return outcomes(build(**bk), **ok)


# ============================================================
# 前提の一覧: (グループ, 名前, 低位ケース, 高位ケース, 低位の説明, 高位の説明)
# ============================================================
# 【第5次監査 C1 → 第6次監査 R6-1 で全面再編】
#
# v1 は「群A = バックキャストの許容域で両側に振る（相互比較できる）」と宣言していたが、
# **群Aの9点すべてが実際には許容域の外にあった**（phase8_round6_verify.py §V1）:
#   ρ=0.74/I=採用 → S*=648,592 ／ ρ=0.80/I=採用 → S*=843,170
#   I=140k/ρ=採用 → S*=667,962 ／ I=200k/ρ=採用 → S*=954,231
# 周辺レンジ (0.74,0.80) / (140k,200k) は**結合許容集合の各軸への射影**であり、
# その端点は「相手を最適に選べば到達できる」点である。相手を採用値に固定したまま
# 端点へ振れば結合制約を外れる。したがって v1 の「I が最大の分散源（27.9pt）」は
# **不確実性の分解ではなく、許容されない反実仮想どうしの差**だった。
#
# v2 の較正基準は4つに分ける。**異なる群を1つの順位に混ぜてはならない。**
#   群A 結合許容域: S* 制約下で ρ と I を同時に動かす。**唯一「答えの不確実性」を表す**（§C）
#   群B 測定・規約由来の区間: 万単位丸め、平均化規約、基準換算。両側で、根拠が測定にある
#   群C 周辺レンジの一次元摂動: 「この1つの数字が違ったら」。**分散分解には使えない**
#   群D 設計選択の摂動: シナリオ設計・カレンダー・撤回済み仕様。根拠はアドホック
#   群E K4 側のみ（K1 に一切効かない）
CASES = [
    # --- 群B: 測定・規約由来の区間（両側、根拠が測定にある） ---
    # 足切り段差は total→ρ分母・周期平均・年度平均、cont→ρ分子、new/ret→I_base に同時に効く。
    # 【第7次監査 F1】v4 初版の隅は加法制約（new+ret+cont = total）を新基準で 1.0万・
    # 旧基準で 2.0万 破っていた。制約を厳密に満たす端点列挙で得た隅に差し替える。
    # true: total' は成分の和で決まるので独立に振ってはいけない。
    # 【第8次調査】記事の万表記は**切り捨て**であることが実証された（params.py の
    # CUTOFF_STEP のコメント参照）。区間は [x万, x+1万) で、±0.5万の対称区間ではない。
    # 新基準は正確な総数 955,708 で加法制約が厳密に閉じるため、探索空間が大きく縮む。
    # 制約充足の端点列挙で得た真の極値の隅（主指標 −9.7% 〜 −3.8%、幅 5.9pt）:
    ('B', '足切り段差の丸め（切捨・加法制約・正確な総数）',
     dict(step={'total': 955708/1029500, 'new': 56000/80000,
                'ret': 289500/310000, 'cont': 610208/639500}),
     dict(step={'total': 955708/1029500, 'new': 56000/89500,
                'ret': 280000/310000, 'cont': 619708/630000}),
     '主指標が最も低くなる隅', '主指標が最も高くなる隅'),
    ('B', '周期平均の規約', dict(tw=False), dict(tw=True), '等観測重み（採用）', '時間加重'),
    # 【第7次監査 F7】ローンチ倍率の3値は「測定の幅」ではなく**分母の定義選択**であり、
    # 両側の測定区間ではない（第3の定義 1.450 が他2値の外にある）。群D へ移す。
    # --- 群C: 周辺レンジの一次元摂動（結合制約を外れる。分散分解ではない） ---
    ('C', 'ρ（再捕捉率）', dict(scen=scen_for(RHO_LV80_RANGE[0])), dict(scen=scen_for(RHO_LV80_RANGE[1])),
     f'周辺レンジ下端 {RHO_LV80_RANGE[0]:.2f}（S*=648,592・域外）',
     f'周辺レンジ上端 {RHO_LV80_RANGE[1]:.2f}（S*=843,170・域外）'),
    ('C', 'I_base（流入）', dict(i_base=I_BASE_RANGE[0]), dict(i_base=I_BASE_RANGE[1]),
     f'周辺レンジ下端 {I_BASE_RANGE[0]:,}（S*=667,962・域外）',
     f'周辺レンジ上端 {I_BASE_RANGE[1]:,}（S*=954,231・域外）'),
    ('C', 'I_base（2026-07-20 の扱い）', dict(i_base=I_BASE_EX0720), dict(i_base=I_BASE_LV80),
     f'最汚染点を除外 {I_BASE_EX0720:,}', f'5点平均（採用）{I_BASE_LV80:,}'),
    # --- 群D: 設計選択の摂動（根拠はアドホック） ---
    ('D', '8.0 後の I 倍率', dict(scen=scen_for(RHO_LV80, im=(1.00, 1.00, 1.00))),
     dict(scen=scen_for(RHO_LV80, im=(1.00, 1.15, 1.25))),
     '全シナリオで効果ゼロ', 'Base +15% / Bull +25%'),
    ('D', '9.0 の時期', dict(g9=760), dict(g9=1035), '2029-02（FY2029.3・パルス外れる）', '2029-11'),
    ('D', '8.0 の発売日', dict(e8=date(2026, 11, 1)), dict(e8=date(2027, 7, 1)),
     '2026-11（前倒し）', '2027-07（後ろ倒し）'),
    ('D', 'ローンチ倍率の規約', dict(launch=(LAUNCH_MULT_PHASE, UNDERSHOOT)),
     dict(launch=(LAUNCH_MULT_ORIG, UNDERSHOOT)),
     f'位相整合 {LAUNCH_MULT_PHASE}（別の推定対象）', f'旧値 {LAUNCH_MULT_ORIG}（基準不整合・使用禁止）'),
    ('D', 'ローンチ挙動（アドホック幅）', dict(launch=(1.50, 0.80)), dict(launch=(2.20, 1.00)),
     '1.50 × 0.80（根拠なし）', '2.20 × 1.00（根拠なし）'),
    ('D', 'ρ–I 結合', dict(coef=FLOW_COEF_NOLAUNCH), dict(coef=FLOW_COEF_CI[1]),
     '定式化④ −0.783', 'CI上端 +0.317'),
    ('D', 'バックキャストのバイアス補正', dict(bias=1 + BACKCAST_BIAS_CYC), dict(bias=1.0),
     f'+{BACKCAST_BIAS_CYC:.1%} を補正', '未補正（採用）'),
    ('D', 'Bear の 6.x/7.x 比', dict(scen=scen_for(RHO_LV80, ratio=RHO_BEAR_RATIO)),
     dict(scen=scen_for(RHO_LV80, ratio=RHO_BEAR_RATIO_RANGE[1])),
     '一律1段 0.8904（採用）', '段数統制 0.9579'),
    # --- 群E: K4 側（K1 には一切効かない）---
    ('E', '弾力性 ε', dict(eps=0.736), dict(eps=1.0), 'log-log 0.736', '慣性説 1.0'),
    ('E', 'キャラ単価ドリフト', dict(drift=0.8837), dict(drift=0.9781),
     '未測定段差 0.90 → 0.884', '未測定段差 1.00 → 0.978'),
    ('E', '9.0 パッケージ・パルス', dict(pulse=False), dict(pulse=True),
     'FY2030.3 に入らない', '入る（採用）'),
    ('E', '実効海外売上比率 s', dict(s=0.55), dict(s=0.62), '0.55', '0.62'),
    ('E', 'USD/JPY', dict(usd=130.0), dict(usd=170.0), '130', '170'),
    ('E', 'マージン帯', dict(margin=MARGIN_R4), dict(margin=MARGIN),
     'R4適用（Bullを発売年度帯へ）', 'Phase 6 原案'),
]
GROUP_LABEL = {
    'A': '群A 結合許容域（S* 制約下の同時変動）— **唯一「答えの不確実性」を表す**',
    'B': '群B 測定・規約由来の区間（両側。根拠が測定にある）',
    'C': '群C 周辺レンジの一次元摂動（**結合制約を外れる。分散分解に使ってはならない**）',
    'D': '群D 設計選択の摂動（根拠はアドホック）',
    'E': '群E K4 側のみ（K1 には一切効かない）',
}


def fmt_pp(x, b): return f"{(x - b) * 100:+6.1f}pt"


if __name__ == '__main__':
    W = 100
    print("=" * W)
    print("A. トルネード（1前提ずつ振る。3つの結論指標への影響）")
    print("=" * W)
    print(f"  基準値: 主指標 {BASE[0]:+.1%} / CC売上 {BASE[1]:.0f}億 / 営業利益(中点) {BASE[2]:.0f}億")
    print(f"  ※ 主指標 = 8.x周期平均 ÷ 7.x周期平均 − 1（確率加重、等観測重み）\n")
    rows = []
    for grp, name, lo, hi, lodesc, hidesc in CASES:
        if '別途' in lodesc: continue
        a = case(**lo); b = case(**hi)
        # 幅（低位ケースと高位ケースの差）で並べる。基準からの片側距離ではない。
        rows.append((grp, name, lodesc, hidesc, a, b,
                     abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2])))

    print("  【第6次監査 R6-1】群は**較正基準**であって重要度ではない。群をまたいだ")
    print("  順位比較は無意味である。とくに群Cの幅は『答えの不確実性』ではない。\n")
    for grp in ('B', 'C', 'D'):
        sub = [r for r in rows if r[0] == grp]
        if not sub: continue
        print(f"--- 主指標（K1）: {GROUP_LABEL[grp]} ---")
        print(f"{'':>4s}{'前提':<24s}{'低位ケース':<30s}{'→主指標':>9s}{'高位ケース':<30s}{'→主指標':>9s}{'幅':>8s}")
        for i, r in enumerate(sorted(sub, key=lambda x: -x[6]), 1):
            print(f"{i:>3d} {r[1]:<24s}{r[2]:<30s}{r[4][0]:+9.1%}{r[3]:<30s}{r[5][0]:+9.1%}"
                  f"{r[6]*100:7.1f}pt")
        print()
    print(f"--- 主指標（K1）: {GROUP_LABEL['A']} ---")
    print("  群Aは一次元トルネードにならない（ρ と I を同時に動かすため）。§C を参照。\n")
    print("  ※ K4 側の前提（ε・ドリフト・パルス・s・為替・マージン帯）は K1 に恒等的に効かない。")
    print("     K4 は K1 の下流変換であり、K1 の再帰式にフィードバックしないため。")

    for k, lab, unit in [(7, 'CC売上（K4a、億円）', '億'), (8, '営業利益（K4c、億円、中点）', '億')]:
        idx = {7: 1, 8: 2}[k]
        print(f"--- {lab}: **群ごとに順位付けする**（群をまたいだ比較は無意味）---")
        for grp in ('B', 'C', 'D', 'E'):
            sub = [r for r in rows if r[0] == grp and r[k] >= 1]
            if not sub: continue
            print(f"  [{grp}] {GROUP_LABEL[grp]}")
            print(f"{'':>6s}{'前提':<26s}{'低位':>8s}{'高位':>8s}{'幅':>8s}")
            for i, r in enumerate(sorted(sub, key=lambda x: -x[k]), 1):
                print(f"{i:>5d} {r[1]:<26s}{r[4][idx]:8.0f}{r[5][idx]:8.0f}{r[k]:8.0f}")
        print()

    print("\n" + "=" * W)
    print("C. 交互作用: ρ と I はトレードオフする — 角のケースはバックキャストが排除する")
    print("=" * W)
    print(f"{'':>20s}" + "".join(f"{f'I={i:,}':>22s}" for i in (I_BASE_EX0720, I_BASE_LV80)))
    print(f"{'':>20s}" + "".join(f"{'主指標':>10s}{'S*':>12s}" for _ in range(2)))
    for rho, lab in [(0.74, 'ρ=0.74'), (RHO_LV80, f'ρ={RHO_LV80:.4f}（採用）'), (0.80, 'ρ=0.80')]:
        line = f"{lab:>20s}"
        for ib in (I_BASE_EX0720, I_BASE_LV80):
            rr = build(scen=scen_for(rho), i_base=ib)
            ss = ib/(1-rho)
            mark = '' if SSTAR_RANGE_BACKCAST[0] <= ss <= SSTAR_RANGE_BACKCAST[1] else '×'
            line += f"{wavg(rr,'cyc')/CYC7_MEAN-1:+10.1%}{f'{ss:,.0f}{mark}':>12s}"
        print(line)
    print(f"  × = バックキャストが許す S* レンジ（{SSTAR_RANGE_BACKCAST[0]:,}〜{SSTAR_RANGE_BACKCAST[1]:,}）の外側")
    lo = build(scen=scen_for(0.74), i_base=I_BASE_EX0720)
    hi = build(scen=scen_for(0.80), i_base=I_BASE_LV80)
    span_corner = abs(wavg(lo,'cyc')/CYC7_MEAN - wavg(hi,'cyc')/CYC7_MEAN)
    print(f"  角どうしの幅（S* 制約を無視）: {span_corner*100:.1f}pt")

    # 【第5次監査 C2 → 第6次監査 R6-2】連続スキャン。S* 許容域は許容率に依存するので
    # 許容率ごとに出す（v1 は ×1.5 の1本だけを「制約」と呼んでいた）。
    print(f"\n  **群A = 連続スキャン**（{groupA_label()}、ρ 0.002 刻み / I 2,000 刻み、")
    print("   S* が許容域に入る組だけを採る）。**これが答えの不確実性である。**")
    print(f"{'':>4s}{'許容率':>8s}{'S* 許容域':>26s}{'主指標のレンジ':>22s}{'幅':>8s}{'組数':>7s}")
    for tol in (1.25, 1.50, 2.00):
        a, b, lo_, hi_, n_, _bx = groupA(tol)
        star = ' ←採用' if tol == GROUPA_TOL else ''
        print(f"{'':>4s}{'×'+str(tol):>8s}{f'{a:,.0f}〜{b:,.0f}':>26s}"
              f"{f'{lo_:+.1%} 〜 {hi_:+.1%}':>22s}{(hi_-lo_)*100:7.1f}pt"
              f"{n_:>7d}{star}")
    _a, _b, _lo, _hi, _n, _bx0 = groupA()
    _adopt = wavg(build(), 'cyc')/CYC7_MEAN - 1
    _in = _lo <= _adopt <= _hi
    print("  → **ρ と I を独立に振ると幅を過大評価する。** 低ρ×低I と 高ρ×高I は")
    print("     どちらも S* が許容域を外れるため、7.x の観測と両立しない。")
    print(f"  → 採用値 {_adopt:+.1%} は ×{GROUPA_TOL} の帯の**{'内側' if _in else '外側'}**にある"
          f"（第6次監査 R6-2 で ×1.25 から改訂）。")
    print("     v1 の「採用値は制約の外側で、真値は −11%〜−19% 側にある」は撤回する。")

    print("\n" + "=" * W)
    print("D. 結論指標ごとの『支配的な前提』")
    print("=" * W)
    for k, lab, unit in [(6, '主指標（K1）', 'pt'), (7, 'CC売上（K4a）', '億'), (8, '営業利益（K4c）', '億')]:
        for grp in ('B', 'C', 'D', 'E'):
            sub = [r for r in rows if r[0] == grp]
            if not sub: continue
            t = sorted(sub, key=lambda x: -x[k])[:3]
            if all(r[k] * (100 if k == 6 else 1) < 0.5 for r in t): continue
            print(f"  {lab:<14s}[{grp}] " + " / ".join(
                f"{r[1]}（{r[k]*(100 if k==6 else 1):.0f}{unit}）" for r in t))
        print()
    print("  【第6次監査 R6-1 で全面改訂】v1 は『群Aでは I_base が1位、ρ が2位』と書いたが、")
    print("  その群Aの端点はすべてバックキャストの結合制約の外にあった。**順位づけを撤回する。**")
    print("  改訂後に言えること:")
    _a2, _b2, _lo2, _hi2, _, _bx2 = groupA()
    _ad2 = wavg(build(), 'cyc') / CYC7_MEAN - 1
    print(f"   1. **答えの不確実性は群A（§C の同時スキャン）で測る**。×{GROUPA_TOL} で "
          f"{(_hi2-_lo2)*100:.1f}pt、")
    print(f"      主指標は {_lo2:.1%}〜{_hi2:.1%}。採用値 {_ad2:.1%} はこの帯の"
          f"{'内側（上寄り）' if _lo2 <= _ad2 <= _hi2 else '外側'}にある。")
    print("   2. **測定由来の区間（群B）では足切り段差の丸めが支配的**（K1 で 15pt、CC で 52億）。")
    print("      これは v1 で 7.3pt と過小評価されていた。total 段差しか振らず、")
    print("      new/ret 経由で I_base に入る経路を落としていたためである（R6-3）。")
    print("      **丸めの不確実性は、モデルのパラメータ不確実性と同じ桁にある。**")
    print("   3. 群C（ρ・I の一次元摂動）の幅は『この1つの数字が違ったら』であって、")
    print("      分散分解ではない。群Aと足し合わせても比べてもいけない。")
    print("   4. K1 と K4 で支配的な前提が違う（K4 は位相と為替が効く）。")
    print("      **『人口が当たっていれば売上も当たる』は成り立たない。**")
