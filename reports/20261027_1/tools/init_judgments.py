"""2026-10-29: 判定の記録（frontline/data/judgments.md）を作った記録。

ページの見直し（コードの観点）で、「採否が判定したときの値に結びついていない。保守者が値だけを直すと、
ユーザーが見ていない値が ○ のまま公開される」と指摘された。そこで、公式でない行の ○ は、
判定したときの値を記録し、今の値と違えば検査で止めるようにした（ledger.py）。

記録のもと:
- 確認用ページの判定（reports/20261027_1/review/decisions/frontline-review-2026-10-28.json）。値は判定したときの値。
- ユーザーのコメントで値を直した行（round2_edits.py）は、直した値を「コメントによる訂正」として記録する。
- コメントから作った行 SEC-EVT-FIRST-KIND と、ゲーム内確認で確かめたローテーションの起点 COM-ROT-ANCHOR。

使い方: python reports/20261027_1/tools/init_judgments.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import ledger  # noqa: E402

DAY = "2026-10-28"
DECISIONS = REPO / "reports" / "20261027_1" / "review" / "decisions" / "frontline-review-2026-10-28.json"
FROM_COMMENT = {"SEI-TOME-NEUTRAL-DRAIN", "NAA-CLAIM-CAST", "TRI-SNOW-BARRIER-PCT", "TRI-AURORA-LB-STACK"}
EXTRA = {
    "SEC-EVT-FIRST-KIND": "ユーザーのコメント（SEC-EVT-FIRST に付けたもの。確認用ページ 2026-10-28）から作った行",
    "COM-ROT-ANCHOR": "ユーザーのゲーム内確認（IG-ROT-TODAY。10/27・10/28 のルール）",
}
HEADER = """# 判定の記録

ユーザーが ○／× を付けたときの値。公式でない行（外部・実測・未確認）は、採否が ○ でも、
今の値がここの「判定時の値」と違えば `python frontline/tools/ledger.py validate` がエラーにする
（値だけを直して、ユーザーが見ていない値を公開しないため）。値を直したら採否を空欄に戻し、確認用ページで判定し直してもらう。
取り込み（`frontline/tools/apply_review.py`）がこの表を書き足す。手で書き換えない。

| ID | 採否 | 判定時の値 | 判定日 | 判定のもと |
|---|---|---|---|---|
"""


def main() -> int:
    if ledger.JUDGE_MD.exists():
        print("すでにある。何もしない:", ledger.JUDGE_MD)
        return 1
    ledgers, _, _ = ledger.load_all()
    rows = {r.id: r for led in ledgers for r in led.rows}
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))["decisions"]
    recs = []
    for rid, d in decisions.items():
        r = rows[rid]
        if r.value == d["value"]:
            recs.append([rid, d["verdict"], d["value"], DAY, "確認用ページ（frontline-review-2026-10-28.json）"])
        elif rid in FROM_COMMENT:
            recs.append([rid, d["verdict"], r.value, DAY, "ユーザーのコメントによる訂正（確認用ページ 2026-10-28。round2_edits.py）"])
        else:
            print("値が判定のときと違い、理由も分からない（記録しない）:", rid)
    for rid, origin in EXTRA.items():
        recs.append([rid, rows[rid].verdict, rows[rid].value, DAY, origin])
    ledger.JUDGE_MD.write_text(HEADER + "\n".join(ledger.join_row(r) for r in recs) + "\n", encoding="utf-8")
    print(f"記録: {len(recs)} 行")
    _, _, errors = ledger.load_all()
    print("検証:", "エラーなし" if not errors else "\n  ".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
