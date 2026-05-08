"""Tests for generator.chapter_assembler (T-3.9; F6 fix).

Covers (per CA-1 ~ CA-5 + task §测试):
  * core assign path under explicit chapter / act ids
  * idempotent skip when scene_anchor already in target slot
  * fallback unassigned (both ids None) → auto-create unassigned bucket
  * mid-bucket fallback (chapter given, act None) → auto-create
    `act_unassigned` inside the named chapter
  * explicit chapter_id missing in ontology → success=False, no write
  * explicit act_id missing in chapter → success=False, no write
  * reassign moves scene_anchor between slots and cleans the prior one
  * data corruption healing (scene in target *and* elsewhere)
  * ValueError on (act_id without chapter_id) and on malformed ids
  * file lock injection: a custom lock_factory is honoured (CA-2 + F6
    "inject lock 形态")
  * default lock invokes fcntl.flock (ontology-level cross-process
    serialisation per CA-2)
  * concurrent thread pool with default lock doesn't lose appends
  * ADR-006: scene.json is not touched
  * chapter schema_version stays "0.3.0" on auto-created unassigned
    bucket (ADR-016 §schema 版本号策略)
  * T-3.5 integration interface signature is stable (F6 修订 — T-3.5
    will `from generator.chapter_assembler import assign_scene_to_chapter`)
  * CLI: success exit code, failure exit code, missing-ontology exit
"""

from __future__ import annotations

