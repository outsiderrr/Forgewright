"""CLI / batch-driver tests (T-3.4 / ADR-022 P-3 + P-4 + P-7 + P-8)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.llm_provider import StructuredResponse
from generator.playtest import cli as cli_mod
from generator.playtest.cli import (
    CALIBRATION_PATHS,
    GuardState,
    GuardTripped,
    next_playtest_dir,
)


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


# ---------------------------------------------------------------------------
# Test scene
# ---------------------------------------------------------------------------


def _two_branch_scene() -> dict:
    return {
        "schema_version": "0.1.1",
        "graph_id": "cli_test_scene",
        "entry_node_id": "n_start",
        "scene_anchor": "test_anchor",
        "nodes": {
            "n_start": {
                "node_id": "n_start",
                "type": "dialogue",
                "narration": "You arrive at the test crossroads.",
                "speaker_ref": None,
                "options": [
                    {
                        "option_id": "go_a",
                        "text": "Take the eastern road.",
                        "target_node_id": "n_end_a",
                        "condition": None,
                        "effects": [],
                        "unavailable_behavior": "hide",
                    },
                    {
                        "option_id": "go_b",
                        "text": "Take the western road.",
                        "target_node_id": "n_end_b",
                        "condition": None,
                        "effects": [],
                        "unavailable_behavior": "hide",
                    },
                ],
            },
            "n_end_a": {
                "node_id": "n_end_a",
                "type": "end",
                "narration": "Eastern outcome.",
                "options": [],
            },
            "n_end_b": {
                "node_id": "n_end_b",
                "type": "end",
                "narration": "Western outcome.",
                "options": [],
            },
        },
    }


def _write_scene(tmp_path: Path) -> Path:
    scene_path = tmp_path / "scene.json"
    scene_path.write_text(json.dumps(_two_branch_scene()), encoding="utf-8")
    return scene_path


# ---------------------------------------------------------------------------
# Provider: dispatches on schema shape
# ---------------------------------------------------------------------------


class _DispatchProvider:
    """Returns canned decisions or judge responses based on the schema's
    required fields. Simple but covers the runner + judge round-trip
    without per-call scripting."""

    model_id = "fake-cli"
    temperature = 0.5

    def __init__(self):
        self.decision_calls = 0
        self.judge_calls = 0

    def generate_structured(self, system_prompt, user_prompt, schema):
        required = schema.get("required") or []
        if "chosen_option_id" in required:
            self.decision_calls += 1
            # Pick the first valid option from the enum.
            enum = (
                schema["properties"]["chosen_option_id"].get("enum") or []
            )
            choice = enum[0] if enum else "go_a"
            content = {"chosen_option_id": choice, "reasoning": "test"}
        elif "path_score" in required:
            self.judge_calls += 1
            content = {
                "path_score": 70,
                "dimensions": {
                    "narrative_coherence": 18,
                    "persona_experience": 18,
                    "pacing": 17,
                    "ending_plausibility": 17,
                },
                "severity_findings": [
                    {"severity": "minor", "description": "fine"},
                ],
                "rationale": "ok",
            }
        else:  # pragma: no cover — unexpected schema would be a regression
            raise AssertionError(f"unexpected schema required: {required}")
        return StructuredResponse(
            content=content,
            raw_text=json.dumps(content, ensure_ascii=False),
            input_tokens=300 if "path_score" in required else 200,
            output_tokens=200 if "path_score" in required else 80,
            model_id=self.model_id,
            finish_reason="STOP",
        )

    def estimate_cost(self, input_tokens, output_tokens):
        return 0.001


# ---------------------------------------------------------------------------
# next_playtest_dir
# ---------------------------------------------------------------------------


def test_next_playtest_dir_starts_at_001(tmp_path):
    out = next_playtest_dir(tmp_path)
    assert out.name == "playtest_001"
    assert out.is_dir()


def test_next_playtest_dir_increments(tmp_path):
    a = next_playtest_dir(tmp_path)
    b = next_playtest_dir(tmp_path)
    c = next_playtest_dir(tmp_path)
    assert a.name == "playtest_001"
    assert b.name == "playtest_002"
    assert c.name == "playtest_003"


def test_next_playtest_dir_skips_non_matching_siblings(tmp_path):
    (tmp_path / "scratch").mkdir()
    (tmp_path / "playtest_007").mkdir()
    out = next_playtest_dir(tmp_path)
    assert out.name == "playtest_008"


# ---------------------------------------------------------------------------
# GuardState
# ---------------------------------------------------------------------------


def test_guard_trips_on_cost():
    import time

    g = GuardState(
        max_cost_usd=0.01,
        max_calls=1000,
        max_wall_clock_min=60,
        started_monotonic=time.monotonic(),
    )
    g.observe(0.005, 100, 50)
    g.check()  # under cap
    g.observe(0.006, 100, 50)
    with pytest.raises(GuardTripped) as exc:
        g.check()
    assert exc.value.which == "cost"


def test_guard_trips_on_calls():
    import time

    g = GuardState(
        max_cost_usd=10.0,
        max_calls=2,
        max_wall_clock_min=60,
        started_monotonic=time.monotonic(),
    )
    g.observe(0.001, 100, 50)
    g.check()
    g.observe(0.001, 100, 50)
    with pytest.raises(GuardTripped) as exc:
        g.check()
    assert exc.value.which == "calls"


def test_guard_trips_on_wall_clock():
    """started_monotonic in the past → elapsed_min already over cap."""
    import time

    g = GuardState(
        max_cost_usd=10.0,
        max_calls=1000,
        max_wall_clock_min=0.05,
        # 100s ago → elapsed > 0.05 min cap
        started_monotonic=time.monotonic() - 100.0,
    )
    with pytest.raises(GuardTripped) as exc:
        g.check()
    assert exc.value.which == "wall_clock"


# ---------------------------------------------------------------------------
# Calibration mode end-to-end
# ---------------------------------------------------------------------------


def test_cli_calibration_mode_writes_report_and_manifest(tmp_path):
    scene_path = _write_scene(tmp_path)
    cost_log = tmp_path / "playtest_cost_log.jsonl"
    experiments_root = tmp_path / "experiments"
    provider = _DispatchProvider()
    rc = cli_mod.main(
        [
            str(scene_path),
            "--calibration",
            "--personas",
            "cautious",
            "--cost-log",
            str(cost_log),
        ],
        provider=provider,
        experiments_root=experiments_root,
    )
    assert rc == 0
    out_dir = experiments_root / "playtest_001"
    assert (out_dir / "calibration_report.md").exists()
    assert (out_dir / "run_manifest.json").exists()

    manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["model_id"] == "fake-cli"
    assert manifest["judge_rubric_version"] == "v1"
    assert manifest["prompt_template_hash"].startswith("sha256:")
    assert manifest["calibration_data"]["n_paths"] == CALIBRATION_PATHS
    assert manifest["calibration_data"]["avg_calls_per_path"] >= 1
    assert "cautious" in manifest["persona_hashes"]

    # Cost log redirected to tmp path
    assert cost_log.exists()


# ---------------------------------------------------------------------------
# Full batch end-to-end
# ---------------------------------------------------------------------------


def test_cli_full_batch_writes_double_tier_output(tmp_path):
    scene_path = _write_scene(tmp_path)
    cost_log = tmp_path / "playtest_cost_log.jsonl"
    experiments_root = tmp_path / "experiments"
    provider = _DispatchProvider()
    rc = cli_mod.main(
        [
            str(scene_path),
            "--n-paths",
            "2",
            "--personas",
            "cautious,aggressive",
            "--skip-calibration",
            "--cost-log",
            str(cost_log),
        ],
        provider=provider,
        experiments_root=experiments_root,
    )
    assert rc == 0
    out_dir = experiments_root / "playtest_001"
    # Double-tier output (F21) plus manifest (F20)
    assert (out_dir / "worst_paths.jsonl").exists()
    assert (out_dir / "worst_scenes.md").exists()
    assert (out_dir / "worst_scenes.json").exists()
    assert (out_dir / "run_manifest.json").exists()

    # Calibration was skipped, so no calibration_report.md.
    assert not (out_dir / "calibration_report.md").exists()

    # 2 personas × 2 paths = 4 rows in worst_paths.jsonl
    rows = [
        json.loads(line)
        for line in (out_dir / "worst_paths.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 4
    assert {r["persona_id"] for r in rows} == {"cautious", "aggressive"}
    # Each path got judged → judge_score populated
    assert all(r["judge_score"] == 70 for r in rows)
    # Each path returned exactly one minor finding
    assert all(r["minor_count"] == 1 for r in rows)

    # worst_scenes.json has the expected scene
    scenes_payload = json.loads(
        (out_dir / "worst_scenes.json").read_text(encoding="utf-8")
    )
    scene_ids = {s["scene_id"] for s in scenes_payload["scenes"]}
    assert scene_ids == {"cli_test_scene"}
    assert scenes_payload["rubric_version"] == "v1"

    # Manifest captures abort=False and the actual call count
    manifest = json.loads(
        (out_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["aborted"] is False
    assert manifest["abort_reason"] is None
    assert manifest["n_paths_per_persona"] == 2
    assert manifest["scenes_played"] == ["cli_test_scene"]
    assert manifest["guard"]["total_calls"] >= 4  # 4 paths × ≥ 1 decision + judge


# ---------------------------------------------------------------------------
# Three-way guard
# ---------------------------------------------------------------------------


def test_cli_aborts_when_cost_guard_trips(tmp_path):
    scene_path = _write_scene(tmp_path)
    cost_log = tmp_path / "playtest_cost_log.jsonl"
    experiments_root = tmp_path / "experiments"
    provider = _DispatchProvider()
    # Each call costs 0.001; max-cost 0.0005 trips after first call.
    rc = cli_mod.main(
        [
            str(scene_path),
            "--n-paths",
            "5",
            "--personas",
            "cautious",
            "--skip-calibration",
            "--max-cost-usd",
            "0.0005",
            "--cost-log",
            str(cost_log),
        ],
        provider=provider,
        experiments_root=experiments_root,
    )
    assert rc == 3
    out_dir = experiments_root / "playtest_001"
    manifest = json.loads(
        (out_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["aborted"] is True
    assert "cost" in (manifest["abort_reason"] or "")


def test_cli_aborts_when_calls_guard_trips(tmp_path):
    scene_path = _write_scene(tmp_path)
    cost_log = tmp_path / "playtest_cost_log.jsonl"
    experiments_root = tmp_path / "experiments"
    provider = _DispatchProvider()
    rc = cli_mod.main(
        [
            str(scene_path),
            "--n-paths",
            "10",
            "--personas",
            "cautious",
            "--skip-calibration",
            "--max-calls",
            "1",
            "--cost-log",
            str(cost_log),
        ],
        provider=provider,
        experiments_root=experiments_root,
    )
    assert rc == 3
    manifest = json.loads(
        (experiments_root / "playtest_001" / "run_manifest.json").read_text(
            "utf-8"
        )
    )
    assert manifest["aborted"] is True
    assert "calls" in (manifest["abort_reason"] or "")


# ---------------------------------------------------------------------------
# CLI argument validation
# ---------------------------------------------------------------------------


def test_cli_calibration_and_skip_calibration_mutually_exclusive(tmp_path, capsys):
    scene_path = _write_scene(tmp_path)
    rc = cli_mod.main(
        [
            str(scene_path),
            "--calibration",
            "--skip-calibration",
            "--cost-log",
            str(tmp_path / "cost.jsonl"),
        ],
        provider=_DispatchProvider(),
        experiments_root=tmp_path / "experiments",
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "mutually exclusive" in err


def test_cli_missing_scene_returns_2(tmp_path, capsys):
    rc = cli_mod.main(
        [str(tmp_path / "no_such_scene.json")],
        provider=_DispatchProvider(),
        experiments_root=tmp_path / "experiments",
    )
    assert rc == 2


def test_cli_select_personas_subset(tmp_path):
    scene_path = _write_scene(tmp_path)
    provider = _DispatchProvider()
    rc = cli_mod.main(
        [
            str(scene_path),
            "--n-paths",
            "1",
            "--personas",
            "speedrunner",
            "--skip-calibration",
            "--cost-log",
            str(tmp_path / "cost.jsonl"),
        ],
        provider=provider,
        experiments_root=tmp_path / "experiments",
    )
    assert rc == 0
    rows = [
        json.loads(line)
        for line in (tmp_path / "experiments" / "playtest_001" / "worst_paths.jsonl")
        .read_text("utf-8")
        .splitlines()
        if line.strip()
    ]
    assert {r["persona_id"] for r in rows} == {"speedrunner"}
