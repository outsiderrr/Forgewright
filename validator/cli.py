"""`python -m validator <path-to-scene.json>` 入口。

三层全跑、不短路；把每条 Issue 按 `[schema]/[graph]/[cons]` 前缀打印到 stdout；
末尾一行 `PASS` 或 `FAIL (N errors, M warnings)`。
返回码：0 = PASS（含有 / 无 warning 两种），1 = FAIL。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

from .report import Issue
from . import validate

_LEVEL_PREFIX = {
    "schema": "[schema] ",
    "graph":  "[graph]  ",
    "cons":   "[cons]   ",
}


def _print_issue(issue: Issue, out: TextIO) -> None:
    prefix = _LEVEL_PREFIX.get(issue.level, f"[{issue.level}] ")
    out.write(f"{prefix}{issue.location} : {issue.message}\n")


def main(argv: list[str], stdout: TextIO | None = None) -> int:
    out = stdout if stdout is not None else sys.stdout
    if len(argv) != 2:
        out.write("Usage: python -m validator <path-to-scene.json>\n")
        return 1
    path = Path(argv[1])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        out.write(f"[error] cannot load {argv[1]!r}: {e}\n")
        out.write("FAIL (1 errors, 0 warnings)\n")
        return 1

    if not isinstance(payload, dict):
        out.write("[error] scene root is not a JSON object\n")
        out.write("FAIL (1 errors, 0 warnings)\n")
        return 1

    report = validate(payload)

    for level in ("schema", "graph", "cons"):
        for issue in report.issues_by_level.get(level, []):
            _print_issue(issue, out)

    n_err = len(report.errors)
    n_warn = len(report.warnings)
    if report.passed:
        out.write("PASS\n")
        return 0
    out.write(f"FAIL ({n_err} errors, {n_warn} warnings)\n")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
