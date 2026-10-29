"""2026-10-29: 翻訳役（英・独・仏の各1）の訳を frontline/data/i18n/ui.md・text.md に書き込む（記録）。

訳の JSON（一時フォルダ）: {"ui": {日本語の雛形: 訳}, "text": {行ID: 訳}, "notes": {...}}。
表にある行だけを埋める（キーは表が正本）。訳がない行は空のまま残し、検査（i18n.py check）で見つける。
EXTRA は翻訳役に渡した作業ファイルより後に足した言い回し（Claude の訳）。

使い方: python -I reports/20261027_1/tools/i18n_merge.py <tr_en.json> <tr_de.json> <tr_fr.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import i18n  # noqa: E402
import ledger  # noqa: E402

EXTRA = {
    "自動翻訳（ゲームの用語は公式の表記）": {
        "en": "Machine-translated (game terms: official)",
        "de": "Maschinell übersetzt (Spielbegriffe: offiziell)",
        "fr": "Traduction automatique (termes du jeu : officiels)",
    },
}


def rewrite(path: Path, cols: list[str], fill) -> tuple[int, list[str]]:
    text = path.read_text(encoding="utf-8")
    head, _, _ = text.partition("| " + " | ".join(cols) + " |")
    found = ledger.find_table(path, cols)
    rows, n, empty = [], 0, []
    for cells in found[0]:
        cells = list(cells) + [""] * (len(cols) - len(cells))
        for i, lg in enumerate(("en", "de", "fr"), start=cols.index("en")):
            v = fill(cells, lg)
            if v:
                cells[i] = v
                n += 1
            elif not cells[i]:
                empty.append(f"{cells[0]} ({lg})")
        rows.append(cells)
    path.write_text(head + "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n", encoding="utf-8", newline="\n")
    i18n.write_rows(path, cols, rows)
    return n, empty


def main(paths: list[str]) -> int:
    tr = {lg: json.load(open(p, encoding="utf-8")) for lg, p in zip(("en", "de", "fr"), paths)}
    n1, e1 = rewrite(i18n.UI_MD, i18n.UI_COLS, lambda c, lg: EXTRA.get(c[0], {}).get(lg) or tr[lg]["ui"].get(c[0], ""))
    n2, e2 = rewrite(i18n.TEXT_MD, i18n.TEXT_COLS, lambda c, lg: tr[lg]["text"].get(c[0], ""))
    print(f"ui.md: {n1} 個の訳 ／ text.md: {n2} 個の訳")
    for e in e1 + e2:
        print("訳がない:", e)
    return 1 if e1 or e2 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
