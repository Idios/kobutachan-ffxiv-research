"""フロントライン早見表の検査の共通部品。

生成は build.build()（ファイルに書かない）で行い、台帳から作ったページを直接調べる。
ブラウザでの検査（test_pages.py）は、リポジトリに書き出したページ（frontline/ の下）を開く。
"""

from __future__ import annotations

import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONT = ROOT / "frontline"
sys.path.insert(0, str(FRONT / "tools"))

import build
import ledger

SKIP_TEXT_IN = {"script", "style", "title", "svg"}


@pytest.fixture(scope="session")
def data() -> build.Data:
    return build.load()


@pytest.fixture(scope="session")
def site(data: build.Data) -> dict[Path, str]:
    return build.build(data)


def public_pages(site: dict[Path, str], *, include_sources: bool = False) -> dict[str, str]:
    """公開ページ（frontline/ からの相対パス → HTML）。既定では出典一覧を除く。"""
    out = {}
    for path, text in site.items():
        rel = path.relative_to(FRONT).as_posix()
        if rel.startswith("sources/") and not include_sources:
            continue
        out[rel] = text
    return out


class TextNodes(HTMLParser):
    """文字の断片と、それを囲む要素の属性（祖先すべて）を集める。"""

    VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "use"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict[str, str]]] = []
        self.nodes: list[tuple[str, list[tuple[str, dict[str, str]]]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.VOID:
            return
        self.stack.append((tag, {k: v or "" for k, v in attrs}))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        return

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, text: str) -> None:
        if text.strip():
            self.nodes.append((text, list(self.stack)))


def text_nodes(html_text: str) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
    p = TextNodes()
    p.feed(html_text)
    return [(t, anc) for t, anc in p.nodes if not any(tag in SKIP_TEXT_IN for tag, _ in anc)]


def src_tokens(anc: list[tuple[str, dict[str, str]]]) -> list[list[str]]:
    """祖先の data-src を内側から順に返す。"""
    return [a["data-src"].split() for _, a in reversed(anc) if "data-src" in a]


def visible_text(html_text: str) -> str:
    return "".join(t for t, _ in text_nodes(html_text))


RETIRED_COLS = ["行ID", "旧値", "範囲", "使わない理由", "時期"]


def retired_rows() -> list[dict[str, str]]:
    """旧値の登録簿。行 ID が台帳にあり、範囲が「行」か「全体」であることも確かめる（綴り違いで素通りしないように）。"""
    found = ledger.find_table(ledger.DATA / "retired.md", RETIRED_COLS)
    assert found is not None, "frontline/data/retired.md の表がない"
    ledgers, _, _ = ledger.load_all()
    ids = {r.id for led in ledgers for r in led.rows}
    rows = [dict(zip(RETIRED_COLS, c)) for c in found[0]]
    for e in rows:
        assert e["行ID"] in ids, f"retired.md の行ID {e['行ID']} が台帳にない"
        assert e["範囲"] in ("行", "全体"), f"retired.md の範囲 {e['範囲']!r} は「行」か「全体」"
    return rows


def norm_text(s: str) -> str:
    """不在検査の比べ方: 全角・半角をそろえ、数字の桁区切りを外し、波線をそろえる。"""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)
    return re.sub(r"[〜～~]", "〜", s)


def find_retired(pages: dict[str, str], entries: list[dict[str, str]]) -> list[str]:
    """旧値がページに残っていれば、その場所を返す（不在検査の本体。変異テストでも使う）。

    範囲「行」は、その行の値をそのまま出す要素（data-src がその行だけ）を見る。派生値は見ない
    （NIN の LB 105秒のように、旧値と同じ数が別の計算で正しく出ることがあるため）。
    """
    hits = []
    for name, html_text in pages.items():
        nodes = text_nodes(html_text)
        whole = norm_text("".join(t for t, _ in nodes))
        for e in entries:
            old = norm_text(e["旧値"])
            if e["範囲"] == "全体":
                if old in whole:
                    hits.append(f"{name}: {e['行ID']} の旧値 {e['旧値']!r}（全体）")
                continue
            own = norm_text(" / ".join(t for t, anc in nodes if (src_tokens(anc) or [[]])[0] == [e["行ID"]]))
            if re.search(rf"(?<![\d.]){re.escape(old)}(?![\d.])", own):
                hits.append(f"{name}: {e['行ID']} の旧値 {e['旧値']!r}（行）")
    return hits
