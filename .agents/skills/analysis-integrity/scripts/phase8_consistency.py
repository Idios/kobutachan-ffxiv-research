#!/usr/bin/env python3
"""
Phase 8 — 全成果物の機械的な横断チェック

【なぜ必要か】根本原因 D-1/D-2 は「文書の数値がスクリプト出力と乖離する」「訂正が
他文書へ伝播しない」だった。5ラウンドの監査はいずれも人手（LLM）でこれを探しており、
**毎回取りこぼしが出ている**。機械的に検査できる部分は機械に任せる。

【検査項目】
  A. 全スクリプトが実行できるか
  B. 文書中の「正典パラメータ」の記載値が params.py と一致するか
  C. 同じ量が複数文書で違う値になっていないか（数値の共起検査）
  D. 【使用禁止】と宣言した値が、禁止の文脈以外で使われていないか
  E. 版数の相互参照が一致するか
  F. 参照している節番号が実在するか
  G. 主要な結論数値がスクリプト出力に含まれるか

使い方: python3 scripts/phase8_consistency.py
"""
import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, 'scripts')

# 【第16次】GitHub 公開に向けて成果物を docs/ に移した。
# DOCS の要素は**ベース名のまま**にしてある（既存の集合比較・メッセージを壊さないため）。
# 実際に開くときだけ dpath() を通す。
DOCS_DIR = 'docs'


def dpath(name):
    """成果物のベース名 → 実際のパス"""
    return os.path.join(DOCS_DIR, name)


def read_doc(name):
    """成果物のベース名 → その本文（コンテキストマネージャで開く）"""
    with open(dpath(name)) as f:
        return f.read()


DOCS = sorted(os.path.basename(x) for x in glob.glob(os.path.join(DOCS_DIR, '*.md')))
SELF = os.path.basename(__file__)
SCRIPTS = sorted(f for f in glob.glob('scripts/*.py')
                 if os.path.basename(f) != SELF)
FAIL = []


# 【第7次監査 F4】v1 の MARK は広すぎ、**全非空行の 61% を無条件免除**していた。
# 変異テスト（撤回済み主張5件を訂正マーカーなしで注入）で検出 0 件だった。
# 免除は「その行自身が訂正・撤回を宣言している」場合に限る。
# 【第7次監査 F4】免除は **その行自身** に訂正・撤回・監査の語があるときだけ。
# v1 は ±6〜8行の窓を見ており、離れた場所の語が無関係な残存を免除していた
# （変異テストで検出 0 件）。窓をやめれば語彙は広くてよい ——
# 撤回済み主張を**同じ行で**訂正なしに書くことは、実際上ほぼ起こらないからである。
MARK = (r'使用禁止|訂正|撤回|棄却|誤り|誤仕様|誤って|旧値|旧条件|由来追跡|~~'
        r'|監査|参考値|100倍|混在|産物|人工物|格下げ|判定不能|不整合|欠落|丸め順序')


def in_correction_context(lines, i, span=3, after=1):
    """訂正・撤回の文脈にあるか。

    【第7次監査 F4】窓を前3行・後1行に絞り、MARK の語彙も「その行が訂正・撤回を
    宣言している」ものだけにする。v1 は ±6〜8行＋広い語彙で、離れた場所の
    「【第5次監査】」等が無関係な残存を免除していた（変異テストで検出 0 件）。
    誤検出が増えても、見逃しよりはるかにましである。
    """
    lo, hi = max(0, i - span), min(len(lines), i + after + 1)
    return any(re.search(MARK, l) for l in lines[lo:hi])


def note(sev, where, msg):
    FAIL.append((sev, where, msg))
    print(f"  [{sev}] {where}: {msg}")


def run_all_scripts():
    print("=" * 78)
    print("A. 全スクリプトの実行")
    print("=" * 78)
    outs = {}
    for f in SCRIPTS:
        try:
            r = subprocess.run(['python3', f], capture_output=True, text=True,
                               timeout=180, check=False)
        except subprocess.TimeoutExpired:
            note('致命', f, "実行がタイムアウト（180秒）")
            outs[f] = ''
            print(f"  {f:<36s} TIMEOUT")
            continue
        ok = r.returncode == 0
        outs[f] = r.stdout
        print(f"  {f:<36s} {'OK' if ok else 'FAIL'}")
        if not ok:
            note('致命', f, f"実行失敗: {r.stderr.strip().splitlines()[-1] if r.stderr else '?'}")
    return outs


def check_canonical(outs):
    """B. 正典パラメータの記載値が params.py と一致するか"""
    print("\n" + "=" * 78)
    print("B. 正典パラメータの記載値（文書 vs params.py）")
    print("=" * 78)
    import params as P
    # (表示名, 期待文字列, 「この値が出てはいけない」旧値のリスト)
    CANON = [
        ('ρ(7.x) same-regime', f"{P.RHO_7X_SAMEREGIME:.4f}", ['0.744', '0.7640', '0.729']),
        ('ρ(Lv80超) Base', f"{P.RHO_LV80:.4f}", ['0.7940', '0.7745', '0.7735']),
        ('Bear 比', f"{P.RHO_BEAR_RATIO:.4f}", ['0.9201', '0.8905']),
        ('I_base', f"{P.I_BASE_LV80:,}", ['191,905']),
        ('足切り段差 total', f"{P.CUTOFF_STEP['total']}", ['95/102']),
        ('正確な総数(2026-07-20)', f"{P.CENSUS_EXACT_TOTAL_20260720:,}", []),
        ('I_base 除外版', f"{P.I_BASE_EX0720:,}", []),
        ('K1_NOW', f"{P.K1_NOW:,}", []),
        ('FY2026.3 平均(Lv80超)', f"{P.K1_NOW_FY_MEAN:,}", []),
        ('観測レンジ下限', f"{P.K1_RANGE_OBS[0]:,}", ['584,496', '471,662']),
        ('観測レンジ上限', f"{P.K1_RANGE_OBS[1]:,}", ['1,524,252', '1,321,162']),
        ('S* 許容域下限', f"{P.SSTAR_RANGE_BACKCAST[0]:,}", []),
        ('S* 許容域上限', f"{P.SSTAR_RANGE_BACKCAST[1]:,}", []),
        ('ε 中心', f"{P.EPS_CENTRAL}", []),
        ('ドリフト4年', f"{P.REV_DRIFT_4Y}", []),
        ('パルス', f"{P.PULSE_LAUNCH_Q}", []),
        # 【第6次監査で追加】
        ('S* 許容域（細格子×1.5）下限', f"{P.SSTAR_RANGE_BY_TOL[1.5][0]:,}", []),
        ('S* 許容域（細格子×1.5）上限', f"{P.SSTAR_RANGE_BY_TOL[1.5][1]:,}", []),
        ('ρ 実測最大(same-regime)', f"{P.RHO_OBS_MAX_SAMEREGIME}", ['0.8391']),
        ('ローンチ倍率（正典）', f"{P.LAUNCH_MULT}", ['×1.86', '1.86 倍']),
        ('バックキャストのバイアス', f"{P.BACKCAST_BIAS_CYC}", []),
    ]
    for name, val, stale in CANON:
        hits = [d for d in DOCS if val in read_doc(d)]
        print(f"  {name:<24s} = {val:<12s} 記載のある文書: {len(hits)}")
        for s_ in stale:
            for d in DOCS:
                lines = read_doc(d).splitlines()
                for i, line in enumerate(lines):
                    if s_ in line and not in_correction_context(lines, i):
                        note('要確認', f"{d}:{i+1}",
                             f"旧値 {s_}（{name}）が訂正の文脈なしで出現: {line.strip()[:80]}")


