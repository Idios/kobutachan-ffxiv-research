"""Kimi の査読（2026-11-17）で確認できた中国版公式の表記へ、簡体字を寄せる一度きりの道具。

- 値は frontline/data/i18n/ の表を書き換える（生成ページは手で直さない）。
- terms.md の「出典」は、簡体字を中国版公式の URL に差し替える（繁体字版からの変換ではなくなったため）。
- 第 2 回査読の指摘（`TRI-CIRCLE-OVERWRITE` の動詞、`雪精の祝福` の `防护罩`）もここに入れてある。
- 実行後は python frontline/tools/i18n.py check / build.py / pytest を通すこと。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "frontline" / "tools"))
import i18n  # noqa: E402
import ledger  # noqa: E402

I18N = ROOT / "frontline" / "data" / "i18n"
TERM_COLS = ["キー", "日本語", "en", "de", "fr", "ko", "zh-hans", "zh-hant", "出典"]
UI_COLS = ["日本語", "en", "de", "fr", "ko", "zh-hans", "zh-hant", "メモ"]
TEXT_COLS = ["ID", "元の文", "en", "de", "fr", "ko", "zh-hans", "zh-hant"]

CN_EVENT = "https://actff1.web.sdo.com/project/160810event/page{}.html"
CN_PVP = CN_EVENT.format("1")
CN_JOB = "https://actff1.web.sdo.com/project/20190917jobguid/index.html#/continfo/{}/pvp"
CN_INDEX = "https://actff1.web.sdo.com/project/20190917jobguid/index.html#/indexpvp"
TW_NAADAM = "https://www.ffxiv.com.tw/web/intro/guide/pvpguide/pvp_page04_4.html"

# ---------------------------------------------------------------- 値の差し替え

TERMS = {
    # マップ名
    "rule-triumph-map": {"zh-hans": "沃刻其特"},
    # 特職名（中国版公式の職名）
    "job-WHM": {"zh-hans": "白魔法师"},
    "job-AST": {"zh-hans": "占星术士"},
    "job-RPR": {"zh-hans": "钐镰客"},
    "job-VPR": {"zh-hans": "蝰蛇剑士"},
    "job-BLM": {"zh-hans": "黑魔法师"},
    "job-SMN": {"zh-hans": "召唤师"},
    "job-RDM": {"zh-hans": "赤魔法师"},
    # 極限技（中国版公式の各職ページ）
    "lb-PLD": {"zh-hans": "列阵"},
    "lb-DRK": {"zh-hans": "夜昏"},
    "lb-WHM": {"zh-hans": "涤罪之心"},
    "lb-SCH": {"zh-hans": "炽天附体"},
    "lb-AST": {"zh-hans": "星河漫天"},
    "lb-SGE": {"zh-hans": "中庸之道"},
    "lb-MNK": {"zh-hans": "陨石冲击"},
    "lb-DRG": {"zh-hans": "冲天"},
    "lb-RPR": {"zh-hans": "暗夜游魂"},
    "lb-VPR": {"zh-hans": "吞天巨蛇"},
    "lb-DNC": {"zh-hans": "行列舞"},
    "lb-SMN-1": {"zh-hans": "龙神召唤"},
    "lb-SMN-2": {"zh-hans": "不死鸟召唤"},
    "lb-RDM": {"zh-hans": "南天十字"},
    "lb-PCT": {"zh-hans": "胖胖之墙"},
    # 職能名（中国版公式の PvP 職能一覧）
    "role-role_melee": {"zh-hans": "近战职业"},
    "role-role_pranged": {"zh-hans": "远程职业"},
    "role-role_mranged": {"zh-hans": "魔法职业"},
    # 共通の用語
    "term-リミットゲージ": {"zh-hans": "极限技积蓄条"},
    "term-リミットブレイク": {"zh-hans": "极限技"},
    "term-雪": {"zh-hans": "小雪"},
}

UI = {
    # 順位（中国版・繁体字版とも 1位/2位/3位）
    "1位": {"zh-hans": "1位", "zh-hant": "1位"},
    "2位": {"zh-hans": "2位", "zh-hant": "2位"},
    "3位": {"zh-hans": "3位", "zh-hant": "3位"},
    # 差し込み値に「秒前／秒後」が入るので、雛形側の「前／後」を落とす
    "2Dマップの予告は 起動の {0}": {"zh-hans": "2D地图预告：启动{0}", "zh-hant": "2D地圖預告：啟動{0}"},
    "予告の {0}に契約できる": {"zh-hans": "预告{0}可契约", "zh-hant": "預告{0}可契約"},
    "停止してから {0}に次が起動（場所はランダム）": {"zh-hans": "停止{0}下一个启动（位置随机）", "zh-hant": "停止{0}下一個啟動（位置隨機）"},
    "大: 壊れて {0}に次の予告": {"zh-hans": "大：破坏{0}下次预告", "zh-hant": "大：破壞{0}下次預告"},
    "記号が出て {0}に制圧できる（開幕 {1}）": {"zh-hans": "记号出现{0}可控制（开局{1}）", "zh-hant": "記號出現{0}可壓制（開場{1}）"},
    "転移装置: 出現の {0}〜{1}（最初は 残り {2} から）・{3}・着いて無敵 {4}": {
        "zh-hans": "传送装置：出现{0}–{1}（最初从剩余{2}开始）· {3} · 抵达后无敌{4}",
        "zh-hant": "傳送裝置：出現{0}–{1}（最初從剩餘{2}開始）· {3} · 抵達後無敵{4}",
    },
    # 継続時間・待ち時間
    "停止まで {0}": {"zh-hans": "距停止还有{0}", "zh-hant": "距停止還有{0}"},
    "秒毎": {"zh-hans": "秒", "zh-hant": "秒"},
    "秒間": {"zh-hans": "秒", "zh-hant": "秒"},
    "分": {"zh-hans": "分钟", "zh-hant": "分鐘"},
    # tick の言い方（「3每秒」→「每3秒」）
    "{0}/{1}": {"zh-hans": "每{1}：{0}", "zh-hant": "每{1}：{0}"},
    "（{0}/{1}）": {"zh-hans": "（每{1}：{0}）", "zh-hant": "（每{1}：{0}）"},
    # 数の並び（「第数列：4」→「第4 · 第7处」）
    "数の並び: {0}・{1}": {"zh-hans": "第{0} · 第{1}", "zh-hant": "第{0} · 第{1}"},
    "{0}か所目で大きく伸びる（青）": {"zh-hans": "{0}处大幅增长（蓝）", "zh-hant": "{0}處大幅成長（藍）"},
    # ジョブ（特職）
    "ジョブ": {"zh-hans": "特职"},
    "ジョブを押すと、ここに補正が出ます（{0}つまで）": {"zh-hans": "点击特职后，在此显示修正（最多{0}个）"},
    "ジョブ補正": {"zh-hans": "特职修正"},
    "ジョブ補正｜フロントライン早見表": {"zh-hans": "特职修正｜纷争前线速查表"},
    "公式ジョブガイド": {"zh-hans": "官方特职指南"},
    "与ダメ": {"zh-hans": "给予伤害"},
    "与ダメ・被ダメはフロントラインでのジョブ補正。LB は基準の蓄積時間に補正を足した秒数（順位による倍率は含まない）。行を押すと自分のジョブとして記憶し、各ルールのページに出ます（{0}つまで）。": {
        "zh-hans": "给予伤害与受到伤害为纷争前线中的特职修正。LB为基准积蓄时间加上修正的秒数（不含排位倍率）。点击行可将其记忆为自己的特职，并显示在各规则页面（最多{0}个）。",
        "zh-hant": "給予傷害與受到傷害為紛爭前線中的特職修正。LB為基準蓄積時間加上修正的秒數（不含排位倍率）。點擊列可記憶為自己的特職，並顯示於各規則頁面（最多{0}個）。",
    },
    "基準の蓄積時間＋ジョブ補正。順位の倍率が1（{0}）のとき": {
        "zh-hans": "基准积蓄时间＋特职修正。排位倍率为1（{0}）时",
        "zh-hant": "基準蓄積時間＋特職修正。排位倍率為1（{0}）時",
    },
    # リミットゲージの見出し（公式の短い呼び方）
    "リミットゲージ {0}": {"zh-hans": "极限槽{0}"},
    # 演習戦の用語（中国版公式）
    "同時に出る戦略目標地の数の上限と天候（残り時間）": {"zh-hans": "同时出现的战略目标点数量上限与天气（剩余时间）"},
    "戦略目標地と制圧のしかた": {"zh-hans": "战略目标点与控制方法"},
    "戦略サークル {0}": {"zh-hans": "占领区域{0}"},
    "サークル1つに {0}（{1}）": {"zh-hans": "每个占领区域{0}（{1}）"},
    "最初のオーロラ": {"zh-hans": "首次极光"},
    "雪精の祝福: 最大HPの {0} のバリア（{1}）": {"zh-hans": "雪精的祝福：最大HP{0}的防护罩（{1}）"},
    "最初の雪 {0}間": {"zh-hans": "首次小雪{0}"},
    # フッタ（未確認の語が残る中国語では「公式」と断定しない）
    "自動翻訳（ゲームの用語は公式の表記）": {
        "zh-hans": "机器翻译（游戏译名参考官方）",
        "zh-hant": "機器翻譯（遊戲譯名參考官方，部分未確認）",
    },
}

TEXT = {
    "COM-LB-RULE": {"zh-hans": "积蓄量按排位乘以倍率", "zh-hant": "蓄積量依排位乘以倍率"},
    "COM-MATCH-TIMEOUT": {"zh-hans": "时间结束时按数值高低排位", "zh-hant": "時間結束時按分數高低排位"},
    "TRI-TIMEOUT": {"zh-hans": "时间结束时按数值高低排位", "zh-hant": "時間結束時按分數高低排位"},
    "NAA-CLAIM-GUARDIAN": {
        "zh-hans": "正在接触场景物体的队友无法以卫护保护",
        "zh-hant": "正在接觸場景物體的隊友無法以衛護保護",
    },
    "SEI-OCC-LOCKOUT": {"zh-hans": "状态变化后短时间内无法接触"},
    "TRI-AURORA-LB-STACK": {"zh-hans": "与排位倍率、英雄的幻想曲叠加", "zh-hant": "與排位倍率·英雄的幻想曲疊加"},
    "TRI-CIRCLE-KEEP": {"zh-hans": "已占领的区域可以离开"},
    "TRI-CIRCLE-OVERWRITE": {"zh-hans": "在控制战略目标点前，其他部队的占领区域也可重新占领"},
    "TRI-CIRCLE-RESET": {"zh-hans": "占领完成前若无人则从头开始"},
    "TRI-CLAIM-CONDITION": {"zh-hans": "同一部队占领全部占领区域即进入控制状态"},
    "TRI-CLAIM-LOCK": {"zh-hans": "已控制的目标点不会被夺走"},
    "TRI-OBJ-RECIPIENT": {"zh-hans": "仅控制部队获得，整个控制期间持续"},
    "TRI-SNOW-STATUE-CENTER": {"zh-hans": "中央三岔路被雪人堵住"},
}

# ---------------------------------------------------------------- 簡体字の出典（中国版公式）

LB_PATH = {
    "lb-PLD": "paladin", "lb-WAR": "warrior", "lb-DRK": "darkknight", "lb-GNB": "gunbreaker",
    "lb-WHM": "whitemage", "lb-SCH": "scholar", "lb-AST": "astrologian", "lb-SGE": "sage",
    "lb-MNK": "monk", "lb-DRG": "dragoon", "lb-NIN": "ninja", "lb-SAM": "samurai",
    "lb-RPR": "reaper", "lb-VPR": "viper", "lb-BRD": "bard", "lb-MCH": "machinist",
    "lb-DNC": "dancer", "lb-BLM": "blackmage", "lb-SMN-1": "summoner", "lb-SMN-2": "summoner",
    "lb-RDM": "redmage", "lb-PCT": "pictomancer",
}
RULE_PAGE = {
    "rule-secure-": "4_1", "rule-seize-": "4_2", "rule-shatter-": "4_3",
    "rule-naadam-": "4_4", "rule-triumph-": "4_5",
}
TERM_PAGE = {
    "term-邀撃ドローン": "4_1", "term-邀撃ドローンα": "4_1", "term-邀撃コマンダー": "4_1",
    "term-邀撃システム": "4_1", "term-戦術値": "4_1", "term-戦意高揚": "4_1",
    "term-戦意値": "4_1", "term-アシスト": "4_1",
    "term-情報値": "4_2", "term-アラガントームリス": "4_2",
    "term-アイスドトームリス": "4_3",
    "term-無垢の土地": "4_4", "term-撃破": "4_4", "term-被撃破": "4_4",
    "term-戦略値": "4_5", "term-雪": "4_5", "term-オーロラ": "4_5",
}


def cn_source(key: str) -> str:
    for prefix, page in RULE_PAGE.items():
        if key.startswith(prefix):
            return CN_EVENT.format(page)
    if key in LB_PATH:
        return CN_JOB.format(LB_PATH[key])
    if key.startswith("job-") or key.startswith("role-"):
        return CN_INDEX
    if key in ("term-リミットゲージ", "term-リミットブレイク"):
        return CN_PVP
    if key in TERM_PAGE:
        return CN_EVENT.format(TERM_PAGE[key])
    raise SystemExit(f"出典の対応表にないキー: {key!r}")


def set_segment(src: str, lang: str, value: str) -> str:
    pat = re.compile(re.escape(lang) + r": [^;]*")
    if pat.search(src):
        return pat.sub(f"{lang}: {value}", src, count=1)
    return (src + "; " if src else "") + f"{lang}: {value}"


def update(name: str, cols: list[str], changes: dict[str, dict[str, str]]) -> int:
    """表のセルを書き換える（i18n の表は {0} を残すので、台帳の escape_cell は使わない）。"""
    path = I18N / name
    found = ledger.find_table(path, cols)
    if found is None:
        raise SystemExit(f"{name}: 表がない")
    body, start = found
    known = {cells[0]: cells for cells in body}
    missing = sorted(set(changes) - set(known))
    if missing:
        raise SystemExit(f"{name}: 知らないキー {missing}")
    lines = path.read_text(encoding="utf-8").splitlines()
    for k, cells in enumerate(body):
        key = cells[0]
        if key not in changes:
            continue
        row = list(cells)
        for col, value in changes[key].items():
            row[cols.index(col)] = value
        lines[start + 1 + k] = "| " + " | ".join(i18n._cell(c) for c in row) + " |"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return len(changes)


def apply_json(lg: str) -> None:
    """中間ファイル（初回の控え）も、正典と同じ値にそろえる（古い値が残らないように）。"""
    path = HERE / f"{lg}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for kind, table in (("ui", UI), ("text", TEXT), ("terms", TERMS)):
        for key, by_lang in table.items():
            if lg in by_lang and key in data[kind]:
                data[kind][key] = by_lang[lg]
    if lg == "ko":
        data["text"]["SEC-CMDR-PTS-UNIT"] = "명중 지점 1곳마다"
    if lg == "zh-hans":
        data["term_sources"] = {key: cn_source(key) for key in data["terms"]}
    if lg == "zh-hant":
        data["term_sources"]["term-被撃破"] = TW_NAADAM
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    n_terms = update("terms.md", TERM_COLS, TERMS)
    n_ui = update("ui.md", UI_COLS, UI)
    n_text = update("text.md", TEXT_COLS, TEXT)

    # 出典: 簡体字は全行を中国版公式へ。繁体字の「被撃破」だけ公式の受け身表現を確認できた
    path = I18N / "terms.md"
    body, _ = ledger.find_table(path, TERM_COLS)
    src_changes: dict[str, dict[str, str]] = {}
    for cells in body:
        key, src = cells[0], cells[-1]
        new = set_segment(src, "zh-hans", cn_source(key))
        if key == "term-被撃破":
            new = set_segment(new, "zh-hant", TW_NAADAM)
        if new != src:
            src_changes[key] = {"出典": new}
    update("terms.md", TERM_COLS, src_changes)

    print(f"terms: {n_terms} 値 / ui: {n_ui} / text: {n_text} / 出典: {len(src_changes)}")
    for lg in ("ko", "zh-hans", "zh-hant"):
        apply_json(lg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
