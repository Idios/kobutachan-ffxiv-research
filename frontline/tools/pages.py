"""ルール別のページの中身（build.py から使う）。

- 値はすべて台帳の行 ID で参照する。ここに数を書かない（build.Data が ○ の行だけを返す）。
- 値を出すときは必ず単位を照合する（台帳の単位が変わったら生成が止まり、表示を見直す）。単位の文字は値の
  span の中に入れ（suffix）、等級の印が単位の後ろに付くようにする。
- 時刻は残り時間（20:00 → 0:00）だけを「分:秒」で書く。長さ・待ち時間は「N秒」「N分」（dur）で書き、
  続く長さは「N秒間」、待ち時間は「N秒後」と書き分ける。
- 見出しや「1分あたり」などの言葉は、同じカードに出す行の項目名・条件を言い換えたものに限る。
  台帳にない事実を書き足さない。
- 文字はモックの倍（最小 24px）。1画面に収まるように、載せる行を選んでいる（plan.md §15）。
"""

from __future__ import annotations

import re

from build import (
    BuildError,
    Card,
    Data,
    band,
    bullets,
    card,
    chips,
    esc,
    event_tiles,
    fmt,
    fmt1,
    mmss,
    rank_tiles,
)

PER_UNIT_HP = 100_000  # 「10万HPあたり」の基準（見やすさのための換算。ゲームの値ではない）
CLOCK = "残り時間（分:秒）"
MIN_LEFT = "分（残り時間）"


def match_seconds(d: Data) -> int:
    return round(d.num("COM-MATCH-TIME", "分") * 60)


def ui(n: int, text: str) -> str:
    """画面の都合で出す数（ゲームの値ではない）。検査で区別できるように印を付ける（data-ui は数そのもの）。"""
    return f'<span data-ui="{n}">{esc(text)}</span>'


def man(n: int) -> str:
    """10万 のような表記（PER_UNIT_HP から作る）。"""
    return f"{n // 10_000:,}万" if n % 10_000 == 0 else f"{n:,}"


def plus(x: float) -> str:
    return "+" + fmt(x)


def times(x: float) -> str:
    return "×" + fmt(x)


def dur(sec: float) -> str:
    """長さ・待ち時間の書き方。2分以上で割り切れれば「N分」、それ以外は「N秒」。"""
    s = round(sec)
    return f"{s // 60}分" if s >= 120 and s % 60 == 0 else f"{s}秒"


def seg_cap(cb: Card, cap_id: str, switch_ids: list[str], unit: str) -> str:
    """時間帯ごとの上限の値。区切りの時刻の行も出どころに含め、そのうち最も確かでない等級の印を付ける。"""
    x = cb.d.num(cap_id, unit)
    return cb.c(x, [cap_id, *switch_ids], suffix=unit)


# ---------------------------------------------------------------- 外縁遺跡群（制圧戦）


