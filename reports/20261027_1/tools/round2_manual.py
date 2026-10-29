"""2026-10-29: 漏れの調査（2回目）の取り込みのあとに、検証役が「手で行うこと」とした3件の記録。

1. official/OF-PN-74.md から COM-MATCH-WIN の抜粋を消す（COM-MATCH-WIN の出典から OF-PN-74 を外したため。
   7.4 ノートの時間切れの文は演習戦の注記で、ほかのルールの勝利条件の根拠ではない）。
2. secure.md の漏れの項目「時間切れ時の順位と、同時に2,400へ達したときの扱い」に、共通台帳の行を書き足す。
3. sources.md の EX-CGW-SECURE の系統に、勝利条件の節（時間切れ・引き分けの文）は Alyko の記述と書き足す。

使い方: python reports/20261027_1/tools/round2_manual.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import ledger  # noqa: E402

DAY = "2026-10-29"


def main() -> int:
    # 1
    p = ledger.DATA / "official" / "OF-PN-74.md"
    lines = p.read_text(encoding="utf-8").splitlines()
    kept = [ln for ln in lines if not ln.startswith("- （COM-MATCH-WIN）")]
    print("1. OF-PN-74 の COM-MATCH-WIN の抜粋:", "消した" if len(kept) < len(lines) else "なし")
    p.write_text("\n".join(kept) + "\n", encoding="utf-8")
    # 2
    p = ledger.LEDGER_DIR / "secure.md"
    lines = p.read_text(encoding="utf-8").splitlines()
    note = f"共通台帳の行 COM-MATCH-TIMEOUT・COM-MATCH-DRAW と確認 IG-COM-01・IG-COM-02 で扱う（{DAY}）"
    done = False
    for i, ln in enumerate(lines):
        if ln.startswith("- 時間切れ時の順位と、同時に2,400へ達したときの扱い") and "COM-MATCH-TIMEOUT" not in ln:
            lines[i] = ln + f"（{note}）"
            done = True
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("2. secure.md の漏れの項目:", "書き足した" if done else "書き足し済みか、項目がない")
    # 3
    src = ledger.find_table(ledger.SOURCES_MD, ledger.SOURCE_COLS)
    cur = next(c for c in src[0] if c[0] == "EX-CGW-SECURE")[ledger.SOURCE_COLS.index("系統")]
    add = "（勝利条件の節の時間切れ・引き分けの文は、利用者 Alyko の 2025-05-24・28 の記述）"
    if add not in cur:
        ledger.update_cells(ledger.SOURCES_MD, ledger.SOURCE_COLS, {"EX-CGW-SECURE": {"系統": cur + add}})
        print("3. EX-CGW-SECURE の系統: 書き足した")
    else:
        print("3. EX-CGW-SECURE の系統: 書き足し済み")
    _, _, errors = ledger.load_all()
    print("検証:", "エラーなし" if not errors else errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
