"""2026-10-28 のユーザー判定（確認用ページのコメント）を台帳に反映した記録。

判定（○×）そのものは frontline/tools/apply_review.py で取り込み済み
（reports/20261027_1/review/decisions/frontline-review-2026-10-28.json）。
このスクリプトは、コメントに書かれた訂正・情報を値・等級・備考・確認リストに反映する。
1回だけ実行する前提。実行前に、直す行の値が判定したときのままかを確かめる（違えば何もしない）。

使い方:
    python reports/20261027_1/tools/round2_edits.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import ledger  # noqa: E402

DAY, PATCH = "2026-10-28", "7.57"
IG = "IG-REVIEW-1028"
L = ledger.LEDGER_DIR

# 値の表の書き換え: 行ID -> (今の値（確認用）, {列: 新しい中身})。出典は追記する
VALUE_EDITS: dict[str, tuple[str, dict[str, str]]] = {
    "SEI-TOME-NEUTRAL-DRAIN": ("不明（推定: 減らない）", {"値": "減らない", "等級": "実測", "現行確認": f"{PATCH} ✔ゲーム内", "+出典": IG}),
    "NAA-CLAIM-CAST": ("4〜7", {"値": "4", "等級": "実測", "現行確認": f"{PATCH} ✔ゲーム内", "+出典": IG}),
    "TRI-SNOW-BARRIER-PCT": ("50〜60", {"値": "50", "等級": "実測", "現行確認": f"{PATCH} ✔ゲーム内", "+出典": IG}),
    "TRI-AURORA-LB-STACK": (
        "順位によるLB補正や、ファイナルファンタジアと重なって効く",
        {"値": "順位によるLB補正や、吟遊詩人のLB「英雄のファンタジア」と重なって効く"},
    ),
    "SEC-EVT-FIRST": (
        "40",
        {"条件・配り方": "試合開始から40秒後。最初に出る種類は SEC-EVT-FIRST-KIND"},
    ),
    "TRI-WX-SNOW-START": (
        "16〜15",
        {"条件・配り方": "最初の雪が始まる時間帯（2回目があるかは未確認。TRI-WX-ORDER）"},
    ),
    "TRI-WX-AURORA-START": (
        "10〜9",
        {"条件・配り方": "オーロラが始まる時間帯（回数と順番は未確認。TRI-WX-ORDER）"},
    ),
}

# 根拠の表の備考に追記する文
NOTE_APPENDS: dict[str, str] = {
    "SEC-EVT-FIRST": f"{DAY}: ユーザーのコメント『最初は邀撃システムか邀撃ドローン。邀撃コマンダーは初回出ない。』を、別の行 SEC-EVT-FIRST-KIND（実測）にした",
    "SEC-DRONE-ALPHA-RATE": f"{DAY}: ユーザーの体感は約1/6（測定ではないので値にしない。採否は ×）",
    "SEC-BH-NODE": f"{DAY}: ユーザーのコメント『邀撃システムは撃破不能』（採否 ×）。公式ガイドは『カウントが5に到達すると点滅を始め、撃破可能な状態となります』と書いており、食い違う。撃破できるかと戦意値の有無を IG-SEC-06 で確かめる",
    "SEI-TOME-NEUTRAL-DRAIN": f"{DAY}: ユーザーがゲーム内の経験から『減らない』と回答（確認用ページのコメント）。値を『不明（推定: 減らない）』から『減らない』に直し、等級を実測にした",
    "NAA-CLAIM-CAST": f"{DAY}: ユーザーがゲーム内の経験から『4秒』と回答。値を『4〜7』から『4』に直し、等級を実測にした。人数で速くならないことは NAA-CLAIM-MULTI",
    "NAA-CLAIM-GUARDIAN": (
        f"{DAY}: ユーザーのコメント（採否 ×）『かばう（ガーディアン）で、リスにアクセス中のキャラクターが受けるダメージを吸収するが、リスの操作は中断する』。"
        "公式（6.25 ノート・現行のナイトのジョブガイド）は、対象がオブジェクトにアクセスしている間は肩代わりの効果が無効化されると書いていて、肩代わりの有無が食い違う。"
        "どちらの場合も、アクセス中の味方をガーディアンで守っても操作は中断される。IG-GUARD-ACCESS で確かめる"
    ),
    "TRI-WX-ORDER": f"{DAY}: ユーザーのコメント『雪は複数回発生する気がする』（採否 ×）。雪が1試合に2回以上あるかを IG-TRI-07 で確かめる",
    "TRI-WX-SNOW-START": f"{DAY}: TRI-WX-ORDER（各1回）が × になったので、条件の『1試合に1回』を外した",
    "TRI-WX-AURORA-START": f"{DAY}: TRI-WX-ORDER（各1回・順番固定）が × になったので、条件の『1試合に1回（雪の後）』を外した",
    "TRI-SNOW-BARRIER-PCT": f"{DAY}: ユーザーがゲーム内の経験から『50%』と回答。値を『50〜60』から『50』に直し、等級を実測にした。割合か固定量かは IG-TRI-08",
    "TRI-AURORA-LB-STACK": f"{DAY}: ユーザーの指摘で、吟遊詩人の LB の名前を英語版の名前（Final Fantasia）の音写から、日本語版の名前『英雄のファンタジア』（COM-LBB-BRD）に直した",
}

NEW_ROWS = {  # 台帳 -> (直後に入れる行ID, 値の行, 根拠の行)
    "secure": [
        (
            "SEC-EVT-FIRST",
            ["SEC-EVT-FIRST-KIND", "中央・時刻", "中央の最初の出現の種類", "邀撃システムか邀撃ドローン（邀撃コマンダーは最初に出ない）",
             "テキスト", "試合で最初の中央の出現（SEC-EVT-FIRST）", "実測", IG, "記録なし", f"{PATCH} ✔ゲーム内", "○",
             "ユーザーのコメント（2026-10-28）から作った行"],
            ["SEC-EVT-FIRST-KIND", "",
             f"ユーザーのゲーム内での経験（{DAY}、確認用ページで SEC-EVT-FIRST に付けたコメント『最初は邀撃システムか邀撃ドローン。邀撃コマンダーは初回出ない。』）。外部資料での裏付けは探していない。ゲーム内確認の対象: IG-SEC-03"],
        )
    ]
}

NEW_SOURCE = [IG, "ゲーム内",
              f"ユーザーのゲーム内での経験（{DAY} に確認用ページで付けたコメント。判定ファイルは reports/20261027_1/review/decisions/frontline-review-2026-10-28.json）",
              "（ゲーム内）", DAY, PATCH, DAY, "ユーザー（ゲーム内）", "出典のみ", ""]

CHECK_EDITS: dict[str, dict[str, str]] = {
    "IG-SEI-05": {"結果": f"減らない（ユーザーのゲーム内での経験。{DAY} の確認用ページのコメント）", "確認日": DAY, "パッチ": PATCH},
    "IG-NAA-06": {"結果": f"契約にかかる時間は4秒（ユーザーの経験。{DAY} のコメント）。人数による違いは記入なし", "確認日": DAY, "パッチ": PATCH},
    "IG-TRI-08": {"結果": f"バリア量は最大HPの50%（ユーザーの経験。{DAY} のコメント）。割合か固定量か・効果時間・上書き・間隔は記入なし", "確認日": DAY, "パッチ": PATCH},
    "IG-SEC-06": {
        "確認すること": "システムのイベント：そもそも撃破できるか（公式ガイドは『カウント5で点滅し撃破可能』、ユーザーは『撃破不能』と指摘。2026-10-28）、HPが0になるたびの戦術値（3部隊の合計が150か）、戦意値が入るか、6回目で撃破したときにイベントが早く終わるか、継続時間（120秒か）",
        "関係する行": "SEC-NODE-PTS-UNIT; SEC-NODE-REFILLS; SEC-BH-NODE; SEC-EVT-DUR-NODE",
    },
    "IG-TRI-07": {
        "確認すること": "天候の順番（変化なし→雪→変化なし→オーロラ）と長さ（雪300秒・オーロラ150秒か）。雪が1試合に2回以上起きるか（ユーザーは複数回あると感じている。2026-10-28）",
        "関係する行": "TRI-WX-ORDER; TRI-WX-SNOW-START; TRI-WX-SNOW-SEC; TRI-WX-AURORA-START; TRI-WX-AURORA-SEC",
    },
    "IG-SEC-03": {"関係する行": "SEC-EVT-HUD-NEXT; SEC-EVT-FIRST; SEC-EVT-FIRST-KIND; SEC-EVT-ORDER"},
}
CHECK_APPEND = {"IG-SEC-08": ("手順", "（ユーザーの体感は約1/6。2026-10-28）")}
NEW_CHECK = ["IG-GUARD-ACCESS",
             "ナイトのガーディアン（肩代わり）は、オブジェクトにアクセス中の味方に効くか。公式（6.25 ノート・現行のジョブガイド）は『無効化される』、ユーザーは『ダメージは吸収するが操作は中断する』と指摘（2026-10-28）",
             "味方と組み、味方がリス・土地・目標地にアクセスしている間に、ナイトがその味方にガーディアンを使う。敵の攻撃が当たったときに、ナイトのHPが減るか（肩代わり）、味方のHPが減るかと、味方の操作が中断されるかを録画で見る",
             "1〜3試合", "NAA-CLAIM-GUARDIAN", "", "", ""]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    dry = ap.parse_args().dry_run
    ledgers, sources, errors = ledger.load_all()
    if errors:
        print("台帳の検証エラーがあるので先に直す:", *errors, sep="\n  ")
        return 2
    rows = {r.id: r for led in ledgers for r in led.rows}
    rule_of = {r.id: r.rule for r in rows.values()}
    problems = []
    for rid, (expect, _) in VALUE_EDITS.items():
        if rows[rid].value != expect:
            problems.append(f"{rid}: 今の値 {rows[rid].value!r} が想定 {expect!r} と違う")
    if "SEC-EVT-FIRST-KIND" in rows or IG in sources:
        problems.append("すでに反映済み（SEC-EVT-FIRST-KIND か IG-REVIEW-1028 がある）")
    if problems:
        print("何もしない:", *problems, sep="\n  ")
        return 1
    value_updates: dict[str, dict[str, dict[str, str]]] = {}
    for rid, (_, cols) in VALUE_EDITS.items():
        upd = {k: v for k, v in cols.items() if not k.startswith("+")}
        if "+出典" in cols:
            upd["出典"] = "; ".join(rows[rid].sources + [cols["+出典"]])
        value_updates.setdefault(rule_of[rid], {})[rid] = upd
    note_updates: dict[str, dict[str, dict[str, str]]] = {}
    for rid, text in NOTE_APPENDS.items():
        old = rows[rid].notes
        note_updates.setdefault(rule_of[rid], {})[rid] = {"備考": f"{old} ／ {text}" if old else text}
    for rule in sorted(set(value_updates) | set(note_updates)):
        print(f"{rule}: 値 {len(value_updates.get(rule, {}))} 行・備考 {len(note_updates.get(rule, {}))} 行")
    print(f"新しい行 {sum(len(v) for v in NEW_ROWS.values())}・出典 1・確認項目 書き換え {len(CHECK_EDITS) + len(CHECK_APPEND)}／追加 1")
    if dry:
        print("（試行のみ）")
        return 0
    for rule, upd in value_updates.items():
        left = ledger.update_cells(L / f"{rule}.md", ledger.LEDGER_COLS, upd)
        assert not left, left
    for rule, upd in note_updates.items():
        left = ledger.update_cells(L / f"{rule}.md", ledger.EVIDENCE_COLS, upd)
        assert not left, left
    for rule, items in NEW_ROWS.items():
        for after, vrow, erow in items:
            assert ledger.insert_rows_after(L / f"{rule}.md", ledger.LEDGER_COLS, after, [vrow])
            ledger.insert_rows_after(L / f"{rule}.md", ledger.EVIDENCE_COLS, after, [erow])
    ledger.append_rows(ledger.SOURCES_MD, ledger.SOURCE_COLS, [NEW_SOURCE])
    checks = ledger.find_table(ledger.CHECKS_MD, ledger.CHECK_COLS)
    assert checks is not None
    cur = {c[0]: dict(zip(ledger.CHECK_COLS, c)) for c in checks[0]}
    upd = {k: dict(v) for k, v in CHECK_EDITS.items()}
    for cid, (col, add) in CHECK_APPEND.items():
        upd.setdefault(cid, {})[col] = cur[cid][col] + add
    left = ledger.update_cells(ledger.CHECKS_MD, ledger.CHECK_COLS, upd)
    assert not left, left
    ledger.insert_rows_after(ledger.CHECKS_MD, ledger.CHECK_COLS, "IG-LB-RANK-TIME", [NEW_CHECK])
    _, _, errors = ledger.load_all()
    print("検証:", "エラーなし" if not errors else errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
