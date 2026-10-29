"""値台帳（Markdown の表）を読み書きし、検証する。

値台帳はページ生成の正典データである。ユーザーは「採否」列に ○／× を、「コメント」列に
訂正を書き込む。ページはこの表からだけ生成する（派生値は生成時に計算し、台帳には書かない）。

使い方:
    python frontline/tools/ledger.py validate      # 全台帳を検証（エラーがあれば終了コード 1）
    python frontline/tools/ledger.py export-json   # 検証済みの全台帳を JSON で標準出力へ
    python frontline/tools/ledger.py set-display <ID> <表示文>   # ページに出す短い言い方を書く（元の値は今の値）
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # frontline/
DATA = ROOT / "data"
LEDGER_DIR = DATA / "ledger"
SOURCES_MD = DATA / "sources.md"
CHECKS_MD = DATA / "ingame-checks.md"
JUDGE_MD = DATA / "judgments.md"

RULES = {
    "common": ("COM-", "ルール共通"),
    "secure": ("SEC-", "外縁遺跡群（制圧戦）"),
    "seize": ("SEI-", "シールロック（争奪戦）"),
    "shatter": ("SHA-", "フィールド・オブ・グローリー（砕氷戦）"),
    "naadam": ("NAA-", "オンサル・ハカイル（終節戦）"),
    "triumph": ("TRI-", "ウォーコー・チーテ（演習戦）"),
}

LEDGER_COLS = [
    "ID",
    "区分",
    "項目",
    "値",
    "単位",
    "条件・配り方",
    "等級",
    "出典",
    "最終変更",
    "現行確認",
    "採否",
    "コメント",
]
EVIDENCE_COLS = ["ID", "公式原文の抜粋", "備考"]
# ページに出す短い言い方。「元の値」が今の値と違えば検査で止める（値が変わったら表示文を見直す）
DISPLAY_COLS = ["ID", "表示", "元の値"]
SOURCE_COLS = [
    "ID",
    "種別",
    "名称",
    "URL",
    "公開・更新",
    "対象パッチ",
    "取得日",
    "系統",
    "保存",
    "アーカイブ",
]
CHECK_COLS = [
    "ID",
    "確認すること",
    "手順",
    "手間",
    "関係する行",
    "結果",
    "確認日",
    "パッチ",
]

# ユーザーの判定の記録。公式でない行は、○ にしたときの値と今の値が同じでなければ検査で止める
JUDGE_COLS = ["ID", "採否", "判定時の値", "判定日", "判定のもと"]

GRADES = {"公式", "外部", "実測", "未確認"}  # 「計算」は派生値用なので台帳には置かない
VERDICTS = {"", "○", "×"}
VERDICT_ALIASES = {
    "〇": "○",
    "◯": "○",
    "o": "○",
    "O": "○",
    "x": "×",
    "X": "×",
    "✕": "×",
    "✖": "×",
}
SOURCE_PREFIXES = ("OF-", "EX-", "IG-")
LIQUID = re.compile(r"\{\{|\{%|%\}|\}\}")
ID_RE = re.compile(r"^[A-Z0-9]+(-[A-Z0-9]+)+$")


@dataclass
class Row:
    """台帳の1行（1つの値）。"""

    id: str
    group: str
    label: str
    value: str
    unit: str
    condition: str
    grade: str
    sources: list[str]
    last_changed: str
    current_check: str
    verdict: str
    comment: str
    quote: str = ""
    notes: str = ""
    rule: str = ""
    display: str = ""  # 表示文（なければ値をそのまま出す）


@dataclass
class Ledger:
    rule: str
    path: Path
    rows: list[Row] = field(default_factory=list)


def split_row(line: str) -> list[str]:
    """Markdown の表の1行をセルに分ける。\\| はセル内の縦棒として扱う。"""
    body = line.strip().removeprefix("|")
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells = re.split(r"(?<!\\)\|", body)
    return [c.strip().replace("\\|", "|") for c in cells]


def escape_cell(text: str) -> str:
    """セルに書く文字列を整える（縦棒と改行を無害化し、Liquid の記法を文字参照にする）。"""
    s = str(text).replace("|", "\\|").replace("\r", " ").replace("\n", "<br>").strip()
    return s.replace("{", "&#123;").replace("}", "&#125;")


def read_tables(path: Path) -> list[tuple[list[str], list[list[str]], int]]:
    """ファイル中のすべての表を (見出し, 行, 開始行番号) で返す。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    tables = []
    i = 0
    while i < len(lines):
        if (
            lines[i].lstrip().startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1])
        ):
            header = split_row(lines[i])
            body, j = [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                body.append(split_row(lines[j]))
                j += 1
            tables.append((header, body, i + 1))
            i = j
        else:
            i += 1
    return tables


def find_table(path: Path, cols: list[str]) -> tuple[list[list[str]], int] | None:
    for header, body, start in read_tables(path):
        if header == cols:
            return body, start
    return None


def join_row(cells: list[str], changed: set[int] | None = None) -> str:
    """表の1行を書く。changed を渡すと、その列だけを整え直し、ほかの列は縦棒の扱いだけ戻す
    （読み込んだときの文字をそのまま残す。書き換えていない値が変わらないように）。"""
    out = []
    for i, c in enumerate(cells):
        out.append(escape_cell(c) if changed is None or i in changed else str(c).replace("|", "\\|"))
    return "| " + " | ".join(out) + " |"


def update_cells(
    path: Path, cols: list[str], updates: dict[str, dict[str, str]]
) -> list[str]:
    """表（見出しが cols）の行を、先頭セルの ID で引いて、指定した列だけ書き換える。

    書き換えなかった ID の一覧を返す。ファイルの他の部分（見出し・本文・別の表）は変えない。
    """
    found = find_table(path, cols)
    if found is None:
        raise ValueError(f"{path}: 表（{' | '.join(cols)}）がない")
    body, start = found
    lines = path.read_text(encoding="utf-8").splitlines()
    pending = dict(updates)
    for k, cells in enumerate(body):
        rid = cells[0] if cells else ""
        if rid not in pending:
            continue
        changed = set()
        for col, value in pending.pop(rid).items():
            cells[cols.index(col)] = value
            changed.add(cols.index(col))
        lines[start + 1 + k] = join_row(cells, changed)  # start は見出しの行番号（1始まり）
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return list(pending)


def append_rows(path: Path, cols: list[str], rows: list[list[str]]) -> None:
    """表（見出しが cols）の末尾に行を足す。"""
    insert_rows_after(path, cols, "", rows)


def insert_rows_after(
    path: Path, cols: list[str], after_id: str, rows: list[list[str]]
) -> bool:
    """表（見出しが cols）の、先頭セルが after_id の行の直後に行を足す。

    after_id が空か表にないときは末尾に足す。after_id の行が見つかったかを返す。
    """
    found = find_table(path, cols)
    if found is None:
        raise ValueError(f"{path}: 表（{' | '.join(cols)}）がない")
    body, start = found
    for r in rows:
        if len(r) != len(cols):
            raise ValueError(f"{path}: 足す行の列の数が {len(r)}（期待 {len(cols)}）: {r[:1]}")
    ids = [cells[0] if cells else "" for cells in body]
    hit = bool(after_id) and after_id in ids
    k = ids.index(after_id) + 1 if hit else len(body)
    lines = path.read_text(encoding="utf-8").splitlines()
    at = start + 1 + k  # start は見出しの行番号（1始まり）。区切り行の次が本文の0行目
    lines[at:at] = [join_row(r) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hit


BANNED_IN_VALUE = ["<br>", "&#123;", "&#125;", "{", "}"]  # 値・表示文に入れない（ページに文字のまま出る／Liquid を壊す）


def load_ledger(rule: str, errors: list[str], path: Path | None = None) -> Ledger:
    path = path or LEDGER_DIR / f"{rule}.md"
    led = Ledger(rule=rule, path=path)
    if not path.exists():
        errors.append(f"{path}: 台帳がない")
        return led
    text = path.read_text(encoding="utf-8")
    if LIQUID.search(text):
        errors.append(
            f"{path}: GitHub Pages のビルドを壊す記法（二重の波括弧など）がある"
        )
    main = find_table(path, LEDGER_COLS)
    if main is None:
        errors.append(f"{path}: 値の表（列: {' | '.join(LEDGER_COLS)}）が見つからない")
        return led
    body, start = main
    prefix = RULES[rule][0]
    for k, cells in enumerate(body):
        where = f"{path.name}:{start + 2 + k}"
        if len(cells) != len(LEDGER_COLS):
            errors.append(f"{where}: 列の数が {len(cells)}（期待 {len(LEDGER_COLS)}）")
            continue
        (
            rid,
            group,
            label,
            value,
            unit,
            cond,
            grade,
            srcs,
            last,
            cur,
            verdict,
            comment,
        ) = cells
        verdict = VERDICT_ALIASES.get(verdict, verdict)
        if not ID_RE.match(rid) or not rid.startswith(prefix):
            errors.append(f"{where}: ID {rid!r} の形式が不正（接頭辞 {prefix}）")
        if grade not in GRADES:
            errors.append(f"{where}: 等級 {grade!r} は {sorted(GRADES)} のどれでもない")
        if verdict not in VERDICTS:
            errors.append(f"{where}: 採否 {verdict!r} は ○ か × か空欄にする")
        if not value:
            errors.append(f"{where}: 値が空")
        bad = [b for b in BANNED_IN_VALUE if b in value]
        if bad:
            errors.append(f"{where}: 値に使えない文字 {bad} がある（改行や波括弧は値に入れない）")
        src_ids = [s.strip() for s in re.split(r"[;；,、\s]+", srcs) if s.strip()]
        if not src_ids:
            errors.append(f"{where}: 出典が空")
        for s in src_ids:
            if not s.startswith(SOURCE_PREFIXES):
                errors.append(f"{where}: 出典ID {s!r} の接頭辞が OF-/EX-/IG- でない")
        if not (cur.startswith("？") or re.match(r"^\d+\.\d+", cur)):
            errors.append(f"{where}: 現行確認 {cur!r} はパッチ番号か「？」で始める")
        led.rows.append(
            Row(
                rid,
                group,
                label,
                value,
                unit,
                cond,
                grade,
                src_ids,
                last,
                cur,
                verdict,
                comment,
                rule=rule,
            )
        )
    ev = find_table(path, EVIDENCE_COLS)
    if ev is not None:
        by_id = {r.id: r for r in led.rows}
        for cells in ev[0]:
            if len(cells) == len(EVIDENCE_COLS) and cells[0] in by_id:
                by_id[cells[0]].quote, by_id[cells[0]].notes = cells[1], cells[2]
    for r in led.rows:
        if r.grade == "公式" and not r.quote:
            errors.append(f"{path.name}: {r.id} は公式なのに原文の抜粋がない")
    disp = find_table(path, DISPLAY_COLS)
    if disp is not None:
        by_id = {r.id: r for r in led.rows}
        for cells in disp[0]:
            if len(cells) != len(DISPLAY_COLS):
                errors.append(f"{path.name}: 表示文の列の数が不正: {cells[:1]}")
                continue
            rid, text, orig = cells
            r = by_id.get(rid)
            if r is None:
                errors.append(f"{path.name}: 表示文の ID {rid} が値の表にない")
                continue
            if r.display:
                errors.append(f"{path.name}: 表示文の ID {rid} が重複")
            if orig != r.value:
                errors.append(
                    f"{path.name}: {rid} の値が変わった（表示文の元の値 {orig!r} → 今の値 {r.value!r}）。表示文を見直して元の値を更新する"
                )
            extra = sorted(set(numbers_in(text)) - set(numbers_in(orig)))
            if extra:
                errors.append(f"{path.name}: {rid} の表示文に、元の値にない数 {extra} がある")
            kanji = sorted(k for k in kanji_numbers(text) if k not in orig)
            if kanji:
                errors.append(f"{path.name}: {rid} の表示文に、元の値にない漢数字 {kanji} がある")
            bad = [b for b in BANNED_IN_VALUE if b in text]
            if bad:
                errors.append(f"{path.name}: {rid} の表示文に使えない文字 {bad} がある")
            if not text:
                errors.append(f"{path.name}: {rid} の表示文が空")
            r.display = text
    return led


KANJI_WORDS = ("一方通行", "一斉", "一定", "一部", "一度", "一緒", "一覧", "唯一", "一番", "一人")  # 数ではない語


def kanji_numbers(text: str) -> list[str]:
    """漢数字の並び（数ではない決まった語を除く）。表示文が数を足していないかの検査に使う。"""
    for w in KANJI_WORDS:
        text = text.replace(w, "")
    return re.findall(r"[〇一二三四五六七八九十百千万]+", text)


def numbers_in(text: str) -> list[str]:
    """文中の数（桁区切りと全角は正規化）を取り出す。表示文が数を足していないかの検査に使う。"""
    import unicodedata

    s = unicodedata.normalize("NFKC", text).replace(",", "")
    return re.findall(r"\d+(?:\.\d+)?", s)


def load_sources(errors: list[str]) -> dict[str, dict[str, str]]:
    if not SOURCES_MD.exists():
        errors.append(f"{SOURCES_MD}: 出典台帳がない")
        return {}
    found = find_table(SOURCES_MD, SOURCE_COLS)
    if found is None:
        errors.append(f"{SOURCES_MD}: 出典の表が見つからない")
        return {}
    out: dict[str, dict[str, str]] = {}
    for cells in found[0]:
        if len(cells) != len(SOURCE_COLS):
            errors.append(f"{SOURCES_MD.name}: 列の数が不正: {cells[:1]}")
            continue
        rec = dict(zip(SOURCE_COLS, cells))
        if rec["ID"] in out:
            errors.append(f"{SOURCES_MD.name}: 出典ID {rec['ID']} が重複")
        out[rec["ID"]] = rec
    return out


def load_judgments(errors: list[str]) -> dict[str, dict[str, str]]:
    if not JUDGE_MD.exists():
        errors.append(f"{JUDGE_MD}: 判定の記録がない")
        return {}
    found = find_table(JUDGE_MD, JUDGE_COLS)
    if found is None:
        errors.append(f"{JUDGE_MD.name}: 判定の記録の表が見つからない")
        return {}
    out: dict[str, dict[str, str]] = {}
    for cells in found[0]:
        if len(cells) != len(JUDGE_COLS):
            errors.append(f"{JUDGE_MD.name}: 列の数が不正: {cells[:1]}")
            continue
        rec = dict(zip(JUDGE_COLS, cells))
        if rec["ID"] in out:
            errors.append(f"{JUDGE_MD.name}: {rec['ID']} が重複（1つの行に1つの記録）")
        out[rec["ID"]] = rec
    return out


def record_judgment(rid: str, verdict: str, value: str, day: str, origin: str) -> str:
    """判定の記録を書く（同じ ID があれば書き換える）。"""
    rec = [rid, verdict, value, day, origin]
    found = find_table(JUDGE_MD, JUDGE_COLS)
    if found is not None and any(c and c[0] == rid for c in found[0]):
        update_cells(JUDGE_MD, JUDGE_COLS, {rid: dict(zip(JUDGE_COLS[1:], rec[1:]))})
        return "更新"
    append_rows(JUDGE_MD, JUDGE_COLS, [rec])
    return "追加"


def load_all() -> tuple[list[Ledger], dict[str, dict[str, str]], list[str]]:
    errors: list[str] = []
    ledgers = [load_ledger(rule, errors) for rule in RULES]
    sources = load_sources(errors)
    judged = load_judgments(errors)
    ids = {r.id for led in ledgers for r in led.rows}
    for rid in judged:
        if rid not in ids:
            errors.append(f"{JUDGE_MD.name}: {rid} が台帳にない")
    for led in ledgers:
        for r in led.rows:
            if r.verdict != "○" or r.grade == "公式":
                continue  # 公式の行は原文照合（check_official.py）で確かめる
            j = judged.get(r.id)
            if j is None or j["採否"] != "○":
                errors.append(f"{led.rule}: {r.id} は ○ だが、ユーザーが ○ にした記録がない（{JUDGE_MD.name}）")
            elif j["判定時の値"] != r.value:
                errors.append(
                    f"{led.rule}: {r.id} の値が判定のあとで変わった（判定時 {j['判定時の値']!r} → 今 {r.value!r}）。"
                    "採否を空欄に戻して、ユーザーに判定し直してもらう"
                )
    seen: dict[str, str] = {}
    for led in ledgers:
        for r in led.rows:
            if r.id in seen:
                errors.append(f"ID {r.id} が {seen[r.id]} と {led.rule} で重複")
            seen[r.id] = led.rule
            for s in r.sources:
                if sources and s not in sources:
                    errors.append(f"{led.rule}: {r.id} の出典 {s} が出典台帳にない")
    return ledgers, sources, errors


DISPLAY_INTRO = (
    "ページに出す短い言い方。「値」を言い換えただけで、事実を足さない（数は値にあるものだけ）。"
    "値が変わると検査で止まるので、そのときは表示文を見直して `python frontline/tools/ledger.py set-display <ID> <表示文>` で書き直す。"
)


def set_display(rid: str, text: str) -> str:
    """表示文を書く（なければ表を作る）。元の値には今の値を入れる。text が空なら行を消す。

    書く前に、書き換えた写しを検査する。表示文の検査に落ちたら書かずに ValueError を出す。
    """
    import tempfile

    rule = next((r for r, (p, _) in RULES.items() if rid.startswith(p)), None)
    if rule is None:
        raise ValueError(f"{rid}: 接頭辞からルールが分からない")
    path = LEDGER_DIR / f"{rule}.md"
    led = load_ledger(rule, [])
    row = next((r for r in led.rows if r.id == rid), None)
    if row is None:
        raise ValueError(f"{rid}: 値の表にない")
    original = path.read_text(encoding="utf-8")
    has_table = find_table(path, DISPLAY_COLS) is not None
    if not text and not has_table:
        return "なし"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / path.name
        work.write_text(original, encoding="utf-8")
        if not has_table:
            lines = original.splitlines()
            ev = find_table(work, EVIDENCE_COLS)
            at = (ev[1] + 1 + len(ev[0])) if ev else len(lines)  # 根拠の表の直後（0始まり）
            block = ["", "## 表示文", "", DISPLAY_INTRO, "", "| " + " | ".join(DISPLAY_COLS) + " |", "|---|---|---|"]
            lines[at:at] = block
            work.write_text("\n".join(lines) + "\n", encoding="utf-8")
        body, start = find_table(work, DISPLAY_COLS)
        ids = [c[0] for c in body]
        if not text:
            if rid not in ids:
                return "なし"
            lines = work.read_text(encoding="utf-8").splitlines()
            del lines[start + 1 + ids.index(rid)]
            work.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = "削除"
        elif rid in ids:
            update_cells(work, DISPLAY_COLS, {rid: {"表示": text, "元の値": row.value}})
            result = "更新"
        else:
            append_rows(work, DISPLAY_COLS, [[rid, text, row.value]])
            result = "追加"
        errors: list[str] = []
        load_ledger(rule, errors, path=work)
        bad = [e for e in errors if rid in e]
        if bad:
            raise ValueError("書かなかった: " + "; ".join(bad))
        path.write_text(work.read_text(encoding="utf-8"), encoding="utf-8")
    return result


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "validate"
    if cmd == "set-display":
        if len(argv) not in (3, 4):
            print("使い方: ledger.py set-display <ID> [<表示文>]（表示文を省くと削除）")
            return 2
        try:
            print(set_display(argv[2], argv[3] if len(argv) == 4 else ""))
        except ValueError as exc:
            print(f"エラー: {exc}")
            return 1
        return 0
    ledgers, sources, errors = load_all()
    if cmd == "validate":
        n = sum(len(led.rows) for led in ledgers)
        pending = sum(1 for led in ledgers for r in led.rows if r.verdict == "")
        print(
            f"台帳 {len(ledgers)} 本・{n} 行・出典 {len(sources)} 件・未判定 {pending} 行"
        )
        for e in errors:
            print(f"エラー: {e}")
        return 1 if errors else 0
    if cmd == "export-json":
        if errors:
            for e in errors:
                print(f"エラー: {e}", file=sys.stderr)
            return 1
        payload = {
            "ledgers": {led.rule: [asdict(r) for r in led.rows] for led in ledgers},
            "sources": sources,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
