"""値台帳から公開ページ（frontline/ の下）を生成する。

使い方:
    python frontline/tools/build.py           # ページを生成する
    python frontline/tools/build.py --check   # 生成物が台帳と合っているかだけ確かめる（違えば終了コード 1）

生成するもの:
    frontline/index.html                  入口。ブラウザの言語（選んだ言語があればそれ）の版へ移る
    frontline/<lang>/index.html           トップ（今日のルールを表示。5ルール分を内包し、タブで切り替える）
    frontline/<lang>/<rule>/index.html    ルール別のページ（secure / seize / shatter / naadam / triumph）
    frontline/<lang>/jobs/index.html      ジョブ補正の一覧（自分のジョブを選ぶ）
    frontline/<lang>/sources/index.html   ページに出している値の出典の一覧
    lang は ja / en / de / fr（訳は frontline/data/i18n/）。2026-10-29 まで日本語版があった frontline/<rule>/ などは、
    ja/ の同じページへ移る案内のページにする（公開済みの URL を切らない）

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
import i18n
import ledger
from i18n import F, H, L, U

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
        """文章の値（表示文があればそれ）。日本語以外は訳の表（frontline/data/i18n/text.md）から。"""
        r = self.row(rid)
        return i18n.text(rid, r.display or r.value)

    def grade(self, rid: str) -> str:
        return self.row(rid).grade


# ---------------------------------------------------------------- 書式


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


fmt = i18n.fmt  # 桁区切り。小数は2桁まで（言語ごとの書き方）
fmt1 = i18n.fmt1  # 小数1桁


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
    t = esc(L(GRADE_TITLE[grade]))
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
        return self.wrap(show(x) + U(suffix), [rid], self.d.grade(rid), cls)

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
        return self.wrap(show(x) + U(suffix), rids, "計算" if g == "公式" else g, cls + " calc")

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
        f'<section class="card {cls}"><h2>{head_icon}<span class="ttl">{esc(L(title))}</span>{badge}{sub_html}</h2>'
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
        shape = svg_use("r-" + it["rank"], "shape", F("ランク{0}", it["rank"])).replace("<svg ", f'<svg data-src="{srcs}" ', 1)
        out.append(
            f'<div class="rk rk-{it["rank"]}">{shape}'
            f'<div class="tot">{it["total"]}<small>{esc(L(it["unit"]))}</small>'
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
            f'<div class="ev"><div class="top">{svg_use(e["svg"], "ill", L(e["name"]))}<div class="nm">{esc(L(e["name"]))}{note}</div></div>'
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
    """ジョブ名は補正の行の項目名（「ナイト 与ダメージ補正」）から取る。日本語以外は用語の表（公式の表記）。"""
    return L(d.row(f"COM-JOB-{code}-DMG").label.split(" ")[0])


def lb_name(d: Data, code: str) -> str:
    """LB の名前（条件の「LB: ファランクス」から）。日本語以外は用語の表（公式の表記）。"""
    return i18n.SLASH().join(L(d.row(b).condition.removeprefix("LB: ")) for b in lb_ids(code))


def lb_ids(code: str) -> list[str]:
    return ["COM-LBB-SMN-BAHAMUT", "COM-LBB-SMN-PHOENIX"] if code == "SMN" else [f"COM-LBB-{code}"]


def lb_header(d: Data) -> str:
    """LB の列の見出し。秒数は順位の倍率が1のときの値なので、その順位を台帳から探して書く。"""
    for i in (1, 2, 3):
        if d.num(f"COM-LB-RANK{i}", "倍") == 1:
            title = esc(F("基準の蓄積時間＋ジョブ補正。順位の倍率が1（{0}）のとき", L(f"{i}位")))
            rank = f'<span data-src="COM-LB-RANK{i}">{esc(L(f"{i}位"))}</span>'
            return f'<th title="{title}">{H("LB({0})", rank)}{icon("計算") if SHOW_GRADES else ""}</th>'
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
    lb = lbc.c(secs[0], lb_ids(code) + [adj_id], suffix="秒") if len(secs) == 1 else i18n.SLASH().join(
        lbc.c(s, lb_ids(code) + [adj_id], suffix="秒") for s in secs
    )
    return pct(f"COM-JOB-{code}-DMG"), pct(f"COM-JOB-{code}-TAKEN"), lb


def common_column(d: Data, prefix: str) -> str:
    # リミットゲージ（順位補正）
    lb_ids_rank = [f"COM-LB-RANK{i}" for i in (1, 2, 3)]
    c1 = Card(d, lb_ids_rank)
    tiles = "".join(
        f'<div class="t"><span class="l" data-src="COM-LB-RANK{i}">{esc(L(f"{i}位"))}</span>'
        f'{c1.v(f"COM-LB-RANK{i}", unit="倍", show=lambda x: "×" + fmt(x))}</div>'
        for i in (1, 2, 3)
    )
    lb_card = card("リミットゲージ", f'<div class="lbrank">{tiles}</div>', sub=c1.t("COM-LB-RULE"),
                   head_icon=f'<img class="hi" src="{ap(prefix)}assets/img/icon_limit_break.png" alt="">', badge=c1.badge())

    # 戦意高揚
    levels = range(1, 6)
    bh_rows = [f"COM-BH-L{i}-EFF" for i in levels] + [f"COM-BH-L{i}-MIN" for i in levels] + [
        f"COM-BHG-{k}-L{i}" for k in ("KO", "AS") for i in range(6)
    ]
    c2 = Card(d, bh_rows)
    roman = ["I", "II", "III", "IV", "V"]
    head = f'<th></th><th class="none">{H("なし")}</th>' + "".join(
        f'<th><img src="{ap(prefix)}assets/img/bh{i}.png" alt="{esc(F("戦意高揚{0}", roman[i - 1]))}"></th>' for i in levels
    )
    eff = f'<th>{H("効果")}</th><td class="none">—</td>' + "".join(
        f'<td>{c2.v(f"COM-BH-L{i}-EFF", unit="%", show=lambda x: "+" + fmt(x), suffix="%")}</td>' for i in levels
    )
    need = f'<th>{esc(i18n.C("戦意高揚の表の行", "戦意値"))}</th><td class="none">—</td>' + "".join(
        f'<td>{c2.v(f"COM-BH-L{i}-MIN", unit="戦意値")}</td>' for i in levels
    )
    ko = f"<th>{H('撃破')}</th>" + "".join(f'<td>{c2.v(f"COM-BHG-KO-L{i}", unit="戦意値", show=lambda x: "+" + fmt(x))}</td>' for i in range(6))
    asst = f"<th>{H('アシスト')}</th>" + "".join(
        f'<td>{c2.v(f"COM-BHG-AS-L{i}", unit="戦意値", show=lambda x: "+" + fmt(x))}</td>' for i in range(6)
    )
    sep = f'<tr class="sep"><td colspan="7">{H("倒した相手の段階で、得る戦意値が決まる")}</td></tr>'
    bh_table = (
        f'<table class="bh"><tr>{head}</tr><tr class="eff">{eff}</tr><tr>{need}</tr>{sep}<tr>{ko}</tr><tr>{asst}</tr></table>'
    )
    bh_card = card(
        "戦意高揚",
        bh_table,
        sub=H("戦闘不能: {0}", c2.t("COM-BH-DEATH")),
        badge=c2.badge(),
    )

    # 自分のジョブ（選んだジョブだけ表示。選ぶまでは選択欄を出す）
    all_codes = [c for _, _, codes in JOB_GROUPS for c in codes]
    jrows = [f"COM-JOB-{c}-{k}" for c in all_codes for k in ("DMG", "TAKEN", "LB")]
    c3 = Card(d, jrows)
    picks = "".join(
        f'<button type="button" class="pick" data-pick="{c}" title="{esc(job_name(d, c))}">'
        f'<img src="{ap(prefix)}assets/img/job_{c}.png" alt="{esc(job_name(d, c))}"></button>'
        for c in all_codes
    )
    rows_html = []
    for code in all_codes:
        dmg, taken, lb = job_cells(c3, code)
        rows_html.append(
            f'<tr data-job="{code}" hidden><td class="jn"><img src="{ap(prefix)}assets/img/job_{code}.png" alt="">{esc(job_name(d, code))}</td>'
            f"<td>{dmg}</td><td>{taken}</td><td>{lb}</td></tr>"
        )
    empty = (f'<tr class="empty"><td colspan="4">'
             f'{H("ジョブを押すと、ここに補正が出ます（{0}つまで）", f"<span data-ui={chr(34)}{MYJOB_MAX}{chr(34)}>{MYJOB_MAX}</span>")}</td></tr>')
    jobs_body = (
        f'<div class="picker">{picks}</div>'
        f'<table class="mine"><tr><th></th><th>{H("与ダメ")}</th><th>{H("被ダメ")}</th>{lb_header(d)}</tr>{empty}{"".join(rows_html)}</table>'
    )
    job_card = card(
        "ジョブ補正",
        jobs_body,
        sub=f'<a class="more" href="{prefix}jobs/">{H("一覧")}</a>',
        cls="myjobs",
        badge=c3.badge(),
    )
    return lb_card + bh_card + job_card


# ---------------------------------------------------------------- ページの組み立て


def rule_names_ja(rule: str) -> tuple[str, str]:
    """「外縁遺跡群（制圧戦）」を (外縁遺跡群, 制圧戦) にする（ledger.RULES の名前から。台帳との照合に使う）。"""
    full = ledger.RULES[rule][1]
    m = re.fullmatch(r"(.+)（(.+)）", full)
    if not m:
        raise BuildError(f"ルール名 {full!r} の形が想定と違う")
    return m.group(1), m.group(2)


def rule_names(rule: str) -> tuple[str, str]:
    """ページに出すマップ名とルール名（日本語以外は用語の表の公式の表記）。"""
    name, sub = rule_names_ja(rule)
    return L(name), L(sub)


def ap(prefix: str) -> str:
    """assets/ への道（どの言語のページも frontline/<lang>/ の下にあるので1段深い）。"""
    return prefix + "../"


FLAGS = {"ja": "flag-ja", "en": "flag-en", "de": "flag-de", "fr": "flag-fr"}  # 自作の国旗（icons.svg）。英語は米国旗（ユーザーの指示）


def flag(lg: str) -> str:
    """言語の切り替えに付ける国旗（飾り。言語は隣の文字で示す）。"""
    # 大きさは属性にも書く（スタイルシートが古いままキャッシュされていても、既定の 300×150 で巨大にならないように）
    return f'<svg class="flag" width="30" height="20" aria-hidden="true"><use href="#{FLAGS[lg]}"/></svg>'


def lang_switch(here: str, prefix: str) -> str:
    """言語の切り替え（同じページの各言語版へ）。選んだ言語はブラウザに記憶し、トップでの自動の切り替えより優先する。"""
    root = ap(prefix)  # frontline/ への道
    out = []
    for lg in i18n.LANGS:
        href = root + lg + "/" + here
        on = " on" if lg == i18n.lang() else ""
        out.append(f'<a class="lg{on}" data-lang="{lg}" lang="{lg}" hreflang="{lg}" href="{href}" '
                   f'title="{esc(i18n.LANG_NAMES[lg])}">{flag(lg)}{lg.upper()}</a>')
    return f'<span class="langs">{"".join(out)}</span>'


def header(d: Data, rule: str, spec: dict, prefix: str, here: str) -> str:
    name, sub = rule_names(rule)
    c = Card(d, [], base="公式")  # ヘッダには見出しの印がないので、公式でない値には必ず印を付ける
    goal_row = d.row(spec["goal"])
    unit = goal_row.unit
    if d.num(spec["ko"][0], unit) <= 0 or d.num(spec["ko"][1], unit) >= 0:
        raise BuildError(f"{spec['ko']}: 撃破は正、被撃破は負の数で書く")
    ko_gain = c.v(spec["ko"][0], unit=unit, show=signed)
    ko_loss = c.v(spec["ko"][1], unit=unit, show=signed)
    today = f'<span class="today" data-today-badge="{rule}" hidden>{H("今日")}</span>'
    return (
        f'<header class="hdr"><div class="title"><img class="badge" src="{ap(prefix)}assets/img/hdr_{rule}.png" alt="">'
        + (f'<h1>{esc(name)}<small>{esc(sub)}</small></h1>{today}</div>' if i18n.lang() == "ja"
           # 英・独・仏: マップ名が長いので、「今日」の印はルール名の行に置く（マップ名の幅を取らない）
           else f'<h1>{esc(name)}<small>{esc(sub)}{today}</small></h1></div>')
        + f'<div class="goal">{c.v(spec["goal"], unit=unit, cls="v gnum")}<span class="gcap">{H("{0}で勝利", esc(L(goal_row.unit)))}{c.t(spec["timeout"], cls="t to")}</span></div>'
        f'<div class="ko"><div class="k"><span class="l">{H("撃破")}</span><span class="kv">{ko_gain}<small>{esc(L(unit))}</small></span></div>'
        f'<div class="k"><span class="l">{H("被撃破")}</span><span class="kv">{ko_loss}<small>{esc(L(unit))}</small></span></div></div>'
        f"{nav(d, rule, prefix, here)}</header>"
    )


def nav(d: Data, current: str, prefix: str, here: str) -> str:
    tabs = "".join(
        f'<a data-go="{r}" class="{"on" if r == current else ""}" href="{prefix}{r}/">{esc(rule_names(r)[1])}</a>' for r in RULE_ORDER
    )
    patch = d.row("COM-META-PATCH").value
    return (
        f'<div class="navbox"><nav class="nav">{tabs}</nav>'
        f'<div class="meta"><a href="{prefix}jobs/" class="{"on" if current == "jobs" else ""}">{H("ジョブ補正")}</a>'
        f'<a href="{prefix}sources/" class="{"on" if current == "sources" else ""}">{H("出典")}</a>'
        f'<span>{H("データ {0} 時点", f"<span data-src={chr(34)}COM-META-PATCH{chr(34)}>{esc(patch)}</span>")}</span>'
        "</div></div>"
    )


FETCHED_MARK = "__FETCHED__"  # build() の最後に、使った出典の取得日の範囲で置き換える


def fetched_range(d: Data) -> str:
    """ページで使った行の出典の取得日の範囲（例: 2026-10-27〜10-29）。"""
    sids = {s for rid in d.used for s in d.rows[rid].sources}
    days = sorted({m for sid in sids for m in re.findall(r"\d{4}-\d{2}-\d{2}", d.sources.get(sid, {}).get("取得日", ""))})
    if not days:
        return L("不明")
    return days[0] if days[0] == days[-1] else F("{0}〜{1}", days[0], days[-1][5:])


def footer(d: Data, here: str, prefix: str) -> str:
    """© SQUARE ENIX（公式の画像・情報を使う条件。著作物利用条件 3-1）と、README（権利・出典・使い方）へのリンク。"""
    return (
        '<footer class="ftr"><span>© SQUARE ENIX</span>'
        # 日本語以外: 訳は機械翻訳で、ゲームの用語だけが公式の表記（2026-10-29 ユーザーに伝えた既定）
        + lang_switch(here, prefix)
        + ("" if i18n.lang() == "ja" else f'<span class="mt">{H("自動翻訳（ゲームの用語は公式の表記）")}</span>')
        + f'<span class="right"><a href="{README_URL}" rel="noopener">{H("このサイトについて（権利・出典）")}</a>'
        f'{i18n.SEP()}{H("確認 {0}", f"<span data-src={chr(34)}sources.md{chr(34)}>{FETCHED_MARK}</span>")}</span></footer>'
    )


SVG_DEFS_PATH = ASSETS / "icons.svg"


def css_version() -> str:
    """site.css の中身の短いハッシュ。URL に付けて、CSS を変えたら閲覧者のブラウザが必ず新しい版を読むようにする
    （GitHub Pages は10分キャッシュする。2026-10-29、新しいページと古い CSS の組み合わせで国旗が巨大に表示された）。"""
    import hashlib

    return hashlib.sha256((ASSETS / "site.css").read_bytes()).hexdigest()[:10]

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
    if (a.dataset.go === today) { var d = document.createElement('span'); d.className = 'dot'; d.title = __TODAY__; a.appendChild(d); }
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
  document.querySelectorAll('[data-lang]').forEach(function (a) {
    a.addEventListener('click', function () { try { localStorage.setItem('fl-lang', a.dataset.lang); } catch (e) {} });
  });
})();
</script>"""

