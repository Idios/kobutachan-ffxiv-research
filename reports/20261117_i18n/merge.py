"""訳の JSON（reports/20261117_i18n/<lang>.json）を i18n の表へ足す一度きりの道具。

- 表は1ファイルに1つ（末尾）。
- 列は決まった順（i18n.py の *_COLS と同じ）に並べ直す。
- 出典の欄には、用語ごとの公式の URL を言語ごとに足す。URL でない注記は短く言い換える。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "frontline" / "data" / "i18n"
HERE = Path(__file__).resolve().parent

LANGS = ["ko", "zh-hans", "zh-hant"]
OLD = {
    "terms.md": ["キー", "日本語", "en", "de", "fr", "出典"],
    "ui.md": ["日本語", "en", "de", "fr", "メモ"],
    "text.md": ["ID", "元の文", "en", "de", "fr"],
}
NEW = {
    "terms.md": ["キー", "日本語", "en", "de", "fr", *LANGS, "出典"],
    "ui.md": ["日本語", "en", "de", "fr", *LANGS, "メモ"],
    "text.md": ["ID", "元の文", "en", "de", "fr", *LANGS],
}
KIND = {"terms.md": "terms", "ui.md": "ui", "text.md": "text"}
NOTE = {
    # 初回のマージ時点の注記。zh-hans は第 1 回査読で中国版公式の URL に差し替えた（apply_cn_official.py）
    "zh-hans": "繁体字版の表記を簡体字化（後に中国版公式へ差し替え）",
    "zh-hant": "公式の表記を確認できず（自動翻訳）",
}
# term_sources が URL でなく注記の行は「未確認」だけを残す（詳細は *-notes.md）。
UNCONFIRMED = "未確認（自動翻訳）"
UNCONFIRMED_WORDS = ("未確認", "未記載", "確認できず", "簡体字化のみ", "自動翻訳")
URL_RE = re.compile(r"https?://[^\s（）]+")


def cells(line: str) -> list[str]:
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        raise ValueError(f"表の行ではない: {line!r}")
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s[1:-1])]


def esc(c: str) -> str:
    return str(c).replace("|", "\\|").replace("\n", " ").strip()


def source_text(lg: str, value: str) -> str:
    value = value.strip()
    prefix = f"{lg}: "
    if value.startswith(prefix):
        value = value[len(prefix):]
    m = URL_RE.search(value)
    if m:
        url = m.group(0)
        # 簡体字版は TW 公式の表記を変換したもの。URL だけだと公式の簡体字表記に見える。
        suffix = f"（{NOTE[lg]}）" if lg == "zh-hans" else ""
        return f"{lg}: {url}{suffix}"
    if any(w in value for w in UNCONFIRMED_WORDS):
        return f"{lg}: {UNCONFIRMED}"
    return f"{lg}: {NOTE.get(lg, value)}"


def merge(name: str, kind_data: dict, sources: dict) -> list[str]:
    path = I18N / name
    lines = path.read_text(encoding="utf-8").splitlines()
    old_cols, new_cols = OLD[name], NEW[name]
    out: list[str] = []
    seen_header = False
    for line in lines:
        if not line.startswith("|"):
            out.append(line)
            continue
        row = cells(line)
        if all(set(c) <= {"-"} for c in row):
            continue  # 見出しの次の区切り（見出しの直後に出す）
        if row == old_cols and not seen_header:
            out.append("| " + " | ".join(new_cols) + " |")
            out.append("|" + "---|" * len(new_cols))
            seen_header = True
            continue
        if not seen_header:
            raise ValueError(f"{name}: 見出しの前に表の行がある: {line!r}")
        old = dict(zip(old_cols, row))
        key = old[old_cols[0]]
        new = []
        for col in new_cols:
            if col in old:
                new.append(old[col])
            else:
                v = kind_data.get(col, {}).get(key)
                if v is None:
                    raise SystemExit(f"{name}: {col} の訳がない: {key!r}")
                new.append(v)
        if "出典" in new_cols:
            i = new_cols.index("出典")
            srcs = []
            for lg in LANGS:
                v = sources.get(lg, {}).get(key, "")
                if v:
                    srcs.append(source_text(lg, v))
            if srcs:
                new[i] = (new[i] + "; " if new[i] else "") + "; ".join(srcs)
        if any("\n" in c for c in new):
            raise SystemExit(f"{name}: 改行を含む訳: {key!r}")
        out.append("| " + " | ".join(esc(c) for c in new) + " |")
    if not seen_header:
        raise SystemExit(f"{name}: 表が見つからない")
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    return out


def main() -> int:
    data = {}
    for lg in LANGS:
        p = HERE / f"{lg}.json"
        if not p.exists():
            raise SystemExit(f"訳がない: {p}")
        data[lg] = json.loads(p.read_text(encoding="utf-8"))
        print(f"{lg}: ui {len(data[lg]['ui'])} / text {len(data[lg]['text'])} / terms {len(data[lg]['terms'])}")
    for name, kind in KIND.items():
        merged = {lg: data[lg][kind] for lg in LANGS}
        sources = {lg: data[lg].get("term_sources", {}) for lg in LANGS}
        rows = merge(name, merged, sources)
        print(f"{name}: {len(rows)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