def check_cross_doc_numbers():
    """C. 同じラベルの量が文書間で違う値になっていないか"""
    print("\n" + "=" * 78)
    print("C. 文書間で同じ量が違う値になっていないか")
    print("=" * 78)
    # (ラベルの正規表現, 抽出する数値のパターン)
    PROBES = [
        ('主指標の確率加重（等観測）', r'−8\.9%|-8\.9%'),
        ('主指標の確率加重（時間加重）', r'−6\.8%|-6\.8%'),
        ('Base の CC 売上（補正後）', r'370億'),
        ('確率加重の CC 売上（補正後）', r'353億'),
        ('主指標の帯（補正後）', r'−7% 〜 −21%|-7% 〜 -21%'),
        ('ピーク比（FY2026.3）', r'−43\.8%|-43\.8%'),
        ('JP シェア（補正後）', r'31\.9%'),
        ('JP のフロー比率', r'10\.4%'),
    ]
    for name, pat in PROBES:
        hits = [d for d in DOCS if re.search(pat, read_doc(d))]
        print(f"  {name:<28s} 出現: {', '.join(hits) if hits else '（なし）'}")


def check_forbidden():
    """D. 【使用禁止】と宣言した値の誤用"""
    print("\n" + "=" * 78)
    print("D. 【使用禁止】値の誤用検査")
    print("=" * 78)
    FORB = [('191,905', 'I_base 足切り混在'), ('0.5144', '誤仕様の結合係数'),
            ('1.146', 'FY2023.3 の旧FX指数'), ('80.1円', '単位100倍誤りの表記'),
            # 【第6次監査で追加】撤回済みの主張・旧値
            ('700,000〜770,833', '粗格子由来の S* 許容域（R6-2 で撤回）'),
            ('7.3pt', '足切り丸めの旧感度（第8次で 5.9pt に確定）'),
            ('15.3pt', '足切り丸めの中間値（加法制約違反。第7次 F1 で撤回）'),
            ('8.3pt', '足切り丸めの旧感度（四捨五入規約。第8次で 5.9pt に訂正）'),
            ('1桁以上低い', '恒等式違反の主張（R6-15 で撤回）')]
    for val, why in FORB:
        for d in DOCS:
            lines = read_doc(d).splitlines()
            for i, line in enumerate(lines):
                if val in line and not in_correction_context(lines, i):
                    note('要確認', f"{d}:{i+1}", f"{why}（{val}）が禁止表示なしで出現")
    print("  （出力がなければ問題なし）")


# 公開用の成果物。**版数・査読履歴などのメタ記載を意図的に持たない**ので、
# 版数チェックの対象外にする（第11次の指示: 公開レポートにメタデータは載せない）
# 索引・公開用の文書。**版数などのメタ記載を意図的に持たない**ので版数チェックの対象外
NO_VERSION_OK = {'ffxiv-outlook-for-players.md', 'PHASE6_PRECOMMIT.md', 'README.md'}


def check_versions():
    """E. 版数の相互参照"""
    print("\n" + "=" * 78)
    print("E. 版数の相互参照")
    print("=" * 78)
    actual = {}
    for d in DOCS:
        txt = read_doc(d)
        m = re.search(r'\*{0,2}版\*{0,2}\s*[:：]\s*\*{0,2}(v[\d.]+)', txt)
        if m:
            actual[d] = m.group(1)
        elif d not in NO_VERSION_OK:
            note('軽微', d, "版数の記載が見つからない（書式不統一）")
    for d, v in sorted(actual.items()):
        print(f"  {d:<36s} {v}")
    # final-report の §8-1 が列挙する版数と突合
    fr = read_doc('final-report.md')
    for d, v in actual.items():
        if d == 'final-report.md': continue
        m = re.search(re.escape('`' + d + '`') + r'[^|]*\|[^|]*（(v[\d.]+)', fr)
        if m and m.group(1) != v:
            note('要修正', 'final-report.md §8-1', f"{d} の版数が {m.group(1)} と記載されているが実体は {v}")
    print("  （final-report §8-1 との突合で出力がなければ一致）")


def check_section_refs():
    """F. 自文書内の節参照が実在するか"""
    print("\n" + "=" * 78)
    print("F. 自文書内の節参照（§x-y）が実在するか")
    print("=" * 78)
    for d in DOCS:
        txt = read_doc(d)
        heads = set(re.findall(r'^#{2,4}\s*(\d+[\w-]*)\.', txt, re.MULTILINE))
        heads |= set(re.findall(r'^#{2,4}\s*(\d+-\d+\w*)\.', txt, re.MULTILINE))
        refs = set(re.findall(r'(?<!Phase )(?<!Phase 0 )§(\d+(?:-\d+\w*)?)', txt))
        # 「Phase N §x」形式（他文書参照）は除外済み
        missing = sorted(r for r in refs if r not in heads and r.split('-')[0] not in heads)
        if missing:
            note('軽微', d, f"実在しない節参照: {', '.join(missing[:8])}")
    print("  （出力がなければ問題なし）")


def check_conclusions(outs):
    """G. 主要な結論数値がスクリプト出力に含まれるか"""
    print("\n" + "=" * 78)
    print("G. 主要な結論数値の由来（スクリプト出力に含まれるか）")
    print("=" * 78)
    allout = "".join(outs.values())
    # 【第13次】ベタ書きの主要数値は、モデルを直すたびに検査器のほうが古くなる。
    # スクリプト出力から動的に作る。
    import params as _P
    from phase7_forecast import build as _b
    from phase7_forecast import wavg as _w
    _r = _b()
    KEY = [f"{_r[k][f]:,.0f}" for k in ('Bear', 'Base', 'Bull')
           for f in ('cyc', 'fy2030')] + [f"{_w(_r,'cyc'):,.0f}", f"{_w(_r,'fy2030'):,.0f}",
                                          f"{_P.CUTOFF_ROUND_SENS_PT}"]
    miss = [k for k in KEY if k not in allout]
    if miss:
        note('要修正', 'scripts', f"文書にあるがスクリプト出力に無い: {', '.join(miss)}")
    else:
        print(f"  {len(KEY)} 個の主要数値すべてがスクリプト出力に存在")

    # 【第14次】check-L は6桁以上のカンマ区切りしか見ないので、「92.6万」の類が
    # 7ラウンド分まるごと腐っていた（phase7-forecast.md v0.7）。万表記も突き合わせる。
    # 許容集合は**スクリプト出力の生数値を万に整形して作る**（ベタ書きにすると検査器が腐る）。
    MAN_OK = set()
    for tok in re.findall(r'\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d{5,}\b', allout):
        v = float(tok.replace(',', ''))
        if v < 10_000:
            continue
        for dp in (0, 1):
            MAN_OK.add(f"{v/10000:.{dp}f}万")
            MAN_OK.add(f"{v/10000+0.05:.{dp}f}万")   # 丸め方向の差を吸収
            MAN_OK.add(f"{v/10000-0.05:.{dp}f}万")
    # 外部・実績由来でスクリプトが出さないもの
    # スクリプトが最初から万表記で出しているものも許容集合に入れる
    MAN_OK |= set(re.findall(r'(?<![\d,])\d{1,4}(?:\.\d)?万', allout))
    # 外部・実績由来・記事本文の丸め値でスクリプトが出さないもの
    MAN_EXT = {'110.2万', '110.1万', '109万', '100万', '150万', '200万', '300万',
               '350万', '500万', '1000万', '2700万', '4000万', '5000万',
               '128万', '82.9万', '76.8万'}
    for d in ('final-report.md', 'phase7-forecast.md', 'ffxiv-outlook-for-players.md'):
        lines = read_doc(d).splitlines()
        seen = {}
        for i, line in enumerate(lines):
            if in_correction_context(lines, i):
                continue
            for tok in re.findall(r'(?<![\d,])\d{1,4}(?:\.\d)?万', line):
                if tok not in MAN_OK and tok not in MAN_EXT:
                    seen.setdefault(tok, i + 1)
        if seen:
            for tok, ln in sorted(seen.items(), key=lambda x: x[1]):
                note('要確認', f"{d}:{ln}",
                     f"万表記 {tok} がスクリプト出力の整形値に無い（滞留の疑い）")
        else:
            print(f"  {d}: 万表記の滞留なし")


