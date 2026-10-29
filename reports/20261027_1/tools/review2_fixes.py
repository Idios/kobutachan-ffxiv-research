"""2026-10-29: ページの見直し（4観点＋検証役。reports/20261027_1/ledger-build/review2/）の指摘のうち、台帳側の直しの記録。

ページ側の直しは frontline/tools/pages.py・build.py にある。

使い方: python reports/20261027_1/tools/review2_fixes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import ledger  # noqa: E402

DISPLAY = {
    # 「確定」がサークルの確定（隣の行）と同じ意味に読めて、値と逆に取れたため
    "TRI-CIRCLE-OVERWRITE": "制圧までは他部隊のサークルも塗り替えられる",
    # ほかの行の数（目標値 1600 = SHA-WIN-TARGET）を表示文に埋め込まない
    "SHA-DRAW-RULE": "2部隊以上が同時に目標値に達すると引き分け",
    # 予告の秒数（30 = SHA-ICE-WARN-LEAD）を表示文に埋め込まない。秒数は同じカードのチップに出ている
    # さらに、箱の中で語の途中で折り返さない長さにした（読みやすさの観点の指摘）
    "SHA-MAP-STATES": "表示なし（破壊直後）→ 黒い影（停止中）→ 縁取り・光る影（予告）→ 氷のアイコン（攻撃できる）",
    # 2つ目の節の主語（高ランクで）が落ちて、リスそのものが増えるとも読めたため
    "SEI-RANK-TREND": "高ランクほど出にくい。時間が経つと高ランクが出やすい",
    # 「契約中」が30秒の契約状態とも読めたため（値と同じ「契約の実行中」に）
    "NAA-CLAIM-INTERRUPT": "契約の実行中に攻撃を受けると中断",
}
CONDITION = {
    # 雪と同じく「最初の」とする（TRI-WX-ORDER の「各1回・順番固定」は ×）
    "TRI-WX-AURORA-START": "最初のオーロラが始まる時間帯（回数と順番は未確認。TRI-WX-ORDER）",
}


def main() -> int:
    for rid, text in DISPLAY.items():
        print(rid, ledger.set_display(rid, text))
    upd = {}
    for rid, cond in CONDITION.items():
        upd.setdefault(rid.split("-", 1)[0], {})[rid] = {"条件・配り方": cond}
    for prefix, rows in upd.items():
        rule = next(r for r, (p, _) in ledger.RULES.items() if p == prefix + "-")
        left = ledger.update_cells(ledger.LEDGER_DIR / f"{rule}.md", ledger.LEDGER_COLS, rows)
        print(rule, "条件", list(rows), "残り", left)
    _, _, errors = ledger.load_all()
    print("検証:", "エラーなし" if not errors else errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