def secure(d: Data, prefix: str) -> str:
    total = match_seconds(d)
    rates = [f"SEC-FLAG-RATE-{i}" for i in range(1, 10)]
    cb = Card(d, rates + ["SEC-FLAG-TICK", "SEC-FLAG-COUNT", "SEC-SHEER-WILL-MULT"])
    tick = d.num("SEC-FLAG-TICK", "秒")
    rate_unit = f"戦術値/{fmt(tick)}秒"
    vals = [d.num(r, rate_unit) for r in rates]
    inc = [b - a for a, b in zip([0.0] + vals[:-1], vals)]
    step = min(inc)
    top = max(vals)
    cols, jumps = [], []
    for i, (rid, v) in enumerate(zip(rates, vals), 1):
        jump = i > 1 and inc[i - 1] > step
        if jump:
            jumps.append(f'<span data-src="{rid}">{i}</span>')
        cols.append(
            f'<div class="bc{" jump" if jump else ""}"><div class="lab">{cb.c(v * 60 / tick, [rid, "SEC-FLAG-TICK"], suffix="/分")}'
            f'<small>{cb.v(rid, unit=rate_unit)}/{cb.v("SEC-FLAG-TICK", unit="秒", suffix="秒毎")}</small></div>'
            f'<div class="bar" style="height:{round(80 * v / top)}px"></div><div class="xl" data-src="{rid}">{i}</div></div>'
        )
    jump_line = (
        f'<span class="big2">{"・".join(jumps)}<small>か所目で大きく伸びる（青）</small></span>' if jumps else ""
    )  # 増え方が一定なら出さない
    below = (
        f'<div class="below">{jump_line}'
        f'<span>全 {cb.v("SEC-FLAG-COUNT", unit="か所", suffix="か所")}</span>'
        f'<span>{cb.t("SEC-SHEER-WILL")}（{cb.v("SEC-SHEER-WILL-MULT", unit="倍", show=times)}）</span></div>'
    )
    bases = card(
        "拠点の占拠",
        f'<div class="bases"><div class="chart">{"".join(cols)}</div></div>{below}',
        sub="横: 占拠している拠点の数 ・ 部隊全体に入る戦術値",
        badge=cb.badge(),
    )

    ev_ids = ["SEC-DRONE-PTS", "SEC-DRONE-COUNT", "SEC-DRONE-ALPHA-PTS", "SEC-CMDR-PTS", "SEC-CMDR-SPOTS",
              "SEC-NODE-PTS", "SEC-NODE-REFILLS", "SEC-NODE-HP", "SEC-BH-DRONE", "SEC-BH-ALPHA", "SEC-BH-CMDR",
              "SEC-EVT-FIRST", "SEC-EVT-FIRST-KIND", "SEC-EVT-PANEL-LEAD", "SEC-EVT-PANEL-INVULN",
              "SEC-EVT-HUD-NEXT", "SEC-BH-DRONE-WHO", "SEC-BH-ALPHA-WHO", "SEC-BH-CMDR-WHO", "SEC-EVT-PANEL-STOP"]
    ce = Card(d, ev_ids)
    drone_n = d.num("SEC-DRONE-COUNT", "体")
    cmdr_n = d.num("SEC-CMDR-SPOTS", "か所")
    node_n = d.num("SEC-NODE-REFILLS", "回") + 1  # 全快の回数＋最後の1回（SEC-NODE-PTS-UNIT）
    m = re.search(r"最大(\d+)回", d.row("SEC-NODE-PTS-UNIT").value)
    if not m or int(m.group(1)) != node_n:
        raise BuildError("SEC-NODE-PTS-UNIT の「最大N回」が SEC-NODE-REFILLS＋1 と合わない。表示を見直す")
    events = [
        {
            "svg": "i-drone", "name": "邀撃ドローン", "note": ce.t("SEC-DRONE-DIST"),
            "big": ce.v("SEC-DRONE-PTS", unit="戦術値") + "<small>戦術値/体</small>",
            "lines": [
                (f'{ce.v("SEC-DRONE-COUNT", unit="体", suffix="体")}で 計 '
                 f'{ce.c(d.num("SEC-DRONE-PTS", "戦術値") * drone_n, ["SEC-DRONE-PTS", "SEC-DRONE-COUNT"], suffix="戦術値")}'),
                f'戦意値 {ce.v("SEC-BH-DRONE", unit="戦意値", show=plus)}',
            ],
        },
        {
            "svg": "i-drone-alpha", "name": "邀撃ドローンα", "note": "金色・" + ce.t("SEC-DRONE-DIST"),
            "big": ce.v("SEC-DRONE-ALPHA-PTS", unit="戦術値") + "<small>戦術値/体</small>",
            "lines": [
                f'戦意値 {ce.v("SEC-BH-ALPHA", unit="戦意値", show=plus)}',
            ],
        },
        {
            "svg": "i-commander", "name": "邀撃コマンダー", "note": ce.t("SEC-CMDR-PTS-UNIT") + "・" + ce.t("SEC-CMDR-DIST"),
            "big": ce.v("SEC-CMDR-PTS", unit="戦術値") + "<small>戦術値/か所</small>",
            "lines": [
                (f'{ce.v("SEC-CMDR-SPOTS", unit="か所", suffix="か所")}で 計 '
                 f'{ce.c(d.num("SEC-CMDR-PTS", "戦術値") * cmdr_n, ["SEC-CMDR-PTS", "SEC-CMDR-SPOTS"], suffix="戦術値")}'),
                f'戦意値 {ce.v("SEC-BH-CMDR", unit="戦意値", show=plus)}',
            ],
        },
        {
            "svg": "i-system", "name": "邀撃システム", "note": ce.t("SEC-NODE-DIST"),
            # 「HP0」の 0 は SEC-NODE-PTS-UNIT（HPが0になるたびに入る）から
            "big": ce.v("SEC-NODE-PTS", unit="戦術値")
            + f'<small>{ce.raw("SEC-NODE-PTS-UNIT", "戦術値/HP0", unit="テキスト", cls="u")}</small>',
            "lines": [
                (f'最大{ce.c(node_n, ["SEC-NODE-REFILLS", "SEC-NODE-PTS-UNIT"], suffix="回")}で 計 '
                 f'{ce.c(d.num("SEC-NODE-PTS", "戦術値") * node_n, ["SEC-NODE-PTS", "SEC-NODE-REFILLS", "SEC-NODE-PTS-UNIT"], suffix="戦術値")}'),
                f'HP {ce.v("SEC-NODE-HP", unit="HP", suffix="（1本）")}',
            ],
        },
    ]
    # ドローンと α の戦意値の受け手は同じ（公式とユーザーの指摘）。違ったら表示を見直す
    if d.row("SEC-BH-DRONE-WHO").value != d.row("SEC-BH-ALPHA-WHO").value:
        raise BuildError("SEC-BH-DRONE-WHO と SEC-BH-ALPHA-WHO の値が違う。戦意値の受け手の表示を見直す")
    both = f'<span class="t" data-src="SEC-BH-DRONE-WHO SEC-BH-ALPHA-WHO">{esc(d.text("SEC-BH-DRONE-WHO"))}</span>'
    first = d.num("SEC-EVT-FIRST", "秒（試合開始からの経過）")
    lead = d.num("SEC-EVT-PANEL-LEAD", "秒（出現の前）")
    timing = chips([
        f'最初は 残り <b>{ce.c(total - first, ["COM-MATCH-TIME", "SEC-EVT-FIRST"], show=mmss)}</b>（{ce.t("SEC-EVT-FIRST-KIND")}）',
        f'2回目から: {ce.t("SEC-EVT-HUD-NEXT")}',
        (
            f'転移装置: 出現の {ce.v("SEC-EVT-PANEL-LEAD", unit="秒（出現の前）", suffix="秒前")}〜{ce.t("SEC-EVT-PANEL-STOP")}'
            f'（最初は 残り <b>{ce.c(total - first + lead, ["COM-MATCH-TIME", "SEC-EVT-FIRST", "SEC-EVT-PANEL-LEAD"], show=mmss)}</b> から）'
            f'・{ce.t("SEC-EVT-PANEL-ONEWAY")}・着いて無敵 {ce.v("SEC-EVT-PANEL-INVULN", unit="秒", suffix="秒")}'
        ),
    ])
    center = card(
        "中央の中立モンスター",
        event_tiles(events) + timing,
        sub=f'戦意値: ドローン・αは{both}、コマンダーは{ce.t("SEC-BH-CMDR-WHO")}',
        badge=ce.badge(),
    )
    return bases + center