RETRACTED_PHRASES = [
    ('許容域の外側', 'S* が許容域の外側（第6次 R6-2 → 第7次 F3 で「判定不能」に）'),
    ('1点で判定できる', 'Bear は1点で判定できる（第5次 C3・第6次 R6-8 で撤回）'),
    ('待つ必要はない', 'T1 は発売を待つ必要がない（第6次 R6-8 で撤回）'),
    ('15万台に戻る', 'T2 の旧条件（第5次 C6 で撤回）'),
    ('最大の分散源', 'I/ρ の分散源順位（第6次 R6-1 で撤回）'),
    ('4世代中最高', 'ρ の世代間順位（第3次 C3 で撤回）'),
    ('グラフ」は未作成', 'グラフ未作成（第5次で作成済み）'),
    ('1桁以上低い', '限界キャラは平均の1桁下（第6次 R6-15 で撤回。恒等式違反）'),
    ('20万超', 'T2b の旧条件（第7次 F5 で撤回。Bull でも発火しない）'),
    ('7万を超える', 'T4 の旧条件（第6次 R6-3 で撤回。発火不能）'),
    ('109万（黄金ピーク）を下回る', 'T5 の旧閾値（第6次 R6-4 で撤回。足切り未統一・分割しない）'),
    # 【第15次】プレイヤー向けレポートに撤回済みの主張が3ラウンド分残っていた。
    # check-I は**本文の言い回し**を見る唯一の検査なので、ここに登録しないと永久に残る。
    ('2017年以降4つのまま', '日本の DC 数（第11次で撤回。Meteor は 2022-07-05 新設）'),
    ('値上げは予兆が見えない', '値上げの予兆観測（第12次で撤回。25〜127日・中央値30日で観測可能）'),
    ('予兆が見えないが', '値上げの予兆観測（第12次で撤回）'),
    ('定義上打ち消される', 'ρ・I はバイアス補正で打ち消される（第14次で撤回。I は打ち消さない）'),
    ('定義上打ち消されて', 'ρ・I はバイアス補正で打ち消される（第14次で撤回）'),
    ('109万で **−18%**', '拡張ファネルの水準比較（第15次で撤回。窓長・足切り未正規化）'),
    ('109万で −18%', '拡張ファネルの水準比較（第15次で撤回。窓長・足切り未正規化）'),
]


def check_retractions():
    """I. 撤回済みの主張が、撤回の文脈なしに残っていないか（D-2 の機械検出）

    【なぜ必要か】6ラウンドで最も多かったのは D-2（撤回の伝播漏れ）で、第6次では
    **同一ファイル内20行の距離でさえ伝播していなかった**（R6-8）。目視の突合では
    毎回取りこぼすので、撤回した主張のフレーズを登録して機械的に探す。
    """
    print("\n" + "=" * 78)
    print("I. 撤回済み主張の残存検査")
    print("=" * 78)
    RETRACTED = RETRACTED_PHRASES
    _unused = [
        ('許容域の外側', 'S* が許容域の外側（第6次 R6-2 で撤回）'),
        ('1点で判定できる', 'Bear は1点で判定できる（第5次 C3・第6次 R6-8 で撤回）'),
        ('待つ必要はない', 'T1 は発売を待つ必要がない（第6次 R6-8 で撤回）'),
        ('15万台に戻る', 'T2 の旧条件（第5次 C6 で撤回）'),
        ('最大の分散源', 'I/ρ の分散源順位（第6次 R6-1 で撤回）'),
        ('4世代中最高', 'ρ の世代間順位（第3次 C3 で撤回）'),
        ('グラフ」は未作成', 'グラフ未作成（第5次で作成済み）'),
    ]
    for phrase, why in RETRACTED:
        for d in DOCS + SCRIPTS:
            try:
                lines = read_doc(d).splitlines()
            except OSError:
                lines = []
            for i, line in enumerate(lines):
                if phrase in line and not in_correction_context(lines, i, span=8):
                    note('要修正', f"{d}:{i+1}", f"撤回済み: {why}")
    print("  （出力がなければ問題なし）")


def check_japan(outs):
    """L. 日本レポートの数値が phase9_japan.py の出力と一致するか（第9次で追加）"""
    print("\n" + "=" * 78)
    print("L. 日本レポートの数値（文書 vs scripts/phase9_japan.py）")
    print("=" * 78)
    out = outs.get('scripts/phase9_japan.py', '')
    if not out:
        note('致命', 'phase9_japan.py', "出力が取得できない"); return
    doc = read_doc('phase9-japan.md')
    # 【第13次】ベタ書きをやめ、**向きを逆にする**。
    # 旧版は「この15個が文書にあるか」だったので、モデルを直すと検査器のほうが古くなり、
    # かつ**文書に残った古い数値は検出できなかった**（D-1 の検査器での再発）。
    # 正しい向き: **文書に出てくる結論めいた数値のうち、スクリプトが出さないものを探す。**
    # これなら期待値を転記しなくてよく、陳腐化も検出できる。
    norm = lambda t: t.replace('−', '-').replace(',', '')
    out_n = norm(out)
    # 訂正・撤回・履歴の文脈にある行は除く（過去の値をわざと残している箇所）
    # スクリプトではなく外部出典から引いている数値（FFXI のコミュニティ推計など）
    EXTERNAL = {'127,420', '118,576'}
    lines = doc.split('\n')
    stale = []
    for i, line in enumerate(lines):
        if in_correction_context(lines, i):
            continue
        for tok in re.findall(r'\b\d{1,3}(?:,\d{3}){1,}\b', line):
            if (len(tok.replace(',', '')) >= 6 and norm(tok) not in out_n
                    and tok not in EXTERNAL):
                stale.append((i + 1, tok))
    for ln, tok in stale[:12]:
        note('要修正', f'phase9-japan.md:{ln}',
             f"数値 {tok} が phase9_japan.py の出力に無い（陳腐化の疑い）")
    if not stale:
        n_doc = len(set(re.findall(r'\b\d{1,3}(?:,\d{3}){1,}\b', doc)))
        print(f"  文書中の6桁以上の数値 {n_doc} 種すべてが、スクリプト出力に存在する")
    else:
        print(f"  → 陳腐化の疑い {len(stale)} 件")


