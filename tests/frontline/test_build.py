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


def test_analytics_tag_matches_config(site: dict[Path, str]) -> None:
    """計測タグ（Cloudflare Web Analytics）は、トークンがあるときだけ本文のページの head に1つ入る。

    入口と移転案内には付けない（すぐ移るので、移り先と同じ閲覧を二重に数えてしまう）。
    トークンが空ならどのページにも出さない。変異テストを兼ねる（HTML を手で書き換えても検出する）。
    """
    for path, text in site.items():
        rel = path.relative_to(FRONT).as_posix()
        count = text.count(build.CF_BEACON_URL)
        assert count == (1 if build.CF_BEACON_TOKEN and rel.split("/")[0] in i18n.LANGS else 0), rel
        if count:
            assert text.index(build.CF_BEACON_URL) < text.index("</head>"), f"{rel}: head の外"
            assert build.CF_BEACON_TOKEN in text, f"{rel}: トークンがない"


# 数字を含むが、ゲームの値ではない決まった言い回し（単位の「1」や固有名）。ここに足すときは値でないことを確かめる
UI_PHRASES = ["1基の合計", "2回目から", "2巡目", "2Dマップ", "サークル1つ"]


def ui_phrases(lang: str) -> list[str]:
    """例外の言い回し（その言語での形）。訳は、例外を含む日本語の雛形の訳から、差し込み {n} の間の地の文字を取る。"""
    if lang == "ja":
        return UI_PHRASES
    import i18n

    _, ui, _ = i18n._tables()
    out = []
    for key, row in ui.items():
        if any(p in key for p in UI_PHRASES):
            out += [f.strip() for f in re.split(r"\{\d+\}", row.get(lang, "")) if re.search(r"\d", f)]
    return sorted(set(out), key=len, reverse=True)