# 入口（frontline/index.html）: 言語を選んだことがなければ、ブラウザの言語の版へ移る（対応していない言語なら英語）。
# 選んだ言語（記憶）があればそれに従う。本文より先に動かす
LANG_REDIRECT = """<script>
(function () {
  var LANGS = __LANGS__, c = null;
  try { c = localStorage.getItem('fl-lang'); } catch (e) {}
  if (LANGS.indexOf(c) < 0) {
    c = null;
    var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'ja'];
    for (var i = 0; i < prefs.length && !c; i++) { var b = String(prefs[i]).slice(0, 2).toLowerCase(); if (LANGS.indexOf(b) >= 0) c = b; }
    if (!c) c = 'en';
  }
  location.replace(c + '/' + location.search + location.hash);
})();
</script>"""


def rotation(d: Data) -> tuple[list[str], list[int], str]:
    """日替わりの周期・起点の日・起点のルールを台帳から取る。"""
    by_name = {rule_names_ja(r)[0]: r for r in RULE_ORDER}
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


def page(d: Data, title: str, panels_html: str, prefix: str, *, extra_cls: str = "", top: bool = False) -> str:
    cycle, anchor, anchor_rule = rotation(d)
    js = (
        JS.replace("__W__", str(CANVAS_W)).replace("__H__", str(CANVAS_H))
        .replace("__CYCLE__", json.dumps(cycle)).replace("__ANCHOR__", json.dumps(anchor))
        .replace("__ANCHOR_RULE__", json.dumps(anchor_rule)).replace("__MAX__", str(MYJOB_MAX))
        .replace("__TODAY__", json.dumps(L("今日"), ensure_ascii=False))
    )
    redirect = ""  # 言語の振り分けは入口のページ（entry_page）だけ
    svg = SVG_DEFS_PATH.read_text(encoding="utf-8")
    return (
        f'<!doctype html>\n<html lang="{i18n.lang()}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        f'<title>{esc(title)}</title>{redirect}<link rel="stylesheet" href="{ap(prefix)}assets/site.css?v={css_version()}"></head>'
        f'<body class="{extra_cls}">{svg}<div id="stage">{panels_html}</div>{js}</body></html>\n'
    )


