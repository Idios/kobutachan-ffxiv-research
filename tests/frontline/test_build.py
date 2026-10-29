"""値台帳と生成したページの検査（ブラウザを使わないもの）。

- ページの数字はすべて台帳の ○ の行に辿れる（data-src）。
- × や空欄の行はページに出ない。生成器は ○ でない行を参照すると止まる。
- 表示文（短い言い方）は、元の値が変わると検査で止まる。数を足していない。
- 旧値の登録簿（frontline/data/retired.md）の値がページに残っていない。
- 検査器そのものの変異テスト: わざと誤りを入れたら検出できること（analysis-integrity スキル）。
- 派生値は、テストの中で台帳から計算し直して突き合わせる（数をテストに手で書かない）。
"""

from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path

import build
import ledger
import pytest
from conftest import (
    FRONT,
    find_retired,
    public_pages,
    retired_rows,
    src_tokens,
    text_nodes,
)

META_TOKENS = {"sources.md"}  # 台帳の行ではない出どころ（出典台帳の取得日）


# ---------------------------------------------------------------- 台帳


def test_ledger_has_no_errors() -> None:
    _, _, errors = ledger.load_all()
    assert errors == []


def test_display_text_detects_changed_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """変異テスト: 表示文のある行の値を書き換えると、検査がエラーを出す。"""
    work = tmp_path / "ledger"
    shutil.copytree(ledger.LEDGER_DIR, work)
    monkeypatch.setattr(ledger, "LEDGER_DIR", work)
    path = work / "seize.md"
    led = ledger.load_ledger("seize", [])
    target = next(r for r in led.rows if r.display)
    ledger.update_cells(path, ledger.LEDGER_COLS, {target.id: {"値": target.value + "（変更）"}})
    errors: list[str] = []
    ledger.load_ledger("seize", errors)
    assert any(target.id in e and "表示文" in e for e in errors), errors


def test_display_text_rejects_new_numbers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """変異テスト: 元の値にない数を表示文に入れると、検査がエラーを出す。"""
    work = tmp_path / "ledger"
    shutil.copytree(ledger.LEDGER_DIR, work)
    monkeypatch.setattr(ledger, "LEDGER_DIR", work)
    led = ledger.load_ledger("triumph", [])
    target = next(r for r in led.rows if r.display)
    ledger.update_cells(work / "triumph.md", ledger.DISPLAY_COLS, {target.id: {"表示": target.display + "（98765）"}})
    errors: list[str] = []
    ledger.load_ledger("triumph", errors)
    assert any(target.id in e and "98765" in e for e in errors), errors


# ---------------------------------------------------------------- 生成物


