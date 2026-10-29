"""ページの多言語化（日本語・英語・ドイツ語・フランス語）。

訳はすべて frontline/data/i18n/ の表に置く（ページやコードに訳を書かない）:
    terms.md  ゲームの用語（マップ名・ジョブ名・LB 名・オブジェクト名など）。各言語の公式サイトの表記をそのまま写す
    ui.md     画面の決まった言い回し。キーは日本語の雛形（{0} {1} … に値が入る）
    text.md   台帳の文章の値（表示文があれば表示文）の訳。行 ID で引き、訳したときの日本語（元の文）を持つ。
              日本語が変わると「元の文」と合わなくなり、生成が止まる（訳し直してから元の文を書き換える）

使い方:
    python frontline/tools/i18n.py check     # 訳の表の検査（足りない訳・古い訳・使っていない訳・数の足し込み）
    python frontline/tools/i18n.py collect   # 足りない訳の行を表の末尾に足す（訳の欄は空）

守ること:
- 訳に、元の日本語にない数を足さない（検査で止まる）。{0} などの差し込みは、数も順番も元と同じものを使う（順番は入れ替えてよい）。
- ゲームの用語は terms.md の公式の表記を使う。
- 日本語のページは、この仕組みを通しても1文字も変わらない（キーがそのまま出る）。
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from typing import ClassVar

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger

LANGS = ["ja", "en", "de", "fr"]
LANG_NAMES = {"ja": "日本語", "en": "English", "de": "Deutsch", "fr": "Français"}
I18N = ledger.DATA / "i18n"
TERMS_MD = I18N / "terms.md"
UI_MD = I18N / "ui.md"
TEXT_MD = I18N / "text.md"
TERM_COLS = ["キー", "日本語", "en", "de", "fr", "出典"]
UI_COLS = ["日本語", "en", "de", "fr", "メモ"]
TEXT_COLS = ["ID", "元の文", "en", "de", "fr"]
FOREIGN = LANGS[1:]
PLACEHOLDER = re.compile(r"\{(\d+)\}")
EMPTY = "∅"  # 訳の表で「この言語では何も出さない」（日本語の助数詞「か所」「体」など、雛形の側で言えているとき）


class I18nError(Exception):
    """訳がない・古い・形が合わない。"""


class State:
    lang = "ja"
    collect: dict[str, set] | None = None  # 集めるとき: {"ui": {キー}, "text": {(ID, 元の文)}}
    used_ui: ClassVar[set[str]] = set()
    used_terms: ClassVar[set[str]] = set()
    used_text: ClassVar[set[str]] = set()
    _cache: tuple | None = None


def set_lang(lang: str) -> None:
    if lang not in LANGS:
        raise I18nError(f"知らない言語: {lang}")
    State.lang = lang


def lang() -> str:
    return State.lang


def _tables() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    if State._cache is None:
        def load(path: Path, cols: list[str]) -> dict[str, dict[str, str]]:
            if not path.exists():
                return {}
            found = ledger.find_table(path, cols)
            if found is None:
                raise I18nError(f"{path}: 表（{' | '.join(cols)}）がない")
            out = {}
            for cells in found[0]:
                row = dict(zip(cols, cells))
                out[cells[1] if cols is TERM_COLS else cells[0]] = row
            return out

        State._cache = (load(TERMS_MD, TERM_COLS), load(UI_MD, UI_COLS), load(TEXT_MD, TEXT_COLS))
    return State._cache


def reload() -> None:
    State._cache = None


def _missing(kind: str, key, shown: str) -> str:
    if State.collect is not None:
        State.collect[kind].add(key)
        return f"⟦{shown}⟧"
    raise I18nError(f"{State.lang} の訳がない（{kind}）: {key}")


def L(key: str) -> str:
    """決まった言い回し（地の文字。呼ぶ側で esc する）。用語の表を先に引く。"""
    if State.lang == "ja":
        return key
    terms, ui, _ = _tables()
    if key in terms:
        State.used_terms.add(key)
        v = terms[key].get(State.lang, "")
        return v if v else _missing("terms", key, key)
    State.used_ui.add(key)
    v = ui.get(key, {}).get(State.lang, "")
    if v == EMPTY:
        return ""
    return v if v else _missing("ui", key, key)


def C(context: str, ja: str) -> str:
    """場所によって短く言い分けたい語（日本語は同じ）。キーは「場所: 日本語」の形（例「表の行: 戦意値」）。日本語では ja を返す。"""
    if State.lang == "ja":
        return ja
    return L(f"{context}: {ja}")


def HC(context: str, key: str, *args: str) -> str:
    """場所によって訳し分けたい雛形（日本語は key のまま）。ほかの言語のキーは「場所: 雛形」。"""
    return H(key if State.lang == "ja" else f"{context}: {key}", *args)


def F(key: str, *args: str) -> str:
    """地の文字の雛形に、地の文字の値を差し込む（呼ぶ側で esc する）。"""
    return PLACEHOLDER.sub(lambda m: str(args[int(m.group(1))]), L(key))


JA_CHARS = re.compile(r"[぀-ヿ㐀-鿿！-～]")


def SLASH() -> str:
    """並べるときの斜線（日本語は全角「／」）。"""
    return "／" if State.lang == "ja" else " / "


def SEP() -> str:
    """区切りの点（日本語は「 ・ 」、ほかの言語は「 · 」）。"""
    return " ・ " if State.lang == "ja" else " · "


def U(suffix: str) -> str:
    """値の後ろに付ける単位（「秒」「か所」「/分」など）。日本語の文字を含むときだけ訳を引く。"""
    if not suffix:
        return suffix
    v = L(suffix) if JA_CHARS.search(suffix) else suffix
    # 用語の表の語（「Siegpunkte」など）を単位に使うときは、数との間を空ける
    return " " + v if State.lang != "ja" and (v[:1].isalpha() or v[:1] == "(") else v


def H(key: str, *args: str) -> str:
    """HTML の断片。雛形の地の文字は esc し、{0} などに args（HTML）を差し込む。"""
    tmpl = L(key)
    parts = PLACEHOLDER.split(tmpl)
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 0:
            out.append(html.escape(p, quote=True))
        else:
            n = int(p)
            if n >= len(args):
                raise I18nError(f"{key!r} の {{{n}}} に入れる値がない")
            out.append(args[n])
    return "".join(out)


def text(rid: str, ja: str) -> str:
    """台帳の文章の値の訳（地の文字）。訳したときの日本語と今の日本語が違えば止まる。"""
    if State.lang == "ja":
        return ja
    _, _, texts = _tables()
    State.used_text.add(rid)
    row = texts.get(rid)
    if row is None or not row.get(State.lang):
        return _missing("text", (rid, ja), ja)
    if row["元の文"] != ja:
        if State.collect is not None:
            State.collect["text"].add((rid, ja))
            return f"⟦{ja}⟧"
        raise I18nError(f"{rid} の訳が古い（訳したときの日本語: {row['元の文']!r} ／ 今: {ja!r}）。訳し直して元の文を書き換える")
    return row[State.lang]


# ---------------------------------------------------------------- 数と長さの書き方（言語ごと）

THIN = " "  # フランス語の桁区切り（狭い改行しない空白）


def group(n: int) -> str:
    s = f"{n:,}"
    if State.lang == "de":
        return s.replace(",", ".")
    if State.lang == "fr":
        return s.replace(",", THIN)
    return s


def decimal(s: str) -> str:
    """「6.7」の小数点を言語に合わせる（桁区切りは group で）。"""
    if State.lang in ("de", "fr"):
        return s.replace(".", ",")
    return s


def fmt(x: float) -> str:
    """桁区切り。小数は2桁まで（末尾の0は落とす）。"""
    if x < 0:
        return "-" + fmt(-x)
    if abs(x - round(x)) < 1e-9:
        return group(round(x))
    ip, fp = f"{x:.2f}".split(".")
    fp = fp.rstrip("0")
    return group(int(ip)) + (decimal("." + fp) if fp else "")


def fmt1(x: float) -> str:
    """小数1桁（10万HPあたりなどの目安値）。"""
    ip, fp = f"{x:.1f}".split(".")
    return group(int(ip)) + ("" if fp == "0" else decimal("." + fp))


def secs(n: float) -> str:
    """「15秒」。"""
    return f"{fmt(n)}{U('秒')}"


def dur(sec: float) -> str:
    """長さ・待ち時間。2分以上で割り切れれば「N分」、それ以外は「N秒」。"""
    s = round(sec)
    return f"{s // 60}{U('分')}" if s >= 120 and s % 60 == 0 else f"{s}{U('秒')}"


def man(n: int) -> str:
    """10万 のような表記（日本語だけ。ほかの言語は桁区切りの数）。"""
    if State.lang == "ja":
        return f"{n // 10_000:,}万" if n % 10_000 == 0 else f"{n:,}"
    return group(n)


# ---------------------------------------------------------------- 検査と、足りない訳の書き足し


def _nums(s: str) -> list[str]:
    return sorted(re.findall(r"\d+(?:[.,]\d+)?", PLACEHOLDER.sub("", s).replace(",", "").replace(".", "")))


def check(used: dict[str, set] | None = None) -> list[str]:
    """訳の表の検査。used（生成で使ったキー）を渡すと、使っていない訳も見つける。"""
    errors: list[str] = []
    try:
        terms, ui, texts = _tables()
    except I18nError as exc:
        return [str(exc)]
    for path in (TERMS_MD, UI_MD, TEXT_MD):
        if path.exists() and ledger.LIQUID.search(path.read_text(encoding="utf-8")):
            errors.append(f"{path.name}: {{{{ や {{% は書けない（GitHub Pages の Liquid が壊れる）")
    for key, row in ui.items():
        want = sorted(PLACEHOLDER.findall(key))
        for lg in FOREIGN:
            v = row.get(lg, "")
            if not v:
                errors.append(f"ui.md: {key!r} の {lg} が空")
                continue
            if sorted(PLACEHOLDER.findall(v)) != want:
                errors.append(f"ui.md: {key!r} の {lg} の差し込み {{n}} が元と違う: {v!r}")
            extra = [n for n in _nums(v) if n not in _nums(key)]
            if extra:
                errors.append(f"ui.md: {key!r} の {lg} に元にない数 {extra}")
    for key, row in terms.items():
        for lg in FOREIGN:
            if not row.get(lg):
                errors.append(f"terms.md: {key!r} の {lg} が空")
    for rid, row in texts.items():
        for lg in FOREIGN:
            v = row.get(lg, "")
            if not v:
                errors.append(f"text.md: {rid} の {lg} が空")
                continue
            extra = [n for n in _nums(v) if n not in _nums(row["元の文"])]
            if extra:
                errors.append(f"text.md: {rid} の {lg} に元にない数 {extra}")
            if "{" in v or "}" in v:
                errors.append(f"text.md: {rid} の {lg} に波括弧（値に使えない）")
    if used is not None:
        for key in sorted(set(ui) - used["ui"]):
            errors.append(f"ui.md: 使っていない訳 {key!r}（日本語が変わったなら、新しいキーに移して消す）")
        for key in sorted(set(texts) - used["text"]):
            errors.append(f"text.md: 使っていない訳 {key}")
    return errors


def _cell(text: str) -> str:
    """訳の表のセル（縦棒だけを逃がす。{0} の波括弧はそのまま。台帳の escape_cell は波括弧を文字参照にするので使わない）。"""
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def write_rows(path: Path, cols: list[str], rows: list[list[str]]) -> None:
    """表の末尾に行を足す（表は1ファイルに1つ。末尾が表である前提）。"""
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    text += "".join("| " + " | ".join(_cell(c) for c in r) + " |\n" for r in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def append_missing(found: dict[str, set]) -> list[str]:
    """集めた足りない訳を表の末尾に足す（訳は空）。足した行の説明を返す。"""
    I18N.mkdir(parents=True, exist_ok=True)
    msgs = []
    for path, cols, intro in (
        (UI_MD, UI_COLS, ("# 画面の言い回しの訳\n\nキーは日本語の雛形。{0} {1} … には値が入る（順番は入れ替えてよい）。元にない数は書けない。∅ は「この言語では何も出さない」。"
                          "ゲームの用語は terms.md の公式の表記を使う。\n\n")),
        (TEXT_MD, TEXT_COLS, ("# 台帳の文章の訳\n\n行 ID で引く。「元の文」は訳したときの日本語（台帳の表示文、なければ値）。"
                             "日本語が変わると生成が止まるので、訳し直してから元の文を書き換える。\n\n")),
        (TERMS_MD, TERM_COLS, ("# ゲームの用語（各言語の公式の表記）\n\n各言語の公式サイト（Lodestone のプレイガイド・ジョブガイド・パッチノート）の表記を"
                              "そのまま写す。出典は言語ごとの URL。\n\n")),
    ):
        if not path.exists():
            path.write_text(intro + "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n", encoding="utf-8", newline="\n")
    _, ui, texts = (_tables() if State._cache else (reload() or _tables()))
    new_ui = sorted(k for k in found["ui"] if k not in ui)
    if new_ui:
        write_rows(UI_MD, UI_COLS, [[k, "", "", "", ""] for k in new_ui])
        msgs.append(f"ui.md に {len(new_ui)} 行")
    new_text = sorted(found["text"])
    if new_text:
        stale = [rid for rid, ja in new_text if rid in texts and texts[rid]["元の文"] != ja]
        fresh = [[rid, ja, "", "", ""] for rid, ja in new_text if rid not in texts]
        if fresh:
            write_rows(TEXT_MD, TEXT_COLS, fresh)
            msgs.append(f"text.md に {len(fresh)} 行")
        if stale:
            msgs.append(f"text.md の古い訳（元の文が変わった）: {', '.join(stale)}")
    terms_missing = sorted(found["terms"])
    if terms_missing:
        msgs.append(f"terms.md の訳が空: {', '.join(terms_missing)}")
    reload()
    return msgs


def main(argv: list[str]) -> int:
    # スクリプトとして動かすと、このファイルは __main__ になる。build が使う i18n モジュールの状態を操作する
    import build
    import i18n as me

    cmd = argv[1] if len(argv) > 1 else "check"
    if cmd == "collect":
        me.State.collect = {"ui": set(), "text": set(), "terms": set()}
        build.build(build.load())
        for m in me.append_missing(me.State.collect) or ["足りない訳はない"]:
            print(m)
        return 0
    if cmd == "check":
        try:
            build.build(build.load())
        except (build.BuildError, me.I18nError) as exc:
            print(f"生成できない: {exc}")
            return 1
        errors = me.check({"ui": me.State.used_ui, "text": me.State.used_text})
        print("\n".join(errors) if errors else "訳の表: エラーなし")
        return 1 if errors else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