def rule_panel(d: Data, rule: str, prefix: str, here: str) -> str:
    import pages

    spec = pages.SPECS[rule]
    left = spec["blocks"](d, prefix)
    return (
        f'<div class="panel" data-rule="{rule}">{header(d, rule, spec, prefix, here)}'
        f'<main class="main"><section class="col rule">{left}</section>'
        f'<section class="col common">{common_column(d, prefix)}</section></main>{footer(d, here, prefix)}</div>'
    )


def jobs_page(d: Data, prefix: str) -> str:
    all_codes = [c for _, _, codes in JOB_GROUPS for c in codes]
    cd = Card(d, [f"COM-JOB-{c}-{k}" for c in all_codes for k in ("DMG", "TAKEN", "LB")])
    tables = []
    for half in (JOB_GROUPS[:2] + [JOB_GROUPS[3]], [JOB_GROUPS[2], JOB_GROUPS[4]]):
        trs = []
        for role, img, codes in half:
            trs.append(f'<tr class="role"><td colspan="5"><img src="{ap(prefix)}assets/img/{img}" alt="">{esc(L(role))}</td></tr>')
            for code in codes:
                dmg, taken, lb = job_cells(cd, code)
                trs.append(
                    f'<tr data-job="{code}"><td class="jn"><img src="{ap(prefix)}assets/img/job_{code}.png" alt="">{esc(job_name(d, code))}</td>'
                    f'<td>{dmg}</td><td>{taken}</td><td>{lb}</td><td class="lbn">{esc(lb_name(d, code))}</td></tr>'
                )
        tables.append(
            f'<table class="jobtable"><tr><th>{H("ジョブ")}</th><th>{H("与ダメ")}</th><th>{H("被ダメ")}</th>{lb_header(d)}'
            f'<th>{H("リミットブレイク")}</th></tr>{"".join(trs)}</table>'
        )
    body = (
        '<p class="lead">' + H("与ダメ・被ダメはフロントラインでのジョブ補正。LB は基準の蓄積時間に補正を足した秒数（順位による倍率は含まない）。"
                               "行を押すと自分のジョブとして記憶し、各ルールのページに出ます（{0}つまで）。",
                               f'<span data-ui="{MYJOB_MAX}">{MYJOB_MAX}</span>') + "</p>"
        f'<div class="jobtables">{"".join(tables)}</div>'
    )
    hdr = (
        f'<header class="hdr"><div class="title"><h1>{H("ジョブ補正")}<small>{H("フロントライン共通")}</small></h1></div>'
        f"{nav(d, 'jobs', prefix, 'jobs/')}</header>"
    )
    return f'<div class="panel jobs">{hdr}<main class="main one">{body}</main>{footer(d, "jobs/", prefix)}</div>'

