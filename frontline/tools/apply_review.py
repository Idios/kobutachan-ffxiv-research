"""確認用ページで書き出した判定（JSON）を、値台帳の「採否」「コメント」列に取り込む。

使い方:
    python frontline/tools/apply_review.py <frontline-review-YYYY-MM-DD.json> [--dry-run]

- 行 ID の接頭辞（COM- / SEC- / SEI- / SHA- / NAA- / TRI-）で台帳を選ぶ。
- 判定したときの値（value）が今の台帳の値と違う行は取り込まない（値が変わったので判定し直す）。
- 台帳の他の列は変えない。取り込んだあとで台帳の検査（validate）を回す。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("decisions")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    decisions: dict[str, dict] = data.get("decisions", {})
    ledgers, _, errors = ledger.load_all()
    if errors:
        print("台帳の検証エラーがあるので先に直す:")
        for e in errors:
            print(" ", e)
        return 2
    rows = {r.id: r for led in ledgers for r in led.rows}
    prefix_rule = {v[0]: k for k, v in ledger.RULES.items()}
    per_rule: dict[str, dict[str, dict[str, str]]] = {}
    skipped: list[str] = []
    counts = {"○": 0, "×": 0, "": 0}
    for rid, d in decisions.items():
        r = rows.get(rid)
        if r is None:
            skipped.append(f"{rid}: 台帳にない行")
            continue
        if d.get("value") is not None and d["value"] != r.value:
            skipped.append(
                f"{rid}: 判定したときの値 {d['value']!r} と今の値 {r.value!r} が違う（判定し直す）"
            )
            continue
        verdict = ledger.VERDICT_ALIASES.get(d.get("verdict", ""), d.get("verdict", ""))
        if verdict not in ledger.VERDICTS:
            skipped.append(f"{rid}: 採否 {verdict!r} は ○ か × か空欄にする")
            continue
        rule = prefix_rule[rid.split("-", 1)[0] + "-"]
        per_rule.setdefault(rule, {})[rid] = {
            "採否": verdict,
            "コメント": d.get("comment", "").strip(),
        }
        counts[verdict] += 1
    day = data.get("exported_at", "")[:10] or Path(args.decisions).stem.removeprefix("frontline-review-")
    for rule, updates in per_rule.items():
        print(f"{rule}: {len(updates)} 行")
        if not args.dry_run:
            left = ledger.update_cells(
                ledger.LEDGER_DIR / f"{rule}.md", ledger.LEDGER_COLS, updates
            )
            skipped += [f"{x}: 台帳の表に見つからない" for x in left]
            # 判定したときの値を記録する（公式でない行は、値が変わると validate が止める）
            for rid, u in updates.items():
                if rid in left:
                    continue
                ledger.record_judgment(
                    rid, u["採否"], rows[rid].value, day, f"確認用ページ（{Path(args.decisions).name}）"
                )
    print(
        f"取り込み: ○ {counts['○']} ／ × {counts['×']} ／ 取消 {counts['']}"
        + ("（試行のみ。台帳は変えていない）" if args.dry_run else "")
    )
    for s in skipped:
        print("取り込まなかった:", s)
    _, _, errors = ledger.load_all()
    for e in errors:
        print("エラー:", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