def test_every_number_has_a_source(site: dict[Path, str]) -> None:
    """数字を含む文字は、data-src（台帳の行）か data-ui（画面の都合の数）を持つ要素の中にある。"""
    missing = []
    for name, html_text in public_pages(site).items():
        lang = name.split("/")[0] if name.split("/")[0] in i18n.FOREIGN else "ja"
        for text, anc in text_nodes(html_text):
            for phrase in ui_phrases(lang):
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
    name, html_text = "ja/triumph/index.html", pages["ja/triumph/index.html"]
    for e in entries:
        if e["範囲"] == "全体":
            injected = html_text.replace("</main>", f"<p>{e['旧値']}</p></main>", 1)
        else:
            injected = html_text.replace("</main>", f'<span data-src="{e["行ID"]}">{e["旧値"]}</span></main>', 1)
        assert find_retired({name: injected}, [e]), f"{e['行ID']} の旧値 {e['旧値']!r} を検出できない"
    # 台帳の書き方（桁区切りなし・波線の違い）で登録しても、ページの書き方を検出できる
    sec = pages["ja/secure/index.html"]
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
    assert build.mmss(first) in shown(site, "ja/secure/index.html", ["COM-MATCH-TIME", "SEC-EVT-FIRST"])
    tele = first + n("SEC-EVT-PANEL-LEAD")
    assert build.mmss(tele) in shown(site, "ja/secure/index.html", ["COM-MATCH-TIME", "SEC-EVT-FIRST", "SEC-EVT-PANEL-LEAD"])
    # 拠点の1分あたりと、伸びが大きい拠点の数（増え方が最小の増え方より大きいところ）
    vals = [n(f"SEC-FLAG-RATE-{i}") for i in range(1, 10)]
    for i in range(1, 10):
        rid = f"SEC-FLAG-RATE-{i}"
        want = build.fmt(n(rid) * 60 / n("SEC-FLAG-TICK")) + "/分"  # 単位つき（2026-10-29 ユーザーの指示）
        assert want in shown(site, "ja/secure/index.html", [rid, "SEC-FLAG-TICK"]), rid
    inc = [b - a for a, b in zip([0.0] + vals[:-1], vals)]
    jumps = [str(i) for i in range(2, 10) if inc[i - 1] > min(inc)]
    big2 = re.search(r'<span class="big2">(.*?)</div>', public_pages(site)["ja/secure/index.html"]).group(1)
    assert re.findall(r'<span class="n" data-src="[^"]+">(\d+)</span>', big2) == jumps
    # 中央の1回の合計と、邀撃システムの最大の回数（合計には「戦術値」を付ける）
    drone = build.fmt(n("SEC-DRONE-PTS") * n("SEC-DRONE-COUNT")) + "戦術値"
    assert drone in shown(site, "ja/secure/index.html", ["SEC-DRONE-PTS", "SEC-DRONE-COUNT"])
    cmdr = build.fmt(n("SEC-CMDR-PTS") * n("SEC-CMDR-SPOTS")) + "戦術値"
    assert cmdr in shown(site, "ja/secure/index.html", ["SEC-CMDR-PTS", "SEC-CMDR-SPOTS"])
    node = shown(site, "ja/secure/index.html", ["SEC-NODE-PTS", "SEC-NODE-REFILLS", "SEC-NODE-PTS-UNIT"])
    assert build.fmt(n("SEC-NODE-PTS") * (n("SEC-NODE-REFILLS") + 1)) + "戦術値" in node
    assert build.fmt(n("SEC-NODE-REFILLS") + 1) + "回" in shown(site, "ja/secure/index.html", ["SEC-NODE-REFILLS", "SEC-NODE-PTS-UNIT"])
    # シールロック・オンサル: 1分あたりと、枯れるまで
    for k in "BAS":
        tot, tk, iv = f"SEI-TOME-{k}-TOTAL", f"SEI-TOME-{k}-TICK", "SEI-TOME-TICK-SEC"
        assert build.fmt(n(tk) * 60 / n(iv)) + "/分" in shown(site, "ja/seize/index.html", [tk, iv])
        assert pages.dur(n(tot) / n(tk) * n(iv)) in shown(site, "ja/seize/index.html", [tot, tk, iv])
        tk2, iv2 = f"NAA-OVOO-{k}-TICK", "NAA-OVOO-TICK-SEC"
        assert build.fmt(n(tk2) * 60 / n(iv2)) + "/分" in shown(site, "ja/naadam/index.html", [tk2, iv2])
    # オンサル: 最初に契約できる時刻
    first_claim = total - (n("NAA-SPAWN-FIRST") + n("NAA-WARN-SEC"))
    assert build.mmss(first_claim) in shown(site, "ja/naadam/index.html", ["COM-MATCH-TIME", "NAA-SPAWN-FIRST", "NAA-WARN-SEC"])
    # 演習戦: 制圧中の1分あたり
    for k in "BAS":
        tot = f"TRI-OBJ-{k}-TOTAL"
        want = build.fmt(n(tot) * 60 / n("TRI-CLAIM-DURATION")) + "/分"
        assert want in shown(site, "ja/triumph/index.html", [tot, "TRI-CLAIM-DURATION"])
    # 砕氷戦: 大の最初の起動、小の2巡目の最速（未確認の規則による）、10万HPあたり
    lead = n("SHA-ICE-WARN-LEAD")
    l_first = total - (n("SHA-L-FIRST-WARN") + lead)
    assert build.mmss(l_first) in shown(site, "ja/shatter/index.html", ["COM-MATCH-TIME", "SHA-L-FIRST-WARN", "SHA-ICE-WARN-LEAD"])
    s_first = total - (n("SHA-S-FIRST-DELAY") + lead)
    s_second = s_first - (n("SHA-S-REACT") + lead)
    assert build.mmss(s_second) in shown(
        site, "ja/shatter/index.html", ["SHA-S-FIRST-ACTIVE", "SHA-S-REACT", "SHA-ICE-WARN-LEAD", "SHA-S-REACT-RULE"])
    for s_ in "LS":
        want = build.fmt1(n(f"SHA-{s_}-DATA") / n(f"SHA-{s_}-HP") * pages.PER_UNIT_HP)
        assert want in shown(site, "ja/shatter/index.html", [f"SHA-{s_}-DATA", f"SHA-{s_}-HP"]), s_
    # ジョブ: LB の秒数（基準＋補正）。召喚士は2つの LB
    for code in ["PLD", "NIN", "BRD", "DNC"]:
        want = build.fmt(n(f"COM-LBB-{code}") + n(f"COM-JOB-{code}-LB")) + "秒"
        assert want in shown(site, "ja/jobs/index.html", [f"COM-LBB-{code}", f"COM-JOB-{code}-LB"]), code
    smn = {build.fmt(n(b) + n("COM-JOB-SMN-LB")) + "秒" for b in ("COM-LBB-SMN-BAHAMUT", "COM-LBB-SMN-PHOENIX")}
    got = set(shown(site, "ja/jobs/index.html", ["COM-LBB-SMN-BAHAMUT", "COM-LBB-SMN-PHOENIX", "COM-JOB-SMN-LB"]))
    assert smn <= got


