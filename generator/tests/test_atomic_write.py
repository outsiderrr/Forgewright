"""Tests for generator._atomic_write (T-3.8a C 阶段 / F4.3).

Covers the shared crash-safe write helper used by version_recorder and
(future) dep_index_writer / chapter helper. Functional surface is small
so the test set is deliberately narrow:

  - write_text_atomic creates the file with exactly the requested text
  - write_text_atomic creates parent directories on demand
  - failed serialisation does not leave temp files behind
  - mid-write crash (simulated) leaves the prior file content intact
  - write_json_atomic emits the project's canonical shape
    (`ensure_ascii=False`, `indent=2`, trailing newline)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from generator._atomic_write import write_json_atomic, write_text_atomic


def test_write_text_atomic_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    write_text_atomic(target, "hello\n")
    assert target.read_text(encoding="utf-8") == "hello\n"


def test_write_text_atomic_makes_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "file.txt"
    write_text_atomic(target, "x")
    assert target.read_text(encoding="utf-8") == "x"


def test_write_text_atomic_overwrites_existing(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    write_text_atomic(target, "new")
    assert target.read_text(encoding="utf-8") == "new"


def test_write_text_atomic_no_temp_files_on_success(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    write_text_atomic(target, "data")
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith("out.txt.")]
    assert leftovers == []


def test_write_text_atomic_cleans_temp_on_replace_failure(
    tmp_path: Path,
) -> None:
    """If os.replace raises mid-write, the sibling tempfile is removed."""
    target = tmp_path / "out.txt"
    target.write_text("prior", encoding="utf-8")

    with patch("generator._atomic_write.os.replace", side_effect=OSError("boom")):
        with pytest.raises(OSError, match="boom"):
            write_text_atomic(target, "new content")

    # Prior content untouched (atomicity guarantee).
    assert target.read_text(encoding="utf-8") == "prior"
    # No leftover tempfile.
    leftovers = [
        p for p in tmp_path.iterdir() if p.name.startswith("out.txt.")
    ]
    assert leftovers == []


def test_write_json_atomic_canonical_shape(tmp_path: Path) -> None:
    """ensure_ascii=False + indent=2 + trailing newline."""
    target = tmp_path / "data.json"
    payload: dict[str, Any] = {"name": "铁誓驿站", "n": 1, "list": [1, 2, 3]}
    write_json_atomic(target, payload)

    text = target.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert "铁誓驿站" in text  # ensure_ascii=False preserves CJK

    # Round-trips back to the same dict.
    assert json.loads(text) == payload

    # indent=2 → multi-line output.
    assert text.count("\n") >= 4


def test_write_json_atomic_custom_indent(tmp_path: Path) -> None:
    target = tmp_path / "compact.json"
    write_json_atomic(target, {"a": 1}, indent=0)
    text = target.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text) == {"a": 1}
