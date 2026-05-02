"""Tests for generate_character_sheet / generate_scene_background (T-1.5.6).

Six scenarios (mapped to the task's §5 acceptance list):

    scenario_1: manual + character_sheet (n=3 expressions) → 3 prompt packages
                land in tmp_path; meta + prompt files all valid.
    scenario_2: manual + scene_background (n=1) → one prompt package.
    scenario_3: api  + character_sheet → mock provider returns image bytes;
                NO real OpenAI call; image_cost_log records the row.
    scenario_4: image_budget exceeded mid-batch → run stops at the cap; the
                successful prefix is still returned, the failing entry is a
                budget_exceeded row, and image_cost_log has not been written
                for the failing variant.
    scenario_5: provider raises mid-batch → that one row reports failure but
                the next variant continues; cost log only carries the
                successful rows.
    scenario_6: target_ref missing from CHARACTER_FEATURES → graceful
                degradation; ontology card is used as fallback feature
                source; a WARNING is logged.

All filesystem state — pending dir, image_cost_log file, ontology, scene —
is redirected under tmp_path so tests do not touch the repo's `/content/`,
`/state/`, or `/generator/image_cost_log.jsonl`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pytest

from generator import generate_visual
from generator.generate_visual import (
    VisualGenerationResult,
    generate_character_sheet,
    generate_scene_background,
)
from generator.image_provider import (
    ImageGenerationResult,
    ImageProvider,
    ImageProviderError,
)
from generator.providers.manual_import import ManualImportProvider
from generator.visual_context import (
    CharacterSheetRequirement,
    SceneBackgroundRequirement,
)


# ---------------------------------------------------------------------------
# Test doubles + fixtures
# ---------------------------------------------------------------------------


_MIN_ONTOLOGY = {
    "entities": [
        {
            "id": "char_vellin",
            "display_name": "Vellin",
            "type": "character",
            "visual_assets": [],
        },
        {
            "id": "char_unknown",
            "display_name": "Unknown",
            "type": "character",
            "visual_assets": [],
        },
        {
            "id": "scene_waystation_of_iron_oath",
            "display_name": "Waystation of the Iron Oath",
            "type": "scene",
        },
    ]
}


@dataclass
class _Recorder:
    """Capture every provider.generate(...) call for assertions."""

    calls: list[dict] = field(default_factory=list)


@dataclass
class FakeApiImageProvider:
    """`api` mode stand-in — returns deterministic image bytes; never opens
    a network connection."""

    cost_per_call: float = 0.04
    model_id: str = "fake-image-model"
    recorder: _Recorder = field(default_factory=_Recorder)

    def generate(
        self,
        *,
        prompt: str,
        ref_images: list[Path] | None = None,
        n: int = 1,
        size: tuple[int, int] = (1024, 1024),
        asset_kind: Literal["character_sheet", "scene_background"],
        target_ref: str,
        target_type: Literal["character", "location", "scene"],
        asset_role: Literal["character_sheet", "scene_background"],
        asset_id_stub: str,
        variant_label: str = "",
    ) -> ImageGenerationResult:
        self.recorder.calls.append(
            {
                "asset_id_stub": asset_id_stub,
                "asset_kind": asset_kind,
                "target_ref": target_ref,
                "variant_label": variant_label,
                "prompt_excerpt": prompt[:80],
            }
        )
        return ImageGenerationResult(
            mode="api",
            asset_id_stub=asset_id_stub,
            image_bytes=b"\x89PNG\r\n\x1a\n-fake-png-bytes-",
            prompt_package_path=None,
            cost_usd=self.cost_per_call,
            raw_metadata={
                "target_ref": target_ref,
                "target_type": target_type,
                "asset_role": asset_role,
                "variant_label": variant_label,
                # review of T-1.5.6 #4.2: model_id is the stable input to
                # the cost log's `provider_id` (`openai_image_<model_id>`).
                "model_id": self.model_id,
            },
        )

    def estimate_cost(self, *, n: int, size: tuple[int, int]) -> float:
        return self.cost_per_call * n


@dataclass
class FakeFlakyProvider:
    """Raises ImageProviderError on the first call, succeeds afterward.

    Models the "single bad call doesn't kill the batch" expectation.
    """

    failure_indexes: tuple[int, ...] = (1,)
    cost_per_call: float = 0.0
    _call_idx: int = 0

    def generate(
        self,
        *,
        prompt: str,
        ref_images: list[Path] | None = None,
        n: int = 1,
        size: tuple[int, int] = (1024, 1024),
        asset_kind: Literal["character_sheet", "scene_background"],
        target_ref: str,
        target_type: Literal["character", "location", "scene"],
        asset_role: Literal["character_sheet", "scene_background"],
        asset_id_stub: str,
        variant_label: str = "",
    ) -> ImageGenerationResult:
        self._call_idx += 1
        if self._call_idx in self.failure_indexes:
            raise ImageProviderError(f"simulated provider failure on call {self._call_idx}")
        return ImageGenerationResult(
            mode="api",
            asset_id_stub=asset_id_stub,
            image_bytes=b"ok",
            prompt_package_path=None,
            cost_usd=self.cost_per_call,
            raw_metadata={
                "target_ref": target_ref,
                "target_type": target_type,
                "asset_role": asset_role,
                "variant_label": variant_label,
            },
        )

    def estimate_cost(self, *, n: int, size: tuple[int, int]) -> float:
        return self.cost_per_call * n


@pytest.fixture
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Redirect ontology / scene / pending / image_cost_log under tmp_path."""

    state_dir = tmp_path / "state" / "ontology"
    state_dir.mkdir(parents=True)
    ontology_path = state_dir / "waystation.json"
    ontology_path.write_text(
        json.dumps(_MIN_ONTOLOGY, ensure_ascii=False), encoding="utf-8"
    )

    scene_dir = tmp_path / "content" / "test_scene_v0"
    scene_dir.mkdir(parents=True)
    scene_path = scene_dir / "scene.json"
    scene_path.write_text(
        json.dumps(
            {"scene_anchor": "scene_waystation_of_iron_oath", "nodes": {}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    pending_root = tmp_path / "content" / "visuals" / "_pending"
    pending_root.mkdir(parents=True)

    reference_dir = tmp_path / "content" / "visuals" / "_reference"
    reference_dir.mkdir(parents=True)

    image_log = tmp_path / "image_cost_log.jsonl"
    monkeypatch.setenv("FORGEWRIGHT_IMAGE_COST_LOG", str(image_log))

    # Default budgets large enough that scenarios 1/2/3/5/6 don't trip them.
    monkeypatch.setenv("FORGEWRIGHT_PER_CALL_IMAGE_BUDGET_USD", "1.00")
    monkeypatch.setenv("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", "5.00")

    return {
        "ontology_path": ontology_path,
        "scene_path": scene_path,
        "pending_root": pending_root,
        "reference_dir": reference_dir,
        "image_log": image_log,
    }


def _manual_provider(pending_root: Path) -> ManualImportProvider:
    return ManualImportProvider(pending_root=pending_root)


def _read_log(image_log: Path) -> list[dict]:
    if not image_log.exists():
        return []
    return [json.loads(line) for line in image_log.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# scenario_1: manual + character_sheet (n=3 expressions)
# ---------------------------------------------------------------------------


def test_scenario_1_manual_character_sheet_writes_three_packages(
    isolated_paths: dict[str, Path],
) -> None:
    pending_root = isolated_paths["pending_root"]
    requirement = CharacterSheetRequirement(
        target_ref="char_vellin",
        n=3,
        expressions=["neutral", "smiling", "wary"],
        poses=["torso_up"],
    )

    results = generate_character_sheet(
        requirement=requirement,
        provider=_manual_provider(pending_root),
        mode="manual",
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
    )

    assert len(results) == 3
    assert all(r.success for r in results)
    assert all(r.cost_usd == 0.0 for r in results)
    assert {r.asset_id_stub for r in results} == {
        "img_vellin_neutral_torso_up_01",
        "img_vellin_smiling_torso_up_02",
        "img_vellin_wary_torso_up_03",
    }
    for r in results:
        assert r.prompt_package_path is not None
        assert (r.prompt_package_path / "prompt.md").is_file()
        assert (r.prompt_package_path / "meta.json").is_file()
        # The bilingual structure must be preserved end-to-end.
        body = (r.prompt_package_path / "prompt.md").read_text(encoding="utf-8")
        assert "## English" in body
        assert "中文" in body
        # B-bottom-line — the fixed-feature anchors must reach the prompt.
        assert "amber, narrow" in body
        assert "ash brown" in body

    # Cost log gets one row per variant (manual mode still logs at $0).
    rows = _read_log(isolated_paths["image_log"])
    assert len(rows) == 3
    assert all(r["mode"] == "manual" and r["cost_usd"] == 0.0 for r in rows)
    # review of T-1.5.6 #4.2: manual rows carry the canonical provider_id.
    assert all(r["provider_id"] == "manual_import" for r in rows)


# ---------------------------------------------------------------------------
# scenario_2: manual + scene_background (n=1)
# ---------------------------------------------------------------------------


def test_scenario_2_manual_scene_background_writes_one_package(
    isolated_paths: dict[str, Path],
) -> None:
    pending_root = isolated_paths["pending_root"]
    requirement = SceneBackgroundRequirement(
        target_ref="scene_waystation_of_iron_oath",
        target_type="scene",
        n=1,
        times_of_day=["dusk"],
        weather=None,
    )

    results = generate_scene_background(
        requirement=requirement,
        provider=_manual_provider(pending_root),
        mode="manual",
        ontology_path=isolated_paths["ontology_path"],
        scene_path=isolated_paths["scene_path"],
        reference_dir=isolated_paths["reference_dir"],
    )

    assert len(results) == 1
    r = results[0]
    assert r.success
    assert r.asset_id_stub == "img_waystation_of_iron_oath_dusk_01"
    body = (r.prompt_package_path / "prompt.md").read_text(encoding="utf-8")
    # No characters in the frame is a hard rule for scene_background.
    assert "No characters visible" in body or "no characters" in body.lower()
    # Time-of-day variant token must reach the prompt.
    assert "dusk" in body.lower()


# ---------------------------------------------------------------------------
# scenario_3: api mode mock returns image_bytes
# ---------------------------------------------------------------------------


def test_scenario_3_api_mode_mock_returns_bytes_and_logs_cost(
    isolated_paths: dict[str, Path],
) -> None:
    fake = FakeApiImageProvider(cost_per_call=0.04)
    requirement = CharacterSheetRequirement(
        target_ref="char_vellin",
        n=2,
        expressions=["neutral", "smiling"],
        poses=["torso_up"],
    )

    results = generate_character_sheet(
        requirement=requirement,
        provider=fake,
        mode="api",
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
        batch_name="t156_scenario_3",
    )

    assert len(results) == 2
    assert all(r.success for r in results)
    assert all(r.image_bytes == b"\x89PNG\r\n\x1a\n-fake-png-bytes-" for r in results)
    assert all(r.cost_usd == 0.04 for r in results)

    rows = _read_log(isolated_paths["image_log"])
    assert len(rows) == 2
    assert all(r["mode"] == "api" for r in rows)
    assert all(r["batch_name"] == "t156_scenario_3" for r in rows)
    assert sum(r["cost_usd"] for r in rows) == pytest.approx(0.08)
    # review of T-1.5.6 #4.2: api rows derive provider_id from raw_metadata.model_id.
    assert all(r["provider_id"] == "openai_image_fake-image-model" for r in rows)


# ---------------------------------------------------------------------------
# scenario_4: image_budget exceeded mid-batch
# ---------------------------------------------------------------------------


def test_scenario_4_budget_exceeded_returns_partial_failure(
    isolated_paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Daily ceiling tight enough to allow ~2 calls at $0.04 each then trip.
    monkeypatch.setenv("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", "0.10")
    monkeypatch.setenv("FORGEWRIGHT_PER_CALL_IMAGE_BUDGET_USD", "1.00")

    fake = FakeApiImageProvider(cost_per_call=0.04)
    requirement = CharacterSheetRequirement(
        target_ref="char_vellin",
        n=4,
        expressions=["neutral", "smiling", "wary", "tense"],
        poses=["torso_up"],
    )

    results = generate_character_sheet(
        requirement=requirement,
        provider=fake,
        mode="api",
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
    )

    # 2 successful + 1 budget-exceeded row; batch stops there.
    successful = [r for r in results if r.success]
    failures = [r for r in results if not r.success]
    assert len(successful) == 2
    assert len(failures) == 1
    assert failures[0].failure_reason and failures[0].failure_reason.startswith(
        "budget_exceeded"
    )
    # The provider was called only for the successful prefix.
    assert len(fake.recorder.calls) == 2
    # Cost log carries only the successful rows.
    rows = _read_log(isolated_paths["image_log"])
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# scenario_5: provider raises on one call, batch continues on the next
# ---------------------------------------------------------------------------


def test_scenario_5_per_call_provider_error_is_isolated(
    isolated_paths: dict[str, Path],
) -> None:
    flaky = FakeFlakyProvider(failure_indexes=(2,), cost_per_call=0.04)
    requirement = CharacterSheetRequirement(
        target_ref="char_vellin",
        n=3,
        expressions=["neutral", "smiling", "wary"],
        poses=["torso_up"],
    )

    results = generate_character_sheet(
        requirement=requirement,
        provider=flaky,
        mode="api",
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
    )

    assert len(results) == 3
    assert results[0].success is True
    assert results[1].success is False
    assert results[1].failure_reason and results[1].failure_reason.startswith(
        "provider_error"
    )
    assert results[2].success is True

    # ADR-014 / R7-style truthfulness: only successful calls show up in the
    # cost log; the failed one did not consume budget.
    rows = _read_log(isolated_paths["image_log"])
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# scenario_6: missing CHARACTER_FEATURES entry → graceful degradation
# ---------------------------------------------------------------------------


def test_scenario_6_missing_features_falls_back_to_ontology_card(
    isolated_paths: dict[str, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    pending_root = isolated_paths["pending_root"]
    requirement = CharacterSheetRequirement(
        target_ref="char_unknown",  # not in CHARACTER_FEATURES
        n=1,
        expressions=["neutral"],
        poses=["torso_up"],
    )

    with caplog.at_level(logging.WARNING):
        results = generate_character_sheet(
            requirement=requirement,
            provider=_manual_provider(pending_root),
            mode="manual",
            ontology_path=isolated_paths["ontology_path"],
            reference_dir=isolated_paths["reference_dir"],
        )

    assert len(results) == 1
    r = results[0]
    assert r.success
    body = (r.prompt_package_path / "prompt.md").read_text(encoding="utf-8")
    # Fallback block names the subject explicitly so ChatGPT doesn't invent.
    assert "Unknown" in body  # display_name from ontology
    assert "no fixed-feature entry registered" in body

    # Both the missing-features warning and (since _reference is empty) the
    # WARN-flavoured note about no style references should appear.
    assert any(
        "no character_features" in r.message.lower() for r in caplog.records
    )


# ---------------------------------------------------------------------------
# Regression #4.2: api row missing model_id falls back to "api_unknown" and
# does NOT crash the run (review of T-1.5.6 #4.2).
# ---------------------------------------------------------------------------


def test_api_provider_without_model_id_logs_api_unknown(
    isolated_paths: dict[str, Path],
) -> None:
    fake = FakeApiImageProvider(cost_per_call=0.04, model_id="")
    requirement = CharacterSheetRequirement(
        target_ref="char_vellin",
        n=1,
        expressions=["neutral"],
        poses=["torso_up"],
    )
    results = generate_character_sheet(
        requirement=requirement,
        provider=fake,
        mode="api",
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
    )
    assert len(results) == 1 and results[0].success
    rows = _read_log(isolated_paths["image_log"])
    assert len(rows) == 1
    assert rows[0]["provider_id"] == "api_unknown"


# ---------------------------------------------------------------------------
# Regression #4.1: scene_background prompt must merge scene.json narration
# even when an ontology card already exists (review of T-1.5.6 #4.1).
# ---------------------------------------------------------------------------


def test_background_prompt_includes_scene_narration_anchors(
    isolated_paths: dict[str, Path],
) -> None:
    """The Stage-0 ontology stub for `scene_waystation_of_iron_oath` only
    carries id/display_name/type, so without merging the scene narration
    GPT-Image would render a generic waystation. Assert the merger pulls
    at least one stable visual anchor from the narration into the prompt."""
    scene_path = isolated_paths["scene_path"]
    scene_path.write_text(
        json.dumps(
            {
                "scene_anchor": "scene_waystation_of_iron_oath",
                "nodes": {
                    "arrival_waystation": {
                        "node_id": "arrival_waystation",
                        "type": "dialogue",
                        "narration": (
                            "黄昏时分你策马抵达铁誓驿站。山风把塔楼顶的旗帜吹得猎猎作响——"
                            "那面绣着断剑与铁环的旗已经褪成铜绿色。\n\n"
                            "推开吱呀作响的橡木门，柜台上一盏油灯映出 Vellin 的轮廓。"
                        ),
                        "location_ref": "scene_waystation_of_iron_oath",
                    },
                    "other_node": {
                        "node_id": "other_node",
                        "type": "end",
                        "narration": "无关地点的结尾文本，应该被过滤。",
                        "location_ref": "scene_other_place",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    requirement = SceneBackgroundRequirement(
        target_ref="scene_waystation_of_iron_oath",
        target_type="scene",
        n=1,
        times_of_day=["dusk"],
    )
    results = generate_scene_background(
        requirement=requirement,
        provider=_manual_provider(isolated_paths["pending_root"]),
        mode="manual",
        ontology_path=isolated_paths["ontology_path"],
        scene_path=scene_path,
        reference_dir=isolated_paths["reference_dir"],
    )

    assert len(results) == 1 and results[0].success
    body = (results[0].prompt_package_path / "prompt.md").read_text(encoding="utf-8")
    # At least one stable visual anchor from the matched narration must
    # surface in the rendered background prompt.
    assert "断剑与铁环" in body
    assert "橡木门" in body or "油灯" in body
    # And the unrelated location's narration must NOT leak in.
    assert "无关地点的结尾文本" not in body


# ---------------------------------------------------------------------------
# Regression #3.1: mode/provider sanity guards (review of T-1.5.6 #3.1).
# ---------------------------------------------------------------------------


def test_manual_mode_with_paid_provider_refuses_before_call(
    isolated_paths: dict[str, Path],
) -> None:
    """`mode="manual"` + provider that estimates > $0 must fail-fast and
    NOT invoke the provider — the safety guard exists precisely because
    `image_budget.check()` short-circuits on manual mode."""
    fake = FakeApiImageProvider(cost_per_call=0.04)
    requirement = CharacterSheetRequirement(
        target_ref="char_vellin",
        n=2,
        expressions=["neutral", "smiling"],
        poses=["torso_up"],
    )

    results = generate_character_sheet(
        requirement=requirement,
        provider=fake,
        mode="manual",  # mismatch — paid provider must not be invoked
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
    )

    assert len(results) == 2
    assert all(not r.success for r in results)
    for r in results:
        assert r.failure_reason and r.failure_reason.startswith(
            "provider_mode_mismatch"
        )
    assert fake.recorder.calls == []
    # No log rows — consumption did not happen.
    assert _read_log(isolated_paths["image_log"]) == []


def test_api_mode_with_manual_provider_returns_mismatch_post_call(
    isolated_paths: dict[str, Path],
) -> None:
    """`mode="api"` + a provider that returns `gen_result.mode="manual"`
    must surface as `provider_mode_mismatch` and NOT write a log row —
    otherwise the cost log would mis-attribute the call."""
    requirement = CharacterSheetRequirement(
        target_ref="char_vellin",
        n=1,
        expressions=["neutral"],
        poses=["torso_up"],
    )

    results = generate_character_sheet(
        requirement=requirement,
        provider=_manual_provider(isolated_paths["pending_root"]),
        mode="api",  # mismatch — ManualImportProvider always returns mode="manual"
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
    )

    assert len(results) == 1
    r = results[0]
    assert not r.success
    assert r.failure_reason and r.failure_reason.startswith(
        "provider_mode_mismatch"
    )
    # No log rows — consumption mis-attribution averted.
    assert _read_log(isolated_paths["image_log"]) == []


# ---------------------------------------------------------------------------
# Regression: deterministic stub re-runs produce identical IDs.
# ---------------------------------------------------------------------------


def test_asset_id_stub_is_deterministic_across_reruns(
    isolated_paths: dict[str, Path],
) -> None:
    pending_root_a = isolated_paths["pending_root"] / "run_a"
    pending_root_b = isolated_paths["pending_root"] / "run_b"
    pending_root_a.mkdir()
    pending_root_b.mkdir()

    requirement = CharacterSheetRequirement(
        target_ref="char_vellin",
        n=2,
        expressions=["neutral", "smiling"],
        poses=["torso_up"],
    )

    a = generate_character_sheet(
        requirement=requirement,
        provider=_manual_provider(pending_root_a),
        mode="manual",
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
    )
    b = generate_character_sheet(
        requirement=requirement,
        provider=_manual_provider(pending_root_b),
        mode="manual",
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
    )

    assert [r.asset_id_stub for r in a] == [r.asset_id_stub for r in b]


# ---------------------------------------------------------------------------
# Smoke check: ImageProvider Protocol satisfied by our test doubles
# (the broader contract test lives in test_image_provider_contract.py;
# this one just keeps these doubles honest as the Protocol evolves).
# ---------------------------------------------------------------------------


def test_test_doubles_satisfy_image_provider_protocol() -> None:
    assert isinstance(FakeApiImageProvider(), ImageProvider)
    assert isinstance(FakeFlakyProvider(), ImageProvider)


# ---------------------------------------------------------------------------
# Stub-format guard: the body MUST stay inside the schema regex bound.
# ---------------------------------------------------------------------------


def test_long_target_ref_stub_stays_under_64_char_body(
    isolated_paths: dict[str, Path],
) -> None:
    """Even with a long target_ref, the stub body cannot exceed 64 chars
    (the ImageAsset.asset_id pattern / ManualImportProvider regex bound)."""
    long_target = "scene_" + "x" * 80
    # Patch ontology so the long anchor exists.
    ontology_path = isolated_paths["ontology_path"]
    data = json.loads(ontology_path.read_text())
    data["entities"].append(
        {"id": long_target, "display_name": "long-anchor", "type": "scene"}
    )
    ontology_path.write_text(json.dumps(data), encoding="utf-8")

    requirement = SceneBackgroundRequirement(
        target_ref=long_target,
        target_type="scene",
        n=1,
        times_of_day=["dusk"],
    )
    results = generate_scene_background(
        requirement=requirement,
        provider=_manual_provider(isolated_paths["pending_root"]),
        mode="manual",
        ontology_path=ontology_path,
        scene_path=isolated_paths["scene_path"],
        reference_dir=isolated_paths["reference_dir"],
    )
    assert len(results) == 1
    r = results[0]
    # asset_id_stub = "img_" + body; body must be ≤ 64 per schema.
    body = r.asset_id_stub.removeprefix("img_")
    assert 1 <= len(body) <= 64