def test_band_positions_match_ledger(site: dict[Path, str], data: build.Data) -> None:
    """帯の区切りと天候の位置が、台帳の時刻から計算した位置にある。"""
    total = data.num("COM-MATCH-TIME") * 60
    seize = public_pages(site)["ja/seize/index.html"]
    sw = data.clock("SEI-CAP-SWITCH", "残り時間（分:秒）")
    assert re.findall(r'class="seg" style="flex:(\d+)"', seize)[:2] == [str(round(total - sw)), str(round(sw))]
    tri = public_pages(site)["ja/triumph/index.html"]
    a, z = (x * 60 for x in data.span("TRI-WX-SNOW-START", "分（残り時間）"))
    left = 100 * (total - a) / total
    width = 100 * ((total - (z - data.num("TRI-WX-SNOW-SEC"))) - (total - a)) / total
    start = 100 * (a - z) / (a - (z - data.num("TRI-WX-SNOW-SEC")))
    assert f'class="wx snow" style="left:{left:.2f}%;width:{width:.2f}%;--start:{start:.1f}%"' in tri


def test_ui_numbers_match_their_value(site: dict[Path, str]) -> None:
    """data-ui（画面の都合の数）は、表示している文字の数と同じ（「10万」は 100000）。"""
    for name, html_text in public_pages(site).items():
        for val, text in re.findall(r'<span data-ui="(\d+)">([^<]*)</span>', html_text):
            m = re.fullmatch(r"([\d,. ]+)(万?)", text)  # 桁区切りは言語ごと（, . 狭い空白）
            assert m, f"{name}: data-ui の文字 {text!r}"
            num = int(re.sub(r"[,. ]", "", m.group(1))) * (10_000 if m.group(2) else 1)
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


# ---------------------------------------------------------------- 多言語（英語・ドイツ語・フランス語・韓国語・中国語。frontline/data/i18n/）

import i18n

FOREIGN = i18n.FOREIGN
KANA_RE = re.compile(r"[぀-ヿ]")
JA_RE = re.compile(r"[぀-ヿ㐀-鿿！-～]")  # ラテン文字の言語に残ってはいけない文字（漢字も日本語の訳し漏れの印）


def test_i18n_tables_have_no_errors(site: dict[Path, str]) -> None:
    """訳の表: 足りない訳・空の訳・差し込みの食い違い・元にない数・使っていない訳がない。"""
    used = {"ui": set(i18n.State.used_ui), "text": set(i18n.State.used_text)}
    assert i18n.check(used) == []


def test_every_language_has_every_page(site: dict[Path, str]) -> None:
    ja = sorted(p.removeprefix("ja/") for p in public_pages(site, include_sources=True) if p.startswith("ja/"))
    for lg in FOREIGN:
        assert sorted(p.removeprefix(lg + "/") for p in public_pages(site, include_sources=True) if p.startswith(lg + "/")) == ja


def test_foreign_pages_have_no_japanese(site: dict[Path, str]) -> None:
    """訳したページに日本語が残っていない（訳し漏れ）。

    英・独・仏は漢字も日本語の印として見る。韓国語・中国語は漢字を正当に使うので、
    かな（とカタカナの「・」）だけを見る。出典一覧の名称などの引用と言語の切り替えは除く。
    """
    leaks = []
    for name, html_text in public_pages(site, include_sources=True).items():
        lg = name.split("/")[0]
        if lg not in FOREIGN:
            continue
        leak_re = JA_RE if lg in ("en", "de", "fr") else KANA_RE
        for text, anc in text_nodes(html_text):
            if any(a.get("class") == "langs" for _, a in anc):
                continue
            if any("cite" in a.get("class", "").split() for _, a in anc):
                continue  # 出典の名称は原文のまま（引用）
            if leak_re.search(text):
                leaks.append(f"{name}: {text.strip()[:40]!r}")
        for attr in re.findall(r'(?:title|alt|aria-label)="([^"]*)"', re.sub(r'<span class="langs">.*?</span>', "", html_text)):
            if leak_re.search(attr):
                leaks.append(f"{name}: 属性 {attr[:40]!r}")
    assert leaks == []


