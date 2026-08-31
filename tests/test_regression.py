"""回帰テスト: 分析スクリプトの出力が変更されていないことを保証する。

【なぜ必要か】ruff / pyright の指摘対応は「出力を変えずに」行わなければならない。
スクリプトは数値を stdout に書き出すので、修正前の stdout を golden ファイルに
保存し、修正後も一字一句一致することを確認する。

golden ファイルの生成・更新:
    UPDATE_GOLDEN=1 python -m pytest tests/test_regression.py

検証のみ（通常の CI / 手元確認）:
    python -m pytest tests/test_regression.py
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILLS = {
    "analysis-integrity": ROOT / ".agents" / "skills" / "analysis-integrity",
    "forecast-with-audit": ROOT / ".agents" / "skills" / "forecast-with-audit",
}
GOLDEN = Path(__file__).resolve().parent / "golden"
UPDATE = os.environ.get("UPDATE_GOLDEN") == "1"

# メタチェッカは実行すると全スクリプトを再実行するため、個別 golden からは除外し、
# 専用テスト（test_consistency_summary）で要約行のみ検証する。
_META = "phase8_consistency.py"


def _scripts(skill: Path) -> list[str]:
    return sorted(
        p.name for p in (skill / "scripts").glob("*.py") if p.name != _META
    )


def _run(skill: Path, name: str) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    r = subprocess.run(
        [sys.executable, "scripts/" + name],
        cwd=skill,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        env=env,
        check=False,
    )
    return r.returncode, r.stdout


ALL = [(s, n) for s, skill in SKILLS.items() for n in _scripts(skill)]


@pytest.mark.parametrize(
    "skill_name,script",
    ALL,
    ids=[f"{s}/{n}" for s, n in ALL],
)
def test_script_output_is_stable(skill_name: str, script: str) -> None:
    skill = SKILLS[skill_name]
    golden_file = GOLDEN / f"{skill_name}__{script}.txt"
    rc, out = _run(skill, script)
    content = f"returncode={rc}\n{out}"

    if UPDATE:
        golden_file.write_text(content, encoding="utf-8")
        return

    assert golden_file.exists(), (
        f"golden ファイルが無い: {golden_file}. "
        "UPDATE_GOLDEN=1 で生成すること。"
    )
    assert golden_file.read_text(encoding="utf-8") == content


def test_consistency_summary() -> None:
    """phase8_consistency.py の要約行が、欠損データ前提の既知状態のままであること。

    期待: 致命 3（census_world の第三者データが同梱されていないため）/ 要修正 0。
    これは SKILL.md に明記された期待出力と一致する。
    """
    skill = SKILLS["analysis-integrity"]
    _, out = _run(skill, _META)
    summary = next(
        (ln for ln in out.splitlines() if ln.startswith("総括:")), None
    )
    assert summary is not None, "要約行（総括: ...）が見つからなかった"
    assert "致命 3 " in summary, f"致命件数が想定と異なる: {summary}"
    assert "要修正 0 " in summary, f"要修正件数が想定と異なる: {summary}"
