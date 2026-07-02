"""Tests for generator.version_recorder (T-3.8a).

Covers (per VR-5 + PR #37 review):
  - First call writes v1 with `previous_versions=[]`
  - Subsequent call bumps version + archives prior into previous_versions
  - git unavailable fallback (FileNotFoundError + CalledProcessError) →
    git_commit / git_branch fields recorded as None, write still succeeds
  - git invocation is anchored to scene's repo via `-C` (review §4.1)
  - whitelist rejects non-read-only git args (review §4.1)
  - concurrent bumps from a thread pool don't lose versions (review §4.2)
  - CLI integration (default method, --method override, --changed-fields
    parsing, missing scene exit code)

Plus sanity coverage on validation + sidecar path shape.
"""

from __future__ import annotations

import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from generator import version_recorder
from generator.version_recorder import (
    SIDECAR_SUFFIX,
    main,
    record_version,
    sidecar_path_for,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SCENE_PAYLOAD = {
    "schema_version": "0.1.1",
    "graph_id": "test_scene_alpha",
    "entry_node_id": "n1",
    "scene_anchor": "scene_test_alpha",
    "character_refs": ["char_test"],
    "nodes": {
        "n1": {
            "node_id": "n1",
            "type": "end",
            "narration": "...",
            "speaker_ref": None,
            "location_ref": "scene_test_alpha",
            "on_enter_effects": [],
            "options": [],
        }
    },
}


@pytest.fixture
def scene_file(tmp_path: Path) -> Path:
    """Write a minimal valid scene.json into tmp_path/<scene_dir>/scene.json."""
    scene_dir = tmp_path / "scene_test_alpha"
    scene_dir.mkdir()
    scene_path = scene_dir / "scene.json"
    scene_path.write_text(
        json.dumps(_SCENE_PAYLOAD, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return scene_path


@pytest.fixture
def stub_git(monkeypatch: pytest.MonkeyPatch) -> dict[str, str | None]:
    """Force git introspection to return deterministic values.

    Returns a mutable dict so tests can rebind `commit` / `branch`
    between record_version calls to simulate evolving git state. The
    fakes accept the new `scene_path` argument added in PR #37 review
    §4.1 but ignore it — tests assert anchoring separately.
    """
    state: dict[str, str | None] = {
        "commit": "deadbeef" * 5,  # 40 chars
        "branch": "test/branch-1",
    }

    def fake_commit(scene_path: Path) -> str | None:
        return state["commit"]

    def fake_branch(scene_path: Path) -> str | None:
        return state["branch"]

    monkeypatch.setattr(version_recorder, "_git_head_commit", fake_commit)
    monkeypatch.setattr(version_recorder, "_git_head_branch", fake_branch)
    return state


# ---------------------------------------------------------------------------
# VR-2: first call → v1 with empty previous_versions
# ---------------------------------------------------------------------------


def test_first_call_writes_v1_sidecar(
    scene_file: Path, stub_git: dict[str, str | None]
) -> None:
    meta = record_version(scene_file, "batch_scheduler")

    assert meta.scene_id == _SCENE_PAYLOAD["graph_id"]
    assert meta.version == 1
    assert meta.previous_versions == []
    assert meta.git_commit_at_generation == stub_git["commit"]
    assert meta.git_branch_at_generation == stub_git["branch"]
    assert meta.generation_method == "batch_scheduler"
    # ISO 8601 timestamp shape (UTC, includes offset).
    assert re.match(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", meta.first_generated_at
    )
    assert meta.first_generated_at == meta.last_modified_at

    sidecar = sidecar_path_for(scene_file)
    assert sidecar.exists()
    raw = json.loads(sidecar.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert raw["scene_id"] == _SCENE_PAYLOAD["graph_id"]
    assert raw["previous_versions"] == []
    # Trailing newline + indent match generator.manifest convention.
    text = sidecar.read_text(encoding="utf-8")
    assert text.endswith("\n")


def test_sidecar_path_is_sibling_of_scene_json(scene_file: Path) -> None:
    sidecar = sidecar_path_for(scene_file)
    assert sidecar.parent == scene_file.parent
    assert sidecar.name == "scene.version.json"
    assert sidecar.suffix == ".json"
    assert sidecar.name.endswith(SIDECAR_SUFFIX)


def test_changed_fields_ignored_on_first_call(
    scene_file: Path, stub_git: dict[str, str | None]
) -> None:
    """On first creation there is no PreviousVersion entry to attach to."""
    meta = record_version(scene_file, "manual_edit", ["nodes.n1.text"])
    assert meta.previous_versions == []


# ---------------------------------------------------------------------------
# VR-2: bump preserves history
# ---------------------------------------------------------------------------


def test_bump_archives_previous_version(
    scene_file: Path, stub_git: dict[str, str | None]
) -> None:
    record_version(scene_file, "batch_scheduler")
    initial_commit = stub_git["commit"]

    stub_git["commit"] = "feedface" * 5
    stub_git["branch"] = "test/branch-2"
    meta = record_version(scene_file, "manual_edit", ["nodes.n1.text"])

    assert meta.version == 2
    assert meta.git_commit_at_generation == "feedface" * 5
    assert meta.git_branch_at_generation == "test/branch-2"
    assert meta.generation_method == "manual_edit"
    assert len(meta.previous_versions) == 1

    archived = meta.previous_versions[0]
    assert archived.version == 1
    assert archived.commit == initial_commit
    # changed_fields on the archived entry = changed_fields passed to the
    # bump that produced version 2 (i.e., what changed *out of* version 1).
    assert archived.changed_fields == ["nodes.n1.text"]


def test_first_generated_at_preserved_through_bumps(
    scene_file: Path, stub_git: dict[str, str | None]
) -> None:
    first = record_version(scene_file, "batch_scheduler")
    second = record_version(scene_file, "regenerate")
    third = record_version(scene_file, "manual_edit", ["nodes.n1"])

    assert second.first_generated_at == first.first_generated_at
    assert third.first_generated_at == first.first_generated_at
    assert third.version == 3
    assert [pv.version for pv in third.previous_versions] == [1, 2]
    # The most-recent archive entry carries the latest bump's
    # changed_fields; older archive entries keep their own.
    assert third.previous_versions[0].changed_fields == []
    assert third.previous_versions[1].changed_fields == ["nodes.n1"]


def test_bump_does_not_require_scene_file_to_still_exist(
    scene_file: Path, stub_git: dict[str, str | None]
) -> None:
    """Once the sidecar carries `scene_id`, bumps work even if the
    scene file is missing — useful for forensic-only re-records."""
    record_version(scene_file, "batch_scheduler")
    scene_file.unlink()
    meta = record_version(scene_file, "manual_edit", ["x"])
    assert meta.version == 2
    assert meta.scene_id == _SCENE_PAYLOAD["graph_id"]


# ---------------------------------------------------------------------------
# VR-2 #5: git unavailable fallback
# ---------------------------------------------------------------------------


def test_git_binary_missing_records_none(
    scene_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError("git: command not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    meta = record_version(scene_file, "batch_scheduler")
    assert meta.git_commit_at_generation is None
    assert meta.git_branch_at_generation is None
    # Sidecar still landed on disk despite git being unavailable.
    assert sidecar_path_for(scene_file).exists()


def test_git_non_repo_records_none(
    scene_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(*args: object, **kwargs: object) -> object:
        raise subprocess.CalledProcessError(
            returncode=128,
            cmd=("git", "rev-parse", "HEAD"),
            stderr="fatal: not a git repository",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    meta = record_version(scene_file, "batch_scheduler")
    assert meta.git_commit_at_generation is None
    assert meta.git_branch_at_generation is None


# ---------------------------------------------------------------------------
# Review §4.1: git invocation must be anchored to scene's repo via `-C`
# ---------------------------------------------------------------------------


def test_git_invocation_anchored_via_dash_C(
    scene_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`record_version` must call `git -C <scene_dir> rev-parse ...`.

    Without `-C`, a CLI run from a non-repo cwd records the calling
    process's git HEAD (or `None`) instead of the scene's repo HEAD —
    the audit trail would silently point at the wrong repo.
    """
    captured: list[list[str]] = []

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(list(args))
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="abc1234567" * 4 + "\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    record_version(scene_file, "batch_scheduler")

    assert captured, "expected at least one git invocation"
    expected_repo = str(scene_file.parent)
    for cmd in captured:
        assert cmd[0] == "git"
        assert cmd[1] == "-C"
        assert cmd[2] == expected_repo
        # Only `rev-parse` invocations are allowed by the whitelist.
        assert cmd[3] == "rev-parse"


def test_run_git_readonly_rejects_non_whitelisted_args() -> None:
    """The whitelist makes mutation commands structurally impossible."""
    with pytest.raises(ValueError, match="whitelisted"):
        version_recorder._run_git_readonly(Path("."), ("commit", "-m", "x"))
    with pytest.raises(ValueError, match="whitelisted"):
        version_recorder._run_git_readonly(Path("."), ("push",))


def test_git_anchored_to_scene_repo_e2e(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: scene in an isolated git repo + CLI run from outside.

    Sets up a fresh git repo at `tmp_path/iso_repo/`, commits a scene,
    then calls `record_version` while pytest's cwd is the project's
    main worktree (a *different* repo). The recorded HEAD must be the
    isolated repo's, not the worktree's — that's the whole point of
    `-C` anchoring (review §4.1).
    """
    iso_repo = tmp_path / "iso_repo"
    iso_repo.mkdir()

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=iso_repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-q", "-b", "main")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Test")
    git("config", "commit.gpgsign", "false")

    scene = iso_repo / "scene.json"
    scene.write_text(
        json.dumps({"graph_id": "iso_scene"}, ensure_ascii=False),
        encoding="utf-8",
    )
    git("add", "scene.json")
    git("commit", "-q", "-m", "init scene")
    iso_head = git("rev-parse", "HEAD")

    # Invoke record_version (which runs subprocess git from whatever cwd
    # pytest happens to be in — typically the project root, which is
    # itself a git repo with a different HEAD).
    meta = record_version(scene, "batch_scheduler")

    assert meta.git_commit_at_generation == iso_head
    assert meta.git_branch_at_generation == "main"


# ---------------------------------------------------------------------------
# Review §4.2: concurrent bumps must not lose versions
# ---------------------------------------------------------------------------


def test_concurrent_bumps_no_lost_versions(
    scene_file: Path, stub_git: dict[str, str | None]
) -> None:
    """5 concurrent record_version calls on the same scene → final v5,
    previous_versions == [1, 2, 3, 4]. Without the load-bump-write lock,
    races would produce a final version < 5 and gaps in the chain."""

    def call(_: int) -> int:
        return record_version(scene_file, "batch_scheduler").version

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(call, i) for i in range(5)]
        observed = sorted(f.result() for f in as_completed(futures))

    assert observed == [1, 2, 3, 4, 5]

    raw = json.loads(
        sidecar_path_for(scene_file).read_text(encoding="utf-8")
    )
    assert raw["version"] == 5
    assert [pv["version"] for pv in raw["previous_versions"]] == [1, 2, 3, 4]


def test_sidecar_lock_file_is_sibling(scene_file: Path) -> None:
    sidecar = sidecar_path_for(scene_file)
    lock = version_recorder._sidecar_lock_path(sidecar)
    assert lock.parent == sidecar.parent
    assert lock.name == "scene.version.json.lock"


# ---------------------------------------------------------------------------
# Validation: invalid method, missing scene, missing graph_id
# ---------------------------------------------------------------------------


def test_invalid_method_raises(scene_file: Path) -> None:
    with pytest.raises(ValueError, match="generation_method"):
        record_version(scene_file, "not_a_method")


def test_missing_scene_raises_on_first_call(tmp_path: Path) -> None:
    missing = tmp_path / "no_such_scene" / "scene.json"
    with pytest.raises(FileNotFoundError):
        record_version(missing, "batch_scheduler")


def test_scene_without_graph_id_raises(
    tmp_path: Path, stub_git: dict[str, str | None]
) -> None:
    bad = tmp_path / "bad_scene"
    bad.mkdir()
    scene = bad / "scene.json"
    scene.write_text(
        json.dumps({"schema_version": "0.1.1"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="graph_id"):
        record_version(scene, "batch_scheduler")


# ---------------------------------------------------------------------------
# VR-3: CLI integration (#7-9)
# ---------------------------------------------------------------------------


def test_cli_default_method_is_manual_edit(
    scene_file: Path,
    stub_git: dict[str, str | None],
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main([str(scene_file)])
    assert rc == 0
    raw = json.loads(
        sidecar_path_for(scene_file).read_text(encoding="utf-8")
    )
    assert raw["generation_method"] == "manual_edit"
    out = capsys.readouterr().out
    assert "version=1" in out


def test_cli_method_override(
    scene_file: Path, stub_git: dict[str, str | None]
) -> None:
    rc = main([str(scene_file), "--method", "regenerate"])
    assert rc == 0
    raw = json.loads(
        sidecar_path_for(scene_file).read_text(encoding="utf-8")
    )
    assert raw["generation_method"] == "regenerate"


def test_cli_changed_fields_parsed_and_attached_to_archive(
    scene_file: Path, stub_git: dict[str, str | None]
) -> None:
    main([str(scene_file)])  # v1 (manual_edit default)
    rc = main(
        [
            str(scene_file),
            "--changed-fields",
            "nodes.n1.text, character_refs",  # spaces tolerated
        ]
    )
    assert rc == 0
    raw = json.loads(
        sidecar_path_for(scene_file).read_text(encoding="utf-8")
    )
    assert raw["version"] == 2
    assert raw["previous_versions"][0]["changed_fields"] == [
        "nodes.n1.text",
        "character_refs",
    ]


def test_cli_missing_scene_returns_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "nope.json"
    rc = main([str(missing)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "does not exist" in err


def test_cli_invalid_method_argparse_rejects(scene_file: Path) -> None:
    with pytest.raises(SystemExit):
        main([str(scene_file), "--method", "garbage"])


def test_cli_empty_changed_fields_yields_empty_archive(
    scene_file: Path, stub_git: dict[str, str | None]
) -> None:
    """`--changed-fields ''` (or whitespace-only) is parsed as no fields."""
    main([str(scene_file)])  # v1
    rc = main([str(scene_file), "--changed-fields", "  ,  "])
    assert rc == 0
    raw = json.loads(
        sidecar_path_for(scene_file).read_text(encoding="utf-8")
    )
    assert raw["previous_versions"][0]["changed_fields"] == []


# ---------------------------------------------------------------------------
# T-3P-0（ADR-039）: generation_method 枚举扩值 writer_ingest —— 既有值回归 + 新值可用
# ---------------------------------------------------------------------------


def test_generation_method_existing_values_preserved_and_writer_ingest_added() -> None:
    """既有四值一个不动（回归）+ 新增 writer_ingest（回流落地统一用值，T-3P-3 只消费）。"""
    from typing import get_args

    from generator.version_recorder import GenerationMethod

    values = get_args(GenerationMethod)
    assert values[:4] == ("batch_scheduler", "manual_edit", "regenerate", "playtest_fix")
    assert set(values) == {
        "batch_scheduler",
        "manual_edit",
        "regenerate",
        "playtest_fix",
        "writer_ingest",
    }


def test_record_version_accepts_writer_ingest(
    scene_file: Path, stub_git: dict[str, str | None]
) -> None:
    meta = record_version(scene_file, "writer_ingest")
    assert meta.generation_method == "writer_ingest"