def test_foreign_pages_keep_every_source(site: dict[Path, str]) -> None:
    """訳したページでも、数字の出どころ（data-src）は日本語のページと同じ並び。"""
    pages = public_pages(site)
    for name, html_text in pages.items():
        lg = name.split("/")[0]
        if lg not in FOREIGN:
            continue
        ja = pages["ja/" + name.removeprefix(lg + "/")]
        assert sorted(re.findall(r'data-src="([^"]*)"', html_text)) == sorted(re.findall(r'data-src="([^"]*)"', ja)), name


def _foreign_build(data: build.Data, mutate) -> None:
    i18n.reload()
    tables = i18n._tables()
    saved = copy.deepcopy(tables)
    try:
        mutate(*tables)
        i18n.State._cache = tables
        build.build(data)
    finally:
        i18n.State._cache = saved


def test_build_refuses_stale_translation(data: build.Data) -> None:
    """変異テスト: 日本語の表示文が変わった（訳したときの元の文と違う）行があると、生成が止まる。"""
    def stale(terms, ui, texts):
        rid = next(iter(texts))
        texts[rid]["元の文"] += "（変更）"

    with pytest.raises(build.BuildError, match="古い"):
        _foreign_build(data, stale)


def test_build_refuses_missing_translation(data: build.Data) -> None:
    """変異テスト: 訳が空の言い回しがあると、生成が止まる（日本語のまま出さない）。"""
    def missing(terms, ui, texts):
        key = next(k for k in ui if "{0}" in k)
        ui[key]["de"] = ""

    with pytest.raises(build.BuildError, match="訳がない"):
        _foreign_build(data, missing)


def test_check_finds_added_number() -> None:
    """変異テスト: 訳に元の日本語にない数を足すと、検査が見つける。"""
    i18n.reload()
    terms, ui, texts = i18n._tables()
    saved = copy.deepcopy((terms, ui, texts))
    try:
        rid = next(iter(texts))
        texts[rid]["fr"] += " 98765"
        assert any("98765" in e for e in i18n.check())
    finally:
        i18n.State._cache = saved


CHINESE_TEMPLATE_ISSUES = (
    ("前の二重", re.compile(r"前\s*\d+\s*秒前")),
    ("後の二重", re.compile(r"[后後]\s*\d+\s*秒[后後]")),
    ("每秒", re.compile(r"\d每秒")),
    ("第数列", re.compile(r"第\s*数列|第\s*數列")),
)


def chinese_template_issues(text: str) -> list[str]:
    """中国語の文に残ってはいけない組み立て（二重の前後・每秒・数列）を返す。"""
    return [label for label, pat in CHINESE_TEMPLATE_ISSUES if pat.search(text)]


def test_chinese_time_words_are_not_doubled(site: dict[Path, str]) -> None:
    """中国語で「前／後」が二重にならず、tick と数の並びも崩れていない。

    2026-11-17 の査読で、雛形の「前」と差し込み値の「30秒前」が重なって「启动前30秒前」になり、
    tick が「3每秒」、数の並びが「第数列：4」になっていた（{n} と数の検査は通っていた）。
    """
    bad = []
    for name, html_text in public_pages(site).items():
        if name.split("/")[0] not in ("zh-hans", "zh-hant"):
            continue
        text = " ".join(t for t, _ in text_nodes(html_text))
        for label in chinese_template_issues(text):
            bad.append(f"{name}: {label}")
    assert bad == []


def test_chinese_template_checker_detects_old_breaks() -> None:
    """変異テスト: 直した 4 種の崩れを、検査器が実際に検出できる（簡体字の「后」も含む）。

    正しい「数の並び」（`数列：4 · 7`）は禁止しない（第 3 回査読の指摘）。
    """
    for broken in ("启动前30秒前", "停止后15秒后", "停止後15秒後", "3每秒", "第数列：4", "第數列：4"):
        assert chinese_template_issues(broken), broken
    assert chinese_template_issues("启动30秒前 · 每3秒：2 · 第4 · 第7处大幅增长（蓝）") == []
    assert chinese_template_issues("数列：4 · 7") == []  # 正当な語（「数の並び」）


