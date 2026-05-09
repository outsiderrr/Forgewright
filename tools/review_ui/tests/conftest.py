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
                "ontology_ids_read": ["char_vellin"],
                "state_paths_read": ["faction.iron_oath.reputation"],
                "state_paths_written": [],
                "visual_asset_ids_referenced": ["img_vellin_neutral"],
                "clock_ids_referenced": ["clk_seasons"],
                "prompt_template_hash": "sha256:" + "a" * 64,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return root


# ---------------------------------------------------------------------------
# T-3.6b integrations fixtures (RUI-INT-1..4) — additive, don't touch the
# MVP fixtures above.  Each fixture is a leaf — tests compose them via
# the ``fixture_full_loader`` factory below.
# ---------------------------------------------------------------------------


# 1×1 transparent PNG (smallest valid).  Used by the visual-streaming test
# so we don't pull a real asset into the repo.
_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x00\x03\x00\x01\xa3\x9d\xc8\xa3"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def fixture_visuals(fixture_scenes_dir: Path) -> Path:
    """Create ``content/visuals/manifest.json`` + 1 character PNG + 1 location PNG.

    Returns the visuals directory path. The manifest references char_x
    (matches s_alpha's character_refs) and scene_alpha (matches its
    scene_anchor) so /api/scene/s_alpha/visuals returns both groups.
    """
    visuals_dir = fixture_scenes_dir / "visuals"
    char_dir = visuals_dir / "char_x"
    loc_dir = visuals_dir / "scene_alpha"
    char_dir.mkdir(parents=True, exist_ok=True)
    loc_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / "img_char_x_neutral.png").write_bytes(_PNG_1X1)
    (loc_dir / "img_scene_alpha_bg.png").write_bytes(_PNG_1X1)

    # file_path is repo-root relative ("content/...") because the real
    # image_import CLI writes them that way.  ReviewDataLoader resolves
    # them via scenes_dir.parent + file_path.
    repo_root = fixture_scenes_dir.parent
    char_rel = (char_dir / "img_char_x_neutral.png").resolve().relative_to(repo_root)
    loc_rel = (loc_dir / "img_scene_alpha_bg.png").resolve().relative_to(repo_root)

    manifest = {
        "schema_version": "0.2.0",
        "assets": {
            "img_char_x_neutral": {
                "schema_version": "0.2.0",
                "asset_id": "img_char_x_neutral",
                "asset_kind": "character_sheet",
                "target_ref": "char_x",
                "target_type": "character",
                "asset_role": "character_sheet",
                "character_ref": "char_x",
                "location_ref": None,
                "source_mode": "manual",
                "format": "png",
                "width": 1,
                "height": 1,
                "file_size_bytes": len(_PNG_1X1),
                "has_alpha": True,
                "file_path": str(char_rel),
                "prompt_hash": "sha256:" + "f" * 64,
                "generation_metadata": None,
                "style_reference_id": None,
                "reference_ids": [],
                "reference_license_note": "",
                "open_source_ok": True,
                "commercial_ok": True,
                "created_at": "2026-05-09T00:00:00Z",
            },
            "img_scene_alpha_bg": {
                "schema_version": "0.2.0",
                "asset_id": "img_scene_alpha_bg",
                "asset_kind": "scene_background",
                "target_ref": "scene_alpha",
                "target_type": "location",
                "asset_role": "scene_background",
                "character_ref": None,
                "location_ref": "scene_alpha",
                "source_mode": "manual",
                "format": "png",
                "width": 1,
                "height": 1,
                "file_size_bytes": len(_PNG_1X1),
                "has_alpha": True,
                "file_path": str(loc_rel),
                "prompt_hash": "sha256:" + "e" * 64,
                "generation_metadata": None,
                "style_reference_id": None,
                "reference_ids": [],
                "reference_license_note": "",
                "open_source_ok": True,
                "commercial_ok": True,
                "created_at": "2026-05-09T00:00:00Z",
            },
        },
    }
    (visuals_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return visuals_dir


@pytest.fixture
def fixture_ontology(tmp_path: Path) -> Path:
    """A minimal world ontology with one chapter, one act, char_x as a
    core-relation entity (so dep_propagate's priority ranking exercises
    the 'core' branch when char_x is in the changed set)."""
    ontology_dir = tmp_path / "state" / "ontology"
    ontology_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "system_time": {"scene_count": 0, "long_rest_count": 0},
        "clocks": [{"clock_id": "clk_seasons"}],
        "chapters": [
            {
                "schema_version": "0.3.0",
                "chapter_id": "chap_intro",
                "display_name": "Intro Chapter",
                "acts": [
                    {
                        "act_id": "act_arrival",
                        "display_name": "Arrival",
                        "included_scenes": ["scene_alpha"],
                    }
                ],
            }
        ],
        "entities": [
            {
                "id": "char_x",
                "type": "character",
                "display_name": "Character X",
                "state_path_slug": "x",
                "relations": [
                    {
                        "target_character_ref": "char_y",
                        "relation_type": "ally",
                        "narrative_weight": "core",
                    }
                ],
            }
        ],
    }
    ontology_path = ontology_dir / "world.json"
    ontology_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return ontology_path


