"""台帳作成ワークフローの戻り値（JSON）から、値台帳・出典台帳・ゲーム内確認リスト・公式抜粋を書き出す（初回の取り込み用）。

使い方:
    python reports/20261027_1/tools/import_ledger.py <workflow-result.json> <repo-root>

方針:
- 作成役の行を土台に、検証役の判定を反映する。
  - ok: そのまま。公式で作成役が preapproved を付けた行だけ採否を ○ にする。
  - fix / downgrade / upgrade: 訂正を反映し、備考に「検証役の訂正」と元の値を残す。採否は空欄（ユーザーが判断）。
  - remove: 値の表から外し、「除外した行」に理由つきで残す。
- 第三者の文は備考に要約だけを書く（原文は写さない）。公式の原文抜粋は根拠の表と official/ に保存する。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RULE_TITLES = {
    "common": "ルール共通",
    "secure": "外縁遺跡群（制圧戦）",
    "seize": "シールロック（争奪戦）",
    "shatter": "フィールド・オブ・グローリー（砕氷戦）",
    "naadam": "オンサル・ハカイル（終節戦）",
    "triumph": "ウォーコー・チーテ（演習戦）",
}
LEDGER_COLS = ["ID", "区分", "項目", "値", "単位", "条件・配り方", "等級", "出典", "最終変更", "現行確認", "採否", "コメント"]
EVIDENCE_COLS = ["ID", "公式原文の抜粋", "備考"]
SOURCE_COLS = ["ID", "種別", "名称", "URL", "公開・更新", "対象パッチ", "取得日", "系統", "保存", "アーカイブ"]
CHECK_COLS = ["ID", "確認すること", "手順", "手間", "関係する行", "結果", "確認日", "パッチ"]
BASE_PATCH = "7.57"
TODAY = "2026-10-27"


def cell(text: object) -> str:
    s = str(text if text is not None else "")
    s = s.replace("|", "\\|").replace("\r", " ").replace("\n", "<br>").strip()
    # GitHub Pages（Jekyll/Liquid）のビルドを壊す記法を無害化する
    return s.replace("{", "&#123;").replace("}", "&#125;")


def table(cols: list[str], rows: list[list[object]]) -> str:
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    out += ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def merge(built: dict, verify: dict | None) -> tuple[list[dict], list[dict], list[str]]:
    verdicts = {v["id"]: v for v in (verify or {}).get("row_verdicts", [])}
    kept, removed, log = [], [], []
    for r in built.get("rows", []):
        r = dict(r)
        v = verdicts.get(r["id"])
        r["verdict_mark"] = ""
        r["extra_notes"] = []
        if v is None:
            if r.get("grade") == "公式" and r.get("preapproved"):
                # 公式の行は check_official.py で原文を機械照合する。照合に失敗した行は後で ○ を外す
                r["verdict_mark"] = "○"
                r["extra_notes"].append("公式の行は check_official.py で原文を機械照合（LLM の検証役は省略）")
            else:
                r["extra_notes"].append("検証役の判定待ち")
        elif v["verdict"] == "remove":
            removed.append({"id": r["id"], "label": r.get("label", ""), "value": r.get("value", ""), "reason": v.get("detail", "")})
            continue
        elif v["verdict"] in ("fix", "downgrade", "upgrade"):
            changes = []
            for key, field in (("corrected_value", "value"), ("corrected_grade", "grade"), ("corrected_current_check", "current_check"), ("corrected_quote", "official_quote")):
                nv = (v.get(key) or "").strip()
                if nv and nv != str(r.get(field, "")).strip():
                    changes.append(f"{field}: {r.get(field, '')} → {nv}")
                    r[field] = nv
            kind = {"fix": "訂正", "downgrade": "格下げ", "upgrade": "格上げ"}[v["verdict"]]
            detail = v.get("detail", "")
            suffix = "（" + "; ".join(changes) + "）" if changes else ""
            r["extra_notes"].append(f"検証役の{kind}: {detail}{suffix}")
            log.append(f"{r['id']}: {v['verdict']} {'; '.join(changes)}")
        elif r.get("grade") == "公式" and r.get("preapproved"):
            r["verdict_mark"] = "○"
        if r.get("grade") not in ("公式", "外部", "未確認"):
            r["extra_notes"].append(f"等級 {r.get('grade')} を未確認に読み替え")
            r["grade"] = "未確認"
        kept.append(r)
    return kept, removed, log


def write_ledger(root: Path, key: str, rows: list[dict], removed: list[dict], verify: dict | None, edits: dict | None = None) -> None:
    title = RULE_TITLES[key]
    main_rows = [[
        r["id"], r.get("group", ""), r.get("label", ""), r.get("value", ""), r.get("unit", ""), r.get("condition", ""),
        r.get("grade", ""), "; ".join(r.get("sources", [])), r.get("last_changed", ""), r.get("current_check", ""),
        r.get("verdict_mark", ""), "",
    ] for r in rows]
    ev_rows = []
    for r in rows:
        notes = [r.get("notes", "")] + r.get("extra_notes", [])
        if r.get("needs_ingame_check"):
            notes.append("ゲーム内確認の対象: " + (r.get("ingame_check_how") or ""))
        ev_rows.append([r["id"], r.get("official_quote", "") if r.get("grade") == "公式" else "", " ／ ".join(n for n in notes if n)])
    parts = [
        f"# 値台帳: {title}",
        "",
        "- このファイルは**正典データ**。ページはこの表から生成する（派生値は生成時に計算し、ここには書かない）。",
        "- **採否**: ○＝採用、×＝不採用。訂正はコメント欄に書く（例: 「× 正しくは -8」）。公式で原文照合済みの行は既定で ○。",
        "- **等級**: 公式／外部（独立した2系統以上が一致）／実測（ゲーム内で確認）／未確認。",
        f"- **現行確認**: 基準パッチ {BASE_PATCH} で値が有効かの確認状況（✔＝確認済み、△＝外部の現行期資料のみ、？＝未確認）。",
        f"- 作成: {TODAY}（台帳作成ワークフローの作成役＋独立検証役。出典は [出典台帳](../sources.md)）",
        "",
        "## 値",
        "",
        table(LEDGER_COLS, main_rows),
        "",
        "## 根拠",
        "",
        "公式の行は原文の抜粋（© SQUARE ENIX）。第三者の資料は要約のみ。",
        "",
        table(EVIDENCE_COLS, ev_rows),
        "",
    ]
    miss = (verify or {}).get("missing_items", [])
    if miss:
        parts += ["## 検証役が指摘した漏れ（未対応）", ""]
        parts += [f"- {cell(m.get('label'))}: {cell(m.get('why'))}" + (f"（候補: {cell(m.get('suggested_source'))}）" if m.get("suggested_source") else "") for m in miss]
        parts.append("")
    if removed:
        parts += ["## 除外した行（検証役の指摘）", ""]
        parts += [f"- {cell(x['id'])} {cell(x['label'])}（値 {cell(x['value'])}）: {cell(x['reason'])}" for x in removed]
        parts.append("")
    copy_issues = (verify or {}).get("copy_issues", [])
    if copy_issues:
        parts += ["## 写しすぎの指摘（要修正）", ""]
        fixed = set((edits or {}).get("notes_replace", {})) | set((edits or {}).get("source_replace", {}))
        parts += [f"- {cell(c.get('id'))}: {cell(c.get('issue'))}" + ("（**対応済み**: 言い換えた）" if c.get("id") in fixed else "") for c in copy_issues]
        parts.append("")
    (root / "frontline" / "data" / "ledger" / f"{key}.md").write_text("\n".join(parts), encoding="utf-8")


def norm_url(u: str) -> str:
    return re.sub(r"#.*$", "", u or "").rstrip("/")


def unify_source_ids(data: dict) -> dict[str, str]:
    """URL が同じ出典に担当ごとに別の ID が付いていたら、最初に現れた ID（台帳の処理順）へ寄せる。"""
    canon_by_url: dict[str, str] = {}
    alias: dict[str, str] = {}
    for item in data["ledgers"]:
        for s in item["built"].get("sources", []):
            u = norm_url(s.get("url", ""))
            if not u:
                continue
            first = canon_by_url.setdefault(u, s["id"])
            if s["id"] != first:
                alias[s["id"]] = first
    for item in data["ledgers"]:
        b = item["built"]
        for r in b.get("rows", []):
            seen, out = set(), []
            for sid in r.get("sources", []):
                sid = alias.get(sid, sid)
                if sid not in seen:
                    seen.add(sid)
                    out.append(sid)
            r["sources"] = out
        b["sources"] = [s for s in b.get("sources", []) if s["id"] not in alias]
        for si in (item.get("verify") or {}).get("source_issues", []):
            si["source_id"] = alias.get(si.get("source_id"), si.get("source_id"))
    return alias


def main() -> int:
    src, root = Path(sys.argv[1]), Path(sys.argv[2])
    data = json.loads(src.read_text(encoding="utf-8"))
    alias = unify_source_ids(data)
    edits_path = src.parent / "manual-edits.json"
    edits = json.loads(edits_path.read_text(encoding="utf-8")) if edits_path.exists() else {}
    sources: dict[str, dict] = {}
    source_conflicts: list[str] = []
    source_issues: list[str] = []
    checks: list[list[object]] = []
    quotes: dict[str, list[tuple[str, str]]] = {}
    report = []
    for item in data["ledgers"]:
        key, built, verify = item["key"], item["built"], item.get("verify")
        rows, removed, log = merge(built, verify)
        # Claude の手作業の修正（manual-edits.json）。出どころが分かるよう備考に残す
        kept = []
        for r in rows:
            if r["id"] in edits.get("remove", {}):
                removed.append({"id": r["id"], "label": r.get("label", ""), "value": r.get("value", ""), "reason": "手作業で除外: " + edits["remove"][r["id"]]})
                continue
            for field, value in edits.get("field_replace", {}).get(r["id"], {}).items():
                r["extra_notes"].append(f"{field} を「{r.get(field, '')}」から「{value}」に修正（Claude、2026-10-28）")
                r[field] = value
            if r["id"] in edits.get("notes_replace", {}):
                r["notes"] = edits["notes_replace"][r["id"]]
                r["extra_notes"].append("備考を言い換え（Claude、2026-10-28、写しすぎの指摘への対応）")
            kept.append(r)
        rows = kept
        write_ledger(root, key, rows, removed, verify, edits)
        report.append(f"{key}: {len(rows)} 行（除外 {len(removed)}、訂正等 {len(log)}）")
        for r in rows:
            if r.get("grade") == "公式" and r.get("official_quote"):
                for s in r.get("sources", []):
                    if s.startswith("OF-"):
                        quotes.setdefault(s, []).append((r["id"], r["official_quote"]))
        for s in built.get("sources", []):
            for field, value in edits.get("source_replace", {}).get(s["id"], {}).items():
                s[field] = value
            prev = sources.get(s["id"])
            if prev and (prev.get("url") != s.get("url")):
                source_conflicts.append(f"{s['id']}: {prev.get('url')} と {s.get('url')}")
                continue
            sources.setdefault(s["id"], s)
        for si in (verify or {}).get("source_issues", []):
            source_issues.append(f"{si.get('source_id')}: {si.get('issue')}")
        for c in built.get("ingame_checks", []):
            cid = c["id"] if c["id"].startswith("IG-") else f"IG-{key.upper()}-{c['id']}"
            checks.append([cid, c.get("what", ""), c.get("how", ""), c.get("effort", ""), "; ".join(c.get("related_rows", [])), "", "", ""])
    src_rows = [[s["id"], s.get("kind", ""), s.get("title", ""), s.get("url", ""), s.get("published", ""), s.get("patch", ""),
                 s.get("retrieved", ""), s.get("lineage", ""), s.get("copy_policy", ""), s.get("wayback", "")]
                for s in sorted(sources.values(), key=lambda x: (not x["id"].startswith("OF-"), x["id"]))]
    parts = [
        "# 出典台帳",
        "",
        "- 値台帳の「出典」列の ID をここで引く。公式（OF-）の原文抜粋は [official/](official/) に保存している（© SQUARE ENIX）。",
        "- 第三者の資料（EX-）は出典のみ（URL・日付・系統・既存のアーカイブ）。本文は保存しない。",
        "- ゲーム内での確認（IG-）は [ゲーム内確認リスト](ingame-checks.md) と対応する。",
        "- 系統: 写し合いの可能性がある資料は同じ系統にまとめる。「外部」等級は独立した系統の数で判定する。",
        "",
        table(SOURCE_COLS, src_rows),
        "",
    ]
    if source_issues or source_conflicts:
        parts += ["## 出典についての指摘", ""]
        parts += [f"- {cell(x)}" for x in source_issues + source_conflicts]
        parts.append("")
    (root / "frontline" / "data" / "sources.md").write_text("\n".join(parts), encoding="utf-8")
    cparts = [
        "# ゲーム内確認リスト",
        "",
        "- ゲーム内でしか確かめられない値の確認手順。結果・確認日・パッチを記入すると、該当する行を「実測」に格上げできる。",
        "- 外部ツール（ACT・Dalamud など）は使わない。録画とゲーム内の表示（スコアHUD・バトルログ・チャットのタイムスタンプ）で確かめる。",
        "",
        table(CHECK_COLS, checks),
        "",
    ]
    (root / "frontline" / "data" / "ingame-checks.md").write_text("\n".join(cparts), encoding="utf-8")
    off_dir = root / "frontline" / "data" / "official"
    for sid, qs in quotes.items():
        s = sources.get(sid, {})
        body = [
            f"# {cell(s.get('title', sid))}",
            "",
            f"- 出典ID: {sid}",
            f"- URL: {s.get('url', '')}",
            f"- 種別: {s.get('kind', '')}",
            f"- 取得日: {s.get('retrieved', TODAY)}",
            "- © SQUARE ENIX（公式サイトの文の抜粋。非商用のファンサイトの保守のために保存）",
            "",
            "## 抜粋",
            "",
        ]
        seen = set()
        for rid, q in qs:
            if q in seen:
                continue
            seen.add(q)
            body.append(f"- （{rid}）「{cell(q)}」")
        (off_dir / f"{sid}.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    print("\n".join(report))
    print(f"出典 {len(sources)} 件（URL の食い違い {len(source_conflicts)}、ID の統合 {len(alias)}: {alias}）、確認項目 {len(checks)} 件、公式抜粋 {len(quotes)} ファイル")
    return 0


if __name__ == "__main__":
    sys.exit(main())
