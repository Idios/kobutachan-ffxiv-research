#!/usr/bin/env python3
"""
Phase 12 — プレイヤー向けレポートの図表（第12次で新設）

出力: charts/*.svg（依存ライブラリなし。SVG を直接書く）
  5. population.svg   活動キャラクター数の推移（64日換算・Lv80超統一）＋世代の節目
  6. flows.svg        新規／復帰／継続の 6.x 比
  7. supply.svg       コンテンツ供給の分解（間隔・1パッチの量・時間あたり）
  8. retention.svg    経過月をそろえた残存率（FFXIV vs 競合）

配色は dataviz スキルの検証済みパレット（light/dark 両対応、CVD 検証済み）。
  slot1 青 #2a78d6 / slot2 橙 #eb6834 / slot3 アクア #1baf7a / slot4 黄 #eda100

使い方: python3 scripts/phase12_charts.py
"""
import sys, csv, os, math
from datetime import date
sys.path.insert(0, 'scripts')
import params as P

OUT = 'charts'
os.makedirs(OUT, exist_ok=True)

S1, S2, S3, S4 = '#2a78d6', '#eb6834', '#1baf7a', '#eda100'
S1D, S2D, S3D, S4D = '#3987e5', '#d95926', '#199e70', '#c98500'

# 明暗どちらのテーマでも読める前置き。CSS 変数で色を切り替える。
HEAD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"
     font-family="Noto Sans CJK JP">