# 簡体字の出典の対応表。apply_cn_official.py とは別に、テスト側で独立して持つ（写し間違いを互いに検出するため）
CN_EVENT_URL = "https://actff1.web.sdo.com/project/160810event/page{}.html"
CN_JOB_URL = "https://actff1.web.sdo.com/project/20190917jobguid/index.html#/continfo/{}/pvp"
CN_INDEX_URL = "https://actff1.web.sdo.com/project/20190917jobguid/index.html#/indexpvp"
CN_PVP_URL = CN_EVENT_URL.format(1)
CN_LB_JOB = {
    "lb-PLD": "paladin", "lb-WAR": "warrior", "lb-DRK": "darkknight", "lb-GNB": "gunbreaker",
    "lb-WHM": "whitemage", "lb-SCH": "scholar", "lb-AST": "astrologian", "lb-SGE": "sage",
    "lb-MNK": "monk", "lb-DRG": "dragoon", "lb-NIN": "ninja", "lb-SAM": "samurai",
    "lb-RPR": "reaper", "lb-VPR": "viper", "lb-BRD": "bard", "lb-MCH": "machinist",
    "lb-DNC": "dancer", "lb-BLM": "blackmage", "lb-SMN-1": "summoner", "lb-SMN-2": "summoner",
    "lb-RDM": "redmage", "lb-PCT": "pictomancer",
}
CN_RULE_PAGE = {
    "rule-secure-": "4_1", "rule-seize-": "4_2", "rule-shatter-": "4_3",
    "rule-naadam-": "4_4", "rule-triumph-": "4_5",
}
CN_TERM_PAGE = {
    "term-邀撃ドローン": "4_1", "term-邀撃ドローンα": "4_1", "term-邀撃コマンダー": "4_1",
    "term-邀撃システム": "4_1", "term-戦術値": "4_1", "term-戦意高揚": "4_1",
    "term-戦意値": "4_1", "term-アシスト": "4_1",
    "term-情報値": "4_2", "term-アラガントームリス": "4_2",
    "term-アイスドトームリス": "4_3",
    "term-無垢の土地": "4_4", "term-撃破": "4_4", "term-被撃破": "4_4",
    "term-戦略値": "4_5", "term-雪": "4_5", "term-オーロラ": "4_5",
}


def cn_expected_source(key: str) -> str:
    for prefix, page in CN_RULE_PAGE.items():
        if key.startswith(prefix):
            return CN_EVENT_URL.format(page)
    if key in CN_LB_JOB:
        return CN_JOB_URL.format(CN_LB_JOB[key])
    if key.startswith("job-") or key.startswith("role-"):
        return CN_INDEX_URL
    if key in ("term-リミットゲージ", "term-リミットブレイク"):
        return CN_PVP_URL
    return CN_EVENT_URL.format(CN_TERM_PAGE[key])


def _source_mismatches(rows: list[tuple[str, str]]) -> list[str]:
    bad = []
    for key, src in rows:
        m = re.search(r"zh-hans: ([^;]+)", src)
        if not m or m.group(1).strip() != cn_expected_source(key):
            bad.append(key)
    return bad


def test_zh_hans_terms_use_correct_chinese_official_page() -> None:
    """簡体字の用語の出典は、キーごとに正しい中国版公式ページを指す（同じ URL への寄せを検出する）。"""
    found = ledger.find_table(i18n.TERMS_MD, i18n.TERM_COLS)
    assert found is not None
    rows = [(cells[0], cells[-1]) for cells in found[0]]
    assert _source_mismatches(rows) == []


def test_source_check_detects_wrong_page() -> None:
    """変異テスト: 職違い・ページ違いの URL を、キーごとの照合が検出する。"""
    all_4_5 = CN_EVENT_URL.format("4_5")
    assert _source_mismatches([("lb-PLD", "zh-hans: " + CN_JOB_URL.format("warrior"))]) == ["lb-PLD"]
    assert _source_mismatches([
        ("lb-PLD", "zh-hans: " + all_4_5),                              # 職違い
        ("rule-secure-map", "zh-hans: " + CN_EVENT_URL.format("4_1")),  # 正しい
    ]) == ["lb-PLD"]


def test_entry_and_moved_pages(site: dict[Path, str]) -> None:
    """入口は全言語へのリンクと振り分けだけ。前の日本語のページの場所（frontline/secure/ など）は ja/ の同じページへ移る。"""
    entry = site[FRONT / "index.html"]
    assert re.findall(r'<a href="([\w-]+)/" data-lang', entry) == i18n.LANGS
    assert "location.replace" in entry and "© SQUARE ENIX" in entry
    for name in build.OLD_JA_PAGES:
        moved = site[FRONT / name / "index.html"]
        assert f'url=../ja/{name}/' in moved and (FRONT / "ja" / name / "index.html") in site
