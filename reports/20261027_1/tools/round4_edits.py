"""2026-10-29: ユーザーの見直し（11項目）のうち台帳の直しの記録。

6. 「邀撃ドローンα、邀撃ドローン撃破で戦意値を受け取るのはもっともダメージを与えたパーティ。戦術値を受け取るのは
   そのパーティが所属するアライアンス。」
   - α の戦意値の受け手は公式に明記がなかった（SEC-BH-ALPHA の条件）。ユーザーの指摘を実測の行 SEC-BH-ALPHA-WHO にする。
   - 戦術値は公式どおり「部隊ごとに与えたダメージの割合に応じて分配」（SEC-DRONE-DIST）。部隊（アライアンス）に入ることが
     分かるように表示文を直す。「最多ダメのパーティの部隊だけに入る」という意味なら公式と食い違うので、ユーザーに確かめる。

使い方: python reports/20261027_1/tools/round4_edits.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import ledger  # noqa: E402

DAY = "2026-10-29"
L = ledger.LEDGER_DIR
SAY = "邀撃ドローンα、邀撃ドローン撃破で戦意値を受け取るのはもっともダメージを与えたパーティ。戦術値を受け取るのはそのパーティが所属するアライアンス。"


def main() -> int:
    ledgers, sources, errors = ledger.load_all()
    if errors:
        print("台帳の検証エラーがあるので先に直す:", *errors, sep="\n  ")
        return 2
    rows = {r.id: r for led in ledgers for r in led.rows}
    sec = L / "secure.md"
    if "SEC-BH-ALPHA-WHO" not in rows:
        who = rows["SEC-BH-DRONE-WHO"].value
        vrow = ["SEC-BH-ALPHA-WHO", "中央・戦意値", "邀撃ドローンα撃破で戦意値を得る相手", who, "テキスト",
                "邀撃ドローンαを討伐したとき。量は SEC-BH-ALPHA", "実測", "IG-REVIEW-1029", "記録なし", "7.57 ✔ゲーム内", "○",
                f"ユーザーの指摘（{DAY}）から作った行"]
        erow = ["SEC-BH-ALPHA-WHO", "", f"ユーザーの指摘（{DAY}、会話）『{SAY}』。公式は α の受け手を書いていない（SEC-BH-ALPHA-MORE は量の比較だけ）。"
                "ドローン（SEC-BH-DRONE-WHO、公式）と同じ相手"]
        assert ledger.insert_rows_after(sec, ledger.LEDGER_COLS, "SEC-BH-ALPHA", [vrow])
        ledger.insert_rows_after(sec, ledger.EVIDENCE_COLS, "SEC-BH-ALPHA", [erow])
        print("行 SEC-BH-ALPHA-WHO を足した")
    if "IG-REVIEW-1029" not in sources:
        ledger.append_rows(ledger.SOURCES_MD, ledger.SOURCE_COLS, [[
            "IG-REVIEW-1029", "ゲーム内", f"ユーザーのゲーム内での経験（{DAY} の会話での指摘）", "（ゲーム内）", DAY, "7.57", DAY,
            "ユーザー（ゲーム内）", "出典のみ", ""]])
    ledger.update_cells(sec, ledger.LEDGER_COLS, {"SEC-BH-ALPHA": {
        "条件・配り方": "1体の撃破ごと。受け取る相手は SEC-BH-ALPHA-WHO（ユーザーの指摘）"}})
    r = rows["SEC-BH-ALPHA"]
    if "SEC-BH-ALPHA-WHO" not in r.notes:
        ledger.update_cells(sec, ledger.EVIDENCE_COLS, {"SEC-BH-ALPHA": {
            "備考": r.notes + f" ／ {DAY}: 受け取る相手はユーザーの指摘で SEC-BH-ALPHA-WHO（最も多くのダメージを与えたパーティ）にした"}})
    d = rows["SEC-DRONE-DIST"]
    if "ユーザーの指摘" not in d.notes:
        ledger.update_cells(sec, ledger.EVIDENCE_COLS, {"SEC-DRONE-DIST": {
            "備考": d.notes + f" ／ {DAY}: ユーザーの指摘『{SAY}』。戦術値が部隊（アライアンス）に入ることは公式どおり。"
                              "『最多ダメのパーティの部隊だけに入る』という意味なら、この行（与ダメージの割合で分配）と食い違うので確かめる"}})
    print("判定の記録:", ledger.record_judgment("SEC-BH-ALPHA-WHO", "○", rows["SEC-BH-DRONE-WHO"].value, DAY,
                                                 "ユーザーの指摘（会話。α もドローンと同じく最多ダメのパーティ）"))
    chk = ledger.find_table(ledger.CHECKS_MD, ledger.CHECK_COLS)
    cur = next(c for c in chk[0] if c[0] == "IG-SEC-05")[ledger.CHECK_COLS.index("確認すること")]
    if "ユーザーの指摘" not in cur:
        ledger.update_cells(ledger.CHECKS_MD, ledger.CHECK_COLS, {"IG-SEC-05": {
            "確認すること": cur + f"（α の戦意値の受け手は、{DAY} のユーザーの指摘で最多ダメのパーティとした）"}})
    for rid, text in {"SEC-DRONE-DIST": "部隊ごとの与ダメ割合で分配", "SEC-BH-ALPHA-WHO": "最多ダメのパーティ全員"}.items():
        print(rid, ledger.set_display(rid, text))
    _, _, errors = ledger.load_all()
    print("検証:", "エラーなし" if not errors else "\n  ".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