@pytest.fixture
def fixture_batch_with_sidecar(fixture_batch_dir: Path) -> Path:
    """Extend the MVP batch with a ``deps/s_alpha.deps.json`` sidecar so
    the sidecar-primary visual / chapter-placement paths can be tested.
    """
    deps_dir = fixture_batch_dir / "deps"
    deps_dir.mkdir(parents=True, exist_ok=True)
    (deps_dir / "s_alpha.deps.json").write_text(
        json.dumps(
            {
                "schema_version": "0.3.0",
                "scene_id": "s_alpha",
                "generated_at": "2026-05-09T00:00:00Z",
                "ontology_ids_read": ["char_x"],
                "state_paths_read": [],
                "state_paths_written": [],
                "visual_asset_ids_referenced": ["img_char_x_neutral", "img_scene_alpha_bg"],
                "clock_ids_referenced": [],
                "chapter_id": "chap_intro",
                "act_id": "act_arrival",
                "prompt_template_hash": "sha256:" + "b" * 64,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return fixture_batch_dir


@pytest.fixture
def fixture_batch_with_playtest_at_experiments_root(tmp_path: Path) -> tuple[Path, Path]:
    """Finding 4.2 — playtest_NNN/ lives at ``generator/experiments/``,
    not nested in a batch directory.  Returns ``(batch_dir, experiments_root)``
    so a test can verify the production-default path heuristic.
    """
    experiments_root = tmp_path / "generator" / "experiments"
    batch_dir = experiments_root / "20260509T000000Z_baseline"
    batch_dir.mkdir(parents=True, exist_ok=True)
    # Minimal scene_results.jsonl so the loader has something to list
    (batch_dir / "scene_results.jsonl").write_text(
        json.dumps(
            {
                "iter_id": 0,
                "fixture_id": "fix",
                "fixture": {
                    "scene_setting": {"scene_anchor": "scene_x"},
                    "target_beats": [],
                    "participating_npcs": [],
                },
                "result": {
                    "success": True,
                    "graph": {
                        "schema_version": "0.1.1",
                        "graph_id": "s_x",
                        "entry_node_id": "n0",
                        "scene_anchor": "scene_x",
                        "character_refs": [],
                        "nodes": {
                            "n0": {"node_id": "n0", "type": "end", "narration": "x", "speaker_ref": None, "options": []}
                        },
                    },
                    "total_cost_usd": 0.0,
                    "inner_attempt_count": 1,
                },
                "validator_summaries": {
                    "mechanical": {"pass": True, "error_node_count": 0, "error_count": 0, "error_codes": []},
                    "topology": {"pass": True, "pure_topology_pass": True, "condition_form_pass": True, "error_count": 0, "warning_count": 0, "error_codes": []},
                    "sampling": {"sample_count": 1, "reached_end_count": 1, "deadlock_count": 0, "avg_path_length": 1.0},
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    # Playtest run lives at the SIBLING level (the real T-3.4 layout).
    run_dir = experiments_root / "playtest_001"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "playtest_id": "playtest_001",
                "scenes_played": ["s_x"],
                "started_at": "2026-05-09T00:00:00Z",
                "completed_at": "2026-05-09T00:01:00Z",
                "model_id": "stub",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "worst_scenes.json").write_text(
        json.dumps(
            {
                "playtest_id": "playtest_001",
                "rubric_version": "test",
                "scenes": [{"scene_id": "s_x", "n_paths": 1, "critical_count": 0, "scene_quality_score": 8.0, "mean_path_score": 8.0, "min_path_score": 8.0, "max_path_score": 8.0, "n_paths_judged": 1, "n_paths_failed": 0, "major_count": 0, "minor_count": 0, "worst_path_summaries": [], "critical_findings": []}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "worst_paths.jsonl").write_text(
        json.dumps({"path_id": "p1", "scene_id": "s_x", "persona_id": "speedrunner", "judge_score": 8.0, "critical_count": 0, "major_count": 0, "minor_count": 0, "reached_end": True, "end_node_id": "n0", "failure_reason": None, "severity_findings": [], "judge_dimensions": {}, "judge_rationale": "ok", "steps": []}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return batch_dir, experiments_root


@pytest.fixture
def fixture_batch_with_playtest(fixture_batch_with_sidecar: Path) -> Path:
    """Add a ``playtest_001/`` directory under ``batch_dir`` with the
    three playtest artifacts (run_manifest + worst_scenes + worst_paths).
    Honors the prompt's literal ``batch_dir/playtest_NNN/`` contract;
    finding 4.2's production-default path is exercised separately via
    :func:`fixture_batch_with_playtest_at_experiments_root`.
    """
    fixture_batch_dir = fixture_batch_with_sidecar
    run_dir = fixture_batch_dir / "playtest_001"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "playtest_id": "playtest_001",
        "started_at": "2026-05-09T00:00:00Z",
        "completed_at": "2026-05-09T00:01:00Z",
        "model_id": "stub-model",
        "temperature": 0.0,
        "scenes_played": ["s_alpha"],
        "n_paths_per_persona": 2,
        "personas": [],
        "rubric_version": "test",
        "guard": {},
        "aborted": False,
        "abort_reason": None,
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    worst_scenes = {
        "playtest_id": "playtest_001",
        "rubric_version": "test",
        "scenes": [
            {
                "scene_id": "s_alpha",
                "n_paths": 2,
                "n_paths_judged": 2,
                "n_paths_failed": 0,
                "mean_path_score": 6.5,
                "min_path_score": 4.0,
                "max_path_score": 9.0,
                "critical_count": 1,
                "major_count": 2,
                "minor_count": 3,
                "scene_quality_score": 1.5,
                "worst_path_summaries": [],
                "critical_findings": [
                    {
                        "dimension": "pacing",
                        "severity": "critical",
                        "text": "玩家在 n_start 处看不到第三个选项",
                    }
                ],
            }
        ],
    }
    (run_dir / "worst_scenes.json").write_text(
        json.dumps(worst_scenes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "worst_scenes.md").write_text(
        "# worst scenes (test fixture)\n\n- s_alpha: critical=1\n", encoding="utf-8"
    )
    paths_rows = [
        {
            "path_id": "p001",
            "persona_id": "speedrunner",
            "scene_id": "s_alpha",
            "reached_end": False,
            "end_node_id": None,
            "failure_reason": "deadlock",
            "llm_calls": 5,
            "cost_usd": 0.01,
            "duration_seconds": 3.0,
            "error": None,
            "judge_score": 4.0,
            "judge_dimensions": {"pacing": 3, "consistency": 5},
            "judge_rationale": "节奏过快，跳过了关键铺垫",
            "severity_findings": [
                {"severity": "critical", "dimension": "pacing", "text": "玩家在 n_start 处看不到第三个选项"},
                {"severity": "major", "dimension": "consistency", "text": "NPC 反应错位"},
            ],
            "critical_count": 1,
            "major_count": 1,
            "minor_count": 0,
            "steps": [],
        },
        {
            "path_id": "p002",
            "persona_id": "completionist",
            "scene_id": "s_alpha",
            "reached_end": True,
            "end_node_id": "n_end",
            "failure_reason": None,
            "llm_calls": 8,
            "cost_usd": 0.02,
            "duration_seconds": 5.0,
            "error": None,
            "judge_score": 9.0,
            "judge_dimensions": {"pacing": 9, "consistency": 9},
            "judge_rationale": "完整探索所有分支",
            "severity_findings": [
                {"severity": "minor", "dimension": "polish", "text": "措辞略冗"},
            ],
            "critical_count": 0,
            "major_count": 1,
            "minor_count": 3,
            "steps": [],
        },
        # noise row — different scene, must NOT appear in /api/playtest/s_alpha
        {
            "path_id": "p003",
            "persona_id": "cautious",
            "scene_id": "s_other",
            "reached_end": True,
            "end_node_id": "n_end",
            "failure_reason": None,
            "llm_calls": 3,
            "cost_usd": 0.005,
            "duration_seconds": 2.0,
            "error": None,
            "judge_score": 7.0,
            "judge_dimensions": {},
            "judge_rationale": "ok",
            "severity_findings": [],
            "critical_count": 0,
            "major_count": 0,
            "minor_count": 0,
            "steps": [],
        },
    ]
    with (run_dir / "worst_paths.jsonl").open("w", encoding="utf-8") as fh:
        for r in paths_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return fixture_batch_dir