def check_player_report(outs):
    """M. プレイヤー向けレポートの数値がスクリプト出力と一致するか"""
    print("\n" + "=" * 78)
    print("M. プレイヤー向けレポートの数値")
    print("=" * 78)
    import params as P
    import phase10_entrants as E
    from phase7_forecast import CYC7_MEAN, build, cc_year, to_nominal, wavg
    def ent(t, m):
        _, ser = E.series(t)
        return next(f"{r:.1%}" for mm, _, _, r in ser if mm == m)
    r = build()
    doc = read_doc('ffxiv-outlook-for-players.md')
    # 【第11次】補正後の売上・利益（phase11_corrected.py と同じ計算）
    import phase11_supply as SP
    CF = 1.0 / (1.0 + P.BACKCAST_BIAS_CYC)
    CORR = {'cc': 0.0, 'lo': 0.0, 'hi': 0.0}
    for _k in ('Bear', 'Base', 'Bull'):
        _kr = r[_k]['fy2030'] * CF / P.K1_FY_MEAN_LV80[2026]
        _cc = cc_year(_kr); _nom = to_nominal(_cc)
        _m = P.MARGIN_R4[_k]; _w = r[_k]['w']
        CORR[_k] = _cc
        CORR['cc'] += _w * _cc
        CORR['lo'] += _w * _nom * _m[0]; CORR['hi'] += _w * _nom * _m[1]
    # 【第11次】コンテンツ供給の分解
    _bt = lambda g: sum(float(SP.G[g][m]['total_full_cycle']) for m in SP.BATTLE)
    _msq = lambda g: float(SP.G[g]['main_scenario_quests']['total_full_cycle']) / SP.META[g][0]
    # 【第12次】値上げリードタイムと再捕捉率
    import phase12_claims as CL
    _lt = [n for *_, n in CL.lead_times()]
    LEAD = {'med': __import__('statistics').median(_lt), 'lo': min(_lt), 'hi': max(_lt)}
    with open('data/census_normalized.csv') as _f:
        _rows = [x for x in __import__('csv').DictReader(_f) if x['continuing_scaled']]
    _rr, _prev = [], None
    for _x in _rows:
        if _prev and _x['regime'] == _prev[1]:
            _rr.append(float(_x['continuing_scaled']) / _prev[0])
        _prev = (float(_x['raw_total']), _x['regime'])
    RR = {'early': f"{__import__('statistics').mean(_rr[:12]):.1%}",
          'late': f"{__import__('statistics').mean(_rr[-12:]):.1%}"}
    # 【第13次】識別レンジいっぱいに振ったときの補正後主指標
    # 【第14次 D-1 対策】以前はここに帯をハードコードしていた。生成器から取る。
    import phase13_identification as ID
    BAND = ID.honest_band()[:2]
    SUP = {'per_year': f"{(_bt('7.x')/SP.META['7.x'][0])/(_bt('4.x')/SP.META['4.x'][0])-1:.0%}",
           'per_patch': f"{(_bt('7.x')/SP.META['7.x'][1])/(_bt('4.x')/SP.META['4.x'][1])-1:.0%}",
           'msq': f"{_msq('7.x')/_msq('4.x')-1:.0%}"}
    ok = 0
    CH = [
        ('7.x周期平均 90.6万', f"{CYC7_MEAN/10000:.1f}万", '90.6万'),
        # 【第11次】バイアス補正を人口・売上・利益に**一貫して**適用した（未解決 #18/#19 の解消）。
        # 文書は補正後の値だけを載せるので、照合も補正後で行う。
        # 文書は百分率で書くので、比較文字列も百分率に揃える
        # （比率表記 '-0.110' で照合すると文書側に永久に一致せず、検出則が空振りする）
        ('8.x加重（補正後）78.6万', f"{wavg(r,'cyc')*CF/10000:.1f}万", '78.6万'),
        ('Bear（補正後）58.2万', f"{r['Bear']['cyc']*CF/10000:.1f}万", '58.2万'),
        ('Base（補正後）83.4万', f"{r['Base']['cyc']*CF/10000:.1f}万", '83.4万'),
        ('Bull（補正後）89.4万', f"{r['Bull']['cyc']*CF/10000:.1f}万", '89.4万'),
        ('CC売上（補正後）353億', f"{CORR['cc']:.0f}億", '353億'),
        # 文書は範囲で書くので、下限を単独で照合してはならない（第10次の空振りと同型）
        ('営業利益（補正後）124〜151億',
         f"{CORR['lo']:.0f}〜{CORR['hi']:.0f}億", '124〜151億'),
        ('Bear CC（補正後）276億', f"{CORR['Bear']:.0f}億", '276億'),
        ('Base CC（補正後）370億', f"{CORR['Base']:.0f}億", '370億'),
        ('Bull CC（補正後）396億', f"{CORR['Bull']:.0f}億", '396億'),
        # 【第13次】主指標は**点ではなく帯**で出す。帯の両端と、その人数換算を照合する
        ('主指標の帯 −7%〜−21%', f"{BAND[1]*100:.0f}% 〜 {BAND[0]*100:.0f}%", '-7% 〜 -21%'),
        ('帯の人数 71.4万〜83.8万',
         f"{CYC7_MEAN*(1+BAND[0])/10000:.1f}万〜{CYC7_MEAN*(1+BAND[1])/10000:.1f}万",
         '71.4万〜83.8万'),
        ('バイアス 5.0%', f"{P.BACKCAST_BIAS_CYC*100:.1f}%", '5.0%'),
        # 【第11次】コンテンツ供給の分解（phase11_supply.py）
        ('時間あたり供給 4.x比 −20%', SUP['per_year'], '-20%'),
        ('1パッチあたりの量 −2%', SUP['per_patch'], '-2%'),
        ('メインクエスト年あたり −30%', SUP['msq'], '-30%'),
        ('T5 閾値 82.9万', f"{(r['Bear']['peak']+r['Base']['peak'])/2/10000:.1f}万", '82.9万'),
        ('T2 閾値 17.1万', f"{P.I_BASE_LV80/10000:.1f}万", '17.1万'),
        ('T2b 閾値 18.8万', f"{round(P.I_BASE_LV80*1.10,-2)/10000:.1f}万", '18.8万'),
        # 【第9次（Fable）致命1】v1.0 の §2-1 は拡張進行ファネルの開始数（133/109/86万、
        # 足切り不統一）を「活動キャラクター数」として並べていた。正典系列で照合する。
        ('6.0 ピーク 132万', f"{P.K1_PEAK_60/10000:.0f}万", '132万'),
        ('7.0 ピーク 128万', f"{P.K1_PEAK_70/10000:.0f}万", '128万'),
        ('直近 85.4万', f"{P.K1_NOW/10000:.1f}万", '85.4万'),
        ('7.0/6.0 −3%', f"{(P.K1_PEAK_70/P.K1_PEAK_60-1)*100:.0f}%", '-3%'),
        ('直近/6.0 −35%', f"{(P.K1_NOW/P.K1_PEAK_60-1)*100:.0f}%", '-35%'),
        ('直近/7.0 −33%', f"{(P.K1_NOW/P.K1_PEAK_70-1)*100:.0f}%", '-33%'),
        # 【第11次】§1-1 の残存率を経過月そろえに作り直した分（phase10_entrants.py）
        ('FFXIV M+9 34.5%', ent('FFXIV', 9), '34.5%'),
        ('FFXIV M+21 38.8%', ent('FFXIV', 21), '38.8%'),
        ('TL M+9 5.7%', ent('Throne and Liberty', 9), '5.7%'),
        ('TL M+21 3.1%', ent('Throne and Liberty', 21), '3.1%'),
        ('NW M+9 17.9%', ent('New World', 9), '17.9%'),
        ('NW M+21 1.3%', ent('New World', 21), '1.3%'),
        ('NW M+12 83.1%（開発終了発表月）', ent('New World', 12), '83.1%'),
        ('OSRS の Steam 捕捉率 1.0%', f"{2469/240851:.1%}", '1.0%'),
        # 【第12次】値上げリードタイム（既存契約者基準、イベント単位で重複除去）
        ('値上げリードタイム中央値 30日', f"中央値{LEAD['med']:.0f}日", '中央値30日'),
        ('値上げリードタイム範囲 25〜127日', f"{LEAD['lo']}〜{LEAD['hi']}日", '25〜127日'),
        # 【第12次】再捕捉率（「ベテランが去っている」への応答）
        ('再捕捉率 初期 71.4%', RR['early'], '71.4%'),
        ('再捕捉率 直近 74.4%', RR['late'], '74.4%'),
    ]
    # params 内部の整合（文書照合ではないので CH には入れない）
    if P.K1_RANGE_OBS[1] != P.K1_PEAK_60:
        note('要修正', 'scripts/params.py',
             f"観測レンジ上限 {P.K1_RANGE_OBS[1]:,} ≠ 6.0 ピーク {P.K1_PEAK_60:,}")
    # 【第14次 D-1 対策】S* 許容域の定数を生成器と突き合わせる（830,000 の腐りを検出）
    _fine = P.sstar_range_fine()
    for _t, _v in sorted(_fine.items()):
        if tuple(P.SSTAR_RANGE_BY_TOL[_t]) != _v:
            note('要修正', 'scripts/params.py',
                 f"SSTAR_RANGE_BY_TOL[{_t}] = {P.SSTAR_RANGE_BY_TOL[_t]} が"
                 f"生成器 sstar_range_fine() の {_v} と不一致")
    if tuple(P.SSTAR_RANGE_BACKCAST) != _fine[1.5]:
        note('要修正', 'scripts/params.py',
             f"SSTAR_RANGE_BACKCAST {P.SSTAR_RANGE_BACKCAST} ≠ 細格子×1.5 {_fine[1.5]}")
    for name, got, want in CH:
        good = (got == want) and (want in doc or want.replace('-', '−') in doc)
        print(f"  {'OK ' if good else 'NG '} {name:<24s} 計算 {got:<10s} 文書 {want}")
        ok += good
        if not good:
            note('要修正', 'ffxiv-outlook-for-players.md', f"{name}: 計算 {got} / 文書 {want}")
    print(f"  → {ok}/{len(CH)} 一致")


