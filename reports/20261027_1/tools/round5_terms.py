"""2026-10-29: 用語の点検（ユーザーの指摘10「用語が正しいか全体を見直して」）のうち、台帳の表示文の直しの記録。

点検は点検役1・懐疑的な検証役1のワークフロー（1ラウンドで打ち切り。結果は reports/20261027_1/ledger-build/terms/）。
検証役が「直すべき」とした語だけを、公式の日本語の表記に合わせる。値（正典の文）は変えず、ページに出す表示文だけを直す。
数は足さない（表示文の検査が止める）。

直さなかったもの（検証役が「誤りではない」とした。terms/verify.json）: 「土地」「目標地」（同じページに正式名がある自然な省略）、
「ドローン・α」「コマンダー」（同じカードの各行が正式名）、「最多ダメのパーティ全員」「段階」（説明文の言い換え）、
「与ダメ」「被ダメ」「LB(2位)」（狭い列見出しの略）、「撃破」「被撃破」（ユーザーの指定。公式サイトの文はプレイヤーに「ノックアウト」を使う）、
終節戦の「同時に出る」（公式は「出現」とも書く）。

使い方: python reports/20261027_1/tools/round5_terms.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import ledger  # noqa: E402

# 行 ID → 新しい表示文（公式の表記。根拠の原文は terms/verify.json）
DISPLAY = {
    # 争奪戦: 通称の「リス」をやめる（公式は「アラガントームリス」としか書かない。frontline/3/）。
    # 正式名を入れると2行になり1画面からあふれるので、カードの見出し（アラガントームリスの占拠のしかた）に任せて主語を省く
    "SEI-OCC-ENEMY": "敵の占拠中は2回の占拠で奪う（1回目で中立）",
    # 争奪戦: 「触れない」→「アクセスできない」（frontline/3/「一定時間アクセスすることができなくなります」）
    "SEI-OCC-LOCKOUT": "状態が変わった直後は、しばらくアクセスできない",
    # 争奪戦: 「Bは出ない」→「ランクBは出ない」（frontline/3/「ランクS、ランクA、ランクB」。演習戦と揃う）
    "SEI-RANK-NO-B-LATE": "ランクBは出ない",
    # 砕氷戦: 「氷」→「アイスドトームリス」（公式は対象を「氷」と略さない）
    "SHA-ICE-BH": "戦意高揚の与ダメージ上昇はアイスドトームリスにも乗る",
    # 演習戦: 「サークル」→「戦略サークル」（frontline/6/。ページに正式名が一度も出ていなかった）
    "TRI-CLAIM-CONDITION": "戦略サークルを全部同じ部隊で占拠すると制圧",
}


def main(only: set[str] | None = None) -> int:
    ledgers, _, errors = ledger.load_all()
    if errors:
        print("台帳の検証エラーがあるので先に直す:", *errors, sep="\n  ")
        return 2
    rows = {r.id: r for led in ledgers for r in led.rows}
    for rid, text in DISPLAY.items():
        if only is not None and rid not in only:
            continue
        if rows[rid].display == text:
            print(rid, "変更なし")
            continue
        print(rid, ledger.set_display(rid, text))
    _, _, errors = ledger.load_all()
    print("検証:", "エラーなし" if not errors else "\n  ".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(set(sys.argv[1:]) or None))
