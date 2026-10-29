"""2026-10-29: ガーディアンの肩代わり（NAA-CLAIM-GUARDIAN）について、ユーザーが「公式を採用して」と指示した記録。

2026-10-28 の判定では ×（コメント「かばうでリスにアクセス中キャラクターが受けるダメージを吸収するがリスの操作は中断する。」）。
公式（6.25 ノート・現行のナイトのジョブガイド）は「対象がオブジェクトにアクセスしている場合は、この効果が無効化される」。
ユーザーが公式の記載の採用を指示したので、採否を ○ にし、判定の記録とゲーム内確認の項目を直し、表示文を書く。

使い方: python reports/20261027_1/tools/round3_guardian.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import ledger  # noqa: E402

DAY = "2026-10-29"
RID = "NAA-CLAIM-GUARDIAN"


def main() -> int:
    ledgers, _, errors = ledger.load_all()
    if errors:
        print("台帳の検証エラーがあるので先に直す:", *errors, sep="\n  ")
        return 2
    r = next(x for led in ledgers for x in led.rows if x.id == RID)
    path = ledger.LEDGER_DIR / f"{r.rule}.md"
    ledger.update_cells(path, ledger.LEDGER_COLS, {RID: {
        "採否": "○",
        "コメント": f"{DAY}: ユーザーが公式の記載の採用を指示（10-28 のコメント「吸収するが操作は中断」は取り下げ）",
    }})
    if "公式の記載の採用を指示" not in r.notes:
        ledger.update_cells(path, ledger.EVIDENCE_COLS, {RID: {
            "備考": r.notes + f" ／ {DAY}: ユーザーが「公式を採用して」と指示。採否を ○ にした（食い違いは解消）"}})
    print("判定の記録:", ledger.record_judgment(RID, "○", r.value, DAY, "ユーザーの指示（会話。公式の記載を採用）"))
    ledger.update_cells(ledger.CHECKS_MD, ledger.CHECK_COLS, {"IG-GUARD-ACCESS": {"確認すること": (
        "ナイトのガーディアン（肩代わり）は、オブジェクトにアクセス中の味方に効くか。公式（6.25 ノート・現行のジョブガイド）は"
        "『無効化される』。2026-10-28 にユーザーが『吸収するが操作は中断』とコメントしたが、2026-10-29 に公式の記載の採用を指示した。"
        "確かめるのは任意（公式の記載と違う挙動を見たときに記録する）")}})
    print("表示文:", ledger.set_display(RID, "アクセス中の味方はガーディアンでかばえない"))
    _, _, errors = ledger.load_all()
    print("検証:", "エラーなし" if not errors else "\n  ".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