import fcntl
import inspect
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from generator import chapter_assembler
from generator.chapter_assembler import (
    UNASSIGNED_ACT_ID,
    UNASSIGNED_CHAPTER_ID,
    ChapterAssignment,
    assign_scene_to_chapter,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _ontology_payload(*, with_chapter: bool = True) -> dict:
    """Minimal ontology shape: top-level chapters[] (ADR-016) + a few
    siblings so we exercise the helper preserving non-chapter fields."""
    base: dict = {
        "system_time": {"scene_count": 0, "long_rest_count": 0},
        "clocks": [],
        "chapters": [],
        "entities": [
            {
                "id": "char_alpha",
                "type": "character",
                "display_name": "Alpha",
            }
        ],
    }
    if with_chapter:
        base["chapters"] = [
            {
                "schema_version": "0.3.0",
                "chapter_id": "chap_arrival",
                "display_name": "Arrival",
                "acts": [
                    {
                        "act_id": "act_intro",
                        "display_name": "Intro",
                        "included_scenes": [],
                    },
                    {
                        "act_id": "act_explore",
                        "display_name": "Explore",
                        "included_scenes": ["scene_existing"],
                    },
                ],
            }
        ]
    return base


@pytest.fixture
def ontology(tmp_path: Path) -> Path:
    """Write the default ontology fixture into tmp_path/waystation.json."""
    path = tmp_path / "waystation.json"
    path.write_text(
        json.dumps(_ontology_payload(), ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def empty_ontology(tmp_path: Path) -> Path:
    """Ontology with no chapters yet (the bare-stub case from waystation)."""
    path = tmp_path / "waystation.json"
    path.write_text(
        json.dumps(
            _ontology_payload(with_chapter=False), ensure_ascii=False, indent=4
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _included(ontology_path: Path, chapter_id: str, act_id: str) -> list[str]:
    data = _read(ontology_path)
    for c in data["chapters"]:
        if c["chapter_id"] == chapter_id:
            for a in c["acts"]:
                if a["act_id"] == act_id:
                    return list(a["included_scenes"])
    return []


# ---------------------------------------------------------------------------
# CA-1: core assign path
# ---------------------------------------------------------------------------


def test_assign_appends_scene_to_explicit_act(ontology: Path) -> None:
    result = assign_scene_to_chapter(
        "scene_alpha",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_intro",
    )
    assert result == ChapterAssignment(
        success=True,
        scene_anchor="scene_alpha",
        chapter_id="chap_arrival",
        act_id="act_intro",
        reason="assigned",
    )
    assert _included(ontology, "chap_arrival", "act_intro") == ["scene_alpha"]


def test_assign_preserves_unrelated_ontology_fields(ontology: Path) -> None:
    """Non-chapter fields (entities, clocks, system_time) round-trip
    untouched — the helper writes the whole ontology back so we want
    to confirm we're not silently dropping siblings."""
    before = _read(ontology)
    assign_scene_to_chapter(
        "scene_alpha",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_intro",
    )
    after = _read(ontology)
    assert before["entities"] == after["entities"]
    assert before["clocks"] == after["clocks"]
    assert before["system_time"] == after["system_time"]


def test_assign_appends_to_act_with_existing_scenes(ontology: Path) -> None:
    """Existing scene_anchors are preserved, new one appended."""
    result = assign_scene_to_chapter(
        "scene_new",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_explore",
    )
    assert result.success
    assert _included(ontology, "chap_arrival", "act_explore") == [
        "scene_existing",
        "scene_new",
    ]


# ---------------------------------------------------------------------------
# CA-1: idempotency
# ---------------------------------------------------------------------------


def test_idempotent_skip_when_already_in_target(ontology: Path) -> None:
    first = assign_scene_to_chapter(
        "scene_alpha",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_intro",
    )
    assert first.reason == "assigned"

    mtime_before = ontology.stat().st_mtime_ns
    second = assign_scene_to_chapter(
        "scene_alpha",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_intro",
    )
    assert second.reason == "idempotent_skip"
    assert second.success
    # idempotent skip = no write; mtime should not advance
    assert ontology.stat().st_mtime_ns == mtime_before
    # And we didn't accidentally double-append:
    assert _included(ontology, "chap_arrival", "act_intro") == ["scene_alpha"]


# ---------------------------------------------------------------------------
# CA-1: fallback unassigned (chapter_id None)
# ---------------------------------------------------------------------------


def test_fallback_unassigned_creates_bucket_when_absent(
    empty_ontology: Path,
) -> None:
    result = assign_scene_to_chapter("scene_alpha", empty_ontology)
    assert result == ChapterAssignment(
        success=True,
        scene_anchor="scene_alpha",
        chapter_id=UNASSIGNED_CHAPTER_ID,
        act_id=UNASSIGNED_ACT_ID,
        reason="fallback_unassigned",
    )

    data = _read(empty_ontology)
    assert len(data["chapters"]) == 1
    bucket = data["chapters"][0]
    assert bucket["chapter_id"] == UNASSIGNED_CHAPTER_ID
    # Auto-created unassigned bucket carries the same schema_version
    # const ("0.3.0") as the chapter.schema.json says (ADR-016 §schema
    # 版本号策略); helper does NOT bump it.
    assert bucket["schema_version"] == "0.3.0"
    assert bucket["display_name"] == "Unassigned"
    assert bucket["acts"][0]["act_id"] == UNASSIGNED_ACT_ID
    assert bucket["acts"][0]["included_scenes"] == ["scene_alpha"]


def test_fallback_unassigned_reuses_existing_bucket(
    empty_ontology: Path,
) -> None:
    """Two fallback assigns in a row must not duplicate the bucket."""
    assign_scene_to_chapter("scene_alpha", empty_ontology)
    assign_scene_to_chapter("scene_beta", empty_ontology)

    data = _read(empty_ontology)
    chapters = data["chapters"]
    assert len(chapters) == 1
    assert chapters[0]["chapter_id"] == UNASSIGNED_CHAPTER_ID
    assert chapters[0]["acts"][0]["included_scenes"] == [
        "scene_alpha",
        "scene_beta",
    ]


def test_chapter_given_act_none_creates_unassigned_act_in_named_chapter(
    ontology: Path,
) -> None:
    result = assign_scene_to_chapter(
        "scene_alpha", ontology, chapter_id="chap_arrival"
    )
    assert result.success
    assert result.chapter_id == "chap_arrival"
    assert result.act_id == UNASSIGNED_ACT_ID
    # Reason is 'assigned' — chapter was author-named, only the act is fallback.
    assert result.reason == "assigned"
    assert _included(ontology, "chap_arrival", UNASSIGNED_ACT_ID) == [
        "scene_alpha"
    ]


# ---------------------------------------------------------------------------
# CA-1: explicit ids that don't exist → failure (no write)
# ---------------------------------------------------------------------------


def test_explicit_chapter_not_found_returns_failure_without_write(
    ontology: Path,
) -> None:
    before = _read(ontology)
    result = assign_scene_to_chapter(
        "scene_alpha",
        ontology,
        chapter_id="chap_does_not_exist",
        act_id="act_intro",
    )
    assert result == ChapterAssignment(
        success=False,
        scene_anchor="scene_alpha",
        chapter_id="chap_does_not_exist",
        act_id="act_intro",
        reason="chapter_not_found",
    )
    assert _read(ontology) == before  # untouched


def test_explicit_act_not_found_returns_failure_without_write(
    ontology: Path,
) -> None:
    before = _read(ontology)
    result = assign_scene_to_chapter(
        "scene_alpha",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_missing",
    )
    assert result.success is False
    assert result.reason == "act_not_found"
    assert _read(ontology) == before


# ---------------------------------------------------------------------------
# CA-1: reassign + cleanup
# ---------------------------------------------------------------------------


def test_reassign_moves_scene_between_acts(ontology: Path) -> None:
    """scene_existing starts in act_explore — reassigning to act_intro
    must remove it from act_explore."""
    result = assign_scene_to_chapter(
        "scene_existing",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_intro",
    )
    assert result.success
    assert _included(ontology, "chap_arrival", "act_intro") == [
        "scene_existing"
    ]
    assert _included(ontology, "chap_arrival", "act_explore") == []


def test_reassign_heals_data_corruption_double_reference(
    ontology: Path,
) -> None:
    """If scene_anchor is in the target *and* elsewhere (corruption),
    the helper writes once and ends with a single reference at target."""
    data = _read(ontology)
    data["chapters"][0]["acts"][0]["included_scenes"].append("scene_corrupt")
    data["chapters"][0]["acts"][1]["included_scenes"].append("scene_corrupt")
    ontology.write_text(
        json.dumps(data, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )

    result = assign_scene_to_chapter(
        "scene_corrupt",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_intro",
    )
    assert result.success
    assert result.reason == "assigned"
    assert _included(ontology, "chap_arrival", "act_intro").count(
        "scene_corrupt"
    ) == 1
    assert "scene_corrupt" not in _included(
        ontology, "chap_arrival", "act_explore"
    )


# ---------------------------------------------------------------------------
# CA-1: input validation
# ---------------------------------------------------------------------------


def test_act_id_without_chapter_id_raises(ontology: Path) -> None:
    with pytest.raises(ValueError, match="act_id cannot be specified"):
        assign_scene_to_chapter(
            "scene_alpha", ontology, chapter_id=None, act_id="act_intro"
        )


def test_empty_scene_anchor_raises(ontology: Path) -> None:
    with pytest.raises(ValueError, match="scene_anchor"):
        assign_scene_to_chapter("", ontology)


@pytest.mark.parametrize(
    "bad_chapter_id",
    [
        "chap_BAD_UPPER",
        "Chap_arrival",
        "wrong_prefix_arrival",
        "chap_",
        "chap_" + "x" * 65,
    ],
)
def test_malformed_chapter_id_raises(
    ontology: Path, bad_chapter_id: str
) -> None:
    with pytest.raises(ValueError, match="chapter_id"):
        assign_scene_to_chapter(
            "scene_alpha",
            ontology,
            chapter_id=bad_chapter_id,
            act_id="act_intro",
        )


@pytest.mark.parametrize(
    "bad_act_id",
    ["act_BAD", "Act_intro", "wrong_prefix", "act_", "act_" + "x" * 65],
)
def test_malformed_act_id_raises(ontology: Path, bad_act_id: str) -> None:
    with pytest.raises(ValueError, match="act_id"):
        assign_scene_to_chapter(
            "scene_alpha",
            ontology,
            chapter_id="chap_arrival",
            act_id=bad_act_id,
        )


# ---------------------------------------------------------------------------
# CA-2: file lock injection (F6 修订 inject-lock 形态)
# ---------------------------------------------------------------------------


def test_custom_lock_factory_is_invoked(ontology: Path) -> None:
    """T-3.5 hands in its own lock factory; the helper must use it."""
    calls: list[Path] = []

    class _Sentinel:
        def __init__(self, path: Path) -> None:
            calls.append(path)

        def __enter__(self) -> None:
            return None

        def __exit__(self, *_args: object) -> None:
            return None

    assign_scene_to_chapter(
        "scene_alpha",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_intro",
        lock_factory=_Sentinel,  # type: ignore[arg-type]
    )
    assert calls == [ontology]


def test_default_lock_invokes_fcntl_flock(
    ontology: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default ontology lock must take an exclusive flock on the
    sibling sentinel — that's what makes overlapping CLI / scheduler
    invocations serialise (CA-2)."""
    flock_calls: list[tuple[int, int]] = []
    real_flock = fcntl.flock

    def spy(fd: int, op: int) -> None:
        flock_calls.append((fd, op))
        real_flock(fd, op)

    monkeypatch.setattr(fcntl, "flock", spy)

    assign_scene_to_chapter(
        "scene_alpha",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_intro",
    )

    ops = [op for _fd, op in flock_calls]
    assert fcntl.LOCK_EX in ops
    assert fcntl.LOCK_UN in ops
    assert (ontology.with_suffix(ontology.suffix + ".lock")).exists()


def test_default_lock_serialises_concurrent_appends(ontology: Path) -> None:
    """Sanity check on the per-process threading.Lock half of the
    default factory: N=8 worker threads each appending a distinct
    scene_anchor must end with all N anchors in the target slot — no
    lost updates from a torn read-modify-write."""
    n = 8

    def task(i: int) -> None:
        assign_scene_to_chapter(
            f"scene_{i}",
            ontology,
            chapter_id="chap_arrival",
            act_id="act_intro",
        )

    with ThreadPoolExecutor(max_workers=n) as ex:
        futures = [ex.submit(task, i) for i in range(n)]
        for fut in as_completed(futures):
            fut.result()

    included = _included(ontology, "chap_arrival", "act_intro")
    assert sorted(included) == sorted(f"scene_{i}" for i in range(n))


# ---------------------------------------------------------------------------
# CA-5: ADR-006 + ADR-016 invariants
# ---------------------------------------------------------------------------


def test_does_not_modify_scene_json_files(
    ontology: Path, tmp_path: Path
) -> None:
    """ADR-006: scene.json is the truth source for scene content; the
    helper must touch the ontology only. Sit a fake scene.json next to
    the ontology and confirm it is byte-identical after assignment."""
    fake_scene = tmp_path / "scene_alpha" / "scene.json"
    fake_scene.parent.mkdir()
    payload = json.dumps(
        {"graph_id": "scene_alpha", "nodes": {}}, ensure_ascii=False, indent=2
    )
    fake_scene.write_text(payload, encoding="utf-8")
    before_bytes = fake_scene.read_bytes()

    assign_scene_to_chapter(
        "scene_alpha",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_intro",
    )
    assert fake_scene.read_bytes() == before_bytes


def test_existing_chapter_schema_version_is_unchanged(ontology: Path) -> None:
    """ADR-016 §schema 版本号策略: helper must not bump
    chapter.schema_version even when it writes the chapter back."""
    before = _read(ontology)["chapters"][0]["schema_version"]
    assign_scene_to_chapter(
        "scene_alpha",
        ontology,
        chapter_id="chap_arrival",
        act_id="act_intro",
    )
    after = _read(ontology)["chapters"][0]["schema_version"]
    assert before == after == "0.3.0"


# ---------------------------------------------------------------------------
# CA-3: T-3.5 integration interface signature
# ---------------------------------------------------------------------------


def test_assign_scene_to_chapter_signature_matches_t35_contract() -> None:
    """T-3.5 batch_scheduler will write::

        from generator.chapter_assembler import assign_scene_to_chapter
        assign_scene_to_chapter(
            scene.scene_anchor, ontology_path,
            chapter_id=spec.chapter_id, act_id=spec.act_id,
        )

    so the public signature must accept exactly that call shape with
    those parameter names. If a future refactor renames a kwarg, T-3.5
    breaks at import — this test is an early tripwire (F6 修订)."""
    sig = inspect.signature(assign_scene_to_chapter)
    params = sig.parameters
    assert list(params)[:4] == [
        "scene_anchor",
        "ontology_path",
        "chapter_id",
        "act_id",
    ]
    assert params["chapter_id"].default is None
    assert params["act_id"].default is None
    # lock_factory is keyword-only with a None default so T-3.5 can swap
    # in its own ontology-wide lock without forcing every other caller
    # to pass it.
    assert params["lock_factory"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["lock_factory"].default is None


def test_chapter_assignment_dataclass_shape_matches_t35_contract() -> None:
    """The ChapterAssignment fields are part of the T-3.5 integration
    contract — T-3.5 will pattern on `success`, `chapter_id`, `act_id`,
    `reason` to wire dep_index trace fields. Lock the field names."""
    fields = {f.name for f in ChapterAssignment.__dataclass_fields__.values()}
    assert fields == {"success", "scene_anchor", "chapter_id", "act_id", "reason"}


# ---------------------------------------------------------------------------
# CA-4: CLI
# ---------------------------------------------------------------------------


def test_cli_assigns_via_chapter_and_act_flags(
    ontology: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(
        [
            "scene_alpha",
            "--chapter",
            "chap_arrival",
            "--act",
            "act_intro",
            "--ontology",
            str(ontology),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "reason=assigned" in out
    assert "success=True" in out
    assert _included(ontology, "chap_arrival", "act_intro") == ["scene_alpha"]


def test_cli_returns_1_on_chapter_not_found(
    ontology: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(
        [
            "scene_alpha",
            "--chapter",
            "chap_does_not_exist",
            "--act",
            "act_intro",
            "--ontology",
            str(ontology),
        ]
    )
    assert rc == 1
    out = capsys.readouterr().out
    assert "reason=chapter_not_found" in out
    assert "success=False" in out


def test_cli_returns_2_on_missing_ontology(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "no_such.json"
    rc = main(["scene_alpha", "--ontology", str(missing)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "ontology not found" in err


def test_cli_returns_2_on_value_error(
    ontology: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(
        [
            "scene_alpha",
            "--chapter",
            "BAD_PREFIX",
            "--ontology",
            str(ontology),
        ]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "chapter_id" in err


def test_cli_default_fallback_unassigned(
    empty_ontology: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No --chapter / --act → unassigned bucket auto-created."""
    rc = main(["scene_alpha", "--ontology", str(empty_ontology)])
    assert rc == 0
    assert "reason=fallback_unassigned" in capsys.readouterr().out
    assert _included(
        empty_ontology, UNASSIGNED_CHAPTER_ID, UNASSIGNED_ACT_ID
    ) == ["scene_alpha"]


# ---------------------------------------------------------------------------
# Internals: ensure helper rejects corrupted ontology shapes loudly
# ---------------------------------------------------------------------------


def test_corrupted_chapters_field_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps({"chapters": "not a list"}, ensure_ascii=False, indent=4)
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not a list"):
        assign_scene_to_chapter("scene_alpha", path)


# ---------------------------------------------------------------------------
# Sanity: module is importable as `python -m generator.chapter_assembler`
# (smoke test — argparse --help runs without raising)
# ---------------------------------------------------------------------------


def test_module_help_is_runnable() -> None:
    """argparse --help triggers SystemExit(0); confirms the parser
    builds cleanly. Tools like pre-commit shell out to `--help` for
    sanity, so we want this to keep working."""
    with pytest.raises(SystemExit) as exc:
        chapter_assembler.main(["--help"])
    assert exc.value.code == 0
