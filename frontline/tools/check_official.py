"""公式の行の原文抜粋が、出典の公式ページに今も載っているかを確かめる。

値台帳で等級が「公式」の行ごとに、出典（OF- の ID）の URL を取得し、
「根拠」の表にある原文抜粋がページ本文に含まれるかを照合する。
パッチ後の保守では最初にこれを回し、見つからなくなった抜粋（=公式の記述が変わった可能性）を洗い出す。

使い方:
    python -I frontline/tools/check_official.py [--cache DIR] [--rule RULE]

- 取得したページは信頼できないデータとして扱い、解析するだけで実行しない。
- 照合は空白・縦棒・全角半角の違いを無視して行う。抜粋が「…」で区切られている場合は、各断片がすべて含まれれば一致とみなす。
"""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
import tempfile
import time
import unicodedata
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger

UA = "Mozilla/5.0 (frontline-cheatsheet maintenance; non-commercial)"


def fetch(url: str, cache: Path) -> str:
    base = url.split("#", 1)[0]
    key = hashlib.sha256(base.encode()).hexdigest()[:16]
    path = cache / f"{key}.html"
    if not path.exists():
        req = urllib.request.Request(base, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as res:
            path.write_bytes(res.read())
        time.sleep(1.0)  # 公式サイトに負荷をかけない
    return path.read_text(encoding="utf-8", errors="replace")


def to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    # ふりがな（ルビ）は本文から外す（例: 魔弾<rt>まだん</rt>の射手）
    raw = re.sub(r"(?is)<(rt|rp)\b.*?</\1>", "", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return html.unescape(raw)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = (
        s.replace("−", "-")
        .replace("―", "-")
        .replace("→", "->")
        .replace("〜", "~")
        .replace("～", "~")
    )
    return re.sub(r"[\s「」『』、。・:：]+", "", s)


ANNOTATION = re.compile(
    r"（[^（）]*(パッチノート|ガイド|公式|表|セル|見出し|キャプション|画像|\d+\.\d+)[^（）]*）"
    r"|【[^】]*】"
    r"|(?<![A-Za-z])EN:\s*"
)


def quote_pieces(quote: str) -> list[str]:
    """抜粋を照合用の断片に分ける。作成役が付けた注記（出典名の括弧書き・【版】・EN:）は除く。"""
    q = ANNOTATION.sub(" ", quote)
    parts = re.split(r"…|\.\.\.|／|/|｜|\||↓|。", q)
    return [p for p in (norm(x) for x in parts) if len(p) >= 2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="")
    ap.add_argument("--rule", default="")
    ap.add_argument(
        "--ignore-missing-ledgers",
        action="store_true",
        help="まだ作っていない台帳があっても照合する",
    )
    args = ap.parse_args()
    cache = (
        Path(args.cache)
        if args.cache
        else Path(tempfile.mkdtemp(prefix="fl_official_"))
    )
    cache.mkdir(parents=True, exist_ok=True)
    ledgers, sources, errors = ledger.load_all()
    if args.ignore_missing_ledgers:
        errors = [e for e in errors if not e.endswith("台帳がない")]
    if errors:
        print("台帳の検証エラーがあるので先に直す:")
        for e in errors:
            print(" ", e)
        return 2
    texts: dict[str, str] = {}
    ok = ng = skipped = 0
    for led in ledgers:
        if args.rule and led.rule != args.rule:
            continue
        for r in led.rows:
            if r.grade != "公式":
                continue
            of_ids = [s for s in r.sources if s.startswith("OF-")]
            if not of_ids or not r.quote:
                print(f"未照合 {r.id}: 公式の出典か原文抜粋がない")
                skipped += 1
                continue
            pieces = quote_pieces(r.quote)
            pages = []
            for sid in of_ids:
                url = sources.get(sid, {}).get("URL", "")
                if not url.startswith("https://"):
                    continue
                if url not in texts:
                    try:
                        texts[url] = norm(to_text(fetch(url, cache)))
                    except Exception as exc:  # noqa: BLE001
                        print(f"取得失敗 {sid} {url}: {exc}")
                        texts[url] = ""
                pages.append(texts[url])
            # 断片ごとに、行のいずれかの公式出典ページに含まれていれば一致（日英の出典をまたぐ抜粋があるため）
            missing = [p for p in pieces if not any(p in t for t in pages if t)]
            found = bool(pieces) and not missing
            if found:
                ok += 1
            else:
                ng += 1
                print(
                    f"不一致 {r.id}（{', '.join(of_ids)}）: 見つからない断片: {' ／ '.join(missing)[:120]}"
                )
    print(f"照合: 一致 {ok} ／ 不一致 {ng} ／ 未照合 {skipped}（キャッシュ: {cache}）")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