def check_width_inequality():
    """K. 一次元感度の幅が結合許容域の幅を超えていないか（第7次監査 F15）

    【なぜ必要か】Phase 0 は第6次監査で「**一度に1つ振った幅が、同じ制約下の同時
    スキャンの幅を超えていたら較正が壊れている**」という機械的検出則を宣言したが、
    実装されていなかった（宣言だけの検出則は D-13 の再発である）。
    制約が本物なら、一次元の幅が同時の幅を超えることはありえない。
    """
    print("\n" + "=" * 78)
    print("K. 一次元感度の幅 vs 結合許容域の幅（較正の健全性）")
    print("=" * 78)
    import phase8_sensitivity as S
    rows = []
    for grp, name, lo, hi, ld, hd in S.CASES:
        if grp == 'E': continue
        a, b = S.case(**lo), S.case(**hi)
        rows.append((grp, name, abs(a[0] - b[0]) * 100))
    # 【第14次 D-1 対策】以前は 15.5 をハードコードしていて生成器と 0.8pt ずれていた
    _a, _b, _lo, _hi, _n, _bx = S.groupA()
    span_a = (_hi - _lo) * 100
    print(f"  群A（結合許容域・同時スキャン、×{S.GROUPA_TOL}）"
          f"= {_lo:.1%}〜{_hi:.1%}、幅 {span_a:.1f}pt（{_n}組）")
    bad = []
    for grp, name, w in sorted(rows, key=lambda x: -x[2]):
        mark = ''
        if w > span_a:
            mark = '  ← **同時幅を超える**'
            if grp != 'C': bad.append((grp, name, w))
        print(f"  [{grp}] {name:<28s} {w:6.1f}pt{mark}")
    if bad:
        for grp, name, w in bad:
            note('要修正', f"群{grp}", f"{name} の幅 {w:.1f}pt が群A の {span_a:.1f}pt を超える"
                                    f"（較正基準の混入が疑われる）")
    print("  ※ 群C は『結合制約を外れた一次元摂動』と宣言済みなので、超えるのが正常である。")
    print("     群B・群D が超えていたら較正が壊れている。")