# ---------------------------------------------------------------- シールロック（争奪戦）


def seize(d: Data, prefix: str) -> str:
    total = match_seconds(d)
    ids = [f"SEI-TOME-{k}-{x}" for k in "BAS" for x in ("TOTAL", "TICK")] + ["SEI-TOME-TICK-SEC"]
    cr = Card(d, ids)
    iv = d.num("SEI-TOME-TICK-SEC", "秒")
    tiles = []
    for k in "BAS":
        tot, tk = f"SEI-TOME-{k}-TOTAL", f"SEI-TOME-{k}-TICK"
        t_v, k_v = d.num(tot, "情報値"), d.num(tk, "情報値/回")
        tiles.append({
            "rank": k, "total": cr.v(tot, unit="情報値"), "unit": "情報値",
            "lines": [
                (f'{cr.c(k_v * 60 / iv, [tk, "SEI-TOME-TICK-SEC"], suffix="/分")}'
                f'<small>（{cr.v(tk, unit="情報値/回")}/{cr.v("SEI-TOME-TICK-SEC", unit="秒", suffix="秒毎")}）</small>'),
                f'停止まで {cr.c(t_v / k_v * iv, [tot, tk, "SEI-TOME-TICK-SEC"], show=dur)}',
            ],
        })
    tomes = card("アラガントームリス", rank_tiles(d, ["SEI-RANK-MAP-SYMBOL", "SEI-RANK-COLOR"], tiles),
                 sub="占拠している部隊だけに入る（1基の合計。停止までは、占拠し続けた場合）", badge=cr.badge())

    sw = d.clock("SEI-CAP-SWITCH", CLOCK)
    late = d.row("SEI-RANK-NO-B-LATE")
    m = re.search(r"残り(\d{1,2}:\d{2})", late.condition)
    if not m or m.group(1) != d.row("SEI-CAP-SWITCH").value:
        raise BuildError("SEI-RANK-NO-B-LATE の時間帯（条件）が SEI-CAP-SWITCH と違う。表示を見直す")
    cb = Card(d, ["SEI-CAP-1", "SEI-CAP-2", "SEI-CAP-SWITCH", "SEI-SPAWN-FIRST-TIME", "SEI-SPAWN-FIRST-COUNT",
                  "SEI-SPAWN-REFILL-SEC", "SEI-RANK-NO-B-LATE"])
    first = d.clock("SEI-SPAWN-FIRST-TIME", CLOCK)
    bandhtml = band(
        d,
        segments=[
            (f'上限 {seg_cap(cb, "SEI-CAP-1", ["SEI-CAP-SWITCH"], "基")}', total, sw),
            (f'上限 {seg_cap(cb, "SEI-CAP-2", ["SEI-CAP-SWITCH"], "基")} ・ {cb.t("SEI-RANK-NO-B-LATE")}', sw, 0),
        ],
        marks=[((f'最初 {cb.v("SEI-SPAWN-FIRST-COUNT", unit="基", suffix="基")} '
                f'{cb.raw("SEI-SPAWN-FIRST-TIME", d.row("SEI-SPAWN-FIRST-TIME").value, unit=CLOCK)}'), first)],
    )
    timing = card(
        "同時に起動するアラガントームリスの数（残り時間）",
        bandhtml + chips([
            f'停止してから {cb.v("SEI-SPAWN-REFILL-SEC", unit="秒", suffix="秒後")}に次が起動（場所はランダム）',
            f'上限が変わるのは 残り {cb.raw("SEI-CAP-SWITCH", d.row("SEI-CAP-SWITCH").value, unit=CLOCK)}',
        ]),
        badge=cb.badge(),
    )

    co = Card(d, ["SEI-OCC-CAST-SEC", "SEI-OCC-INTERRUPT", "SEI-OCC-ENEMY", "SEI-OCC-LOCKOUT",
                  "SEI-TOME-NEUTRAL-DRAIN", "SEI-TOME-STACK", "SEI-RANK-TREND", "SEI-OCC-CAPTURE-BONUS", "SEI-OCC-PERSIST",
                  "NAA-CLAIM-GUARDIAN"])
    rules = card(
        "占拠のしかた",
        bullets([
            f'占拠に 約{co.v("SEI-OCC-CAST-SEC", unit="秒", suffix="秒")}・{co.t("SEI-OCC-INTERRUPT")}',
            co.t("SEI-OCC-PERSIST"),
            co.t("SEI-OCC-ENEMY"),
            co.t("SEI-OCC-LOCKOUT"),
            co.t("SEI-OCC-CAPTURE-BONUS"),
            co.t("SEI-TOME-NEUTRAL-DRAIN"),
            co.t("SEI-TOME-STACK"),
            co.t("SEI-RANK-TREND"),
            co.t("NAA-CLAIM-GUARDIAN"),  # PvP 全般の規則（オブジェクトにアクセス中）。行は終節戦の台帳にある
        ]),
        badge=co.badge(),
    )
    return tomes + timing + rules


