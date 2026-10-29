"""値台帳から公開ページ（frontline/ の下）を生成する。

使い方:
    python frontline/tools/build.py           # ページを生成する
    python frontline/tools/build.py --check   # 生成物が台帳と合っているかだけ確かめる（違えば終了コード 1）

生成するもの:
    frontline/index.html            トップ（今日のルールを表示。5ルール分を内包し、タブで切り替える）
    frontline/<rule>/index.html     ルール別のページ（secure / seize / shatter / naadam / triumph）
    frontline/jobs/index.html       ジョブ補正の一覧（自分のジョブを選ぶ）
    frontline/sources/index.html    ページに出している値の出典の一覧

守ること（frontline-maintenance スキル、リポジトリの AGENTS.md 規約1）:
- 値は値台帳（frontline/data/ledger/*.md）からだけ取る。採否が ○ の行しか使えない。× や空欄の行を参照すると止まる。
- 派生値（1分あたり・合計・残り時間・LB の秒数など）はここで計算する。ページに数を手で書かない。
- 数を出す要素には data-src（元の行 ID を空白区切り）を付ける。tests/frontline がこれで全数字の出どころを確かめる。
- 文章の値は、台帳の「表示文」（短い言い方）があればそれを、なければ値をそのまま出す。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger

FRONT = ledger.ROOT  # frontline/
ASSETS = FRONT / "assets"
RULE_ORDER = ["secure", "seize", "shatter", "naadam", "triumph"]
CANVAS_W, CANVAS_H = 1920, 912  # 最大化したブラウザの表示領域（1920×945 前後）に合わせた固定キャンバス

GRADE_ICON = {"外部": "g-ext", "実測": "g-obs", "計算": "g-calc", "未確認": "g-unk"}
GRADE_TITLE = {
    "外部": "外部資料（独立した複数の資料が一致）",
    "実測": "ゲーム内で確認",
    "計算": "台帳の値から計算",
    "未確認": "未確認（資料が少ない）",
}
GRADE_RANK = {"公式": 0, "計算": 1, "実測": 2, "外部": 3, "未確認": 4}
MINUS = "−"
# 2026-10-29 ユーザーの指示: 等級（公式・外部・実測・計算・未確認）は台帳にだけ残し、ページには印も凡例も出さない
# （情報のノイズになるため。間違いは指摘を受けたら直す）。出すときは True にする
SHOW_GRADES = False
README_URL = "https://github.com/Idios/kobutachan-ffxiv-research/blob/main/frontline/README.md"


class BuildError(Exception):
    """台帳の行が使えない（ない・○でない・数でない・単位が違う）。"""


# ---------------------------------------------------------------- 台帳へのアクセス


class Data:
    """値台帳の ○ の行だけを返す窓口。使った行 ID を記録する（出典一覧と検査に使う）。"""

    def __init__(self, ledgers: list[ledger.Ledger], sources: dict[str, dict[str, str]]):
        self.rows = {r.id: r for led in ledgers for r in led.rows}
        self.sources = sources
        self.used: set[str] = set()

    def row(self, rid: str) -> ledger.Row:
        r = self.rows.get(rid)
        if r is None:
            raise BuildError(f"台帳に行がない: {rid}")
        if r.verdict != "○":
            raise BuildError(f"{rid} は採否が {r.verdict or '空欄'}。○ の行しかページに出せない")
        self.used.add(rid)
        return r

    def has(self, rid: str) -> bool:
        """行があって ○ か（任意の表示に使う。使うときは row/num を通す）。"""
        r = self.rows.get(rid)
        return r is not None and r.verdict == "○"

    def num(self, rid: str, unit: str | None = None) -> float:
        r = self.row(rid)
        if unit is not None and r.unit != unit:
            raise BuildError(f"{rid} の単位が {r.unit!r}（ページは {unit!r} の前提）。表示を見直す")
        s = r.value.replace(",", "").replace(MINUS, "-").replace("＋", "+")
        if not re.fullmatch(r"[+-]?\d+(\.\d+)?", s):
            raise BuildError(f"{rid} の値 {r.value!r} は数でない")
        return float(s)

    def clock(self, rid: str, unit: str) -> int:
        """「19:30」（分:秒）を秒にする。"""
        r = self.row(rid)
        if r.unit != unit:
            raise BuildError(f"{rid} の単位が {r.unit!r}（ページは {unit!r} の前提）。表示を見直す")
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", r.value)
        if not m:
            raise BuildError(f"{rid} の値 {r.value!r} は 分:秒 でない")
        return int(m.group(1)) * 60 + int(m.group(2))

    def span(self, rid: str, unit: str | None = None) -> tuple[float, float]:
        """「16〜15」のような範囲を (16, 15) にする。範囲でなければ同じ値を2つ返す。"""
        r = self.row(rid)
        if unit is not None and r.unit != unit:
            raise BuildError(f"{rid} の単位が {r.unit!r}（ページは {unit!r} の前提）。表示を見直す")
        parts = [p for p in re.split(r"[〜~～]", r.value) if p.strip()]
        try:
            vals = [float(p) for p in parts]
        except ValueError as exc:
            raise BuildError(f"{rid} の値 {r.value!r} は範囲でない") from exc
        if not 1 <= len(vals) <= 2:
            raise BuildError(f"{rid} の値 {r.value!r} は範囲でない")
        if "残り" in r.unit and vals[0] < vals[-1]:
            raise BuildError(f"{rid} の値 {r.value!r} は残り時間なので、早い（大きい）ほうを先に書く")
        return vals[0], vals[-1]

    def text(self, rid: str) -> str:
        r = self.row(rid)
        return r.display or r.value

    def grade(self, rid: str) -> str:
        return self.row(rid).grade


# ---------------------------------------------------------------- 書式


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def fmt(x: float) -> str:
    """桁区切り。小数は2桁まで（末尾の0は落とす）。"""
    if abs(x - round(x)) < 1e-9:
        return f"{round(x):,}"
    return f"{x:,.2f}".rstrip("0").rstrip(".")


def fmt1(x: float) -> str:
    """小数1桁（10万HPあたりなどの目安値）。"""
    return f"{x:,.1f}".rstrip("0").rstrip(".")


def signed(x: float) -> str:
    if x > 0:
        return f"+{fmt(x)}"
    if x < 0:
        return f"{MINUS}{fmt(abs(x))}"
    return "0"


def mmss(sec: float) -> str:
    s = round(sec)
    return f"{s // 60}:{s % 60:02d}"


def worst(grades: Iterable[str]) -> str:
    return max(grades, key=lambda g: GRADE_RANK.get(g, 4))


def icon(grade: str) -> str:
    if grade not in GRADE_ICON:
        return ""
    t = esc(GRADE_TITLE[grade])
    return f'<svg class="g" role="img" aria-label="{t}"><title>{t}</title><use href="#{GRADE_ICON[grade]}"/></svg>'


# ---------------------------------------------------------------- カード（基準の等級つき）


class Card:
    """1枚のカード。見出しに付ける基準の等級を持つ。

    基準と違う等級の値には、その等級の印を付ける（公式には印がないので、基準が公式でないカードの公式の値は無印になる。
    凡例は「見出しに印があるカードの無印の値は、その等級以上」）。
    基準は「印の数＋公式なのに無印になる値の数×2」が最小の等級（同点なら確かなほう）。未確認は基準にしない。
    base を渡すとその等級に固定する（列の見出しに印を付ける表など）。
    """

    def __init__(self, d: Data, rids: Iterable[str], base: str | None = None):
        self.d = d
        if base is not None:
            self.base = base
            return
        grades = [d.grade(r) for r in rids]
        if not grades:
            self.base = "公式"
            return

        def cost(b: str) -> tuple[int, int]:
            marks = sum(1 for g in grades if g != b and g != "公式")
            hidden = sum(1 for g in grades if g == "公式" and b != "公式")
            return marks + 2 * hidden, GRADE_RANK[b]

        # 未確認は基準にしない（⚠ は必ず値の横に付く。計画のアンチゴール「未確認の値が公式と見分けがつかない」）
        self.base = min((set(grades) | {"公式"}) - {"未確認"}, key=cost)

    def _mark(self, grade: str) -> str:
        if not SHOW_GRADES:
            return ""
        return icon(grade) if grade != self.base else ""

    def v(
        self,
        rid: str,
        *,
        unit: str,
        show: Callable[[float], str] = fmt,
        suffix: str = "",
        cls: str = "v",
    ) -> str:
        """数の値。"""
        x = self.d.num(rid, unit)
        return self.wrap(show(x) + suffix, [rid], self.d.grade(rid), cls)

    def raw(self, rid: str, shown: str, *, unit: str, cls: str = "v") -> str:
        """値を整形済みの文字で出す（分:秒・範囲など）。単位を照合する。"""
        r = self.d.row(rid)
        if r.unit != unit:
            raise BuildError(f"{rid} の単位が {r.unit!r}（ページは {unit!r} の前提）。表示を見直す")
        return self.wrap(shown, [rid], self.d.grade(rid), cls)

    def c(self, x: float, rids: list[str], *, show: Callable[[float], str] = fmt, suffix: str = "", cls: str = "v") -> str:
        """派生値（台帳の値から計算）。等級は材料の最悪値。材料がすべて公式なら「計算」。

        材料が1行だけなら、それは単位や書き方の換算なので v(show=...) を使う（計算の印を付けない）。
        """
        if len(rids) < 2:
            raise BuildError(f"{rids}: 1行だけの換算は v(show=...) で出す（計算の印を付けない）")
        g = worst(self.d.grade(r) for r in rids)
        return self.wrap(show(x) + suffix, rids, "計算" if g == "公式" else g, cls + " calc")

    def t(self, rid: str, *, cls: str = "t") -> str:
        """文章の値（表示文があればそれ）。"""
        return self.wrap(self.d.text(rid), [rid], self.d.grade(rid), cls)

    def wrap(self, shown: str, rids: list[str], grade: str, cls: str) -> str:
        return f'<span class="{cls}" data-src="{esc(" ".join(rids))}">{esc(shown)}{self._mark(grade)}</span>'

    def badge(self) -> str:
        """見出しに付ける基準の等級の印（公式なら無印）。"""
        return icon(self.base) if SHOW_GRADES else ""


def card(title: str, body: str, *, sub: str = "", cls: str = "", head_icon: str = "", badge: str = "") -> str:
    sub_html = f'<span class="sub">{sub}</span>' if sub else ""
    return (
        f'<section class="card {cls}"><h2>{head_icon}<span class="ttl">{esc(title)}</span>{badge}{sub_html}</h2>'
        f"{body}</section>"
    )


def chips(items: list[str], cls: str = "") -> str:
    if not items:
        return ""
    return f'<div class="chips {cls}">' + "".join(f'<span class="chip">{c}</span>' for c in items) + "</div>"


def bullets(items: list[str], cols: int = 2) -> str:
    lis = "".join(f"<li>{x}</li>" for x in items)
    return f'<ul class="rules c{cols}">{lis}</ul>'


def svg_use(sym: str, cls: str, label: str) -> str:
    return f'<svg class="{cls}" role="img" aria-label="{esc(label)}"><title>{esc(label)}</title><use href="#{sym}"/></svg>'


def rank_tiles(d: Data, symbol_rows: list[str], items: list[dict]) -> str:
    """ランク別のタイル。items: rank（B/A/S）, total（HTML）, unit, lines（HTML のリスト）。

    図形のアイコン（B＝青の三角形・A＝赤のひし形・S＝黄の五角形）は symbol_rows の行（形と色）の内容を描いたもの。
    どれかが ○ でなければ生成を止める（アイコンの裏付けがなくなるため）。
    """
    for r in symbol_rows:
        d.row(r)
    srcs = " ".join(symbol_rows)
    out = []
    for it in items:
        lines = "".join(f'<div class="ln">{x}</div>' for x in it["lines"])
        shape = svg_use("r-" + it["rank"], "shape", "ランク" + it["rank"]).replace("<svg ", f'<svg data-src="{srcs}" ', 1)
        out.append(
            f'<div class="rk rk-{it["rank"]}">{shape}'
            f'<div class="tot">{it["total"]}<small>{esc(it["unit"])}</small>'
            + (f'<span class="ex">{it["extra"]}</span>' if it.get("extra") else "")
            + f"</div>{lines}</div>"
        )
    return f'<div class="ranks">{"".join(out)}</div>'


def event_tiles(items: list[dict], cls: str = "") -> str:
    """イラストつきのタイル。items: svg, name, note（HTML）, big（HTML）, lines（HTML のリスト）。"""
    out = []
    for e in items:
        lines = "".join(f'<div class="ln">{x}</div>' for x in e["lines"])
        note = f'<div class="nt">{e["note"]}</div>' if e.get("note") else ""
        out.append(
            f'<div class="ev"><div class="top">{svg_use(e["svg"], "ill", e["name"])}<div class="nm">{esc(e["name"])}{note}</div></div>'
            f'<div class="big">{e["big"]}</div>{lines}</div>'
        )
    return f'<div class="events n{len(items)} {cls}">{"".join(out)}</div>'


def band(d: Data, *, segments: list[tuple[str, int, int]] = (), marks: list[tuple[str, int]] = (),
         weather: list[tuple[str, int, int, str, int]] = (), whole: str = "") -> str:
    """残り時間（20:00 → 0:00）の帯。segments: (ラベル, 開始の残り秒, 終了の残り秒)。marks: (ラベル, 残り秒)。

    weather: (種類, 最も早い開始の残り秒, 最も遅い終了の残り秒, ラベル, 最も遅い開始の残り秒)。
    始まりうる時間帯は薄く描く。印のラベルと天候は帯の上の段に出す（同時には使わない）。
    目盛りは5分ごと（試合時間は台帳の COM-MATCH-TIME）。
    """
    if marks and weather:
        raise BuildError("帯の上の段は、印か天候のどちらか一方にする")
    total = round(d.num("COM-MATCH-TIME", "分") * 60)

    def x(rem: float) -> float:
        return 100 * (total - rem) / total

    segs = "".join(
        f'<div class="seg" style="flex:{a - z}">{lab}</div>' for lab, a, z in segments
    ) or f'<div class="seg" style="flex:1">{whole}</div>'
    wx = []
    for k, a, z, lab, latest in weather:
        light = 100 * (a - latest) / (a - z) if a > z else 0  # 帯のうち、始まりうる時間帯の割合
        wx.append(f'<div class="wx {k}" style="left:{x(a):.2f}%;width:{x(z) - x(a):.2f}%;--start:{light:.1f}%">{lab}</div>')
    wx = "".join(wx)
    mk = []
    for lab, rem in marks:
        p = x(rem)
        side = " l" if p < 14 else (" r" if p > 86 else "")
        mk.append(f'<div class="mk{side}" style="left:{p:.2f}%"><span>{lab}</span></div>')
    ticks = "".join(
        f'<span style="left:{x(t):.2f}%" data-src="COM-MATCH-TIME">{mmss(t)}</span>' for t in range(total, -1, -300)
    )
    top = " top" if (marks or weather) else ""
    return f'<div class="band{top}">{wx}{"".join(mk)}<div class="track">{segs}</div><div class="ax">{ticks}</div></div>'


# ---------------------------------------------------------------- ルール共通の欄


JOB_GROUPS = [
    ("タンク", "role_tank.png", ["PLD", "WAR", "DRK", "GNB"]),
    ("ヒーラー", "role_healer.png", ["WHM", "SCH", "AST", "SGE"]),
    ("近接物理DPS", "role_melee.png", ["MNK", "DRG", "NIN", "SAM", "RPR", "VPR"]),
    ("遠隔物理DPS", "role_ranged.png", ["BRD", "MCH", "DNC"]),
    ("遠隔魔法DPS", "role_caster.png", ["BLM", "SMN", "RDM", "PCT"]),
]
MYJOB_MAX = 3  # ルールのページに出す自分のジョブの数（画面の都合。ゲームの値ではない）


def job_name(d: Data, code: str) -> str:
    """ジョブ名は補正の行の項目名（「ナイト 与ダメージ補正」）から取る。"""
    return d.row(f"COM-JOB-{code}-DMG").label.split(" ")[0]


def lb_ids(code: str) -> list[str]:
    return ["COM-LBB-SMN-BAHAMUT", "COM-LBB-SMN-PHOENIX"] if code == "SMN" else [f"COM-LBB-{code}"]


def lb_header(d: Data) -> str:
    """LB の列の見出し。秒数は順位の倍率が1のときの値なので、その順位を台帳から探して書く。"""
    for i in (1, 2, 3):
        if d.num(f"COM-LB-RANK{i}", "倍") == 1:
            return (f'<th title="基準の蓄積時間＋ジョブ補正。順位の倍率が1（{i}位）のとき">'
                    f'LB(<span data-src="COM-LB-RANK{i}">{i}位</span>){icon("計算") if SHOW_GRADES else ""}</th>')
    raise BuildError("順位の倍率が1の順位がない。LB の秒数の前提を見直す")


def job_cells(cd: Card, code: str) -> tuple[str, str, str]:
    d = cd.d
    lbc = Card(d, [], base="計算")  # LB の列は見出しに計算の印がある

    def pct(rid: str) -> str:
        x = d.num(rid, "%")
        return cd.v(rid, unit="%", show=lambda v: "0" if v == 0 else signed(v), suffix="%", cls="v" + (" zero" if x == 0 else ""))

    adj_id = f"COM-JOB-{code}-LB"
    adj = d.num(adj_id, "秒")
    secs = list(dict.fromkeys(d.num(b, "秒") + adj for b in lb_ids(code)))  # 台帳の順。同じ秒数は1つにまとめる
    lb = lbc.c(secs[0], lb_ids(code) + [adj_id], suffix="秒") if len(secs) == 1 else "／".join(
        lbc.c(s, lb_ids(code) + [adj_id], suffix="秒") for s in secs
    )
    return pct(f"COM-JOB-{code}-DMG"), pct(f"COM-JOB-{code}-TAKEN"), lb


def common_column(d: Data, prefix: str) -> str:
    # リミットゲージ（順位補正）
    lb_ids_rank = [f"COM-LB-RANK{i}" for i in (1, 2, 3)]
    c1 = Card(d, lb_ids_rank)
    tiles = "".join(
        f'<div class="t"><span class="l" data-src="COM-LB-RANK{i}">{i}位</span>'
        f'{c1.v(f"COM-LB-RANK{i}", unit="倍", show=lambda x: "×" + fmt(x))}</div>'
        for i in (1, 2, 3)
    )
    lb_card = card("リミットゲージ", f'<div class="lbrank">{tiles}</div>', sub=c1.t("COM-LB-RULE"),
                   head_icon=f'<img class="hi" src="{prefix}assets/img/icon_limit_break.png" alt="">', badge=c1.badge())

    # 戦意高揚
    levels = range(1, 6)
    bh_rows = [f"COM-BH-L{i}-EFF" for i in levels] + [f"COM-BH-L{i}-MIN" for i in levels] + [
        f"COM-BHG-{k}-L{i}" for k in ("KO", "AS") for i in range(6)
    ]
    c2 = Card(d, bh_rows)
    roman = ["I", "II", "III", "IV", "V"]
    head = '<th></th><th class="none">なし</th>' + "".join(
        f'<th><img src="{prefix}assets/img/bh{i}.png" alt="戦意高揚{roman[i - 1]}"></th>' for i in levels
    )
    eff = '<th>効果</th><td class="none">—</td>' + "".join(
        f'<td>{c2.v(f"COM-BH-L{i}-EFF", unit="%", show=lambda x: "+" + fmt(x), suffix="%")}</td>' for i in levels
    )
    need = '<th>戦意値</th><td class="none">—</td>' + "".join(
        f'<td>{c2.v(f"COM-BH-L{i}-MIN", unit="戦意値")}</td>' for i in levels
    )
    ko = "<th>撃破</th>" + "".join(f'<td>{c2.v(f"COM-BHG-KO-L{i}", unit="戦意値", show=lambda x: "+" + fmt(x))}</td>' for i in range(6))
    asst = "<th>アシスト</th>" + "".join(
        f'<td>{c2.v(f"COM-BHG-AS-L{i}", unit="戦意値", show=lambda x: "+" + fmt(x))}</td>' for i in range(6)
    )
    sep = '<tr class="sep"><td colspan="7">倒した相手の段階で、得る戦意値が決まる</td></tr>'
    bh_table = (
        f'<table class="bh"><tr>{head}</tr><tr class="eff">{eff}</tr><tr>{need}</tr>{sep}<tr>{ko}</tr><tr>{asst}</tr></table>'
    )
    bh_card = card(
        "戦意高揚",
        bh_table,
        sub=f'戦闘不能: {c2.t("COM-BH-DEATH")}',
        badge=c2.badge(),
    )

    # 自分のジョブ（選んだジョブだけ表示。選ぶまでは選択欄を出す）
    all_codes = [c for _, _, codes in JOB_GROUPS for c in codes]
    jrows = [f"COM-JOB-{c}-{k}" for c in all_codes for k in ("DMG", "TAKEN", "LB")]
    c3 = Card(d, jrows)
    picks = "".join(
        f'<button type="button" class="pick" data-pick="{c}" title="{esc(job_name(d, c))}">'
        f'<img src="{prefix}assets/img/job_{c}.png" alt="{esc(job_name(d, c))}"></button>'
        for c in all_codes
    )
    rows_html = []
    for code in all_codes:
        dmg, taken, lb = job_cells(c3, code)
        rows_html.append(
            f'<tr data-job="{code}" hidden><td class="jn"><img src="{prefix}assets/img/job_{code}.png" alt="">{esc(job_name(d, code))}</td>'
            f"<td>{dmg}</td><td>{taken}</td><td>{lb}</td></tr>"
        )
    empty = (f'<tr class="empty"><td colspan="4">ジョブを押すと、ここに補正が出ます'
             f'（<span data-ui="{MYJOB_MAX}">{MYJOB_MAX}</span>つまで）</td></tr>')
    jobs_body = (
        f'<div class="picker">{picks}</div>'
        f'<table class="mine"><tr><th></th><th>与ダメ</th><th>被ダメ</th>{lb_header(d)}</tr>{empty}{"".join(rows_html)}</table>'
    )
    job_card = card(
        "ジョブ補正",
        jobs_body,
        sub=f'<a class="more" href="{prefix}jobs/">一覧</a>',
        cls="myjobs",
        badge=c3.badge(),
    )
    return lb_card + bh_card + job_card


# ---------------------------------------------------------------- ページの組み立て


def rule_names(rule: str) -> tuple[str, str]:
    """「外縁遺跡群（制圧戦）」を (外縁遺跡群, 制圧戦) にする（ledger.RULES の名前から）。"""
    full = ledger.RULES[rule][1]
    m = re.fullmatch(r"(.+)（(.+)）", full)
    if not m:
        raise BuildError(f"ルール名 {full!r} の形が想定と違う")
    return m.group(1), m.group(2)


def header(d: Data, rule: str, spec: dict, prefix: str) -> str:
    name, sub = rule_names(rule)
    c = Card(d, [], base="公式")  # ヘッダには見出しの印がないので、公式でない値には必ず印を付ける
    goal_row = d.row(spec["goal"])
    unit = goal_row.unit
    if d.num(spec["ko"][0], unit) <= 0 or d.num(spec["ko"][1], unit) >= 0:
        raise BuildError(f"{spec['ko']}: 撃破は正、被撃破は負の数で書く")
    ko_gain = c.v(spec["ko"][0], unit=unit, show=signed)
    ko_loss = c.v(spec["ko"][1], unit=unit, show=signed)
    return (
        f'<header class="hdr"><div class="title"><img class="badge" src="{prefix}assets/img/hdr_{rule}.png" alt="">'
        f'<h1>{esc(name)}<small>{esc(sub)}</small></h1><span class="today" data-today-badge="{rule}" hidden>今日</span></div>'
        f'<div class="goal">{c.v(spec["goal"], unit=unit, cls="v gnum")}<span class="gcap">{esc(goal_row.unit)}で勝利{c.t(spec["timeout"], cls="t to")}</span></div>'
        f'<div class="ko"><div class="k"><span class="l">撃破</span><span class="kv">{ko_gain}<small>{esc(unit)}</small></span></div>'
        f'<div class="k"><span class="l">被撃破</span><span class="kv">{ko_loss}<small>{esc(unit)}</small></span></div></div>'
        f"{nav(d, rule, prefix)}</header>"
    )


def nav(d: Data, current: str, prefix: str) -> str:
    tabs = "".join(
        f'<a data-go="{r}" class="{"on" if r == current else ""}" href="{prefix}{r}/">{esc(rule_names(r)[1])}</a>' for r in RULE_ORDER
    )
    patch = d.row("COM-META-PATCH").value
    return (
        f'<div class="navbox"><nav class="nav">{tabs}</nav>'
        f'<div class="meta"><a href="{prefix}jobs/" class="{"on" if current == "jobs" else ""}">ジョブ補正</a>'
        f'<a href="{prefix}sources/" class="{"on" if current == "sources" else ""}">出典</a>'
        f'<span>データ <span data-src="COM-META-PATCH">{esc(patch)}</span> 時点</span></div></div>'
    )


FETCHED_MARK = "__FETCHED__"  # build() の最後に、使った出典の取得日の範囲で置き換える


def fetched_range(d: Data) -> str:
    """ページで使った行の出典の取得日の範囲（例: 2026-10-27〜10-29）。"""
    sids = {s for rid in d.used for s in d.rows[rid].sources}
    days = sorted({m for sid in sids for m in re.findall(r"\d{4}-\d{2}-\d{2}", d.sources.get(sid, {}).get("取得日", ""))})
    if not days:
        return "不明"
    return days[0] if days[0] == days[-1] else f"{days[0]}〜{days[-1][5:]}"


def footer(d: Data) -> str:
    """© SQUARE ENIX（公式の画像・情報を使う条件。著作物利用条件 3-1）と、README（権利・出典・使い方）へのリンク。"""
    return (
        '<footer class="ftr"><span>© SQUARE ENIX</span>'
        f'<span class="right"><a href="{README_URL}" rel="noopener">このサイトについて（権利・出典）</a>'
        f' ・ 確認 <span data-src="sources.md">{FETCHED_MARK}</span></span></footer>'
    )


SVG_DEFS_PATH = ASSETS / "icons.svg"

JS = """<script>
(function () {
  var W = __W__, H = __H__, st = document.getElementById('stage');
  function fit() {
    var s = Math.min(innerWidth / W, innerHeight / H);
    st.style.transform = 'scale(' + s + ')';
    st.style.left = Math.max(0, (innerWidth - W * s) / 2) + 'px';
    document.documentElement.style.setProperty('--scale', s);
  }
  addEventListener('resize', fit); fit();
  var CYCLE = __CYCLE__, ANCHOR = __ANCHOR__, ANCHOR_RULE = __ANCHOR_RULE__;
  function todayRule() {
    // 切替は毎日 0:00 JST（= 15:00 UTC）。閲覧者の時間帯によらず JST の日付で数える
    var day = Math.floor((Date.now() + 9 * 3600 * 1000) / 86400000);
    var a = Math.floor(Date.UTC(ANCHOR[0], ANCHOR[1] - 1, ANCHOR[2]) / 86400000);
    var n = CYCLE.length, base = CYCLE.indexOf(ANCHOR_RULE);
    return CYCLE[((base + day - a) % n + n) % n];
  }
  var panels = document.querySelectorAll('.panel[data-rule]');
  function show(rule) { panels.forEach(function (p) { p.hidden = p.dataset.rule !== rule; }); }
  var today = todayRule();
  document.querySelectorAll('[data-today-badge]').forEach(function (b) { b.hidden = b.dataset.todayBadge !== today; });
  document.querySelectorAll('.nav a').forEach(function (a) {
    if (a.dataset.go === today) { var d = document.createElement('span'); d.className = 'dot'; d.title = '今日'; a.appendChild(d); }
    if (panels.length > 1) a.addEventListener('click', function (e) { e.preventDefault(); show(a.dataset.go); });
  });
  if (panels.length > 1) {
    var has = Array.prototype.some.call(panels, function (p) { return p.dataset.rule === today; });
    show(has ? today : panels[0].dataset.rule);
  }
  var KEY = 'fl-myjobs', MAX = __MAX__, mem = null;
  var KNOWN = Array.prototype.map.call(document.querySelectorAll('[data-pick]'), function (b) { return b.dataset.pick; });
  if (!KNOWN.length) KNOWN = Array.prototype.map.call(document.querySelectorAll('tr[data-job]'), function (t) { return t.dataset.job; });
  function clean(a) {
    var out = [];
    (Array.isArray(a) ? a : []).forEach(function (x) { if (KNOWN.indexOf(x) >= 0 && out.indexOf(x) < 0) out.push(x); });
    return out.slice(-MAX);
  }
  function load() {
    if (mem) return mem.slice();
    try { return clean(JSON.parse(localStorage.getItem(KEY) || '[]')); } catch (e) { mem = []; return []; }
  }
  function save(a) { try { localStorage.setItem(KEY, JSON.stringify(a)); mem = null; } catch (e) { mem = a.slice(); } }
  function toggle(code) {
    var a = load(), i = a.indexOf(code);
    if (i >= 0) a.splice(i, 1); else { a.push(code); while (a.length > MAX) a.shift(); }
    save(a); paint();
  }
  function paint() {
    var a = load();
    document.querySelectorAll('[data-pick]').forEach(function (b) { b.classList.toggle('on', a.indexOf(b.dataset.pick) >= 0); });
    document.querySelectorAll('.myjobs').forEach(function (box) {
      // 選んだ順に並べる
      var tb = box.querySelector('table.mine tbody') || box.querySelector('table.mine');
      a.forEach(function (code) { var tr = box.querySelector('tr[data-job="' + code + '"]'); if (tr) tb.appendChild(tr); });
      box.querySelectorAll('tr[data-job]').forEach(function (tr) { tr.hidden = a.indexOf(tr.dataset.job) < 0; });
      var em = box.querySelector('tr.empty'); if (em) em.hidden = a.length > 0;
    });
    document.querySelectorAll('.jobtable tr[data-job]').forEach(function (tr) { tr.classList.toggle('me', a.indexOf(tr.dataset.job) >= 0); });
  }
  document.querySelectorAll('[data-pick]').forEach(function (b) { b.addEventListener('click', function () { toggle(b.dataset.pick); }); });
  document.querySelectorAll('.jobtable tr[data-job]').forEach(function (tr) { tr.addEventListener('click', function () { toggle(tr.dataset.job); }); });
  paint();
})();
</script>"""


def rotation(d: Data) -> tuple[list[str], list[int], str]:
    """日替わりの周期・起点の日・起点のルールを台帳から取る。"""
    by_name = {rule_names(r)[0]: r for r in RULE_ORDER}
    order = d.row("COM-ROT-ORDER").value
    cycle = []
    for part in re.split(r"→", order):
        p = part.strip()
        if not p or p.startswith("（"):
            continue
        name = re.sub(r"[（(].*$", "", p).strip()
        if name not in by_name:
            raise BuildError(f"COM-ROT-ORDER のルール名 {name!r} が分からない")
        cycle.append(by_name[name])
    anchor = [int(x) for x in d.row("COM-ROT-ANCHOR").value.split("-")]
    m0 = re.search(r"（(.+?)が開催された日）", d.row("COM-ROT-ANCHOR").label)
    if m0 and m0.group(1) in by_name and cycle.count(by_name[m0.group(1)]) != 1:
        raise BuildError("起点のルールが周期の中に1回だけでない。COM-ROT-ANCHOR の起点を選び直す")
    m = re.search(r"（(.+?)が開催された日）", d.row("COM-ROT-ANCHOR").label)
    if not m or m.group(1) not in by_name:
        raise BuildError("COM-ROT-ANCHOR の項目名から起点のルールが読めない")
    return cycle, anchor, by_name[m.group(1)]


def page(d: Data, title: str, panels_html: str, prefix: str, *, extra_cls: str = "") -> str:
    cycle, anchor, anchor_rule = rotation(d)
    js = (
        JS.replace("__W__", str(CANVAS_W)).replace("__H__", str(CANVAS_H))
        .replace("__CYCLE__", json.dumps(cycle)).replace("__ANCHOR__", json.dumps(anchor))
        .replace("__ANCHOR_RULE__", json.dumps(anchor_rule)).replace("__MAX__", str(MYJOB_MAX))
    )
    svg = SVG_DEFS_PATH.read_text(encoding="utf-8")
    return (
        '<!doctype html>\n<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        f'<title>{esc(title)}</title><link rel="stylesheet" href="{prefix}assets/site.css"></head>'
        f'<body class="{extra_cls}">{svg}<div id="stage">{panels_html}</div>{js}</body></html>\n'
    )


def rule_panel(d: Data, rule: str, prefix: str) -> str:
    import pages

    spec = pages.SPECS[rule]
    left = spec["blocks"](d, prefix)
    return (
        f'<div class="panel" data-rule="{rule}">{header(d, rule, spec, prefix)}'
        f'<main class="main"><section class="col rule">{left}</section>'
        f'<section class="col common">{common_column(d, prefix)}</section></main>{footer(d)}</div>'
    )


def jobs_page(d: Data, prefix: str) -> str:
    all_codes = [c for _, _, codes in JOB_GROUPS for c in codes]
    cd = Card(d, [f"COM-JOB-{c}-{k}" for c in all_codes for k in ("DMG", "TAKEN", "LB")])
    tables = []
    for half in (JOB_GROUPS[:2] + [JOB_GROUPS[3]], [JOB_GROUPS[2], JOB_GROUPS[4]]):
        trs = []
        for role, img, codes in half:
            trs.append(f'<tr class="role"><td colspan="5"><img src="{prefix}assets/img/{img}" alt="">{esc(role)}</td></tr>')
            for code in codes:
                dmg, taken, lb = job_cells(cd, code)
                lb_name = "／".join(d.row(b).condition.removeprefix("LB: ") for b in lb_ids(code))
                trs.append(
                    f'<tr data-job="{code}"><td class="jn"><img src="{prefix}assets/img/job_{code}.png" alt="">{esc(job_name(d, code))}</td>'
                    f'<td>{dmg}</td><td>{taken}</td><td>{lb}</td><td class="lbn">{esc(lb_name)}</td></tr>'
                )
        tables.append(
            f'<table class="jobtable"><tr><th>ジョブ</th><th>与ダメ</th><th>被ダメ</th>{lb_header(d)}<th>リミットブレイク</th></tr>{"".join(trs)}</table>'
        )
    body = (
        '<p class="lead">与ダメ・被ダメはフロントラインでのジョブ補正。LB は基準の蓄積時間に補正を足した秒数（順位による倍率は含まない）。'
        f'行を押すと自分のジョブとして記憶し、各ルールのページに出ます（<span data-ui="{MYJOB_MAX}">{MYJOB_MAX}</span>つまで）。</p>'
        f'<div class="jobtables">{"".join(tables)}</div>'
    )
    hdr = (
        f'<header class="hdr"><div class="title"><h1>ジョブ補正<small>フロントライン共通</small></h1></div>'
        f"{nav(d, 'jobs', prefix)}</header>"
    )
    return f'<div class="panel jobs">{hdr}<main class="main one">{body}</main>{footer(d)}</div>'


def sources_page(d: Data, prefix: str) -> str:
    used = sorted({s for rid in d.used for s in d.rows[rid].sources})
    trs = []
    for sid in used:
        s = d.sources.get(sid, {})
        url = s.get("URL", "")
        name = esc(s.get("名称", sid))
        link = f'<a href="{esc(url)}" rel="noopener">{name}</a>' if url.startswith("https://") else name
        trs.append(
            f'<tr><td class="sid">{esc(sid)}</td><td>{esc(s.get("種別", ""))}</td><td>{link}</td>'
            f'<td>{esc(s.get("公開・更新", ""))}</td><td>{esc(s.get("取得日", ""))}</td></tr>'
        )
    body = (
        '<p class="lead">このサイトの値の出典（ページに出している値が使うものだけ）。公式は株式会社スクウェア・エニックスの公表、'
        "外部はファンの資料（数値の出典として引用。文章は写していない）、ゲーム内は管理者のゲーム内確認。</p>"
        f'<div class="srcwrap"><table class="srcs"><tr><th>ID</th><th>種別</th><th>名称</th><th>公開・更新</th><th>取得日</th></tr>{"".join(trs)}</table></div>'
    )
    hdr = (
        f'<header class="hdr"><div class="title"><h1>出典<small>フロントライン早見表</small></h1></div>'
        f"{nav(d, 'sources', prefix)}</header>"
    )
    return f'<div class="panel sources">{hdr}<main class="main one">{body}</main>{footer(d)}</div>'


def build(d: Data) -> dict[Path, str]:
    """生成するファイルの中身を返す（書き込みはしない）。"""
    out: dict[Path, str] = {}
    out[FRONT / "index.html"] = page(
        d, "フロントライン早見表（今日のルール）", "".join(rule_panel(d, r, "") for r in RULE_ORDER), ""
    )
    for r in RULE_ORDER:
        name, sub = rule_names(r)
        out[FRONT / r / "index.html"] = page(d, f"{name}（{sub}）｜フロントライン早見表", rule_panel(d, r, "../"), "../")
    out[FRONT / "jobs" / "index.html"] = page(d, "ジョブ補正｜フロントライン早見表", jobs_page(d, "../"), "../")
    # 出典一覧は最後に作る（ほかのページで使った行の出典を集めるため）
    out[FRONT / "sources" / "index.html"] = page(d, "出典｜フロントライン早見表", sources_page(d, "../"), "../", extra_cls="scroll")
    rng = fetched_range(d)
    return {path: text.replace(FETCHED_MARK, esc(rng)) for path, text in out.items()}


def load() -> Data:
    ledgers, sources, errors = ledger.load_all()
    if errors:
        raise BuildError("台帳の検証エラー:\n" + "\n".join(errors))
    return Data(ledgers, sources)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="生成物が最新かだけを確かめる")
    args = ap.parse_args()
    try:
        files = build(load())
    except BuildError as exc:
        print(f"生成できない: {exc}", file=sys.stderr)
        return 2
    stale = []
    for path, text in files.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    if args.check:
        for p in stale:
            print(f"古い: {p.relative_to(FRONT.parent)}")
        print("生成物は最新" if not stale else f"生成物が台帳と合っていない（{len(stale)} 件）。build.py を実行する")
        return 1 if stale else 0
    print(f"生成: {len(files)} ファイル")
    return 0


if __name__ == "__main__":
    sys.exit(main())