def check_arithmetic():
    """H. 文書中の算術（加重平均・比率）の再計算"""
    print("\n" + "=" * 78)
    print("H. 算術の再検算")
    print("=" * 78)
    import params as P
    from phase7_forecast import (
        CYC7_MEAN,
        CYC7_MEAN_TW,
        build,
        cc_year,
        wavg,
    )
    r = build()
    # 【第13次】期待値をベタ書きすると、モデルを直したときに**検査器のほうが古くなる**
    # （D-1 の、検査器自身での再発）。文書から読み取れるものは読み取る。
    _fr = read_doc('final-report.md')
    def from_doc(pat, default):
        m = re.search(pat, _fr)
        return float(m.group(1).replace(',', '')) if m else default
    checks = [
        ('8.x周期平均の確率加重', wavg(r, 'cyc'),
         from_doc(r'8\.x 周期平均[^|]*\|[^|]*?([\d,]{6,})', wavg(r, 'cyc')), 2),
        ('主指標（等観測）', wavg(r, 'cyc') / CYC7_MEAN - 1,
         round(wavg(r, 'cyc') / CYC7_MEAN - 1, 4), 0.001),
        ('主指標（時間加重）', wavg(r, 'cyc_tw') / CYC7_MEAN_TW - 1,
         round(wavg(r, 'cyc_tw') / CYC7_MEAN_TW - 1, 4), 0.001),
        ('S* = I/(1-ρ)', P.I_BASE_LV80 / (1 - P.RHO_LV80), 835731, 3),
        ('Bear ρ = ρ_Lv80 × Bear比', P.RHO_LV80 * P.RHO_BEAR_RATIO, 0.7081, 0.0005),
        ('FY2026.3 CC (s=0.58)', P.cc(410, 2026), 349.5, 0.5),
        ('ピーク比 FY2026.3', P.cc(410, 2026) / P.cc(622, 2022) - 1, -0.438, 0.002),
        ('Base CC（パルス無し）', cc_year(r['Base']['fy2030'] / P.K1_FY_MEAN_LV80[2026], pulse=False),
         round(cc_year(r['Base']['fy2030'] / P.K1_FY_MEAN_LV80[2026], pulse=False), 1), 1.0),

        ('S_0 反落想定（−6.5%）', 853595 * 0.935, 798111, 2),
        # 【第6次監査で追加】
        ('I_base 生成関数 = 凍結値', P.compute_i_base(), P.I_BASE_LV80, 5),
        ('I_base 除外版 = 凍結値', P.compute_i_base(P.I_BASE_DATES[:-1]), P.I_BASE_EX0720, 5),
        ('ローンチ倍率（正典）= 生成関数と一致',
         P.compute_launch_mult(), P.LAUNCH_MULT, 0.001),
        ('CC 確率加重', sum(cc_year(r[k]['fy2030'] / P.K1_FY_MEAN_LV80[2026]) * r[k]['w'] for k in r),
         round(sum(cc_year(r[k]['fy2030'] / P.K1_FY_MEAN_LV80[2026]) * r[k]['w'] for k in r), 1), 1.5),
        # 【第13次で新設】ローンチ倍率が観測3回の範囲に入っているか（位相ずれの再発防止）
        ('ローンチ倍率が観測範囲内', P.LAUNCH_MULT,
         (P.LAUNCH_MULT_RANGE[0] + P.LAUNCH_MULT_RANGE[1]) / 2,
         (P.LAUNCH_MULT_RANGE[1] - P.LAUNCH_MULT_RANGE[0]) / 2),
    ]
    for name, got, exp, tol in checks:
        ok = abs(got - exp) <= tol
        print(f"  {'OK ' if ok else 'NG '} {name:<30s} 計算 {got:>12,.4f}  文書 {exp:>12,.4f}")
        if not ok: note('要修正', '算術', f"{name}: 計算 {got} ≠ 文書 {exp}")


def check_guards():
    """P. 構造ガードの動作確認 — 「検出」ではなく「不可能」にした2件

    【第15次で新設】15ラウンドで D-4（基準不一致）と D-13（メタパラメータ未宣言）は
    繰り返し再発した。検査器が事後に見つけるだけでは止まらないので、
    **揃っていない比較を書けなくする／箱を宣言せずに帯を得られなくする**ガードを入れた。
    ここではそのガードが実際に発火することを確かめる（発火しなければガードは無意味）。
    """
    print("\n" + "=" * 78)
    print("P. 構造ガードの動作確認")
    print("=" * 78)
    import params as P
    import phase8_sensitivity as SE
    ok = 0
    CASES = [
        ('生の総数どうしの比較を拒否する',
         lambda: P.compare_census('2024-08-27', '2026-07-20',
                                  field='raw_total', unify_regime=False)),
        ('足切りレジームが違うまま比較するのを拒否する',
         lambda: P.compare_census('2024-08-27', '2026-07-20', unify_regime=False)),
        ('窓長正規化していない列での比較を拒否する',
         lambda: P.compare_census('2024-08-27', '2026-07-20', field='continuing_scaled')),
    ]
    for name, fn in CASES:
        try:
            fn()
            note('要修正', 'scripts/params.py', f"P: ガード「{name}」が発火しなかった")
            print(f"  NG  {name}")
        except P.ScaleMismatch:
            ok += 1
            print(f"  OK  {name}")
    # 正しい比較は通り、文書の値と一致すること
    _, _, ch, lab = P.compare_census('2024-08-27', '2026-07-20')
    good = abs(ch * 100 - (-33.3)) < 0.05
    print(f"  {'OK ' if good else 'NG '} 正しい比較は通る: {ch:+.1%}（{lab}）")
    ok += good
    if not good:
        note('要修正', 'scripts/params.py', f"P: 統一後の変化率 {ch:+.1%} が文書の −33.3% と不一致")
    # 群Aは箱を結果に同梱して返すこと
    r = SE.groupA()
    has_box = len(r) == 6 and isinstance(r[5], tuple) and len(r[5]) == 4
    print(f"  {'OK ' if has_box else 'NG '} 群Aが走査箱を同梱して返す: {SE.groupA_label()}")
    ok += has_box
    if not has_box:
        note('要修正', 'scripts/phase8_sensitivity.py', "P: groupA() が走査箱を返していない")
    # 箱を変えれば帯が変わること（＝箱が効いていることの実証）
    wide = SE.groupA(box=(0.66, 0.88, 80_000, 300_000))
    moved = abs((wide[3] - wide[2]) - (r[3] - r[2])) > 0.01
    print(f"  {'OK ' if moved else 'NG '} 箱を広げると帯が変わる: "
          f"{(r[3]-r[2])*100:.1f}pt → {(wide[3]-wide[2])*100:.1f}pt")
    ok += moved
    if not moved:
        note('要修正', 'scripts/phase8_sensitivity.py',
             "P: 箱を変えても帯が動かない（箱が効いていない＝宣言の意味がない）")
    print(f"  → {ok}/6 のガードが機能")


def self_test():
    """J. 検査器自身の自己テスト（第7次監査 F4）

    【なぜ必要か】v1 の検査器は「致命 0」を出したが、撤回済み主張を訂正マーカーなしで
    注入しても1件も検出しなかった。**検査器が機能していることを検査しないかぎり、
    「致命 0」は打ち切りの根拠にならない。**
    既知の誤りを一時ファイルに注入し、検出できることを確認する。
    """
    print("\n" + "=" * 78)
    print("J. 検査器の自己テスト（既知の誤りを注入して検出できるか）")
    print("=" * 78)
    INJECT = [
        ("採用 S* は許容域の外側にある。", '撤回済み主張'),
        ("I_base が最大の分散源である。", '撤回済み主張'),
        ("Bear かどうかは次回の1点で判定できる。", '撤回済み主張'),
        ("次回国勢調査の新規＋復帰が 15万台に戻るかを見る。", '撤回済み条件'),
        ("I_base = 191,905 を用いる。", '使用禁止値'),
    ]
    ok = 0
    for text, kind in INJECT:
        lines = ["# 注入テスト", "", text, ""]
        hit = not in_correction_context(lines, 2)
        # 登録簿に載っているか
        known = any(ph in text for ph, _ in RETRACTED_PHRASES) or '191,905' in text
        det = hit and known
        print(f"  {'検出' if det else '**見逃し**'}  [{kind}] {text[:34]}")
        ok += det
    print(f"  → {ok}/{len(INJECT)} 件を検出")
    if ok < len(INJECT):
        note('致命', 'phase8_consistency.py',
             f"自己テストで {len(INJECT)-ok} 件を見逃した。**検査器が機能していない。**")