def sources_page(d: Data, prefix: str) -> str:
    used = sorted({s for rid in d.used for s in d.rows[rid].sources})
    foreign = i18n.lang() != "ja"
    trs = []
    for sid in used:
        s = d.sources.get(sid, {})
        url = s.get("URL", "")
        name = esc(s.get("名称", sid))
        link = f'<a href="{esc(url)}" rel="noopener">{name}</a>' if url.startswith("https://") else name
        trs.append(
            f'<tr><td class="sid">{esc(sid)}</td><td class="kind">{esc(L(s.get("種別", "")) if s.get("種別") else "")}</td>'
            # 名称は出典の原文のまま（引用）。公開・更新の欄は日本語の注記なので、日本語のページにだけ出す
            f'<td class="cite" lang="ja">{link}</td>'
            + ("" if foreign else f'<td>{esc(s.get("公開・更新", ""))}</td>')
            # 取得日の欄の注記（取得不可など）は日本語なので、ほかの言語では日付だけ
            + f'<td>{esc(s.get("取得日", "") if not foreign else ", ".join(re.findall(r"\d{4}-\d{2}-\d{2}", s.get("取得日", ""))))}</td></tr>'
        )
    body = (
        '<p class="lead">' + H("このサイトの値の出典（ページに出している値が使うものだけ）。公式は株式会社スクウェア・エニックスの公表、"
                               "外部はファンの資料（数値の出典として引用。文章は写していない）、ゲーム内は管理者のゲーム内確認。") + "</p>"
        f'<div class="srcwrap"><table class="srcs"><tr><th>ID</th><th>{H("種別")}</th><th>{H("名称")}</th>'
        + ("" if foreign else f'<th>{H("公開・更新")}</th>')
        + f'<th>{H("取得日")}</th></tr>{"".join(trs)}</table></div>'
    )
    hdr = (
        f'<header class="hdr"><div class="title"><h1>{H("出典")}<small>{H("フロントライン早見表")}</small></h1></div>'
        f"{nav(d, 'sources', prefix, 'sources/')}</header>"
    )
    return f'<div class="panel sources">{hdr}<main class="main one">{body}</main>{footer(d, "sources/", prefix)}</div>'

