"""Unit tests for the T-3.5 dep_index sidecar writer (ADR-023)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from generator.context_assembler import (
    GenerationDependencyTrace,
    PriorSceneSummary,
    TokenMetrics,
)
from generator.dep_index_writer import (
    DEP_INDEX_SCHEMA_VERSION,
    SIDECAR_SUFFIX,
    build_sidecar_payload,
    sidecar_path_for,
    write_sidecar,
)


def _make_trace(tmp_path: Path) -> GenerationDependencyTrace:
    template_file = tmp_path / "system.py"
    template_file.write_text("SCENE_SYSTEM_PROMPT = 'hello'", encoding="utf-8")
    return GenerationDependencyTrace(
        ontology_ids_read={"char_vellin", "scene_waystation_of_iron_oath"},
        state_paths_read={"relationship.vellin.trust", "flag.met_vellin"},
        state_paths_written={"relationship.vellin.trust"},
        clock_ids_referenced={"clk_corvan_search"},
        prompt_template_files=[template_file],
    )


def _minimal_scene() -> dict:
    return {
        "graph_id": "scene_smoke",
        "schema_version": "0.1.1",
        "scene_anchor": "scene_smoke",
        "nodes": {},
    }


# ---------------------------------------------------------------------------
# build_sidecar_payload
# ---------------------------------------------------------------------------


def test_payload_required_fields_only(tmp_path):
    trace = _make_trace(tmp_path)
    payload = build_sidecar_payload(
        scene=_minimal_scene(),
        trace=trace,
        prior_scene_summaries=None,
        token_metrics=None,
        chapter_id=None,
        act_id=None,
        generated_at="2026-05-08T10:00:00+00:00",
    )
    assert payload["schema_version"] == DEP_INDEX_SCHEMA_VERSION
    assert payload["scene_id"] == "scene_smoke"
    assert payload["generated_at"] == "2026-05-08T10:00:00+00:00"
    assert payload["ontology_ids_read"] == [
        "char_vellin",
        "scene_waystation_of_iron_oath",
    ]
    assert payload["state_paths_read"] == [
        "flag.met_vellin",
        "relationship.vellin.trust",
    ]
    assert payload["state_paths_written"] == [
        "relationship.vellin.trust",
    ]
    assert payload["prompt_template_hash"].startswith("sha256:")
    assert "chapter_id" not in payload
    assert "act_id" not in payload
    assert "scene_history_referenced" not in payload


def test_payload_includes_optional_fields_when_supplied(tmp_path):
    trace = _make_trace(tmp_path)
    trace.visual_asset_ids_referenced.add("asset_vellin_portrait")
    history = [
        PriorSceneSummary(
            scene_id="scene_alpha",
            summary="prior",
            key_state_paths=[],
        ),
    ]
    metrics = TokenMetrics(
        prompt_token_estimate=1234,
        summaries_injected_count=1,
        summary_source_hashes=["sha256:" + "0" * 64],
        truncation_reason="summaries_over_5",
    )
    payload = build_sidecar_payload(
        scene=_minimal_scene(),
        trace=trace,
        prior_scene_summaries=history,
        token_metrics=metrics,
        chapter_id="chap_arrival",
        act_id="act_one",
    )
    assert payload["visual_asset_ids_referenced"] == [
        "asset_vellin_portrait"
    ]
    assert payload["clock_ids_referenced"] == ["clk_corvan_search"]
    assert payload["chapter_id"] == "chap_arrival"
    assert payload["act_id"] == "act_one"
    assert payload["scene_history_referenced"] == ["scene_alpha"]
    assert payload["prompt_token_estimate"] == 1234
    assert payload["summaries_injected_count"] == 1
    assert payload["summary_source_hashes"] == ["sha256:" + "0" * 64]
    assert payload["truncation_reason"] == "summaries_over_5"


def test_payload_drops_token_metric_defaults(tmp_path):
    """Default TokenMetrics (zero counts, reason='none') stays out of
    the payload — the schema declares those fields missing-only and
    the convention is to emit them only when they carry signal."""
    trace = _make_trace(tmp_path)
    payload = build_sidecar_payload(
        scene=_minimal_scene(),
        trace=trace,
        prior_scene_summaries=None,
        token_metrics=TokenMetrics(),
        chapter_id=None,
        act_id=None,
    )
    assert "prompt_token_estimate" not in payload
    assert "summaries_injected_count" not in payload
    assert "summary_source_hashes" not in payload
    assert "truncation_reason" not in payload


def test_payload_rejects_bare_namespace_state_path(tmp_path):
    trace = _make_trace(tmp_path)
    trace.state_paths_read.add("world")  # bare namespace
    with pytest.raises(ValueError, match="state_paths_read"):
        build_sidecar_payload(
            scene=_minimal_scene(),
            trace=trace,
            prior_scene_summaries=None,
            token_metrics=None,
            chapter_id=None,
            act_id=None,
        )


def test_payload_rejects_relationship_with_only_slug(tmp_path):
    trace = _make_trace(tmp_path)
    trace.state_paths_written.add("relationship.vellin")  # missing field
    with pytest.raises(ValueError, match="state_paths_written"):
        build_sidecar_payload(
            scene=_minimal_scene(),
            trace=trace,
            prior_scene_summaries=None,
            token_metrics=None,
            chapter_id=None,
            act_id=None,
        )


def test_payload_projects_graph_id_to_scene_id_pattern(tmp_path):
    trace = _make_trace(tmp_path)
    scene = _minimal_scene()
    scene["graph_id"] = "scene-with-dash"
    payload = build_sidecar_payload(
        scene=scene,
        trace=trace,
        prior_scene_summaries=None,
        token_metrics=None,
        chapter_id=None,
        act_id=None,
    )
    assert payload["scene_id"] == "scene_with_dash"


def test_payload_rejects_unprojectable_graph_id(tmp_path):
    trace = _make_trace(tmp_path)
    scene = _minimal_scene()
    scene["graph_id"] = "Scene With Space"
    with pytest.raises(ValueError, match="cannot be projected"):
        build_sidecar_payload(
            scene=scene,
            trace=trace,
            prior_scene_summaries=None,
            token_metrics=None,
            chapter_id=None,
            act_id=None,
        )


# ---------------------------------------------------------------------------
# write_sidecar (atomic + schema-validated)
# ---------------------------------------------------------------------------


def test_write_sidecar_lands_validated_payload(tmp_path):
    trace = _make_trace(tmp_path)
    scene_path = tmp_path / "scene_smoke" / "scene.json"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_text("{}", encoding="utf-8")
    sidecar = write_sidecar(
        scene_path,
        _minimal_scene(),
        trace,
        None,
        None,
        "chap_arrival",
        "act_one",
    )
    assert sidecar == sidecar_path_for(scene_path)
    assert sidecar.suffix == ".json"
    assert sidecar.name.endswith(SIDECAR_SUFFIX)
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["schema_version"] == DEP_INDEX_SCHEMA_VERSION
    assert payload["chapter_id"] == "chap_arrival"
    assert payload["act_id"] == "act_one"


def test_write_sidecar_validates_schema_failure_aware(tmp_path, monkeypatch):
    """If the assembled payload somehow violates the schema, the writer
    must raise ValidationError before writing bytes — never silently
    land malformed sidecars."""
    trace = _make_trace(tmp_path)
    scene_path = tmp_path / "scene_smoke" / "scene.json"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_text("{}", encoding="utf-8")

    # Force an invalid prompt_template_hash (no sha256: prefix) by
    # monkeypatching the digest helper.
    import generator.dep_index_writer as mod

    monkeypatch.setattr(
        mod, "_hash_template_files", lambda paths: "not-a-sha256-hash"
    )
    with pytest.raises(ValidationError):
        write_sidecar(
            scene_path,
            _minimal_scene(),
            trace,
            None,
            None,
            None,
            None,
        )
    # No sidecar should have been written.
    assert not sidecar_path_for(scene_path).exists()


def test_write_sidecar_rejects_invalid_history_scene_id(tmp_path):
    trace = _make_trace(tmp_path)
    bad = [
        PriorSceneSummary(
            scene_id="Scene With Space",
            summary="oops",
            key_state_paths=[],
        )
    ]
    with pytest.raises(ValueError, match="invalid scene_id"):
        build_sidecar_payload(
            scene=_minimal_scene(),
            trace=trace,
            prior_scene_summaries=bad,
            token_metrics=None,
            chapter_id=None,
            act_id=None,
        )