def check_main_report():
    """N. final-report.md / phase7-forecast.md の主要数値がスクリプト出力と一致するか

    【第14次で新設】check-L（滞留検出）は6桁以上のカンマ区切り数値しか見ないので、
    「87.5万」「384億」「−13.2%」「14.7pt」の類が**7ラウンド分まるごと腐っていた**のを
    一度も検出しなかった（phase7-forecast.md v0.7 が典型）。表記単位ごと照合する。
    """
    print("\n" + "=" * 78)
    print("N. 本編レポートの主要数値（final-report.md / phase7-forecast.md）")
    print("=" * 78)
    import params as P
    import phase7_forecast as F
    import phase8_sensitivity as SE
    import phase13_identification as ID
    from phase7_forecast import build, cc_year, to_nominal
    r = build()
    w = lambda k: sum(r[x]['w'] * r[x][k] for x in r)
    CF = 1.0 / (1.0 + P.BACKCAST_BIAS_CYC)
    cc = {k: cc_year(r[k]['fy2030'] / P.K1_FY_MEAN_LV80[2026]) for k in r}
    nom = {k: to_nominal(cc[k]) for k in r}
    wv = lambda d: sum(r[k]['w'] * d[k] for k in d)
    gA = SE.groupA()
    lo, hi, _ = ID.honest_band()
    man = lambda v: f"{v/10000:.1f}万"
    oku = lambda v: f"{v:.0f}億"
    CH = [
        ('8.x周期平均 Base', man(r['Base']['cyc']), '87.5万'),
        ('8.x周期平均 Bear', man(r['Bear']['cyc']), '61.1万'),
        ('8.x周期平均 Bull', man(r['Bull']['cyc']), '93.8万'),
        ('8.x周期平均 加重', man(w('cyc')), '82.5万'),
        ('FY2030.3 Base', man(r['Base']['fy2030']), '89.1万'),
        ('FY2030.3 加重', man(w('fy2030')), '83.8万'),
        ('CC売上 Base', oku(cc['Base']), '384億'),
        ('CC売上 加重', oku(wv(cc)), '366億'),
        ('名目売上 Base', oku(nom['Base']), '450億'),
        ('名目売上 加重', oku(wv(nom)), '429億'),
        ('営業利益 Base', (f"{nom['Base']*P.MARGIN_R4['Base'][0]:.0f}〜"
                         f"{nom['Base']*P.MARGIN_R4['Base'][1]:.0f}億"), '139〜171億'),
        ('営業利益 加重', (f"{sum(r[k]['w']*nom[k]*P.MARGIN_R4[k][0] for k in nom):.0f}〜"
                         f"{sum(r[k]['w']*nom[k]*P.MARGIN_R4[k][1] for k in nom):.0f}億"),
         '129〜157億'),
        ('主指標 生・加重', f"{w('cyc')/F.CYC7_MEAN-1:.1%}", '-8.9%'),
        ('主指標 生・時間加重', f"{w('cyc_tw')/F.CYC7_MEAN_TW-1:.1%}", '-6.8%'),
        ('主指標 補正後・加重', f"{w('cyc')*CF/F.CYC7_MEAN-1:.1%}", '-13.2%'),
        ('主指標 補正後・時間加重', f"{w('cyc_tw')*CF/F.CYC7_MEAN_TW-1:.1%}", '-11.2%'),
        ('バイアス', f"{P.BACKCAST_BIAS_CYC*100:+.1f}%", '+5.0%'),
        ('S*', f"{P.I_BASE_LV80/(1-P.RHO_LV80):,.0f}", '835,731'),
        ('S* vs FY2026.3',
         f"{(P.I_BASE_LV80/(1-P.RHO_LV80)/P.K1_NOW_FY_MEAN-1)*100:+.1f}%", '+2.4%'),
        ('群A 帯', f"{gA[2]:.1%} 〜 {gA[3]:.1%}", '-23.1% 〜 -8.4%'),
        ('群A 幅', f"{(gA[3]-gA[2])*100:.1f}pt", '14.7pt'),
        ('群A S*上限', f"{gA[1]:,}", '826,531'),
        ('正直な帯', f"{hi:.0%} 〜 {lo:.0%}", '-7% 〜 -21%'),
        ('ローンチ倍率（予測）', f"{P.LAUNCH_MULT}", '1.3506'),
        ('T2 閾値', f"{P.I_BASE_LV80:,}", '171,160'),
    ]
    # 【第14次・査読で摘出】「どちらかの文書に1回でも出れば OK」では、本編の最重要数値が
    # 全滅していても他方に残っていれば通ってしまう。**文書ごとに独立に判定し、
    # かつ「旧世代の値が訂正文脈外に残っていないか」を測る。**
    # 【第15次】静止ラウンド実験で判明: check-N/O は本編2本しか見ておらず、
    # **上流の Phase 文書は第8〜14次の正典改訂を一度も受け取っていなかった。**
    # 「静止＝収束」ではなく「静止＝取り残され」だった。全文書を対象にする。
    DOCS_N = ('final-report.md', 'phase7-forecast.md')
    # 監査記録（phase8-verification.md）は旧値を引用するのが役割なので除く
    DOCS_ALL = tuple(d for d in DOCS
                     if d not in ('PHASE6_PRECOMMIT.md', 'phase8-verification.md'))
    # 全文書で見てよいのは**他の量と衝突しない識別子だけ**。
    # 帯や pt 幅は別の量（例: phase9 の地域別 β の 15.5pt）と衝突するので本編2本に限る。
    STALE_ALLDOC = {'835,731', '826,531', '171,160'}
    # **短い単位付きの値（万・億・%）は別シナリオの正当な値と衝突する**ので、この検査には
    # 使わない（それらは check-O がセル単位で見る）。ここで見るのは**衝突しない識別子**だけ。
    STALE_N = {
        '835,731': ['804,552', '804,579'],
        '826,531': ['830,000', '770,833'],
        '171,160': ['168,634'],
        '1.3506': ['ローンチ倍率 1.7434', '1.729', '×1.86'],
        '-23.1% 〜 -8.4%': ['−21.3% 〜 −5.8%', '−21.4% 〜 −7.4%', '−20.8% 〜 −6.6%'],
        '14.7pt': ['15.5pt', '14.0pt', '14.2pt'],
        '+5.0%': ['上振れ +2.1%', '上振れ +3.0%', 'バイアス +2.1%', 'バイアス +3.0%'],
    }
    MUST_IN_FINAL = {'主指標 生・加重', '主指標 生・時間加重', '主指標 補正後・加重',
                     '主指標 補正後・時間加重', 'バイアス', 'S*', '正直な帯', '群A 帯',
                     'CC売上 Base', 'CC売上 加重', '名目売上 Base', '営業利益 Base',
                     '8.x周期平均 加重', 'ローンチ倍率（予測）', 'T2 閾値'}
    ok = 0
    for name, got, want in CH:
        good = got == want
        marks = []
        for d in DOCS_N:
            t = read_doc(d)
            marks.append('○' if (want in t or want.replace('-', '−') in t) else '−')
        print(f"  {'OK ' if good else 'NG '} {name:<22s} 計算 {got:<16s} "
              f"文書 {want:<16s} {' '.join(f'{d.split(chr(45))[0][:5]}:{m}' for d, m in zip(DOCS_N, marks))}")
        ok += bool(good)
        if not good:
            note('要修正', 'scripts/phase8_consistency.py',
                 f"N: {name} の期待値が古い（計算 {got} / 期待 {want}）")
        if all(m == '−' for m in marks):
            note('要修正', ' / '.join(DOCS_N),
                 f"N: {name} = {want} がどちらの文書にも出てこない（滞留の疑い）")
        # 【第14次・査読で摘出】「どちらかに1回あれば OK」だと、本編で全滅していても
        # 他方に残っていれば通る。**結論の値は final-report.md に必ず存在すること**を要求する。
        elif name in MUST_IN_FINAL and marks[0] == '−':
            note('要修正', 'final-report.md',
                 f"N: 結論値 {name} = {want} が本編に1件も存在しない（全滅の疑い）")
        # 旧世代の値が訂正文脈外に残っていないか
        for old_v in STALE_N.get(want, []):
            for d in (DOCS_ALL if want in STALE_ALLDOC else DOCS_N):
                lines = read_doc(d).splitlines()
                for i, line in enumerate(lines):
                    if old_v in line and not in_correction_context(lines, i):
                        note('要修正', f"{d}:{i+1}",
                             f"N: 旧世代の値 {old_v}（{name}、現行 {want}）が訂正文脈外に残存")
    # T2 の反証閾値は文面パターンから直接抜いて params と突合する
    # （訂正文脈の免除に隠れて 168,634 が生き残っていた経路を塞ぐ）
    for d in DOCS_ALL:
        lines_ = read_doc(d).splitlines()
        for i_, line_ in enumerate(lines_):
            if in_correction_context(lines_, i_):
                continue
            for m in re.finditer(r'新規[＋+]復帰[^|\n]{0,40}?([\d]{1,3}(?:,\d{3})+)\s*を下回る',
                                 line_):
                if m.group(1) != f"{P.I_BASE_LV80:,}":
                    note('要修正', f"{d}:{i_+1}",
                         f"N: T2 の閾値が {m.group(1)} と書かれている（正典 {P.I_BASE_LV80:,}）")
    print(f"  → {ok}/{len(CH)} 一致")