def build_lang(d: Data, base: Path) -> dict[Path, str]:
    """今の言語（i18n.lang()）のページ一式。base は frontline/ か frontline/<lang>/。"""
    out: dict[Path, str] = {}
    out[base / "index.html"] = page(
        d, L("フロントライン早見表（今日のルール）"), "".join(rule_panel(d, r, "", "") for r in RULE_ORDER), "", top=True
    )
    for r in RULE_ORDER:
        name, sub = rule_names(r)
        out[base / r / "index.html"] = page(d, F("{0}（{1}）｜フロントライン早見表", name, sub),
                                            rule_panel(d, r, "../", f"{r}/"), "../")
    out[base / "jobs" / "index.html"] = page(d, L("ジョブ補正｜フロントライン早見表"), jobs_page(d, "../"), "../")
    # 出典一覧は最後に作る（ほかのページで使った行の出典を集めるため）
    out[base / "sources" / "index.html"] = page(d, L("出典｜フロントライン早見表"), sources_page(d, "../"), "../", extra_cls="scroll")
    rng = fetched_range(d)
    return {path: text.replace(FETCHED_MARK, esc(rng)) for path, text in out.items()}


OLD_JA_PAGES = [*RULE_ORDER, "jobs", "sources"]  # 2026-10-29 まで frontline/ の直下にあった日本語のページ


