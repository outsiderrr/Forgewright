"""Shared fixtures: a minimal in-tmp_path batch + scenes directory.

Hand-built fixture data — no LLM calls — that mirrors the shape
``scene_experiment`` writes (one success row + one failure row) plus
the AI judge advisory + graph_views triple + a minimal content/ scene.
The fixture is what the API tests + the data layer tests both build on.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def fixture_batch_dir(tmp_path: Path) -> Path:
    """A two-row batch: one success ('s_alpha'), one failure (no graph)."""
    batch = tmp_path / "batch"
    success_envelope = {
        "iter_id": 0,
        "fixture_id": "fix_alpha",
        "fixture": {
            "scene_setting": {
                "scene_anchor": "scene_alpha",
                "primary_location_ref": "scene_alpha",
                "chapter_ref": None,
                "expected_node_count_min": 3,
                "expected_node_count_max": 5,
            },
            "target_beats": ["beat_a", "beat_b"],
            "participating_npcs": ["char_x"],
        },
        "result": {
            "success": True,
            "failure_reason": None,
            "failure_node_id": None,
            "failure_metadata": None,
            "total_cost_usd": 0.1234,
            "inner_attempt_count": 1,
            "graph": {
                "schema_version": "0.1.1",
                "graph_id": "s_alpha",
                "entry_node_id": "n_start",
                "scene_anchor": "scene_alpha",
                "character_refs": ["char_x"],
                "nodes": {
                    "n_start": {
                        "node_id": "n_start",
                        "type": "dialogue",
                        "narration": "alpha narration",
                        "speaker_ref": "char_x",
                        "options": [
                            {
                                "option_id": "opt_go",
                                "text": "go",
                                "target_node_id": "n_end",
                                "condition": None,
                                "effects": [],
                                "unavailable_behavior": "hide",
                            }
                        ],
                    },
                    "n_end": {
                        "node_id": "n_end",
                        "type": "end",
                        "narration": "the end",
                        "speaker_ref": None,
                        "options": [],
                    },
                },
            },
        },
        "validator_summaries": {
            "mechanical": {"pass": True, "error_node_count": 0, "error_count": 0, "error_codes": []},
            "topology": {
                "pass": True,
                "pure_topology_pass": True,
                "condition_form_pass": True,
                "error_count": 0,
                "warning_count": 0,
                "error_codes": [],
            },
            "sampling": {
                "sample_count": 100,
                "reached_end_count": 100,
                "deadlock_count": 0,
                "avg_path_length": 2.0,
            },
        },
    }
    failure_envelope = {
        "iter_id": 1,
        "fixture_id": "fix_beta",
        "fixture": {"scene_setting": {"scene_anchor": "scene_beta"}, "target_beats": [], "participating_npcs": []},
        "result": {
            "success": False,
            "failure_reason": "schema_validation",
            "failure_node_id": None,
            "failure_metadata": {"reason": "missing entry_node_id"},
            "total_cost_usd": 0.05,
            "inner_attempt_count": 3,
            "graph": None,
        },
        "validator_summaries": {},
    }
    # success=True but failed mechanical pre-check — must still be unreviewable.
    mech_fail_envelope = {
        "iter_id": 2,
        "fixture_id": "fix_gamma",
        "fixture": {"scene_setting": {"scene_anchor": "scene_gamma"}, "target_beats": [], "participating_npcs": []},
        "result": {
            "success": True,
            "failure_reason": None,
            "failure_node_id": None,
            "failure_metadata": None,
            "total_cost_usd": 0.07,
            "inner_attempt_count": 1,
            "graph": {
                "schema_version": "0.1.1",
                "graph_id": "s_gamma",
                "entry_node_id": "g0",
                "scene_anchor": "scene_gamma",
                "character_refs": [],
                "nodes": {"g0": {"node_id": "g0", "type": "end", "narration": "g", "speaker_ref": None, "options": []}},
            },
        },
        "validator_summaries": {
            "mechanical": {"pass": False, "error_node_count": 1, "error_count": 1, "error_codes": ["E_MECH_001"]},
            "topology": {"pass": True, "pure_topology_pass": True, "condition_form_pass": True, "error_count": 0, "warning_count": 0, "error_codes": []},
            "sampling": {"sample_count": 100, "reached_end_count": 100, "deadlock_count": 0, "avg_path_length": 1.0},
        },
    }
    _write_jsonl(
        batch / "scene_results.jsonl",
        [success_envelope, failure_envelope, mech_fail_envelope],
    )
    _write_text(
        batch / "graph_views" / "s_alpha" / "mermaid.mmd",
        "flowchart TD\n  n_start[\"n_start\"]\n  n_end([\"n_end\"]):::endNode\n  n_start --> n_end\n  classDef endNode fill:#fce4ec,stroke:#ad1457;\n",
    )
    _write_text(
        batch / "graph_views" / "s_alpha" / "dot.gv",
        "digraph G { n_start -> n_end; }\n",
    )
    _write_text(
        batch / "graph_views" / "s_alpha" / "ascii.txt",
        "n_start -> n_end\n",
    )
    judge_report = {
        "metadata": {
            "advisory_authority": "informational_only",
            "acceptance_source": "scene_review_cli_author_A_R",
            "adr": "ADR-020 §6",
        },
        "advisory_recommendation": {"s_alpha": "accept"},
        "rationales": {
            "s_alpha": {
                "lenient": "good vibes",
                "strict": "well-structured ending",
            }
        },
    }
    (batch / "AI_JUDGE_REPORT.json").write_text(
        json.dumps(judge_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return batch


@pytest.fixture
def fixture_scenes_dir(tmp_path: Path) -> Path:
    """A single content scene + sidecar — enough to test scenes_dir merging."""
    root = tmp_path / "content"
    scene_dir = root / "demo_scene"
    scene_dir.mkdir(parents=True)
    (scene_dir / "scene.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1.1",
                "graph_id": "demo_scene",
                "entry_node_id": "n0",
                "scene_anchor": "scene_demo",
                "character_refs": [],
                "nodes": {
                    "n0": {"node_id": "n0", "type": "end", "narration": "demo", "speaker_ref": None, "options": []}
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (scene_dir / "demo_scene.deps.json").write_text(
        json.dumps(
            {
                "schema_version": "0.3.0",
                "scene_id": "demo_scene",
                "generated_at": "2026-05-08T00:00:00Z",
                "ontology_ids_read": [],
                "state_paths_read": [],
                "state_paths_written": [],
                "prompt_template_hash": "sha256:" + "a" * 64,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return root