# ---------------------------------------------------------------- フィールド・オブ・グローリー（砕氷戦）


def shatter(d: Data, prefix: str) -> str:
    total = match_seconds(d)
    ids = [f"SHA-{s}-{x}" for s in "LS" for x in ("DATA", "HP", "MAX-ACTIVE", "SPOTS")]
    ci = Card(d, ids)

    def tile(s: str, svg: str) -> dict:
        data, hp = d.num(f"SHA-{s}-DATA", "情報値"), d.num(f"SHA-{s}-HP", "HP")
        return {
            "svg": svg, "name": d.row(f"SHA-{s}-DATA").group.split("：")[-1],
            "big": ci.v(f"SHA-{s}-DATA", unit="情報値") + "<small>情報値</small>",
            "lines": [
                f'HP {ci.v(f"SHA-{s}-HP", unit="HP")}',
                f'{ui(PER_UNIT_HP, man(PER_UNIT_HP))}HPあたり {ci.c(data / hp * PER_UNIT_HP, [f"SHA-{s}-DATA", f"SHA-{s}-HP"], show=fmt1)}',
                f'同時に {ci.v(f"SHA-{s}-MAX-ACTIVE", unit="個", suffix="個")}まで ・ 全 {ci.v(f"SHA-{s}-SPOTS", unit="か所", suffix="か所")}',
            ],
        }

    ice = card(
        "アイスドトームリス",
        event_tiles([tile("L", "i-ice-large"), tile("S", "i-ice-small")], cls="wide"),
        sub=ci.t("SHA-ICE-DISTRIB"),
        badge=ci.badge(),
    )

    lead = d.num("SHA-ICE-WARN-LEAD", "秒")
    l_first = total - (d.num("SHA-L-FIRST-WARN", "秒（試合開始からの経過）") + lead)
    s_first = d.clock("SHA-S-FIRST-ACTIVE", CLOCK)
    # 小の初回の一斉起動（外部の時刻）は、公式の「最初に起動するまでの時間」＋予告と合っているか
    if s_first != total - (d.num("SHA-S-FIRST-DELAY", "秒") + lead):
        raise BuildError("SHA-S-FIRST-ACTIVE が、SHA-S-FIRST-DELAY と SHA-ICE-WARN-LEAD から求まる時刻と違う。台帳を見直す")
    s_react = d.num("SHA-S-REACT", "秒")
    s_second = s_first - (s_react + lead)
    cb = Card(d, ["SHA-ICE-WARN-LEAD", "SHA-L-FIRST-WARN", "SHA-S-FIRST-ACTIVE", "SHA-S-REACT", "SHA-L-REACT",
                  "SHA-L-RESPAWN", "SHA-S-RESPAWN", "SHA-S-REACT-RULE", "COM-MATCH-DRAW", "SHA-ICE-BH", "SHA-L-MAX-ACTIVE",
                  "SHA-S-MAX-ACTIVE", "SHA-S-SPOTS"])
    bandhtml = band(
        d,
        whole=f'同時に 大は最大 {cb.v("SHA-L-MAX-ACTIVE", unit="個", suffix="個")} ・ 小は最大 {cb.v("SHA-S-MAX-ACTIVE", unit="個", suffix="個")}',
        marks=[
            (f'大 最初 {cb.c(l_first, ["COM-MATCH-TIME", "SHA-L-FIRST-WARN", "SHA-ICE-WARN-LEAD"], show=mmss)}', l_first),
            ((f'小 {cb.v("SHA-S-SPOTS", unit="か所", suffix="か所")} 一斉 '
             f'{cb.raw("SHA-S-FIRST-ACTIVE", d.row("SHA-S-FIRST-ACTIVE").value, unit=CLOCK)}'), s_first),
            (f'小 2巡目 最速 {cb.c(s_second, ["SHA-S-FIRST-ACTIVE", "SHA-S-REACT", "SHA-ICE-WARN-LEAD", "SHA-S-REACT-RULE"], show=mmss)}', s_second),
        ],
    )
    steps = [s.strip() for s in d.text("SHA-MAP-STATES").split("→") if s.strip()]
    flow = (
        f'<div class="note">2Dマップでの表示{cb.wrap("", ["SHA-MAP-STATES"], d.grade("SHA-MAP-STATES"), "t")}</div>'
        '<div class="flow">'
        + "".join(f'<div class="st"><span class="t" data-src="SHA-MAP-STATES">{esc(s)}</span></div>' for s in steps)
        + "</div>"
    )
    timing = card(
        "アイスドトームリスが起動する時刻（残り時間）",
        bandhtml + chips([
            f'2Dマップの予告は 起動の {cb.v("SHA-ICE-WARN-LEAD", unit="秒", suffix="秒前")}',
            f'大: 壊れて {cb.v("SHA-L-REACT", unit="秒", suffix="秒後")}に次の予告',
            f'壊れてから再出現まで 大 {cb.v("SHA-L-RESPAWN", unit="秒", show=dur)} ・ 小 {cb.v("SHA-S-RESPAWN", unit="秒", show=dur)}',
            f'小: 壊れて {cb.c(s_react, ["SHA-S-REACT", "SHA-S-REACT-RULE"], show=dur, suffix="後")}に予告（{cb.t("SHA-S-REACT-RULE")}）',
            cb.t("SHA-ICE-BH"),
            cb.t("COM-MATCH-DRAW"),
        ]) + flow,
        badge=cb.badge(),
    )
    return ice + timing


