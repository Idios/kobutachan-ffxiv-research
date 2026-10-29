"""2026-10-29: 2回目の判定（frontline-review-2026-10-29.json）の後の台帳の直しの記録。

1. 砕氷戦の SHA-DRAW-RULE を、同じ規則の共通の行 COM-MATCH-DRAW（ユーザーが ○）に寄せて消す（値を2か所に置かない。
   検証役が「ユーザーがこの行を採ったら SHA-DRAW-RULE を外す」と書いていた）。判定の記録とゲーム内確認の参照も直す。
2. 邀撃システムの撃破について、ユーザーの回答を記録する（公式の記載を採用）。
3. 新しく ○ になった8行のコメント欄の「判定待ち」を直す。
4. ページに出す行の表示文を書く。

使い方: python reports/20261027_1/tools/round3_edits.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import ledger  # noqa: E402

DAY = "2026-10-29"
L = ledger.LEDGER_DIR


def drop_row(path: Path, cols: list[str], rid: str) -> bool:
    found = ledger.find_table(path, cols)
    if found is None:
        return False
    body, start = found
    ids = [c[0] if c else "" for c in body]
    if rid not in ids:
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    del lines[start + 1 + ids.index(rid)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def append_to_section(path: Path, heading: str, bullet: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    i = lines.index(heading)
    j = i + 1
    while j < len(lines) and not lines[j].startswith("## "):
        j += 1
    while j > i + 1 and not lines[j - 1].strip():
        j -= 1
    lines[j:j] = [bullet]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ledgers, _, errors = ledger.load_all()
    if errors:
        print("台帳の検証エラーがあるので先に直す:", *errors, sep="\n  ")
        return 2
    rows = {r.id: r for led in ledgers for r in led.rows}

    # 1. SHA-DRAW-RULE を COM-MATCH-DRAW に寄せる
    if "SHA-DRAW-RULE" in rows:
        old = rows["SHA-DRAW-RULE"]
        sha = L / "shatter.md"
        for cols in (ledger.LEDGER_COLS, ledger.EVIDENCE_COLS, ledger.DISPLAY_COLS):
            drop_row(sha, cols, "SHA-DRAW-RULE")
        append_to_section(
            sha, "## 除外した行（検証役の指摘）",
            f"- SHA-DRAW-RULE（{DAY}）: 共通の COM-MATCH-DRAW（ユーザーが ○）と同じ規則なので、共通台帳に寄せて消した（値を2か所に置かない）。"
            f"消した行の値「{old.value}」（等級 {old.grade}、2026-10-28 にユーザーが ○）。出典 {'; '.join(old.sources)}。",
        )
        drop_row(ledger.JUDGE_MD, ledger.JUDGE_COLS, "SHA-DRAW-RULE")
        com = rows["COM-MATCH-DRAW"]
        ledger.update_cells(L / "common.md", ledger.EVIDENCE_COLS, {"COM-MATCH-DRAW": {
            "備考": com.notes + f" ／ {DAY}: ユーザーが ○。砕氷戦の SHA-DRAW-RULE（同じ規則）は、この行に寄せて消した"}})
        chk = ledger.find_table(ledger.CHECKS_MD, ledger.CHECK_COLS)
        for c in chk[0]:
            rel = c[ledger.CHECK_COLS.index("関係する行")]
            if "SHA-DRAW-RULE" in rel:
                new = "; ".join(x for x in (s.strip() for s in rel.split(";")) if x and x != "SHA-DRAW-RULE")
                ledger.update_cells(ledger.CHECKS_MD, ledger.CHECK_COLS, {c[0]: {"関係する行": new}})
                print("確認項目の参照を直した:", c[0])
        print("SHA-DRAW-RULE を COM-MATCH-DRAW に寄せた")

    # 2. 邀撃システムの撃破（ユーザーの回答）
    node = rows["SEC-BH-NODE"]
    note = (f"{DAY}: ユーザーの回答「プレイヤーの攻撃によって撃破はできないがギミックが撃破するものだと思う。公式の記載を採用でよい」。"
            "公式ガイドの記載（カウント5で点滅し撃破可能）を採用し、食い違いは解消とした。撃破したときの戦意値は分からないまま（この行は ×）")
    if "公式の記載を採用でよい" not in node.notes:
        ledger.update_cells(L / "secure.md", ledger.EVIDENCE_COLS, {"SEC-BH-NODE": {"備考": node.notes + " ／ " + note}})
    ledger.update_cells(ledger.CHECKS_MD, ledger.CHECK_COLS, {"IG-SEC-06": {"確認すること": (
        "システムのイベント：最後（6回目）の撃破が何によるか（ユーザーの見立ては、プレイヤーの攻撃ではなくギミック。"
        "撃破できるかは公式の記載を採用。2026-10-29）、HPが0になるたびの戦術値（3部隊の合計が150か）、戦意値が入るか、"
        "撃破したときにイベントが早く終わるか（終わるなら転移装置もそのとき止まるか）、継続時間（120秒か）")}})

    # 3. 新しく ○ になった行のコメント
    newly = ["COM-MATCH-TIMEOUT", "COM-MATCH-DRAW", "SEI-OCC-PERSIST", "SHA-ICE-BH", "NAA-WARN-NOTICE", "NAA-CLAIM-LOOK",
             "TRI-CIRCLE-DEFEND", "TRI-SNOW-BLESS-TIMING"]
    by_rule: dict[str, dict[str, dict[str, str]]] = {}
    for rid in newly:
        if "判定待ち" in rows[rid].comment:
            by_rule.setdefault(rows[rid].rule, {})[rid] = {
                "コメント": f"2026-10-29 に追加（検証役が指摘した漏れ）。ユーザーが ○（{DAY}）"}
    for rule, upd in by_rule.items():
        ledger.update_cells(L / f"{rule}.md", ledger.LEDGER_COLS, upd)

    # 4. 表示文
    texts = {
        "COM-MATCH-TIMEOUT": "時間切れは多い順",
        "TRI-TIMEOUT": "時間切れは多い順",
        "SEI-OCC-PERSIST": "占拠したら、離れても加算は続く",
        "SHA-ICE-BH": "戦意高揚の与ダメージ上昇は氷にも乗る",
        "NAA-CLAIM-LOOK": "契約した土地の柱に、部隊の紋章入りの旗が立つ",
        "TRI-CIRCLE-CONTEST": "敵がいる間は進まない",
        "TRI-CIRCLE-DEFEND": "味方がいる間は取られない",
        "TRI-SNOW-BLESS-TIMING": "円が満ちたとき中にいると付く",
    }
    for rid, text in texts.items():
        print(rid, ledger.set_display(rid, text))
    _, _, errors = ledger.load_all()
    print("検証:", "エラーなし" if not errors else "\n  ".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