def test_generated_pages_are_up_to_date(site: dict[Path, str]) -> None:
    stale = [p.relative_to(FRONT).as_posix() for p, text in site.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    assert stale == [], f"python frontline/tools/build.py を実行して作り直す: {stale}"


# 数字を含むが、ゲームの値ではない決まった言い回し（単位の「1」や固有名）。ここに足すときは値でないことを確かめる
UI_PHRASES = ["1基の合計", "2回目から", "2巡目", "2Dマップ", "サークル1つ"]


def test_every_number_has_a_source(site: dict[Path, str]) -> None:
    """数字を含む文字は、data-src（台帳の行）か data-ui（画面の都合の数）を持つ要素の中にある。"""
    missing = []
    for name, html_text in public_pages(site).items():
        for text, anc in text_nodes(html_text):
            for phrase in UI_PHRASES:
                text = text.replace(phrase, "")
            if not re.search(r"\d", text):
                continue
            if any("data-src" in a or "data-ui" in a for _, a in anc):
                continue
            missing.append(f"{name}: {text.strip()[:40]!r}")
    assert missing == []


def test_ui_phrases_are_still_used(site: dict[Path, str]) -> None:
    """例外の言い回しは、ページに今もあるものだけにする（使わなくなった例外が、出どころのない数を見逃す穴にならないように）。"""
    texts = [t for html_text in public_pages(site).values() for t, _ in text_nodes(html_text)]
    assert [p for p in UI_PHRASES if not any(p in t for t in texts)] == []


def test_sources_are_approved_rows(site: dict[Path, str], data: build.Data) -> None:
    bad = set()
    for name, html_text in public_pages(site).items():
        for tokens in re.findall(r'data-src="([^"]*)"', html_text):
            for t in tokens.split():
                if t in META_TOKENS:
                    continue
                r = data.rows.get(t)
                if r is None or r.verdict != "○":
                    bad.add(f"{name}: {t}（{'台帳にない' if r is None else '採否 ' + (r.verdict or '空欄')}）")
    assert sorted(bad) == []


def test_rejected_rows_never_appear(site: dict[Path, str], data: build.Data) -> None:
    rejected = {rid for rid, r in data.rows.items() if r.verdict != "○"}
    assert rejected, "× の行がない（検査の前提が変わった）"
    used = {t for html_text in public_pages(site).values() for s in re.findall(r'data-src="([^"]*)"', html_text) for t in s.split()}
    assert used & rejected == set()


@pytest.mark.parametrize("verdict", ["×", ""])
@pytest.mark.parametrize("rid", ["SEC-WIN-TARGET", "TRI-SNOW-BARRIER-PCT", "COM-JOB-PLD-DMG", "SEI-OCC-ENEMY", "SHA-L-DATA"])
def test_build_refuses_unapproved_rows(data: build.Data, rid: str, verdict: str) -> None:
    """変異テスト: ページで使う行の採否を × や空欄にすると、生成が止まる。"""
    d = build.Data([], data.sources)
    d.rows = copy.deepcopy(data.rows)
    d.rows[rid].verdict = verdict
    with pytest.raises(build.BuildError, match=rid):
        build.build(d)


def test_build_refuses_changed_unit(data: build.Data) -> None:
    """変異テスト: 単位が変わった行は、表示を見直すまで使わない。"""
    d = build.Data([], data.sources)
    d.rows = copy.deepcopy(data.rows)
    d.rows["SEC-FLAG-TICK"].unit = "分"
    with pytest.raises(build.BuildError, match="SEC-FLAG-TICK"):
        build.build(d)


def mutated(data: build.Data) -> build.Data:
    d = build.Data([], data.sources)
    d.rows = copy.deepcopy(data.rows)
    return d


@pytest.mark.parametrize(
    ("rid", "field", "value", "match"),
    [
        ("TRI-SNOW-BARRIER-PCT", "unit", "HP", "TRI-SNOW-BARRIER-PCT"),  # 単位が変わった（%→HP）
        ("TRI-AURORA-LB-RATE", "unit", "%（通常時に対する増分）", "TRI-AURORA-LB-RATE"),
        ("SEC-FLAG-COUNT", "unit", "本", "SEC-FLAG-COUNT"),
        ("SEI-SPAWN-FIRST-TIME", "unit", "経過時間（分:秒）", "SEI-SPAWN-FIRST-TIME"),
        ("SHA-KO-GAIN", "unit", "戦意値", "SHA-KO-GAIN"),
        ("SEC-KO-LOSS", "value", "10", "撃破は正"),  # 減点を正の数で書いた
        ("TRI-WX-SNOW-START", "value", "15〜16", "早い"),  # 残り時間の範囲の向き
        ("SEC-NODE-PTS-UNIT", "value", "撃破したときに1回だけ150", "最大N回"),  # 最大の回数の根拠が変わった
        ("SHA-S-FIRST-DELAY", "value", "360", "SHA-S-FIRST-ACTIVE"),  # 公式の秒数と外部の時刻が食い違った
    ],
)
def test_build_refuses_inconsistent_rows(data: build.Data, rid: str, field: str, value: str, match: str) -> None:
    """変異テスト: 単位・符号・書き方・ほかの行との照合が合わない台帳では、生成が止まる。"""
    d = mutated(data)
    setattr(d.rows[rid], field, value)
    with pytest.raises(build.BuildError, match=match):
        build.build(d)


def test_build_refuses_ambiguous_anchor(data: build.Data) -> None:
    """変異テスト: 周期に2回あるルールを起点にすると、起点の位置が決まらないので止まる。"""
    d = mutated(data)
    d.rows["COM-ROT-ANCHOR"].label = "ローテーションの起点（シールロックが開催された日）"
    with pytest.raises(build.BuildError, match="起点"):
        build.rotation(d)


def test_single_row_conversion_is_not_calc(data: build.Data) -> None:
    """1行だけの換算に計算の印を付けない（v(show=...) を使う）。"""
    cd = build.Card(mutated(data), [])
    with pytest.raises(build.BuildError, match="1行だけ"):
        cd.c(300, ["TRI-WX-SNOW-SEC"])


def test_judgment_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """変異テスト: 外部の ○ の行の値だけを書き換えると、判定の記録と合わず validate が止まる。"""
    work = tmp_path / "ledger"
    shutil.copytree(ledger.LEDGER_DIR, work)
    monkeypatch.setattr(ledger, "LEDGER_DIR", work)
    ledger.update_cells(work / "seize.md", ledger.LEDGER_COLS, {"SEI-KO-GAIN": {"値": "6"}})
    _, _, errors = ledger.load_all()
    assert any("SEI-KO-GAIN" in e and "判定" in e for e in errors), errors
    # 採否を空欄に戻せば止まらない（ページには出ない）
    ledger.update_cells(work / "seize.md", ledger.LEDGER_COLS, {"SEI-KO-GAIN": {"採否": ""}})
    _, _, errors = ledger.load_all()
    assert not any("SEI-KO-GAIN" in e for e in errors), errors


def test_value_rejects_banned_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """変異テスト: 値に改行（<br>）や波括弧を入れると検査が止める。"""
    work = tmp_path / "ledger"
    shutil.copytree(ledger.LEDGER_DIR, work)
    monkeypatch.setattr(ledger, "LEDGER_DIR", work)
    ledger.update_cells(work / "seize.md", ledger.LEDGER_COLS, {"SEI-OCC-ENEMY": {"値": "1行目<br>2行目"}})
    errors: list[str] = []
    ledger.load_ledger("seize", errors)
    assert any("使えない文字" in e for e in errors), errors


def test_set_display_keeps_file_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """変異テスト: 検査に落ちる表示文（値にない数・漢数字）は書かない。台帳は変わらない。"""
    work = tmp_path / "ledger"
    shutil.copytree(ledger.LEDGER_DIR, work)
    monkeypatch.setattr(ledger, "LEDGER_DIR", work)
    before = (work / "common.md").read_text(encoding="utf-8")
    for bad in ["順位で溜まる量に倍率（9倍）", "順位で溜まる量に倍率（三倍）"]:
        with pytest.raises(ValueError, match="書かなかった"):
            ledger.set_display("COM-LB-RULE", bad)
    assert (work / "common.md").read_text(encoding="utf-8") == before


def test_update_cells_keeps_other_cells(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """採否とコメントを書き換えても、同じ行のほかのセル（値など）は1字も変わらない。"""
    work = tmp_path / "ledger"
    shutil.copytree(ledger.LEDGER_DIR, work)
    monkeypatch.setattr(ledger, "LEDGER_DIR", work)
    row_before = next(ln for ln in (work / "seize.md").read_text(encoding="utf-8").splitlines() if ln.startswith("| SEI-OCC-ENEMY |"))
    ledger.update_cells(work / "seize.md", ledger.LEDGER_COLS, {"SEI-OCC-ENEMY": {"コメント": "テスト"}})
    row_after = next(ln for ln in (work / "seize.md").read_text(encoding="utf-8").splitlines() if ln.startswith("| SEI-OCC-ENEMY |"))
    assert row_after.rsplit("|", 2)[0].rsplit("|", 1)[0] == row_before.rsplit("|", 2)[0].rsplit("|", 1)[0]


def test_retired_values_absent(site: dict[Path, str]) -> None:
    assert find_retired(public_pages(site), retired_rows()) == []


def test_retired_checker_detects_injected_values(site: dict[Path, str]) -> None:
    """変異テスト: 旧値をページに入れると、不在検査が見つける（行の範囲と全体の範囲の両方）。"""
    entries = retired_rows()
    pages = public_pages(site)
    name, html_text = "triumph/index.html", pages["triumph/index.html"]
    for e in entries:
        if e["範囲"] == "全体":
            injected = html_text.replace("</main>", f"<p>{e['旧値']}</p></main>", 1)
        else:
            injected = html_text.replace("</main>", f'<span data-src="{e["行ID"]}">{e["旧値"]}</span></main>', 1)
        assert find_retired({name: injected}, [e]), f"{e['行ID']} の旧値 {e['旧値']!r} を検出できない"
    # 台帳の書き方（桁区切りなし・波線の違い）で登録しても、ページの書き方を検出できる
    sec = pages["secure/index.html"]
    assert find_retired({"secure": sec}, [{"行ID": "SEC-NODE-HP", "旧値": "1500000", "範囲": "行"}])
    assert find_retired({"triumph": html_text}, [{"行ID": "TRI-WX-SNOW-START", "旧値": "16:00～15:00", "範囲": "全体"}])


# ---------------------------------------------------------------- 派生値（台帳から計算し直して突き合わせる）


def shown(site: dict[Path, str], page: str, tokens: list[str]) -> list[str]:
    """data-src がちょうど tokens の要素の文字（印の title を除く）。"""
    html_text = public_pages(site)[page]
    out = []
    for text, anc in text_nodes(html_text):
        srcs = src_tokens(anc)
        if srcs and srcs[0] == tokens:
            out.append(text.strip())
    return out


def test_derived_values_match_ledger(site: dict[Path, str], data: build.Data) -> None:
    import pages

    n = data.num
    total = n("COM-MATCH-TIME") * 60
    # 外縁遺跡群: 最初の出現の残り時間と、転移装置の起動
    first = total - n("SEC-EVT-FIRST")
    assert build.mmss(first) in shown(site, "secure/index.html", ["COM-MATCH-TIME", "SEC-EVT-FIRST"])
    tele = first + n("SEC-EVT-PANEL-LEAD")
    assert build.mmss(tele) in shown(site, "secure/index.html", ["COM-MATCH-TIME", "SEC-EVT-FIRST", "SEC-EVT-PANEL-LEAD"])
    # 拠点の1分あたりと、伸びが大きい拠点の数（増え方が最小の増え方より大きいところ）
    vals = [n(f"SEC-FLAG-RATE-{i}") for i in range(1, 10)]
    for i in range(1, 10):
        rid = f"SEC-FLAG-RATE-{i}"
        want = build.fmt(n(rid) * 60 / n("SEC-FLAG-TICK")) + "/分"  # 単位つき（2026-10-29 ユーザーの指示）
        assert want in shown(site, "secure/index.html", [rid, "SEC-FLAG-TICK"]), rid
    inc = [b - a for a, b in zip([0.0] + vals[:-1], vals)]
    jumps = [str(i) for i in range(2, 10) if inc[i - 1] > min(inc)]
    big2 = re.search(r'<span class="big2">(.*?)<small>', public_pages(site)["secure/index.html"]).group(1)
    assert re.findall(r">(\d+)</span>", big2) == jumps
    # 中央の1回の合計と、邀撃システムの最大の回数（合計には「戦術値」を付ける）
    drone = build.fmt(n("SEC-DRONE-PTS") * n("SEC-DRONE-COUNT")) + "戦術値"
    assert drone in shown(site, "secure/index.html", ["SEC-DRONE-PTS", "SEC-DRONE-COUNT"])
    cmdr = build.fmt(n("SEC-CMDR-PTS") * n("SEC-CMDR-SPOTS")) + "戦術値"
    assert cmdr in shown(site, "secure/index.html", ["SEC-CMDR-PTS", "SEC-CMDR-SPOTS"])
    node = shown(site, "secure/index.html", ["SEC-NODE-PTS", "SEC-NODE-REFILLS", "SEC-NODE-PTS-UNIT"])
    assert build.fmt(n("SEC-NODE-PTS") * (n("SEC-NODE-REFILLS") + 1)) + "戦術値" in node
    assert build.fmt(n("SEC-NODE-REFILLS") + 1) + "回" in shown(site, "secure/index.html", ["SEC-NODE-REFILLS", "SEC-NODE-PTS-UNIT"])
    # シールロック・オンサル: 1分あたりと、枯れるまで
    for k in "BAS":
        tot, tk, iv = f"SEI-TOME-{k}-TOTAL", f"SEI-TOME-{k}-TICK", "SEI-TOME-TICK-SEC"
        assert build.fmt(n(tk) * 60 / n(iv)) + "/分" in shown(site, "seize/index.html", [tk, iv])
        assert pages.dur(n(tot) / n(tk) * n(iv)) in shown(site, "seize/index.html", [tot, tk, iv])
        tk2, iv2 = f"NAA-OVOO-{k}-TICK", "NAA-OVOO-TICK-SEC"
        assert build.fmt(n(tk2) * 60 / n(iv2)) + "/分" in shown(site, "naadam/index.html", [tk2, iv2])
    # オンサル: 最初に契約できる時刻
    first_claim = total - (n("NAA-SPAWN-FIRST") + n("NAA-WARN-SEC"))
    assert build.mmss(first_claim) in shown(site, "naadam/index.html", ["COM-MATCH-TIME", "NAA-SPAWN-FIRST", "NAA-WARN-SEC"])
    # 演習戦: 制圧中の1分あたり
    for k in "BAS":
        tot = f"TRI-OBJ-{k}-TOTAL"
        want = build.fmt(n(tot) * 60 / n("TRI-CLAIM-DURATION")) + "/分"
        assert want in shown(site, "triumph/index.html", [tot, "TRI-CLAIM-DURATION"])
    # 砕氷戦: 大の最初の起動、小の2巡目の最速（未確認の規則による）、10万HPあたり
    lead = n("SHA-ICE-WARN-LEAD")
    l_first = total - (n("SHA-L-FIRST-WARN") + lead)
    assert build.mmss(l_first) in shown(site, "shatter/index.html", ["COM-MATCH-TIME", "SHA-L-FIRST-WARN", "SHA-ICE-WARN-LEAD"])
    s_first = total - (n("SHA-S-FIRST-DELAY") + lead)
    s_second = s_first - (n("SHA-S-REACT") + lead)
    assert build.mmss(s_second) in shown(
        site, "shatter/index.html", ["SHA-S-FIRST-ACTIVE", "SHA-S-REACT", "SHA-ICE-WARN-LEAD", "SHA-S-REACT-RULE"])
    for s_ in "LS":
        want = build.fmt1(n(f"SHA-{s_}-DATA") / n(f"SHA-{s_}-HP") * pages.PER_UNIT_HP)
        assert want in shown(site, "shatter/index.html", [f"SHA-{s_}-DATA", f"SHA-{s_}-HP"]), s_
    # ジョブ: LB の秒数（基準＋補正）。召喚士は2つの LB
    for code in ["PLD", "NIN", "BRD", "DNC"]:
        want = build.fmt(n(f"COM-LBB-{code}") + n(f"COM-JOB-{code}-LB")) + "秒"
        assert want in shown(site, "jobs/index.html", [f"COM-LBB-{code}", f"COM-JOB-{code}-LB"]), code
    smn = {build.fmt(n(b) + n("COM-JOB-SMN-LB")) + "秒" for b in ("COM-LBB-SMN-BAHAMUT", "COM-LBB-SMN-PHOENIX")}
    got = set(shown(site, "jobs/index.html", ["COM-LBB-SMN-BAHAMUT", "COM-LBB-SMN-PHOENIX", "COM-JOB-SMN-LB"]))
    assert smn <= got


def test_band_positions_match_ledger(site: dict[Path, str], data: build.Data) -> None:
    """帯の区切りと天候の位置が、台帳の時刻から計算した位置にある。"""
    total = data.num("COM-MATCH-TIME") * 60
    seize = public_pages(site)["seize/index.html"]
    sw = data.clock("SEI-CAP-SWITCH", "残り時間（分:秒）")
    assert re.findall(r'class="seg" style="flex:(\d+)"', seize)[:2] == [str(round(total - sw)), str(round(sw))]
    tri = public_pages(site)["triumph/index.html"]
    a, z = (x * 60 for x in data.span("TRI-WX-SNOW-START", "分（残り時間）"))
    left = 100 * (total - a) / total
    width = 100 * ((total - (z - data.num("TRI-WX-SNOW-SEC"))) - (total - a)) / total
    start = 100 * (a - z) / (a - (z - data.num("TRI-WX-SNOW-SEC")))
    assert f'class="wx snow" style="left:{left:.2f}%;width:{width:.2f}%;--start:{start:.1f}%"' in tri


def test_ui_numbers_match_their_value(site: dict[Path, str]) -> None:
    """data-ui（画面の都合の数）は、表示している文字の数と同じ（「10万」は 100000）。"""
    for name, html_text in public_pages(site).items():
        for val, text in re.findall(r'<span data-ui="(\d+)">([^<]*)</span>', html_text):
            m = re.fullmatch(r"([\d,]+)(万?)", text)
            assert m, f"{name}: data-ui の文字 {text!r}"
            num = int(m.group(1).replace(",", "")) * (10_000 if m.group(2) else 1)
            assert num == int(val), f"{name}: data-ui={val} と文字 {text!r} が違う"


def test_rotation_from_ledger(data: build.Data) -> None:
    cycle, anchor, anchor_rule = build.rotation(data)
    assert len(cycle) == 8 and set(cycle) == set(build.RULE_ORDER)
    assert anchor_rule in build.RULE_ORDER
    assert "-".join(f"{x:02d}" if i else str(x) for i, x in enumerate(anchor)) == data.rows["COM-ROT-ANCHOR"].value


# ---------------------------------------------------------------- 書式


@pytest.mark.parametrize(("x", "want"), [(0, "0"), (1500000, "1,500,000"), (0.75, "0.75"), (1.5, "1.5"), (6.666, "6.67")])
def test_fmt(x: float, want: str) -> None:
    assert build.fmt(x) == want


@pytest.mark.parametrize(("x", "want"), [(1160, "19:20"), (0, "0:00"), (65, "1:05"), (1200, "20:00")])
def test_mmss(x: float, want: str) -> None:
    assert build.mmss(x) == want


def test_signed_uses_true_minus() -> None:
    assert build.signed(10) == "+10"
    assert build.signed(-10) == "−10"
    assert build.signed(0) == "0"
