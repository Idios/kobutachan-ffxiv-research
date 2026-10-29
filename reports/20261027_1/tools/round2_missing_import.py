"""2026-10-29: 「検証役が指摘した漏れ（未対応）」の調査結果（2回目）を台帳に取り込んだ記録。

入力: reports/20261027_1/ledger-build/round2/verify_<グループ>.json（調査役の提案を、独立の検証役が確かめて直した最終版）
- 値の行は insert_after の行の直後に入れる。公式の行は採否を ○（原文照合が済んだ公式の値は既定で ○）、
  それ以外は空欄（ユーザーの判定待ち）。公式の行の抜粋は frontline/data/official/<出典ID>.md にも足す。
- 出典・確認項目は表の末尾（確認項目は同じ接頭辞の最後の項目の後ろ）に足す。
- 既存のセルの書き換え（updates）は、今の中身と新しい中身を表示してから当てる。
- 漏れの項目には「対応済み」と書き足す（行は消さない）。

使い方:
    python reports/20261027_1/tools/round2_missing_import.py <グループ...> [--dry-run]
    （グループ: secure seize-shatter naadam triumph）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import ledger  # noqa: E402

DAY = "2026-10-29"
IN = REPO / "reports" / "20261027_1" / "ledger-build" / "round2"
PREFIX_RULE = {p: r for r, (p, _) in ledger.RULES.items()}
TABLES = {"値": ledger.LEDGER_COLS, "根拠": ledger.EVIDENCE_COLS, "確認": ledger.CHECK_COLS}
# 表示文の対象: 値を書き換える行に表示文があれば、表示文も見直す必要がある


def rule_of(rid: str) -> str:
    return PREFIX_RULE[rid.split("-", 1)[0] + "-"]


def cell(path: Path, cols: list[str], rid: str, col: str) -> str | None:
    found = ledger.find_table(path, cols)
    if found is None:
        return None
    for c in found[0]:
        if c and c[0] == rid:
            return c[cols.index(col)]
    return None


def append_excerpt(of_id: str, rid: str, quote: str, sources: dict[str, dict[str, str]], dry: bool) -> str:
    path = ledger.DATA / "official" / f"{of_id}.md"
    line = f"- （{rid}）「{ledger.escape_cell(quote)}」"
    if not path.exists():
        s = sources.get(of_id, {})
        head = [f"# {s.get('名称', of_id)}", "", f"- 出典ID: {of_id}", f"- URL: {s.get('URL', '')}", f"- 種別: {s.get('種別', '')}",
                f"- 取得日: {s.get('取得日', DAY)}", "- © SQUARE ENIX（公式サイトの文の抜粋。非商用のファンサイトの保守のために保存）", "", "## 抜粋", ""]
        if not dry:
            path.write_text("\n".join(head + [line]) + "\n", encoding="utf-8")
        return "新規"
    text = path.read_text(encoding="utf-8")
    if f"（{rid}）" in text:
        return "既存"
    if not dry:
        path.write_text(text.rstrip("\n") + "\n" + line + "\n", encoding="utf-8")
    return "追記"


def mark_done(rule: str, item: str, done: str, dry: bool) -> bool:
    """漏れの節の、item で始まる項目に「対応済み」を書き足す。"""
    path = ledger.LEDGER_DIR / f"{rule}.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    key = item.split("／")[0].strip()[:12]
    in_sec = False
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            in_sec = ln.startswith("## 検証役が指摘した漏れ")
            continue
        if in_sec and ln.startswith("- ") and key and key in ln and "対応済み" not in ln:
            if not dry:
                lines[i] = ln + f"（**対応済み {DAY}**: {done}）"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("groups", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run
    ledgers, sources, errors = ledger.load_all()
    if errors:
        print("台帳の検証エラーがあるので先に直す:", *errors, sep="\n  ")
        return 2
    rows = {r.id: r for led in ledgers for r in led.rows}
    checks = {c[0] for c in ledger.find_table(ledger.CHECKS_MD, ledger.CHECK_COLS)[0]}
    for g in args.groups:
        v = json.loads((IN / f"verify_{g}.json").read_text(encoding="utf-8"))
        print(f"===== {g}")
        # 出典
        for s in v["new_sources"]:
            if s["id"] in sources:
                print(f"  出典 {s['id']}: すでにある（足さない）")
                continue
            rec = [s["id"], s["kind"], s["name"], s["url"], s["published"], s["patch"], s["fetched"], s["lineage"], s["storage"], s["archive"]]
            print(f"  出典 {s['id']}: 追加")
            if not dry:
                ledger.append_rows(ledger.SOURCES_MD, ledger.SOURCE_COLS, [rec])
            sources[s["id"]] = dict(zip(ledger.SOURCE_COLS, rec))
        # 値の行
        for r in v["rows"]:
            if r["id"] in rows:
                print(f"  行 {r['id']}: すでにある（足さない）")
                continue
            rule = rule_of(r["id"])
            path = ledger.LEDGER_DIR / f"{rule}.md"
            verdict = "○" if r["grade"] == "公式" else ""
            comment = "" if verdict else f"{DAY} に追加（検証役が指摘した漏れ）。判定待ち"
            vrow = [r["id"], r["group"], r["label"], r["value"], r["unit"], r["condition"], r["grade"], "; ".join(r["sources"]),
                    r["last_changed"], r["current_check"], verdict, comment]
            erow = [r["id"], r["quote"], r["notes"]]
            print(f"  行 {r['id']} [{r['grade']}] 採否={verdict or '空欄'} → {rule}（{r['insert_after']} の後）")
            if not dry:
                hit = ledger.insert_rows_after(path, ledger.LEDGER_COLS, r["insert_after"], [vrow])
                ledger.insert_rows_after(path, ledger.EVIDENCE_COLS, r["insert_after"], [erow])
                if not hit:
                    print(f"    注意: {r['insert_after']} がないので表の末尾に足した")
            if r["grade"] == "公式":
                for sid in r["sources"]:
                    if sid.startswith("OF-"):
                        print(f"    抜粋 {sid}: {append_excerpt(sid, r['id'], r['quote'], sources, dry)}")
        # 確認項目
        for c in v["checks"]:
            if c["id"] in checks:
                print(f"  確認 {c['id']}: すでにある（足さない）")
                continue
            prefix = c["id"].rsplit("-", 1)[0]
            same = [x for x in checks if x.startswith(prefix + "-")]
            # 同じ接頭辞の項目がなければ、ルール共通の確認項目（IG-GUARD-ACCESS）の後ろへ
            after = sorted(same)[-1] if same else ("IG-GUARD-ACCESS" if "IG-GUARD-ACCESS" in checks else "")
            print(f"  確認 {c['id']}: 追加（{after or '末尾'} の後）")
            if not dry:
                ledger.insert_rows_after(ledger.CHECKS_MD, ledger.CHECK_COLS, after,
                                         [[c["id"], c["what"], c["how"], c["effort"], "; ".join(c["related"]), "", "", ""]])
            checks.add(c["id"])
        # 既存のセルの書き換え
        for u in v["updates"]:
            path = REPO / u["file"]
            cols = TABLES[u["table"]]
            cur = cell(path, cols, u["target_id"], u["column"])
            if cur is None:
                print(f"  書き換え {u['target_id']}.{u['column']}: 対象がない（当てない）")
                continue
            if cur == u["new_text"]:
                print(f"  書き換え {u['target_id']}.{u['column']}: 同じ（当てない）")
                continue
            print(f"  書き換え {u['target_id']}.{u['column']}（{u['table']}）\n    今: {cur[:160]}\n    新: {u['new_text'][:160]}")
            if u["table"] == "値" and u["column"] == "値" and rows.get(u["target_id"]) and rows[u["target_id"]].display:
                print("    注意: この行には表示文がある。値を変えたら表示文を見直す")
            if not dry:
                left = ledger.update_cells(path, cols, {u["target_id"]: {u["column"]: u["new_text"]}})
                assert not left, left
        # 漏れの節に対応済みと書く
        done_by_item: dict[str, list[str]] = {}
        for r in v["rows"]:
            done_by_item.setdefault(r["item"], []).append(f"行 {r['id']}")
        for c in v["checks"]:
            done_by_item.setdefault(c["item"], []).append(f"確認 {c['id']}")
        for s in v["skipped"]:
            done_by_item.setdefault(s["item"], []).append("値の行は作らない（理由は reports/20261027_1/ledger-build/round2）")
        for item, what in done_by_item.items():
            # 行の入る台帳に加えて、グループ自身の台帳も探す（共通台帳に入った行の漏れ項目は、元の台帳に書いてある）
            rules = {rule_of(x.split()[1]) for x in what if x.startswith("行 ")}
            rules |= {"seize", "shatter"} if g == "seize-shatter" else {g}
            ok = any(mark_done(rule, item, "・".join(dict.fromkeys(what)), dry) for rule in sorted(rules))
            print(f"  漏れの項目「{item[:24]}」: {'対応済みと記入' if ok else '見つからない（手で確かめる）'}")
    _, _, errors = ledger.load_all()
    print("検証:", "エラーなし" if not errors else "\n  ".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
