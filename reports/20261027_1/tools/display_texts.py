"""2026-10-28: 文字を倍にしたページ用の表示文（短い言い方）を台帳に書いた記録。

台帳の値（文）が長く、倍の文字では1画面に収まらないため。表示文は値を言い換えただけで、
数は値にあるものだけ（ledger.py validate が検査する）。値が変わると検査で止まる。

使い方:
    python reports/20261027_1/tools/display_texts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "frontline" / "tools"))
import ledger  # noqa: E402

TEXTS = {
    # ルール共通
    "COM-LB-RULE": "部隊の順位で溜まる量に倍率がかかる",
    # 外縁遺跡群
    "SEC-SHEER-WILL": "拠点エリアの中は「不退転」で与ダメージが大幅に上がる",
    "SEC-DRONE-DIST": "与ダメージの割合で分ける",
    "SEC-CMDR-DIST": "受け止めた部隊に入る",
    "SEC-CMDR-PTS-UNIT": "予兆1か所ごと",
    "SEC-NODE-DIST": "HP0のたびに与ダメージの割合で分ける",
    "SEC-EVT-FIRST-KIND": "システムかドローン。コマンダーは出ない",
    "SEC-EVT-PANEL-ONEWAY": "中央への一方通行",
    "SEC-EVT-HUD-NEXT": "戦況情報に次の出現までの時間（と種類）が出る",
    # シールロック
    "SEI-OCC-INTERRUPT": "攻撃を受けると中断",
    "SEI-OCC-ENEMY": "敵のリスは2回の占拠で奪う（1回目で中立）",
    "SEI-OCC-LOCKOUT": "状態が変わった直後は、しばらく触れない",
    "SEI-OCC-CAPTURE-BONUS": "占拠した瞬間の加点はない（加算は占拠中だけ）",
    "SEI-TOME-NEUTRAL-DRAIN": "中立の間、残りの情報値は減らない",
    "SEI-TOME-STACK": "複数を占拠すると、それぞれの加算の合計",
    "SEI-RANK-TREND": "高ランクほど出にくく、時間が経つと出やすくなる",
    "SEI-RANK-NO-B-LATE": "Bは出ない",
    # フィールド・オブ・グローリー
    "SHA-ICE-DISTRIB": "壊した時点で、各部隊の与ダメージの割合で分ける",
    "SHA-DRAW-RULE": "2部隊以上が同時に1600に達すると引き分け",
    "SHA-S-REACT-RULE": "1個壊れるごとに1か所ずつ（2巡目は一斉ではない）",
    # オンサル・ハカイル
    "NAA-OVOO-RECIPIENT": "契約した部隊だけに、契約の間ずっと入る",
    "NAA-CLAIM-MULTI": "人数で速くならない",
    "NAA-NOREPEAT": "同じ地点には続けて出ない",
    "NAA-SPAWN-REFILL": "契約が終わると、別の地点が予告になる",
    "NAA-CLAIM-INTERRUPT": "契約中に攻撃を受けると中断",
    "NAA-CLAIM-LOCK": "契約した土地は、終わるまで奪われない",
    "NAA-TIME-TREND": "時間が経つほど上限が減り、高ランクが出やすい",
    "NAA-STATE-WARN": "上空の記号が完成すると契約できる",
    # ウォーコー・チーテ
    "TRI-OBJ-RECIPIENT": "制圧した部隊だけに、制圧の間ずっと入る",
    "TRI-SPAWN-REFILL": "制圧が終わると、別の地点が移行状態になる",
    "TRI-TIMEOUT": "時間切れは戦略値の多い順",
    "TRI-SNOW-STATUE-CENTER": "中央の三叉路が雪像でふさがる",
    "TRI-AURORA-LB-STACK": "順位の倍率や英雄のファンタジアと重なる",
    "TRI-AURORA-NO-B": "ランクBは出ない",
    "TRI-AURORA-HIGHRANK": "高ランクが出やすい",
    "TRI-CLAIM-CONDITION": "サークルを全部同じ部隊で占拠すると制圧",
    "TRI-CIRCLE-HEADCOUNT": "人数で速くならない",
    "TRI-CIRCLE-CONTEST": "敵がサークルにいる間は進まない",
    "TRI-CIRCLE-RESET": "確定する前に無人になると最初から",
    "TRI-CIRCLE-KEEP": "確定したサークルは離れてよい",
    "TRI-CIRCLE-OVERWRITE": "制圧が確定するまでは、他部隊のサークルを塗り替えられる",
    "TRI-CLAIM-LOCK": "制圧した目標地は奪われない（時間がたつと無効に戻る）",
}


def main() -> int:
    for rid, text in TEXTS.items():
        print(rid, ledger.set_display(rid, text))
    _, _, errors = ledger.load_all()
    print("検証:", "エラーなし" if not errors else "\n".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