def entry_page() -> str:
    """入口: 言語を選ぶ（スクリプトが動けば、すぐ選んだ言語かブラウザの言語の版へ移る）。"""
    svg = SVG_DEFS_PATH.read_text(encoding="utf-8")
    links = "".join(
        f'<li><a href="{lg}/" data-lang="{lg}" lang="{lg}" hreflang="{lg}">{flag(lg)}{esc(i18n.LANG_NAMES[lg])}</a></li>'
        for lg in i18n.LANGS
    )
    return (
        '<!doctype html>\n<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>FF14 Frontline</title>'
        + LANG_REDIRECT.replace("__LANGS__", json.dumps(i18n.LANGS))
        + f'<link rel="stylesheet" href="assets/site.css?v={css_version()}"></head>'
        f'<body class="entry">{svg}<main><h1>FF14 Frontline</h1><ul class="entry-langs">{links}</ul>'
        '<p class="ftr-entry">© SQUARE ENIX</p></main>'
        "<script>document.querySelectorAll('[data-lang]').forEach(function (a) { a.addEventListener('click', function () {"
        " try { localStorage.setItem('fl-lang', a.dataset.lang); } catch (e) {} }); });</script></body></html>\n"
    )


def moved_page(path: str) -> str:
    """前の日本語のページの場所に置く案内（ja/ の同じページへ移る）。"""
    to = f"../ja/{path}/"
    return (
        '<!doctype html>\n<html lang="ja"><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url={to}"><link rel="canonical" href="{to}">'
        '<title>フロントライン早見表</title>'
        f"<script>location.replace({json.dumps(to)} + location.search + location.hash);</script></head>"
        f'<body><p><a href="{to}">フロントライン早見表（日本語）へ</a></p></body></html>\n'
    )


def build(d: Data) -> dict[Path, str]:
    """生成するファイルの中身を返す（書き込みはしない）。各言語は frontline/<lang>/、入口は frontline/index.html。"""
    out: dict[Path, str] = {FRONT / "index.html": entry_page()}
    out.update({FRONT / name / "index.html": moved_page(name) for name in OLD_JA_PAGES})
    try:
        for lg in i18n.LANGS:
            i18n.set_lang(lg)
            out.update(build_lang(d, FRONT / lg))
    except i18n.I18nError as exc:
        raise BuildError(str(exc)) from exc
    finally:
        i18n.set_lang("ja")
    return out


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