<style>
  .bg{{fill:#fcfcfb}} .ink{{fill:#0b0b0b}} .sub{{fill:#52514e}}
  .grid{{stroke:#d8d8d4;stroke-width:1}}
  .s1{{fill:%s}} .s2{{fill:%s}} .s3{{fill:%s}} .s4{{fill:%s}}
  .l1{{stroke:%s}} .l2{{stroke:%s}} .l3{{stroke:%s}} .l4{{stroke:%s}}
  .ring{{stroke:#fcfcfb}}
  .ttl{{font-size:15px;font-weight:700}} .sc{{font-size:11.5px}} .lb{{font-size:12px}}
  .vl{{font-size:12.5px;font-weight:700}}
  @media (prefers-color-scheme: dark) {{
    .bg{{fill:#1a1a19}} .ink{{fill:#ffffff}} .sub{{fill:#c3c2b7}}
    .grid{{stroke:#3a3a38}} .ring{{stroke:#1a1a19}}
    .s1{{fill:%s}} .s2{{fill:%s}} .s3{{fill:%s}} .s4{{fill:%s}}
    .l1{{stroke:%s}} .l2{{stroke:%s}} .l3{{stroke:%s}} .l4{{stroke:%s}}
  }}
</style>
<rect class="bg" x="0" y="0" width="{w}" height="{h}"/>
""" % (S1, S2, S3, S4, S1, S2, S3, S4,
       S1D, S2D, S3D, S4D, S1D, S2D, S3D, S4D)


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def txt(x, y, s, cls='ink lb', anchor='start', extra=''):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" '
            f'text-anchor="{anchor}" {extra}>{esc(s)}</text>\n')


def write(name, w, h, body):
    with open(f'{OUT}/{name}.svg', 'w') as f:
        f.write(HEAD.format(w=w, h=h) + body + '</svg>\n')
    print(f"  {OUT}/{name}.svg")


# ------------------------------------------------------------------ 5
def chart_population():
    """活動キャラクター数の推移。**64日換算・Lv80超統一の正典系列**"""
    ser = P.K1_SERIES_LV80
    W, H = 880, 400
    L, R, T, B = 62, 24, 52, 76
    xs = [date(*map(int, d.split('-'))).toordinal() for d, _ in ser]
    ys = [v for _, v in ser]
    x0, x1 = min(xs), max(xs)
    y1 = 1_400_000
    px = lambda x: L + (x - x0) / (x1 - x0) * (W - L - R)
    py = lambda y: T + (1 - y / y1) * (H - T - B)

    b = txt(L, 24, '活動キャラクター数の推移（64日換算・レベル下限を統一）', 'ink ttl')
    b += txt(L, 40, '有志の国勢調査を、調査の間隔と集計対象のレベル下限で揃え直したもの', 'sub sc')
    for g in range(0, y1 + 1, 200_000):
        b += f'<line class="grid" x1="{L}" y1="{py(g):.1f}" x2="{W-R}" y2="{py(g):.1f}"/>\n'
        b += txt(L - 8, py(g) + 4, f'{g//10000}万', 'sub sc', 'end')
    # 節目
    MARK = [('2021-12-07', '6.0 暁月'), ('2024-07-02', '7.0 黄金'), ('2027-01-01', '8.0')]
    for d, lab in MARK:
        o = date(*map(int, d.split('-'))).toordinal()
        if not (x0 <= o <= x1):
            continue
        b += (f'<line class="grid" x1="{px(o):.1f}" y1="{T}" x2="{px(o):.1f}" '
              f'y2="{H-B}" stroke-dasharray="3 3"/>\n')
        b += txt(px(o) + 4, H - B + 16, lab, 'sub sc')
    pts = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in zip(xs, ys))
    b += (f'<polyline points="{pts}" fill="none" class="l1" '
          f'stroke-width="2" stroke-linejoin="round"/>\n')
    # 注記する3点
    NOTE = [(P.k1_peak_in('2021-11-01', '2023-07-01')[1], '6.0ピーク 132万', -6, -12, 'end'),
            (P.k1_peak_in('2023-12-01', '2025-05-01')[1], '7.0ピーク 128万', 6, -12, 'start'),
            ('2026-07-20', '直近 85.4万', -8, 22, 'end')]
    for d, lab, dx, dy, an in NOTE:
        o = date(*map(int, d.split('-'))).toordinal()
        v = dict(ser)[d]
        b += (f'<circle cx="{px(o):.1f}" cy="{py(v):.1f}" r="4.5" class="s1"/>\n'
              f'<circle cx="{px(o):.1f}" cy="{py(v):.1f}" r="4.5" fill="none" '
              f'class="ring" stroke-width="2"/>\n')
        b += txt(px(o) + dx, py(v) + dy, lab, 'ink vl', an)
    b += txt(L, H - B + 32, '2017年', 'sub sc')
    b += txt(W - R, H - B + 32, '2026年7月', 'sub sc', 'end')
    b += txt(L, H - 6,
             '※ 調査の間隔は35〜123日とばらつくので、すべて64日相当に換算してある。'
             '公表値（直近95万）をそのまま並べてはいけない', 'sub sc')
    write('population', W, H, b)


# ------------------------------------------------------------------ 6
def chart_flows():
    """新規／復帰／継続の 6.x 比。分母は同じ項目の 6.x サイクルでの値"""
    W, H = 760, 300
    L, T, BW, RH, STEP = 176, 84, 400, 26, 58
    ROWS = [('新規キャラクター', 0.38, 0.56, 's2'),
            ('復帰キャラクター', 0.63, 0.69, 's4'),
            ('継続キャラクター', 0.85, 0.87, 's3')]
    b = txt(24, 28, '7.x サイクルは 6.x サイクルの何割か', 'ink ttl')
    b += txt(24, 48, '分母は「6.x サイクルでの同じ項目の数」。'
                     '新規38〜56% ＝ 7.x の新規キャラ数 ÷ 6.x の新規キャラ数', 'sub sc')
    b += txt(24, 65, '減り方には序列がある： 新規 ≫ 復帰 ＞ 継続', 'sub sc')
    # 100% の基準線
    x100 = L + BW
    b += (f'<line class="grid" x1="{x100:.1f}" y1="{T-10}" x2="{x100:.1f}" '
          f'y2="{T+len(ROWS)*STEP-6}" stroke-dasharray="4 3"/>\n')
    b += txt(x100, T - 16, '6.x と同じ = 100%', 'sub sc', 'middle')
    b += f'<line class="grid" x1="{L}" y1="{T-10}" x2="{L}" y2="{T+len(ROWS)*STEP-6}"/>\n'
    for i, (lab, lo, hi, cs) in enumerate(ROWS):
        y = T + i * STEP
        b += txt(L - 14, y + 18, lab, 'ink lb', 'end')
        # 下限までを塗り、上限までを薄い線で示す
        b += (f'<rect x="{L}" y="{y}" width="{lo*BW:.1f}" height="{RH}" rx="4" '
              f'class="{cs}"/>\n')
        b += (f'<rect x="{L+lo*BW:.1f}" y="{y+RH/2-1.5}" width="{(hi-lo)*BW:.1f}" '
              f'height="3" class="{cs}" opacity="0.55"/>\n')
        b += (f'<line x1="{L+hi*BW:.1f}" y1="{y+4}" x2="{L+hi*BW:.1f}" y2="{y+RH-4}" '
              f'class="l{cs[1]}" stroke-width="2"/>\n')
        b += txt(L + hi * BW + 12, y + 18, f'{lo:.0%}〜{hi:.0%}', 'ink vl')
    for t_ in (0, 0.5, 1.0):
        b += txt(L + t_ * BW, T + len(ROWS) * STEP + 12, f'{t_:.0%}', 'sub sc', 'middle')
    b += txt(24, H - 10,
             '※ 塗りが下限、細い線が上限。幅は3通りの補正のしかたによる範囲', 'sub sc')
    write('flows', W, H, b)


# ------------------------------------------------------------------ 7
def chart_supply():
    """コンテンツ供給の分解: 時間あたり = 1パッチの量 ÷ 間隔"""
    import phase11_supply as SP
    W, H = 720, 340
    L, T, BW, RH = 210, 92, 380, 30
    bt = lambda g: sum(float(SP.G[g][m]['total_full_cycle']) for m in SP.BATTLE)
    base = ('4.x', bt('4.x') / SP.META['4.x'][1], SP.META['4.x'][0] / SP.META['4.x'][1],
            bt('4.x') / SP.META['4.x'][0])
    cur = ('7.x', bt('7.x') / SP.META['7.x'][1], SP.META['7.x'][0] / SP.META['7.x'][1],
           bt('7.x') / SP.META['7.x'][0])
    ROWS = [('パッチ間隔', cur[2] / base[2], S4, '長いほど供給は減る'),
            ('1パッチあたりの本数', cur[1] / base[1], S3, 'ほぼ変わっていない'),
            ('時間あたりの供給', cur[3] / base[3], S2, '＝ 上の2つの割り算')]
    b = txt(24, 26, 'コンテンツ供給はなぜ減ったのか', 'ink ttl')
    b += txt(24, 44, '『紅蓮のリベレーター』期（4.x）を 100 としたときの、『黄金のレガシー』期（7.x）', 'sub sc')
    b += txt(24, 62, '時間あたりの供給 ＝ 1パッチあたりの本数 ÷ パッチ間隔', 'ink sc')
    for i, (lab, rel, col, note) in enumerate(ROWS):
        y = T + i * (RH + 44)
        cs = {S2: 's2', S3: 's3', S4: 's4'}[col]
        b += txt(L - 12, y + 20, lab, 'ink lb', 'end')
        b += f'<line class="grid" x1="{L}" y1="{y-6}" x2="{L}" y2="{y+RH+6}"/>\n'
        w = rel * BW * 0.72
        b += f'<rect x="{L}" y="{y}" width="{w:.1f}" height="{RH}" rx="4" class="{cs}"/>\n'
        b += txt(L + w + 10, y + 20, f'{rel*100:.0f}', 'ink vl')
        b += txt(L + w + 46, y + 20, f'（{rel-1:+.0%}）  {note}', 'sub sc')
    x100 = L + BW * 0.72
    b += (f'<line class="grid" x1="{x100:.1f}" y1="{T-14}" x2="{x100:.1f}" '
          f'y2="{H-52}" stroke-dasharray="4 3"/>\n')
    b += txt(x100, T - 20, '4.x = 100', 'sub sc', 'middle')
    b += txt(24, H - 30,
             '※ 「本数」はダンジョン・討滅戦・レイド・絶・アライアンスレイドの実装本数を数えたもの。',
             'sub sc')
    b += txt(24, H - 14,
             '　 プレイ時間で測ってはいない（公開資料が存在しない）。メインクエストは別に数える必要がある',
             'sub sc')
    write('supply', W, H, b)


# ------------------------------------------------------------------ 8
def chart_retention():
    """経過月をそろえた残存率"""
    import phase10_entrants as E
    W, H = 820, 380
    L, R, T, B = 62, 178, 68, 62
    MMAX = 21
    px = lambda m: L + m / MMAX * (W - L - R)
    py = lambda r: T + (1 - min(r, 1.0)) * (H - T - B)
    b = txt(24, 26, '発売直後のピークから、何割が残っているか', 'ink ttl')
    b += txt(24, 44, '横軸は発売からの経過月数。同じ経過月どうしで比べないと意味がない', 'sub sc')
    for g in (0, 0.25, 0.5, 0.75, 1.0):
        b += f'<line class="grid" x1="{L}" y1="{py(g):.1f}" x2="{W-R}" y2="{py(g):.1f}"/>\n'
        b += txt(L - 8, py(g) + 4, f'{g:.0%}', 'sub sc', 'end')
    for m in (0, 3, 6, 9, 12, 15, 18, 21):
        b += txt(px(m), H - 30, f'{m}か月', 'sub sc', 'middle')
    SER = [('FFXIV（7.0）', 'FFXIV', 'l1', 's1', 0),
           ('Throne and Liberty', 'Throne and Liberty', 'l2', 's2', -14),
           ('New World', 'New World', 'l3', 's3', 14)]
    for lab, key, lcls, fcls, dy in SER:
        _, s = E.series(key)
        pts = [(m, r) for m, _, _, r in s if 0 <= m <= MMAX]
        d = ' '.join(f'{px(m):.1f},{py(r):.1f}' for m, r in pts)
        b += f'<polyline points="{d}" fill="none" class="{lcls}" stroke-width="2" stroke-linejoin="round"/>\n'
        lm, lr = pts[-1]
        b += f'<circle cx="{px(lm):.1f}" cy="{py(lr):.1f}" r="4" class="{fcls}"/>\n'
        b += f'<circle cx="{px(lm):.1f}" cy="{py(lr):.1f}" r="4" fill="none" class="ring" stroke-width="2"/>\n'
        b += txt(px(lm) + 10, py(lr) + 4 + dy, f'{lab} {lr:.0%}', 'ink lb')
    # New World の開発終了を注記
    _, nw = E.series('New World')
    m12 = next(r for m, _, _, r in nw if m == 12)
    b += (f'<line class="grid" x1="{px(12):.1f}" y1="{T}" x2="{px(12):.1f}" y2="{H-B}" '
          f'stroke-dasharray="3 3"/>\n')
    b += txt(px(12) - 8, T + 30, 'New World が開発終了を発表', 'sub sc', 'end')
    b += txt(px(12) - 8, T + 46, '（以降の落ち込みは打ち切りの結果）', 'sub sc', 'end')
    b += txt(24, H - 6,
             '※ Steam の同時接続数。Steam が全プレイヤーの何割を捕まえるかはタイトルで桁が違うので、'
             '絶対値の比較には使えない', 'sub sc')
    write('retention', W, H, b)


if __name__ == "__main__":
    print("図を生成:")
    chart_population(); chart_flows(); chart_supply(); chart_retention()
