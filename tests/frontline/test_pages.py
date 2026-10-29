"""公開ページをブラウザで開いて確かめる（Playwright。ブラウザがなければ飛ばす）。

- 想定する表示領域すべてで、スクロールが出ず、文字が欄の外にはみ出さない（計画のアンチゴール「スクロールしないと見えない」）。
- 文字の下限: 画面上の実寸で 24px 以上（モックの倍。ユーザーの指示「文字は倍でいい」）。
- 今日のルール: ユーザーがゲーム内で確かめた日（2026-10-27 オンサル・ハカイル、10-28 ウォーコー・チーテ）と、
  0:00 JST の切り替わり。
- 自分のジョブの選択（3つまで）と記憶、リンク切れがないこと。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

import pytest
from conftest import FRONT

sync_api = pytest.importorskip("playwright.sync_api")

MIN_PX = 24.0  # 画面上の実寸（CSS px × 表示倍率 × デバイスの倍率）
VIEWPORTS = [
    (1920, 945, 1.0),  # 1920×1080・表示スケール100%・最大化（ブックマークバーなし）
    (1920, 912, 1.0),  # 同・ブックマークバーあり
    (1920, 1080, 1.0),  # 全画面（F11）
    (1536, 801, 1.25),  # 表示スケール125%・最大化
]
PAGE_NAMES = ["index.html", "secure/index.html", "seize/index.html", "shatter/index.html", "naadam/index.html",
              "triumph/index.html", "jobs/index.html"]
# 4言語とも同じ検査をする（ドイツ語・フランス語は文が長いので、1画面に収まるかを必ず確かめる）
PAGES = [f"{lg}/{p}" for lg in ("ja", "en", "de", "fr") for p in PAGE_NAMES]
JST = timezone(timedelta(hours=9))

MEASURE = """() => {
  const st = document.getElementById('stage');
  // 実際にかかっている倍率（CSS で打ち消されることがあるので、インラインの指定ではなく計算後の行列から読む）
  const tf = getComputedStyle(st).transform;
  const mm = tf && tf !== 'none' ? tf.match(/matrix\\(([^,]+)/) : null;
  const s = mm ? parseFloat(mm[1]) : 1;
  const shown = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !el.closest('[hidden]') && getComputedStyle(el).visibility !== 'hidden'; };
  const texts = [...document.querySelectorAll('#stage *')].filter(e => !e.closest('svg') && shown(e) &&
      [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()));
  const small = texts.map(e => ({px: parseFloat(getComputedStyle(e).fontSize) * s * devicePixelRatio, t: e.textContent.trim().slice(0, 30)}))
                     .filter(x => x.px < __MIN__ - 0.5);
  const out = [];
  for (const e of texts) {
    const r = e.getBoundingClientRect();
    const box = e.closest('.ev, .rk, .card, .hdr, .ftr, .panel').getBoundingClientRect();
    if (r.left < box.left - 1 || r.right > box.right + 1 || r.top < box.top - 1 || r.bottom > box.bottom + 1)
      out.push(e.textContent.trim().slice(0, 30));
  }
  const panel = [...document.querySelectorAll('.panel')].find(p => !p.hidden);
  const main = panel.querySelector('main').getBoundingClientRect();
  const spill = [...panel.querySelectorAll('main .card, main table')].filter(shown)
                  .filter(c => c.getBoundingClientRect().bottom > main.bottom + 1).map(c => (c.querySelector('h2') || c).textContent.trim().slice(0, 20));
  // スクロールは html と body の両方を見る（body が overflow:auto だと、はみ出しは body の中で起きる）
  const over = el => [el.scrollWidth > el.clientWidth + 1, el.scrollHeight > el.clientHeight + 1];
  const de = document.documentElement, bd = document.body;
  const scroll = [de.scrollWidth > innerWidth || over(bd)[0], de.scrollHeight > innerHeight || over(bd)[1]];
  // 見出しの欄（タイトル・勝利条件・撃破・タブ）どうしが重ならず、欄の中で文字があふれない
  // （2026-10-29、撃破に単位を足したとき、文字は見出しの中に収まったまま隣の欄と重なり、上の検査を素通りした）
  const hdr = panel.querySelector('.hdr');
  const kids = hdr ? [...hdr.children].filter(shown) : [];
  const clash = [];
  if (hdr && hdr.scrollWidth > hdr.clientWidth + 1) clash.push('あふれ: hdr');
  kids.forEach((k, i) => {
    if (k.scrollWidth > k.clientWidth + 1) clash.push('あふれ: ' + k.className);
    const a = k.getBoundingClientRect();
    kids.slice(i + 1).forEach(o => {
      const b = o.getBoundingClientRect();
      if (a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1)
        clash.push(k.className + ' と ' + o.className);
    });
  });
  // キャンバスが表示領域からはみ出していないか（縮小が効いていないと、ここで分かる）
  const r = st.getBoundingClientRect();
  const offscreen = r.right > innerWidth + 1 || r.bottom > innerHeight + 1;
  // 「…」で切れている文字（見出しの説明など。overflow:hidden の欄で、中身が欄より広い）
  const cut = [...panel.querySelectorAll('.sub, .wx, .seg, .chip, .st')].filter(shown)
                .filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.textContent.trim().slice(0, 30));
  return {scroll, offscreen, small: small.slice(0, 5), outside: out.slice(0, 5), spill, clash, cut};
}""".replace("__MIN__", str(MIN_PX))


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = None
        for channel in ("chrome", "msedge", None):
            try:
                b = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
            except Exception:  # noqa: BLE001 入っていないブラウザは次を試す
                b = None
            if b is not None:
                break
        if b is None:
            pytest.skip("Chromium 系のブラウザがない")
        yield b
        b.close()


def open_page(browser, rel: str, w: int, h: int, dpr: float, *, jobs: list[str] | None = None, now_ms: int | None = None,
              langs: list[str] | None = None):
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr)
    # ブラウザの言語（指定がなければ日本語。トップでの自動の切り替えが、ほかの検査を邪魔しないように）
    ctx.add_init_script(f"Object.defineProperty(navigator, 'languages', {{get: function () {{ return {json.dumps(langs or ['ja-JP'])}; }}}});")
    if jobs is not None:
        ctx.add_init_script(f"localStorage.setItem('fl-myjobs', {json.dumps(json.dumps(jobs))});")
    if now_ms is not None:
        ctx.add_init_script(f"Date.now = function () {{ return {now_ms}; }};")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((FRONT / rel).resolve().as_uri())
    page.wait_for_timeout(250)
    return ctx, page, errors


@pytest.mark.parametrize("rel", PAGES)
@pytest.mark.parametrize(("w", "h", "dpr"), VIEWPORTS)
@pytest.mark.parametrize("jobs", [[], ["NIN", "WHM", "SMN"]], ids=["no-jobs", "3-jobs"])
def test_fits_one_screen(browser, rel: str, w: int, h: int, dpr: float, jobs: list[str]) -> None:
    ctx, page, errors = open_page(browser, rel, w, h, dpr, jobs=jobs)
    try:
        r = page.evaluate(MEASURE)
        assert r["scroll"] == [False, False], "スクロールが出る"
        assert not r["offscreen"], "キャンバスが表示領域からはみ出す（縮小が効いていない）"
        assert r["spill"] == [], f"欄が下にはみ出す: {r['spill']}"
        assert r["outside"] == [], f"文字が欄の外にはみ出す: {r['outside']}"
        assert r["clash"] == [], f"見出しの欄が重なる・あふれる: {r['clash']}"
        assert r["cut"] == [], f"文字が切れている（…）: {r['cut']}"
        assert r["small"] == [], f"文字が小さすぎる（{MIN_PX}px 未満）: {r['small']}"
        assert errors == []
    finally:
        ctx.close()


def test_header_checker_detects_clash(browser) -> None:
    """変異テスト: 見出しのタイトルを長くして隣の欄に重ねると、検査が見つける。"""
    ctx, page, _ = open_page(browser, "ja/shatter/index.html", 1920, 945, 1.0)
    try:
        assert page.evaluate(MEASURE)["clash"] == []
        page.evaluate("document.querySelector('.panel .hdr .title h1').textContent = 'フィールド・オブ・グローリー（とても長い名前）'")
        assert page.evaluate(MEASURE)["clash"]
    finally:
        ctx.close()


def test_fit_checker_detects_overflow(browser) -> None:
    """変異テスト: 欄に行を足して画面からあふれさせると、検査が見つける。"""
    ctx, page, _ = open_page(browser, "ja/triumph/index.html", 1920, 945, 1.0, jobs=["NIN", "WHM", "SMN"])
    try:
        page.evaluate("""() => { const ul = document.querySelector('.panel .rules');
            for (let i = 0; i < 6; i++) { const li = document.createElement('li'); li.textContent = 'あふれさせるための行'; ul.appendChild(li); } }""")
        r = page.evaluate(MEASURE)
        assert r["spill"] or r["outside"] or any(r["scroll"])
    finally:
        ctx.close()


def test_scroll_checker_detects_unscaled_page(browser) -> None:
    """変異テスト: 縮小を止めて（body に scroll を付けて）125% で開くと、スクロールとはみ出しを検査が見つける。

    2026-10-29 まで、ジョブ補正のページはこの状態で、html だけを見る検査を素通りしていた。
    """
    ctx, page, _ = open_page(browser, "ja/jobs/index.html", 1536, 801, 1.25)
    try:
        page.evaluate("document.body.classList.add('scroll')")
        r = page.evaluate(MEASURE)
        assert any(r["scroll"]) and r["offscreen"]
    finally:
        ctx.close()


def test_font_checker_detects_small_text(browser) -> None:
    """変異テスト: 文字を下限より小さくすると、検査が見つける。"""
    ctx, page, _ = open_page(browser, "ja/secure/index.html", 1920, 945, 1.0)
    try:
        page.evaluate("document.querySelector('.card h2 .ttl').style.fontSize = '12px'")
        assert page.evaluate(MEASURE)["small"]
    finally:
        ctx.close()


def jst_ms(y: int, mo: int, d: int, hh: int = 12, mm: int = 0, ss: int = 0) -> int:
    return int(datetime(y, mo, d, hh, mm, ss, tzinfo=JST).timestamp() * 1000)


@pytest.mark.parametrize(
    ("when", "rule"),
    [
        # ユーザーがゲーム内で確かめた日（frontline/data/ingame-checks.md の IG-ROT-TODAY）
        (jst_ms(2026, 10, 27), "naadam"),
        (jst_ms(2026, 10, 28), "triumph"),
        # 切り替わりは 0:00 JST
        (jst_ms(2026, 10, 27, 23, 59, 59), "naadam"),
        (jst_ms(2026, 10, 28, 0, 0, 0), "triumph"),
    ],
)
def test_today_rule(browser, when: int, rule: str) -> None:
    ctx, page, errors = open_page(browser, "ja/index.html", 1920, 945, 1.0, now_ms=when)
    try:
        visible = page.evaluate("[...document.querySelectorAll('.panel[data-rule]')].filter(p => !p.hidden).map(p => p.dataset.rule)")
        badge = page.evaluate("[...document.querySelectorAll('[data-today-badge]')].filter(b => !b.hidden).map(b => b.dataset.todayBadge)")
        assert visible == [rule]
        assert set(badge) == {rule}
        assert errors == []
    finally:
        ctx.close()


def test_anchor_day_is_secure(browser, data) -> None:
    """台帳の起点の日（COM-ROT-ANCHOR）は、項目名に書かれたルールになる。"""
    import build

    _, anchor, anchor_rule = build.rotation(data)
    ctx, page, _ = open_page(browser, "ja/index.html", 1920, 945, 1.0, now_ms=jst_ms(*anchor))
    try:
        visible = page.evaluate("[...document.querySelectorAll('.panel[data-rule]')].filter(p => !p.hidden).map(p => p.dataset.rule)")
        assert visible == [anchor_rule]
    finally:
        ctx.close()


def test_tabs_switch_panels(browser) -> None:
    ctx, page, errors = open_page(browser, "ja/index.html", 1920, 945, 1.0, now_ms=jst_ms(2026, 10, 28))
    try:
        page.click(".panel:not([hidden]) .nav a[data-go='seize']")
        visible = page.evaluate("[...document.querySelectorAll('.panel[data-rule]')].filter(p => !p.hidden).map(p => p.dataset.rule)")
        assert visible == ["seize"]
        assert page.url.endswith("index.html")  # 移動せずに切り替わる
        assert errors == []
    finally:
        ctx.close()


# ジョブ補正の欄（2026-10-29 ユーザーの指示で、選ぶ欄と表をいつも両方出す。押したらすぐ下の表に出る）
SHOWN_JOBS = "[...document.querySelectorAll('.myjobs tr[data-job]')].filter(r => !r.hidden).map(r => r.dataset.job)"
EMPTY_SHOWN = "!document.querySelector('.myjobs tr.empty').hidden"
PICKER_SHOWN = "document.querySelector('.myjobs .picker').getBoundingClientRect().height > 0"


def test_job_picker_keeps_three(browser) -> None:
    # 新しいコンテキストは記憶が空（初期化スクリプトで空にすると、再読み込みのたびに消えてしまう）
    ctx, page, errors = open_page(browser, "ja/secure/index.html", 1920, 945, 1.0)
    try:
        assert page.evaluate(PICKER_SHOWN) and page.evaluate(EMPTY_SHOWN)
        assert page.evaluate(SHOWN_JOBS) == []
        page.click(".myjobs [data-pick='PLD']")
        assert page.evaluate(SHOWN_JOBS) == ["PLD"]  # 押したらすぐ出る（ボタンを押し直さない）
        assert not page.evaluate(EMPTY_SHOWN)
        for code in ["WHM", "NIN", "BRD"]:
            page.click(f".myjobs [data-pick='{code}']")
        stored = json.loads(page.evaluate("localStorage.getItem('fl-myjobs')"))
        assert stored == ["WHM", "NIN", "BRD"]  # 4つ目を選ぶと、最初の1つが外れる
        assert page.evaluate(SHOWN_JOBS) == stored  # 選んだ順
        page.click(".myjobs [data-pick='NIN']")  # もう一度押すと外れる
        assert page.evaluate(SHOWN_JOBS) == ["WHM", "BRD"]
        page.reload()
        page.wait_for_timeout(200)
        assert page.evaluate(SHOWN_JOBS) == ["WHM", "BRD"]
        assert page.evaluate(PICKER_SHOWN) and not page.evaluate(EMPTY_SHOWN)
        assert errors == []
    finally:
        ctx.close()


def test_job_picker_without_storage(browser) -> None:
    """ブラウザに記憶できない（Cookie をすべてブロックした状態など）ときも、そのページの中では選べる。"""
    ctx = browser.new_context(viewport={"width": 1920, "height": 945})
    ctx.add_init_script(
        "Object.defineProperty(window, 'localStorage', {get: function () { throw new DOMException('blocked', 'SecurityError'); }});"
    )
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto((FRONT / "ja/secure/index.html").resolve().as_uri())
        page.wait_for_timeout(200)
        for code in ["NIN", "WHM"]:
            page.click(f".myjobs [data-pick='{code}']")
        assert page.evaluate(SHOWN_JOBS) == ["NIN", "WHM"]
        assert errors == []
    finally:
        ctx.close()


def test_broken_storage_shows_guide(browser) -> None:
    """記憶が壊れている（知らないジョブの記号だけ）ときは、案内の行を出す（見出しだけの表にしない）。"""
    ctx, page, errors = open_page(browser, "ja/secure/index.html", 1920, 945, 1.0, jobs=["XXX", "1"])
    try:
        assert page.evaluate(SHOWN_JOBS) == []
        assert page.evaluate(PICKER_SHOWN) and page.evaluate(EMPTY_SHOWN)
        assert errors == []
    finally:
        ctx.close()


def test_relative_links_exist() -> None:
    missing = []
    for path in FRONT.rglob("index.html"):
        if "data" in path.relative_to(FRONT).parts:
            continue
        html_text = path.read_text(encoding="utf-8")
        for ref in re.findall(r'(?<![\w-])(?:href|src)="([^"#:?]+)', html_text):  # ?v= などは外して比べる
            target = (path.parent / ref).resolve()
            if ref.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                missing.append(f"{path.relative_to(FRONT).as_posix()}: {ref}")
    assert missing == []



# ---------------------------------------------------------------- 言語の切り替え


@pytest.mark.parametrize(
    ("langs", "stored", "want"),
    [
        (["de-DE", "en-US"], None, "de/index.html"),  # ブラウザの言語
        (["fr-CA"], None, "fr/index.html"),
        (["es-ES", "it"], None, "en/index.html"),  # 対応していない言語は英語
        (["ja-JP"], None, "ja/index.html"),  # 日本語
        (["en-US"], "ja", "ja/index.html"),  # 選んだ言語（記憶）が優先
        (["ja-JP"], "fr", "fr/index.html"),
    ],
)
def test_top_follows_browser_language(browser, langs, stored, want) -> None:
    ctx = browser.new_context(viewport={"width": 1920, "height": 945})
    ctx.add_init_script(f"Object.defineProperty(navigator, 'languages', {{get: function () {{ return {json.dumps(langs)}; }}}});")
    if stored:
        ctx.add_init_script(f"localStorage.setItem('fl-lang', {json.dumps(stored)});")
    page = ctx.new_page()
    try:
        page.goto((FRONT / "index.html").resolve().as_uri())
        page.wait_for_timeout(300)
        # ファイルで開くと、言語の版のフォルダ（de/ など）の URL になる（サーバーでは de/index.html が返る）
        assert page.url.endswith(want) or page.url.endswith(want.removesuffix("index.html")), page.url
        page.goto(page.url.rstrip("/") + "/index.html" if page.url.endswith("/") else page.url)
        assert page.evaluate("document.documentElement.lang") == want[:2]
    finally:
        ctx.close()


def test_language_switch_remembers_choice(browser) -> None:
    """切り替えで選んだ言語を記憶し、日本語のトップを開き直しても、その言語の版に移る。同じページの別の言語に移る。"""
    ctx, page, errors = open_page(browser, "ja/secure/index.html", 1920, 945, 1.0)
    try:
        page.click(".panel .langs a[data-lang='de']")
        page.wait_for_timeout(300)
        assert page.url.endswith("/de/secure/"), page.url
        assert page.evaluate("localStorage.getItem('fl-lang')") == "de"
        page.goto((FRONT / "index.html").resolve().as_uri())
        page.wait_for_timeout(300)
        assert page.url.endswith("de/index.html") or page.url.endswith("/de/"), page.url
        assert errors == []
    finally:
        ctx.close()


def test_moved_page_goes_to_ja(browser) -> None:
    """前の日本語のページの場所（公開済みの URL）は、ja/ の同じページへ移る。"""
    ctx, page, _ = open_page(browser, "secure/index.html", 1920, 945, 1.0)
    try:
        assert page.url.rstrip("/").endswith("ja/secure") or page.url.endswith("ja/secure/index.html"), page.url
    finally:
        ctx.close()


def test_flags_in_language_switch(browser) -> None:
    """言語の切り替えに国旗が出る（4つとも描かれている）。"""
    ctx, page, _ = open_page(browser, "ja/secure/index.html", 1920, 945, 1.0)
    try:
        sizes = page.evaluate("[...document.querySelectorAll('.panel:not([hidden]) .langs .flag')].map(f => f.getBoundingClientRect().width)")
        assert len(sizes) == 4 and all(w > 10 for w in sizes)
    finally:
        ctx.close()


def test_flags_stay_small_without_css(browser) -> None:
    """スタイルシートが古い（読めない）ままでも国旗は小さい（2026-10-29、公開直後に古い CSS のキャッシュで国旗が巨大になった）。"""
    ctx, page, _ = open_page(browser, "ja/seize/index.html", 1920, 945, 1.0)
    try:
        page.evaluate("document.querySelectorAll('link[rel=stylesheet]').forEach(l => l.remove())")
        widths = page.evaluate("[...document.querySelectorAll('.langs .flag')].map(f => f.getBoundingClientRect().width)")
        assert widths and max(widths) <= 31, widths
    finally:
        ctx.close()


def test_stylesheet_url_changes_with_css(site) -> None:
    """CSS の URL には中身のハッシュが付く（CSS を変えると URL が変わり、ブラウザのキャッシュを使わない）。"""
    import build

    for path, text in site.items():
        if "site.css" in text:  # 前の日本語の URL の案内ページは CSS を読まない
            assert f"site.css?v={build.css_version()}" in text, path