# ---------------------------------------------------------------- オンサル・ハカイル（終節戦）


def naadam(d: Data, prefix: str) -> str:
    total = match_seconds(d)
    ids = [f"NAA-OVOO-{k}-{x}" for k in "BAS" for x in ("TOTAL", "TICK")] + ["NAA-OVOO-TICK-SEC", "NAA-CLAIM-DURATION"]
    cr = Card(d, ids)
    iv = d.num("NAA-OVOO-TICK-SEC", "秒")
    tiles = []
    for k in "BAS":
        tot, tk = f"NAA-OVOO-{k}-TOTAL", f"NAA-OVOO-{k}-TICK"
        k_v = d.num(tk, "戦略値/回")
        tiles.append({
            "rank": k, "total": cr.v(tot, unit="戦略値"), "unit": "戦略値",
            "lines": [
                (f'{cr.c(k_v * 60 / iv, [tk, "NAA-OVOO-TICK-SEC"], suffix="/分")}'
                f'<small>（{cr.v(tk, unit="戦略値/回")}/{cr.v("NAA-OVOO-TICK-SEC", unit="秒", suffix="秒毎")}）</small>'),
                f'契約 {cr.v("NAA-CLAIM-DURATION", unit="秒", suffix="秒間")}',
            ],
        })
    lands = card("無垢の土地", rank_tiles(d, ["NAA-RANK-SYMBOL"], tiles), sub=cr.t("NAA-OVOO-RECIPIENT"), badge=cr.badge())

    caps = [f"NAA-CAP-{i}" for i in range(1, 5)]
    sw_ids = [f"NAA-CAP-SWITCH-{i}" for i in range(1, 4)]
    sws = [round(d.num(s, MIN_LEFT) * 60) for s in sw_ids]
    edges = [total] + sws + [0]
    cb = Card(d, caps + sw_ids + ["NAA-SPAWN-FIRST", "NAA-WARN-SEC", "NAA-CLAIM-CAST", "NAA-CLAIM-MULTI",
                                  "NAA-NOREPEAT", "NAA-SPAWN-REFILL"])
    first = total - (d.num("NAA-SPAWN-FIRST", "秒") + d.num("NAA-WARN-SEC", "秒"))
    bandhtml = band(
        d,
        segments=[(f'上限 {seg_cap(cb, c, sw_ids[:i][-1:] + sw_ids[i:i + 1], "個")}', edges[i], edges[i + 1])
                  for i, c in enumerate(caps)],
        marks=[(f'最初に契約できる {cb.c(first, ["COM-MATCH-TIME", "NAA-SPAWN-FIRST", "NAA-WARN-SEC"], show=mmss)}', first)],
    )
    timing = card(
        "同時に出る無垢の土地の数の上限（残り時間）",
        bandhtml + chips([
            f'予告の {cb.v("NAA-WARN-SEC", unit="秒", suffix="秒後")}に契約できる',
            f'契約に {cb.v("NAA-CLAIM-CAST", unit="秒", suffix="秒")}（{cb.t("NAA-CLAIM-MULTI")}）',
            cb.t("NAA-SPAWN-REFILL"),
            cb.t("NAA-NOREPEAT"),
        ]),
        badge=cb.badge(),
    )

    co = Card(d, ["NAA-CLAIM-INTERRUPT", "NAA-CLAIM-LOCK", "NAA-RANK-CENTER", "NAA-TIME-TREND", "NAA-STATE-WARN",
                  "NAA-WARN-NOTICE", "NAA-CLAIM-LOOK", "NAA-CLAIM-GUARDIAN"])
    rules = card(
        "契約のしかた",
        bullets([co.t("NAA-WARN-NOTICE"), co.t("NAA-STATE-WARN"), co.t("NAA-CLAIM-INTERRUPT"), co.t("NAA-CLAIM-LOCK"),
                 co.t("NAA-CLAIM-LOOK"), co.t("NAA-RANK-CENTER"), co.t("NAA-TIME-TREND"), co.t("NAA-CLAIM-GUARDIAN")]),
        badge=co.badge(),
    )
    return lands + timing + rules