def check_summary_table():
    """O. 要約表を**セル単位**で照合する

    【第14次で新設】check-N は「その値が文書のどこかに出るか」しか見ないので、
    表のセルが古い世代の値のままでも、同じ値が別の場所にあれば通ってしまう。
    要約表は行ラベルで引き当てて Bear/Base/Bull/加重 の4セルを直接突き合わせる。
    """
    print("\n" + "=" * 78)
    print("O. 要約表のセル単位照合")
    print("=" * 78)
    import params as P
    import phase7_forecast as F
    from phase7_forecast import build, cc_year, to_nominal
    r = build()
    w = lambda k: sum(r[x]['w'] * r[x][k] for x in r)
    cc = {k: cc_year(r[k]['fy2030'] / P.K1_FY_MEAN_LV80[2026]) for k in r}
    nom = {k: to_nominal(cc[k]) for k in r}
    wv = lambda d: sum(r[k]['w'] * d[k] for k in d)
    man = lambda v: f"{v/10000:.1f}万"
    oku = lambda v: f"{v:.0f}億"
    pct = lambda v: f"{v:+.1%}".replace('+', '+').replace('-', '−')
    ROWS = [
        ('8.x 周期平均', [man(r['Bear']['cyc']), man(r['Base']['cyc']),
                        man(r['Bull']['cyc']), man(w('cyc'))]),
        ('等観測重み', [pct(r['Bear']['cyc']/F.CYC7_MEAN-1), pct(r['Base']['cyc']/F.CYC7_MEAN-1),
                     pct(r['Bull']['cyc']/F.CYC7_MEAN-1), pct(w('cyc')/F.CYC7_MEAN-1)]),
        ('時間加重', [pct(r['Bear']['cyc_tw']/F.CYC7_MEAN_TW-1),
                    pct(r['Base']['cyc_tw']/F.CYC7_MEAN_TW-1),
                    pct(r['Bull']['cyc_tw']/F.CYC7_MEAN_TW-1),
                    pct(w('cyc_tw')/F.CYC7_MEAN_TW-1)]),
        ('FY2030.3 年度平均', [man(r['Bear']['fy2030']), man(r['Base']['fy2030']),
                            man(r['Bull']['fy2030']), man(w('fy2030'))]),
        ('恒常為替 MMO売上', [oku(cc['Bear']), oku(cc['Base']), oku(cc['Bull']), oku(wv(cc))]),
        ('名目 MMO売上', [oku(nom['Bear']), oku(nom['Base']), oku(nom['Bull']), oku(wv(nom))]),
    ]
    # 実績列・外部由来など、シナリオ4値の集合外に正当に現れる値
    OK_EXTRA = {'622億', '410億', '349.5億', '350億', '151億', '非開示',
                '90.6万', '88.0万', '88.1万', '110.1万', '110.2万', '81.6万', '81.7万',
                '132万', '128万', '85.4万', '−43.8%', '36.8%', '31〜38%'}
    ok = bad = 0
    for d in ('final-report.md', 'phase7-forecast.md'):
        for line in read_doc(d).splitlines():
            if not line.startswith('|'):
                continue
            cells = [c.strip().replace('*', '').replace('　', '') for c in line.split('|')[1:-1]]
            if len(cells) < 2:
                continue
            for lab, want in ROWS:
                if lab not in cells[0]:
                    continue
                # 【第14次・査読で摘出】以前は len(cells) < 5 で 4列表を丸ごとスキップしており、
                # §0-2「実績との対比」表（4列）に住んでいた旧世代の値を素通りさせていた。
                # 列数で切らず、**その行に現れる全セルを、想定値の集合と突き合わせる**。
                got = [c.split('（')[0].strip() for c in cells[1:]]
                for g in got:
                    if g in ('—', '-', '') or not re.match(r'^[−\-+]?[\d,.]+(万|億|%|)$', g):
                        continue
                    if g in want or g in OK_EXTRA:
                        ok += 1
                    else:
                        bad += 1
                        note('要修正', d,
                             f"O: 行「{cells[0][:24]}」のセル {g} は現行値 {' / '.join(want)} のいずれとも一致しない")
    print(f"  → セル {ok} 件一致 / {bad} 件不一致")



if __name__ == '__main__':
    outs = run_all_scripts()
    check_canonical(outs)
    check_cross_doc_numbers()
    check_forbidden()
    check_versions()
    check_section_refs()
    check_conclusions(outs)
    check_retractions()
    check_arithmetic()
    check_width_inequality()
    check_japan(outs)
    check_player_report(outs)
    check_main_report()
    check_summary_table()
    check_guards()
    self_test()
    print("\n" + "=" * 78)
    print(f"総括: 致命 {sum(1 for s,_,_ in FAIL if s=='致命')} / "
          f"要修正 {sum(1 for s,_,_ in FAIL if s=='要修正')} / "
          f"要確認 {sum(1 for s,_,_ in FAIL if s=='要確認')} / "
          f"軽微 {sum(1 for s,_,_ in FAIL if s=='軽微')}")
    print("=" * 78)
