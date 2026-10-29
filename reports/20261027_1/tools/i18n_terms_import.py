"""2026-10-29: 多言語化（英・独・仏）のゲーム用語を frontline/data/i18n/terms.md に書く（記録。やり直しても同じ結果）。

元は、言語ごとの調査役が各言語の公式サイト（Lodestone のフロントラインのガイド・ジョブガイド・パッチノート）から
一字一句写した用語の JSON（一時フォルダ。引用の照合は調査役のスクリプトで済み）。ここでは、ページで使う日本語の
用語ごとに、各言語の公式の表記を選ぶ。選び方:
- マップ名・ルール名・ジョブ名・ロール名・LB 名は公式の表記そのまま。
- 見出しに使う語は先頭だけ大文字にする（英語の公式文は文中で小文字のため）。
- 公式に単数形しか（または複数形しか）出てこない語は、出てきた形を使う（ドイツ語は Echolithen と複数形）。
- 英語・ドイツ語は 戦術値 と 戦略値 を同じ語で呼ぶ（tactical points ／ Siegpunkte）。フランス語は 戦術値＝score stratégique、
  戦略値＝score tactique と、日本語と逆に見える対応が公式の表記。

使い方: python -I reports/20261027_1/tools/i18n_terms_import.py <terms_en.json> <terms_de.json> <terms_fr.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import i18n  # noqa: E402
import ledger  # noqa: E402

RULES_JA = {r: ledger.RULES[r][1] for r in ("secure", "seize", "shatter", "naadam", "triumph")}

# 日本語 → 言語ごとの調査役のキー（None は下の FIXED を使う）
KEYS = {
    "邀撃ドローン": ("interceptor_drone", "drone", "drone"),
    "邀撃ドローンα": ("interceptor_drone_alpha", "drone_alpha", "drone_alpha"),
    "邀撃コマンダー": ("interceptor_command_system", "commander", "commander"),
    "邀撃システム": ("interceptor_node", "system", "system"),
    "戦術値": ("tactical_points", "tactical_points", "tactical_points"),
    "情報値": ("data", "data_points", "data_points"),
    "戦略値": ("tactical_points", "strategy_points", "strategy_points"),
    "戦意高揚": ("battle_high", "battle_high", "battle_high"),
    "リミットゲージ": ("limit_gauge", "limit_gauge", "limit_gauge"),
    "リミットブレイク": ("limit_break", "limit_break", "limit_break"),
    "アシスト": ("assist", "assist", "assist"),
}
# 調査役の表記から形を変えたもの（理由つき）。値は (en, de, fr)
FIXED = {
    "アラガントームリス": ("Allagan tomelith", "Allagische Echolithen", "Mémolithe allagois"),  # 見出し用に先頭を大文字。独は複数形しか出ない
    "アイスドトームリス": ("Icebound tomelith", "Vereiste Echolithen", "Mémolithe congelé"),
    "無垢の土地": ("Ovoo", "Unschuldsfleck", "Terre immaculée"),
    "戦意値": ("Battle High rating", "Kampfgeist", "Jauge d'ivresse"),  # 英は 7.2 ノートの battle high rating
    "撃破": ("KO", "K. o.", "K.O."),  # 英はガイドの表の見出し KO。独は K. o.（改行しない空白）
    "被撃破": ("Knocked out", "Kampfunfähig", "Mis K.O."),
    "雪": ("Snow", "Schnee", "Neige"),
    "オーロラ": ("Auroras", "Aurora", "Aurores"),
}


def main(paths: list[str]) -> int:
    src = {lg: json.load(open(p, encoding="utf-8")) for lg, p in zip(("en", "de", "fr"), paths)}
    by_key = {lg: {t["key"]: t for t in d["terms"]} for lg, d in src.items()}
    rows: list[list[str]] = []

    def url(lg: str, key: str | None = None, fallback: str = "") -> str:
        if key and key in by_key[lg]:
            return by_key[lg][key].get("url", "")
        return fallback

    def cap(s: str) -> str:
        return s[:1].upper() + s[1:]

    # マップ名・ルール名
    for r, full in RULES_JA.items():
        name, mode = full.removesuffix("）").split("（")
        for ja, part in ((name, "map"), (mode, "mode")):
            vals = [src[lg]["rules"][r][part] for lg in ("en", "de", "fr")]
            if part == "mode" and r != "naadam":
                vals[2] = cap(vals[2])  # 仏はルール名を文中で小文字（annexion など）。タブの見出しなので先頭を大文字に
            srcs = "; ".join(f"{lg}: {src[lg]['rules'][r]['url']}" for lg in ("en", "de", "fr"))
            rows.append([f"rule-{r}-{part}", ja, *vals, srcs])
    # ジョブ・LB・ロール
    jobs = {lg: {j["code"]: j for j in src[lg]["jobs"]} for lg in src}
    ja_jobs = json.load(open(Path(paths[0]).with_name("term_inputs.json"), encoding="utf-8"))["jobs"]
    roles_done = set()
    role_keys = {"タンク": "role_tank", "ヒーラー": "role_healer", "近接物理DPS": "role_melee",
                 "遠隔物理DPS": ("role_pranged", "role_physical_ranged", "role_physical_ranged"),
                 "遠隔魔法DPS": ("role_mranged", "role_magical_ranged", "role_magical_ranged")}
    for j in ja_jobs:
        c = j["code"]
        srcs = "; ".join(f"{lg}: {jobs[lg][c]['url']}" for lg in ("en", "de", "fr"))
        rows.append([f"job-{c}", j["job_ja"], *(jobs[lg][c]["job"] for lg in ("en", "de", "fr")), srcs])
        for i, lb_ja in enumerate(j["lb_ja"]):
            rows.append([f"lb-{c}" + (f"-{i + 1}" if len(j["lb_ja"]) > 1 else ""), lb_ja,
                         *(jobs[lg][c]["lb"][i] for lg in ("en", "de", "fr")), srcs])
        if j["role"] not in roles_done:
            roles_done.add(j["role"])
            k = role_keys[j["role"]]
            ks = k if isinstance(k, tuple) else (k, k, k)
            vals = [by_key[lg][kk]["term"] for lg, kk in zip(("en", "de", "fr"), ks)]
            rows.append([f"role-{ks[0]}", j["role"], *vals,
                         "; ".join(f"{lg}: {url(lg, kk)}" for lg, kk in zip(("en", "de", "fr"), ks))])
    # そのほかの用語
    for ja, ks in KEYS.items():
        # 点数の名前は文中の単位として使うので、公式の文のとおり小文字のまま（見出しに使う語だけ先頭を大文字に）
        keep = ja in ("戦術値", "情報値", "戦略値")
        vals = [(lambda t: t if keep else cap(t))(by_key[lg][k]["term"]) for lg, k in zip(("en", "de", "fr"), ks)]
        rows.append([f"term-{ja}", ja, *vals, "; ".join(f"{lg}: {url(lg, k)}" for lg, k in zip(("en", "de", "fr"), ks))])
    for ja, vals in FIXED.items():
        rows.append([f"term-{ja}", ja, *vals, "調査役の JSON（各言語の公式ページの引用つき）から。形を変えた理由は reports/20261027_1/tools/i18n_terms_import.py"])
    # 英雄のファンタジア（吟遊詩人の LB）は LB の行と同じ日本語なので重ねない
    seen, out = set(), []
    for r in rows:
        if r[1] in seen:
            continue
        seen.add(r[1])
        out.append(r)
    missing = [r[0] for r in out if not all(r[2:5])]
    if missing:
        print("訳が空:", missing)
        return 1
    if i18n.TERMS_MD.exists():
        i18n.TERMS_MD.unlink()
    i18n.State.collect = {"ui": set(), "text": set(), "terms": set()}
    i18n.append_missing(i18n.State.collect)  # 見出しだけの表を作る
    i18n.write_rows(i18n.TERMS_MD, i18n.TERM_COLS, out)
    print(f"terms.md: {len(out)} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