# ---------------------------------------------------------------- ウォーコー・チーテ（演習戦）


def triumph(d: Data, prefix: str) -> str:
    total = match_seconds(d)
    ids = [f"TRI-OBJ-{k}-TOTAL" for k in "BAS"] + [f"TRI-CIRCLE-{k}" for k in "BAS"] + ["TRI-CLAIM-DURATION"]
    rule_ids = ["TRI-CLAIM-CONDITION", "TRI-CIRCLE-SEC", "TRI-CIRCLE-HEADCOUNT", "TRI-CIRCLE-CONTEST",
                "TRI-CIRCLE-RESET", "TRI-CIRCLE-OVERWRITE", "TRI-CIRCLE-KEEP", "TRI-CLAIM-LOCK", "TRI-CIRCLE-DEFEND",
                "TRI-ACTIVATING-SEC", "TRI-SPAWN-OPEN-COUNT"]
    cr = Card(d, ids + rule_ids)  # 目標地の点数と制圧のしかたを1枚にまとめる（等級の基準も1つ）
    dur_s = d.num("TRI-CLAIM-DURATION", "秒")
    tiles = []
    for k in "BAS":
        tot = f"TRI-OBJ-{k}-TOTAL"
        t_v = d.num(tot, "戦略値")
        tiles.append({
            "rank": k, "total": cr.v(tot, unit="戦略値"), "unit": "戦略値",
            "lines": [
                f'戦略サークル {cr.v(f"TRI-CIRCLE-{k}", unit="か所", suffix="か所")}',
                (f'{cr.c(t_v * 60 / dur_s, [tot, "TRI-CLAIM-DURATION"], suffix="/分")}'
                f'<small>（{cr.v("TRI-CLAIM-DURATION", unit="秒", suffix="秒間")}）</small>'),
            ],
        })
    rules_html = bullets([
        (f'記号が出て {cr.v("TRI-ACTIVATING-SEC", unit="秒", suffix="秒後")}に制圧できる'
        f'（開幕 {cr.v("TRI-SPAWN-OPEN-COUNT", unit="か所", suffix="か所")}）'),
        f'サークル1つに {cr.v("TRI-CIRCLE-SEC", unit="秒", suffix="秒")}（{cr.t("TRI-CIRCLE-HEADCOUNT")}）',
        cr.t("TRI-CLAIM-CONDITION"),
        f'{cr.t("TRI-CIRCLE-CONTEST")}・{cr.t("TRI-CIRCLE-DEFEND")}',
        cr.t("TRI-CIRCLE-RESET"),
        cr.t("TRI-CIRCLE-OVERWRITE"),
        cr.t("TRI-CIRCLE-KEEP"),
        cr.t("TRI-CLAIM-LOCK"),
    ])
    objs = card("戦略目標地と制圧のしかた", rank_tiles(d, ["TRI-RANK-SHAPE"], tiles) + rules_html,
                sub=cr.t("TRI-OBJ-RECIPIENT"), badge=cr.badge())

    caps = [f"TRI-CAP-{i}" for i in range(1, 5)]
    sw_ids = [f"TRI-CAP-SWITCH-{i}" for i in range(1, 4)]
    sws = [round(d.num(s, MIN_LEFT) * 60) for s in sw_ids]
    edges = [total] + sws + [0]
    s_a, s_z = (round(x * 60) for x in d.span("TRI-WX-SNOW-START", MIN_LEFT))
    a_a, a_z = (round(x * 60) for x in d.span("TRI-WX-AURORA-START", MIN_LEFT))
    snow_len, aurora_len = d.num("TRI-WX-SNOW-SEC", "秒"), d.num("TRI-WX-AURORA-SEC", "秒")
    wx_ids = ["TRI-WX-SNOW-START", "TRI-WX-SNOW-SEC", "TRI-WX-AURORA-START", "TRI-WX-AURORA-SEC",
              "TRI-SNOW-BARRIER-PCT", "TRI-SNOW-BARRIER-SEC", "TRI-SNOW-BLESS-INTERVAL", "TRI-SNOW-STATUE-CENTER", "TRI-SNOW-BLESS-TIMING",
              "TRI-AURORA-LB-RATE", "TRI-AURORA-LB-STACK", "TRI-AURORA-NO-B", "TRI-AURORA-HIGHRANK"]
    cb = Card(d, caps + sw_ids + wx_ids)

    def win(rid: str) -> str:
        a, z = d.span(rid, MIN_LEFT)
        return cb.raw(rid, f"{mmss(a * 60)}〜{mmss(z * 60)}", unit=MIN_LEFT)

    bandhtml = band(
        d,
        segments=[(f'上限 {seg_cap(cb, c, sw_ids[:i][-1:] + sw_ids[i:i + 1], "か所")}', edges[i], edges[i + 1])
                  for i, c in enumerate(caps)],
        weather=[
            ("snow", s_a, s_z - snow_len, f'最初の雪 {cb.v("TRI-WX-SNOW-SEC", unit="秒", show=dur, suffix="間")}', s_z),
            ("aurora", a_a, a_z - aurora_len, f'オーロラ {cb.v("TRI-WX-AURORA-SEC", unit="秒", show=dur, suffix="間")}', a_z),
        ],
    )
    effects = (
        '<div class="wxfx">'
        f'<div class="fx snow"><svg class="ill" role="img" aria-label="雪"><title>雪</title><use href="#i-snow"/></svg><div>'
        f'<div class="hd">最初の雪 <small>残り {win("TRI-WX-SNOW-START")} に始まる</small></div>'
        f'<div class="ln">雪精の祝福: 最大HPの {cb.v("TRI-SNOW-BARRIER-PCT", unit="%（最大HPに対して）", suffix="%")} のバリア'
        f'（{cb.v("TRI-SNOW-BARRIER-SEC", unit="秒", suffix="秒間")}）</div>'
        f'<div class="ln">約{cb.v("TRI-SNOW-BLESS-INTERVAL", unit="秒", suffix="秒")}ごと・{cb.t("TRI-SNOW-BLESS-TIMING")}</div>'
        f'<div class="ln">{cb.t("TRI-SNOW-STATUE-CENTER")}</div></div></div>'
        f'<div class="fx aurora"><svg class="ill" role="img" aria-label="オーロラ"><title>オーロラ</title><use href="#i-aurora"/></svg><div>'
        f'<div class="hd">最初のオーロラ <small>残り {win("TRI-WX-AURORA-START")} に始まる</small></div>'
        f'<div class="ln">リミットゲージ {cb.v("TRI-AURORA-LB-RATE", unit="倍（通常時の速さに対して）", show=times)}</div>'
        f'<div class="ln">{cb.t("TRI-AURORA-LB-STACK")}</div>'
        f'<div class="ln">{cb.t("TRI-AURORA-NO-B")}・{cb.t("TRI-AURORA-HIGHRANK")}</div></div></div>'
        "</div>"
    )
    timing = card("同時に出る戦略目標地の数の上限と天候（残り時間）", bandhtml + effects, sub="天候の帯は、薄い部分が始まりうる時間帯",
                  badge=cb.badge())
    return objs + timing


SPECS = {
    "secure": {"timeout": "COM-MATCH-TIMEOUT", "goal": "SEC-WIN-TARGET", "ko": ("SEC-KO-GAIN", "SEC-KO-LOSS"), "blocks": secure},
    "seize": {"timeout": "COM-MATCH-TIMEOUT", "goal": "SEI-GOAL", "ko": ("SEI-KO-GAIN", "SEI-KO-LOSS"), "blocks": seize},
    "shatter": {"timeout": "COM-MATCH-TIMEOUT", "goal": "SHA-WIN-TARGET", "ko": ("SHA-KO-GAIN", "SHA-DEATH-LOSS"), "blocks": shatter},
    "naadam": {"timeout": "COM-MATCH-TIMEOUT", "goal": "NAA-GOAL", "ko": ("NAA-KO-GAIN", "NAA-KO-LOSS"), "blocks": naadam},
    "triumph": {"timeout": "TRI-TIMEOUT", "goal": "TRI-GOAL", "ko": ("TRI-KO-GAIN", "TRI-KO-LOSS"), "blocks": triumph},
}
