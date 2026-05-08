"""T-3.3 (ADR-024) — scene_summary_writer.

Coverage:

  * `extract_key_state_paths` walks node + option effects and dedupes.
  * Sidecar round-trip — write then read produces an equivalent
    `PriorSceneSummary`.
  * `draft_summary` charges the budget, honours `LLMProvider`, builds
    a `SummaryDraft` with extracted state paths.
  * `manual_edit` round-trips through ``$EDITOR`` (mocked via
    `subprocess.run`) and refuses bad / empty saves.
  * `run_cli` orchestration: `--auto-accept`, `--manual`, default
    `[A]ccept`, default `[Q]uit`, `--manual + --auto-accept` rejected.
"""
from __future__ import annotations

import json
import os
import subprocess
from io import StringIO
from pathlib import Path

import pytest

from generator.context_assembler import PriorSceneSummary
from generator.llm_provider import ProviderError, StructuredResponse
from generator.scene_summary_writer import (
    SummaryDraft,
    draft_summary,
    draft_to_summary,
    extract_key_state_paths,
    manual_edit,
    read_summary_sidecar,
    run_cli,
    summary_sidecar_path,
    write_summary_sidecar,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_budget(tmp_path, monkeypatch):
    """Match scene_strategies' test convention so the writer's
    `budget.check_and_charge` calls go through but never spill into
    the real cost log."""
    monkeypatch.setenv("FORGEWRIGHT_COST_LOG", str(tmp_path / "cost_log.jsonl"))
    monkeypatch.setenv("DAILY_BUDGET_USD", "100")
    monkeypatch.setenv("PER_CALL_BUDGET_USD", "10")


def _scene_graph() -> dict:
    return {
        "schema_version": "0.1.1",
        "graph_id": "scene_alpha",
        "scene_anchor": "scene_alpha",
        "entry_node_id": "n_root",
        "character_refs": ["char_vellin"],
        "nodes": {
            "n_root": {
                "node_id": "n_root",
                "type": "dialogue",
                "speaker_ref": "char_vellin",
                "narration": "Vellin opens the door.",
                "location_ref": "loc_main",
                "on_enter_effects": [
                    {"op": "set", "path": "world.scene_count", "value": 1}
                ],
                "options": [
                    {
                        "option_id": "opt_yes",
                        "text": "好的",
                        "target_node_id": "n_end",
                        "effects": [
                            {"op": "set", "path": "flag.has_decided", "value": True}
                        ],
                    },
                    {
                        "option_id": "opt_no",
                        "text": "不",
                        "target_node_id": "n_end",
                        "effects": [
                            # Duplicate path on purpose to verify dedupe.
                            {"op": "set", "path": "flag.has_decided", "value": False}
                        ],
                    },
                ],
            },
            "n_end": {
                "node_id": "n_end",
                "type": "end",
                "speaker_ref": None,
                "narration": "幕落。",
                "location_ref": "loc_main",
                "on_enter_effects": [
                    {"op": "increment", "path": "world.long_rest_count", "value": 1}
                ],
                "options": [],
            },
        },
    }


def _write_scene(tmp_path: Path) -> Path:
    target = tmp_path / "scene_alpha.json"
    target.write_text(
        json.dumps(_scene_graph(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


class _ScriptedProvider:
    """Same shape as the scene_strategies one — single linear script."""

    model_id = "fake-summary-model"

    def __init__(self, script):
        self._script = list(script)
        self._idx = 0
        self.call_count = 0
        self.user_prompts: list[str] = []

    def generate_structured(self, system_prompt, user_prompt, json_schema):
        self.call_count += 1
        self.user_prompts.append(user_prompt)
        item = self._script[self._idx]
        self._idx += 1
        if isinstance(item, Exception):
            raise item
        return item

    def estimate_cost(self, input_tokens, output_tokens):
        return 0.0001


def _make_response(content) -> StructuredResponse:
    return StructuredResponse(
        content=content,
        raw_text=json.dumps(content, ensure_ascii=False),
        input_tokens=200,
        output_tokens=80,
        model_id="fake-summary-model",
        finish_reason="STOP",
    )


# ---------------------------------------------------------------------------
# extract_key_state_paths
# ---------------------------------------------------------------------------


def test_extract_key_state_paths_collects_node_and_option_effects():
    paths = extract_key_state_paths(_scene_graph())
    assert "world.scene_count" in paths
    assert "flag.has_decided" in paths
    assert "world.long_rest_count" in paths


def test_extract_key_state_paths_deduplicates():
    """Two options on n_root both touch flag.has_decided — should appear once."""
    paths = extract_key_state_paths(_scene_graph())
    assert paths.count("flag.has_decided") == 1


def test_extract_key_state_paths_handles_empty_graph():
    assert extract_key_state_paths({"nodes": {}}) == []
    assert extract_key_state_paths({}) == []


def test_extract_key_state_paths_skips_malformed_entries():
    """Defensive iteration — nodes / effects that aren't dicts get
    silently skipped so a half-formed scene doesn't crash the writer."""
    paths = extract_key_state_paths(
        {
            "nodes": {
                "n_a": {"on_enter_effects": [{"path": "world.a"}]},
                "n_b": "not-a-dict",
                "n_c": {"on_enter_effects": [{"path": ""}]},  # empty path skipped
                "n_d": {"options": [{"effects": [{"path": "flag.b"}]}]},
            }
        }
    )
    assert paths == ["world.a", "flag.b"]


# ---------------------------------------------------------------------------
# Sidecar round-trip
# ---------------------------------------------------------------------------


def test_summary_sidecar_path_format(tmp_path):
    scene = tmp_path / "scenes" / "foo.json"
    assert summary_sidecar_path(scene).name == "foo.summary.json"


def test_write_then_read_sidecar_round_trip(tmp_path):
    scene = _write_scene(tmp_path)
    summary = PriorSceneSummary(
        scene_id="scene_alpha",
        summary="Vellin opens the door.",
        key_state_paths=["world.scene_count", "flag.has_decided"],
        chapter_id="chap_glades",
        act_id=None,
    )
    written = write_summary_sidecar(summary, scene)
    assert written.exists()
    raw = json.loads(written.read_text(encoding="utf-8"))
    # `act_id` is None → must be omitted (no null pollution).
    assert "act_id" not in raw
    assert raw["chapter_id"] == "chap_glades"

    rehydrated = read_summary_sidecar(scene)
    assert rehydrated == summary


def test_read_missing_sidecar_returns_none(tmp_path):
    scene = _write_scene(tmp_path)
    assert read_summary_sidecar(scene) is None


def test_read_malformed_sidecar_raises(tmp_path):
    scene = _write_scene(tmp_path)
    sidecar = summary_sidecar_path(scene)
    sidecar.write_text(json.dumps([1, 2, 3]), encoding="utf-8")  # not an object
    with pytest.raises(ValueError):
        read_summary_sidecar(scene)


# ---------------------------------------------------------------------------
# draft_summary (LLM path)
# ---------------------------------------------------------------------------


def test_draft_summary_returns_extracted_paths_and_llm_prose(tmp_path):
    scene = _write_scene(tmp_path)
    provider = _ScriptedProvider(
        [_make_response({"summary": "Vellin lets Corvan in; the oath bends but holds."})]
    )
    draft = draft_summary(scene_path=scene, provider=provider)
    assert isinstance(draft, SummaryDraft)
    assert draft.scene_id == "scene_alpha"
    assert draft.summary == "Vellin lets Corvan in; the oath bends but holds."
    # State paths come from the scene, NOT from the LLM.
    assert "world.scene_count" in draft.key_state_paths
    assert "flag.has_decided" in draft.key_state_paths
    assert provider.call_count == 1


def test_draft_summary_user_prompt_includes_node_text(tmp_path):
    scene = _write_scene(tmp_path)
    provider = _ScriptedProvider(
        [_make_response({"summary": "..."})]
    )
    draft_summary(scene_path=scene, provider=provider)
    prompt = provider.user_prompts[0]
    assert "scene_alpha" in prompt
    assert "Vellin opens the door." in prompt
    assert "好的" in prompt
    assert "[A]ccept" not in prompt  # CLI prompt copy never reaches the LLM


def test_draft_summary_propagates_provider_error(tmp_path):
    scene = _write_scene(tmp_path)
    provider = _ScriptedProvider([ProviderError("relay timeout")])
    with pytest.raises(ProviderError):
        draft_summary(scene_path=scene, provider=provider)


def test_draft_summary_rejects_missing_summary_field(tmp_path):
    scene = _write_scene(tmp_path)
    provider = _ScriptedProvider(
        [_make_response({"not_summary": "wrong field"})]
    )
    with pytest.raises(ProviderError):
        draft_summary(scene_path=scene, provider=provider)


def test_draft_to_summary_drops_metadata():
    draft = SummaryDraft(
        scene_id="scene_a",
        summary="...",
        key_state_paths=["world.x"],
        chapter_id="chap_a",
        act_id=None,
        raw_response_text='{"summary":"..."}',
        cost_usd=0.0123,
    )
    summary = draft_to_summary(draft)
    assert isinstance(summary, PriorSceneSummary)
    assert summary.summary == "..."
    assert summary.chapter_id == "chap_a"
    # metadata fields gone.
    assert not hasattr(summary, "raw_response_text")
    assert not hasattr(summary, "cost_usd")


# ---------------------------------------------------------------------------
# manual_edit (--manual flow)
# ---------------------------------------------------------------------------


def _patch_editor(monkeypatch, edited_payload):
    """Replace `subprocess.run` with a stub that overwrites the tempfile.

    `edited_payload` may be either a dict (serialised as JSON) or a raw
    string (left as-is — used to test malformed-save handling)."""
    captured = {"argv": None, "tempfile": None}

    def fake_run(cmd, check=False):
        captured["argv"] = cmd
        captured["tempfile"] = cmd[-1]
        target = Path(cmd[-1])
        if isinstance(edited_payload, dict):
            target.write_text(
                json.dumps(edited_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            target.write_text(str(edited_payload), encoding="utf-8")

        class _R:
            returncode = 0

        return _R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("generator.scene_summary_writer.subprocess.run", fake_run)
    return captured


def test_manual_edit_returns_summary_from_editor_output(tmp_path, monkeypatch):
    scene = _write_scene(tmp_path)
    edited = {
        "scene_id": "scene_alpha",
        "summary": "Author-written digest.",
        "key_state_paths": ["world.scene_count"],
        "chapter_id": "chap_glades",
    }
    captured = _patch_editor(monkeypatch, edited)
    monkeypatch.setenv("EDITOR", "true")
    summary = manual_edit(scene_path=scene)
    assert isinstance(summary, PriorSceneSummary)
    assert summary.summary == "Author-written digest."
    assert summary.chapter_id == "chap_glades"
    # Argv last element is the tempfile path; first element honours $EDITOR.
    assert os.path.basename(captured["argv"][-1]).endswith(".summary.json")


def test_manual_edit_seeds_template_with_initial_draft(tmp_path, monkeypatch):
    """When edit is launched from the [E] CLI branch, the template's
    summary field must start with the LLM draft text."""
    scene = _write_scene(tmp_path)
    seen_template = {}

    def fake_run(cmd, check=False):
        target = Path(cmd[-1])
        seen_template["pre_edit"] = json.loads(
            target.read_text(encoding="utf-8")
        )
        # Author tweaks the prose but keeps everything else.
        edited = dict(seen_template["pre_edit"])
        edited["summary"] = "Author refined: " + edited["summary"]
        target.write_text(
            json.dumps(edited, ensure_ascii=False), encoding="utf-8"
        )

        class _R:
            returncode = 0

        return _R()

    monkeypatch.setattr("generator.scene_summary_writer.subprocess.run", fake_run)
    draft = SummaryDraft(
        scene_id="scene_alpha",
        summary="LLM raw text",
        key_state_paths=["world.scene_count"],
    )
    summary = manual_edit(scene_path=scene, initial_draft=draft)
    assert seen_template["pre_edit"]["summary"] == "LLM raw text"
    assert summary.summary == "Author refined: LLM raw text"


def test_manual_edit_rejects_invalid_json(tmp_path, monkeypatch):
    scene = _write_scene(tmp_path)
    _patch_editor(monkeypatch, "this is not json {")
    with pytest.raises(RuntimeError):
        manual_edit(scene_path=scene)


def test_manual_edit_rejects_empty_summary(tmp_path, monkeypatch):
    scene = _write_scene(tmp_path)
    _patch_editor(
        monkeypatch,
        {"scene_id": "scene_alpha", "summary": "   ", "key_state_paths": []},
    )
    with pytest.raises(RuntimeError):
        manual_edit(scene_path=scene)


# ---------------------------------------------------------------------------
# run_cli
# ---------------------------------------------------------------------------


def test_run_cli_auto_accept_writes_sidecar(tmp_path):
    scene = _write_scene(tmp_path)
    provider = _ScriptedProvider(
        [_make_response({"summary": "Auto-accept digest."})]
    )
    out, err = StringIO(), StringIO()
    rc = run_cli(
        scene_path=scene,
        auto_accept=True,
        manual=False,
        provider_factory=lambda: provider,
        stdout=out,
        stderr=err,
    )
    assert rc == 0
    rehydrated = read_summary_sidecar(scene)
    assert rehydrated is not None
    assert rehydrated.summary == "Auto-accept digest."


def test_run_cli_manual_skips_provider(tmp_path, monkeypatch):
    scene = _write_scene(tmp_path)
    _patch_editor(
        monkeypatch,
        {
            "scene_id": "scene_alpha",
            "summary": "Author cold-write.",
            "key_state_paths": ["world.scene_count"],
        },
    )

    def _fail():
        raise AssertionError("provider should not be built in manual mode")

    out, err = StringIO(), StringIO()
    rc = run_cli(
        scene_path=scene,
        auto_accept=False,
        manual=True,
        provider_factory=_fail,
        stdout=out,
        stderr=err,
    )
    assert rc == 0
    rehydrated = read_summary_sidecar(scene)
    assert rehydrated is not None
    assert rehydrated.summary == "Author cold-write."


def test_run_cli_default_accept_path(tmp_path):
    scene = _write_scene(tmp_path)
    provider = _ScriptedProvider(
        [_make_response({"summary": "Default-mode digest."})]
    )
    out, err = StringIO(), StringIO()
    rc = run_cli(
        scene_path=scene,
        auto_accept=False,
        manual=False,
        provider_factory=lambda: provider,
        stdout=out,
        stderr=err,
        input_fn=lambda _prompt: "a",
    )
    assert rc == 0
    rehydrated = read_summary_sidecar(scene)
    assert rehydrated is not None
    assert rehydrated.summary == "Default-mode digest."


def test_run_cli_default_quit_does_not_write(tmp_path):
    scene = _write_scene(tmp_path)
    provider = _ScriptedProvider(
        [_make_response({"summary": "Will be discarded."})]
    )
    out, err = StringIO(), StringIO()
    rc = run_cli(
        scene_path=scene,
        auto_accept=False,
        manual=False,
        provider_factory=lambda: provider,
        stdout=out,
        stderr=err,
        input_fn=lambda _prompt: "q",
    )
    assert rc == 5
    assert read_summary_sidecar(scene) is None


def test_run_cli_rejects_manual_with_auto_accept(tmp_path):
    scene = _write_scene(tmp_path)
    out, err = StringIO(), StringIO()
    rc = run_cli(
        scene_path=scene,
        auto_accept=True,
        manual=True,
        provider_factory=lambda: pytest.fail("provider should not be built"),
        stdout=out,
        stderr=err,
    )
    assert rc == 2
    assert "mutually exclusive" in err.getvalue()


def test_run_cli_missing_scene_returns_2(tmp_path):
    bogus = tmp_path / "missing.json"
    out, err = StringIO(), StringIO()
    rc = run_cli(
        scene_path=bogus,
        auto_accept=False,
        manual=True,
        provider_factory=lambda: pytest.fail("provider should not be built"),
        stdout=out,
        stderr=err,
    )
    assert rc == 2
    assert "scene file not found" in err.getvalue()
