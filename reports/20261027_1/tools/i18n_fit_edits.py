"""2026-10-29: 英・独・仏のページを1画面に収めるための訳の短縮（記録。何度実行しても同じ結果）。

翻訳役の訳のうち、折り返して欄からあふれた行を短くする。意味は変えない（数を足さない・事実を足さない）。
同じページの見出しやタイルに名前が出ているときは、箇条書きでは主語を省く（例: 仏の SEI-OCC-ENEMY）。

使い方: python -I reports/20261027_1/tools/i18n_fit_edits.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "frontline" / "tools"))
import i18n  # noqa: E402
import ledger  # noqa: E402

# 台帳の文の訳: 行 ID → {言語: 訳}
TEXT = {
    "SEC-DRONE-DIST": {"de": "je Fraktion nach Schaden", "fr": "Selon dégâts des camps"},
    "SEC-NODE-DIST": {"de": "je LP 0 nach Schaden", "fr": "Par PV 0, selon dégâts"},
    "SEI-OCC-ENEMY": {"fr": "Ennemi : 2 prises (la 1re le libère)"},
    "SEI-OCC-LOCKOUT": {"fr": "Après changement : inaccessible un moment"},
    "SEI-OCC-CAPTURE-BONUS": {"fr": "Aucun bonus à la prise (gain en occupant)"},
    "SEI-OCC-PERSIST": {"fr": "Occupé : le gain continue même absent"},
    "SEI-RANK-TREND": {"fr": "Rangs élevés rares, puis plus fréquents"},
    "SEI-TOME-NEUTRAL-DRAIN": {"fr": "Libre : données restantes intactes"},
    "SEI-TOME-STACK": {"fr": "Plusieurs occupés : gains cumulés"},
    "NAA-WARN-NOTICE": {"fr": "Message au début de l'annonce"},
    "NAA-STATE-WARN": {"fr": "Indicateur complet : pacte possible"},
    "NAA-TIME-TREND": {"fr": "Avec le temps : max en baisse, rangs élevés"},
    "NAA-CLAIM-GUARDIAN": {"fr": "Gardien : sans effet si l'allié interagit"},
    "NAA-CLAIM-LOCK": {"fr": "Capturée : imprenable jusqu'à la fin"},
    "NAA-CLAIM-LOOK": {"fr": "Capturée : drapeau du camp sur le pilier"},
    "NAA-RANK-CENTER": {"fr": "Rangs élevés plus fréquents au centre"},
    "TRI-CLAIM-CONDITION": {"de": "Alle Zirkel einer Fraktion → besetzt", "fr": "Tous les cercles au même camp : Contrôlé"},
    "TRI-CIRCLE-CONTEST": {"de": "Feind drin: stoppt", "fr": "Ennemi dedans : bloqué"},
    "TRI-CIRCLE-DEFEND": {"de": "Verbündete drin: sicher", "fr": "allié dedans : protégé"},
    "TRI-CIRCLE-OVERWRITE": {"fr": "Cercles adverses reprenables avant contrôle"},
    "TRI-CIRCLE-RESET": {"fr": "Vidé avant acquisition : retour à zéro"},
    "TRI-SNOW-BLESS-TIMING": {"fr": "si dedans, cercle plein"},
    "TRI-SNOW-STATUE-CENTER": {"de": "Schneestatuen blockieren mittlere Gabelung",
                               "fr": "Carrefour central bloqué par un bonhomme"},
    "TRI-AURORA-LB-STACK": {"de": "stapelt mit Platz-Faktor & Fantasie des Helden",
                            "fr": "Cumul : classement, Fantaisie héroïque"},
    "SHA-MAP-STATES": {"fr": "Rien (détruit) → Ombre noire (désactivé) → Contour lumineux (annonce) → Glace (attaquable)"},
    "TRI-TIMEOUT": {"fr": "Temps écoulé : classement par score"},
    "COM-MATCH-TIMEOUT": {"fr": "Temps écoulé : classement par score"},
    # 2回目（外縁遺跡群・砕氷戦の表示を詰める）
    "SEC-EVT-PANEL-STOP": {"en": "end", "de": "Ende", "fr": "la fin"},
    "SEC-EVT-PANEL-ONEWAY": {"fr": "aller simple au centre"},
    "SEC-EVT-HUD-NEXT": {"fr": "prochaine apparition affichée (et type)"},
    "SEC-BH-DRONE-WHO": {"fr": "équipe aux plus gros dégâts"},
    "SEC-BH-CMDR-WHO": {"fr": "tous au point d'impact"},
    "SEC-SHEER-WILL": {"de": "„Fest entschlossen“ in Stellung: mehr Schaden",
                       "fr": "Poste : « Détermination », dégâts fortement accrus"},
    "SHA-ICE-BH": {"fr": "Bonus d'Ivresse du combat valable sur les mémolithes"},
    "COM-MATCH-DRAW": {"de": "2+ Fraktionen zugleich am Ziel: Unentschieden", "fr": "2 camps ou + au score cible ensemble : égalité"},
    "SHA-MAP-STATES": {"fr": "Rien (détruit) → Ombre noire (désactivé) → Contour / ombre lumineuse (annonce) → Glace (attaquable)"},
    # 3回目（共通の欄の見出しの説明・外縁遺跡群の見出しの説明）
    "COM-LB-RULE": {"de": "Aufladung je nach Platz", "fr": "Recharge selon le rang"},
    "COM-BH-DEATH": {"fr": "intacte"},
    # 6回目: 別の LLM の見直し（意味の欠けを戻す）
    "SEC-EVT-HUD-NEXT": {"de": "Schlachtinfo zeigt Zeit und Art des nächsten Erscheinens",
                         "fr": "la fenêtre de situation affiche délai et type de la suivante"},
    "TRI-SNOW-STATUE-CENTER": {"de": "Schneestatuen blockieren mittlere Gabelung",
                               "fr": "Un bonhomme de neige bloque le carrefour central"},
    "NAA-TIME-TREND": {"fr": "Avec le temps : max en baisse, rangs élevés plus fréquents"},
    "NAA-CLAIM-LOOK": {"fr": "Capturée : drapeau aux armoiries du camp sur le pilier"},
    "SEC-BH-DRONE-WHO": {"de": "ganze Top-Schaden-Gruppe", "fr": "toute l'équipe aux plus gros dégâts"},
    "SEC-BH-CMDR-WHO": {"de": "alle am Einschlag", "fr": "tous au point d'impact"},
}
# 言い回しの訳: 日本語のキー → {言語: 訳}
UI = {
    "倒した相手の段階で、得る戦意値が決まる": {"en": "Rating gain depends on KO'd foe's level", "de": "Gewinn je nach Stufe des Besiegten",
                                            "fr": "Gain selon le niveau de la victime"},
    "{0}で 計 {1}": {"fr": "{0}× = {1}"},
    "最大{0}で 計 {1}": {"fr": "max {0} = {1}"},
    "体": {"fr": "∅"},
    "合計の単位: 戦術値": {"en": "∅", "de": "Siegpunkte", "fr": "∅"},
    "雪精の祝福: 最大HPの {0} のバリア（{1}）": {"fr": "Bénédiction des neiges : barrière {0} PV max ({1})"},  # 仏は天候の絵を出さない（幅のため）
    "転移装置: 出現の {0}〜{1}（最初は 残り {2} から）・{3}・着いて無敵 {4}": {
        "en": "Personnel displacement panels: {0} before spawn → {1} (from {2}) · {3} · invulnerable {4}",
        "de": "Einheitentransporter: {0} vor Erscheinen → {1} (ab {2}) · {3} · unverwundbar {4}",
        "fr": "Téléporteurs : {0} l'apparition → {1} (dès {2}) · {3} · invuln. {4}",
    },
    "壊れてから再出現まで 大 {0} ・ 小 {1}": {"fr": "Réapparition : grand {0} · petit {1}", "de": "Regeneration: groß {0} · klein {1}"},
    "小: 壊れて {0}後に予告（{1}）": {"fr": "Petit : annonce {0} après ({1})"},
    "戦術値/HP0": {"fr": "score strat./PV 0", "en": "tactical pts/HP 0"},
    "戦意値: ドローン・αは{0}、コマンダーは{1}": {"de": "Kampfgeist: Drohne/α {0}, Kommandant {1}",
                                          "fr": "Jauge : drone/α {0} · commandant {1}",
                                          "en": "Rating: drone/α → {0}; command system → {1}"},
    # 4回目（タイルの中で切れる単位・合計の行）
    "戦術値/か所": {"en": "tactical points/spot", "fr": "score strat./zone"},
    "戦術値/体": {"fr": "score strat./drone"},
    "{0}で 計 {1}": {"en": "{0}× = {1}"},
    "最大{0}で 計 {1}": {"en": "Max {0} = {1}"},
    "体": {"en": "∅"},
    # 5回目（狭いタイルで折り返す順位、切れる見出しの説明）
    # 6回目: 別の LLM の見直し（ユーザーが反映を了承した分。plan.md §17）
    "{0}か所目で大きく伸びる（青）": {"en": "Big jumps at {0} locations held (blue)",
                                  "de": "Große Sprünge bei {0} Stellungen (blau)",
                                  "fr": "Fortes hausses à {0} postes occupés (bleu)"},
    "数の並び: {0}・{1}": {"en": "{0} and {1}", "de": "{0} und {1}", "fr": "{0} et {1}"},
    "中央の中立モンスター": {"de": "Neutrale Gegner (Mitte)"},  # 見出しの説明（戦意値の受け手）の幅のため
    "天候の帯は、薄い部分が始まりうる時間帯": {"fr": "Partie pâle : début possible"},  # 「…」で切れていた
    "{0}/{1}": {"en": "{0} per {1}", "de": "{0} je {1}", "fr": "{0} par {1}"},
    "（{0}/{1}）": {"en": "({0} every {1})", "de": "({0} alle {1})", "fr": "({0} par {1})"},  # 仏はタイルの幅で「par」
    "約{0}ごと・{1}": {"fr": "Toutes les {0} environ · {1}"},
    "同時に {0}まで ・ 全 {1}": {"en": "Max {0} at once · {1} spots", "fr": "Max {0} simult. · {1} emplacements"},
    "大: 壊れて {0}に次の予告": {"en": "Large: next warning {0} after destruction"},
    "壊れてから再出現まで 大 {0} ・ 小 {1}": {"en": "Respawn after destruction: large {0} · small {1}"},
    "小: 壊れて {0}後に予告（{1}）": {"en": "Small: warning {0} after destruction ({1})", "fr": "Petit : annonce {0} après destruction ({1})"},
    "2Dマップの予告は 起動の {0}": {"en": "Map warning: {0} before activation"},
    "占拠している部隊だけに入る（1基の合計。停止までは、占拠し続けた場合）": {
        "en": "Occupying team only (total per tomelith; time until inactive assumes held throughout)"},
    "{0}で勝利": {"de": "{0} zum Sieg", "fr": "{0} pour gagner"},
    "アイスドトームリスが起動する時刻（残り時間）": {"de": "Aktivierung der Vereisten Echolithen (Restzeit)"},
    "1位": {"de": "1."},
    "2位": {"de": "2."},
    "3位": {"de": "3."},
}


def set_cells(path: Path, cols: list[str], edits: dict[str, dict[str, str]], add_missing: bool) -> list[str]:
    found = ledger.find_table(path, cols)
    rows = [list(r) + [""] * (len(cols) - len(r)) for r in found[0]]
    keys = {r[0] for r in rows}
    for key, by_lang in edits.items():
        if key not in keys:
            if not add_missing:
                raise SystemExit(f"{path.name}: {key} がない")
            rows.append([key] + [""] * (len(cols) - 1))
            keys.add(key)
    for r in rows:
        for lg, v in edits.get(r[0], {}).items():
            r[cols.index(lg)] = v
    head = path.read_text(encoding="utf-8").partition("| " + " | ".join(cols) + " |")[0]
    path.write_text(head + "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n", encoding="utf-8", newline="\n")
    i18n.write_rows(path, cols, rows)
    return sorted(edits)


REMOVE_UI = ["か所目で大きく伸びる（青）"]  # 雛形を「{0}か所目で…」に変えた（数の並びごと差し込む）


def main() -> int:
    lines = i18n.UI_MD.read_text(encoding="utf-8").splitlines(keepends=True)
    i18n.UI_MD.write_text("".join(x for x in lines if not any(x.startswith(f"| {k} |") for k in REMOVE_UI)),
                          encoding="utf-8", newline="\n")
    set_cells(i18n.TEXT_MD, i18n.TEXT_COLS, TEXT, add_missing=False)
    set_cells(i18n.UI_MD, i18n.UI_COLS, UI, add_missing=True)
    i18n.reload()
    errors = i18n.check()
    print("検査:", "エラーなし" if not errors else "\n".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
