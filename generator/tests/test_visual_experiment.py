"""Tests for visual_experiment harness (T-1.5.8).

Cover the three contracts the harness must honour:

  1. manual + character_sheet → results.jsonl with N rows + summary.txt +
     prompt_packages/<stub> mirrors of `_pending/<stub>/`.
  2. budget_exceeded mid-batch → loop stops, summary marks the batch as
     stopped_early, the budget row is the last entry.
  3. asset_role/target_type mismatch → ValueError before any provider call.

No real provider; we drive `ManualImportProvider` (cost = $0) plus a tiny
fake API provider for budget assertions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pytest

from generator.image_provider import ImageGenerationResult
from generator.providers.manual_import import ManualImportProvider
from generator.visual_experiment import run_visual_experiment


_MIN_ONTOLOGY = {
    "entities": [
        {
            "id": "char_vellin",
            "display_name": "Vellin",
            "type": "character",
            "visual_assets": [],
        },
        {
            "id": "scene_waystation_of_iron_oath",
            "display_name": "Waystation",
            "type": "scene",
        },
    ]
}


@dataclass
class _ExpensiveFakeProvider:
    """Stand-in for `api` mode that estimates a price >= the per-call ceiling
    so the second call trips ImageBudgetExceeded inside generate_visual.
    """

    cost_per_call: float = 0.40
    model_id: str = "fake-image-model"
    calls: list[str] = field(default_factory=list)

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
        self.calls.append(asset_id_stub)
        return ImageGenerationResult(
            mode="api",
            asset_id_stub=asset_id_stub,
            image_bytes=b"\x89PNG\r\n\x1a\n-fake-",
            prompt_package_path=None,
            cost_usd=self.cost_per_call,
            raw_metadata={
                "target_ref": target_ref,
                "target_type": target_type,
                "asset_role": asset_role,
                "variant_label": variant_label,
                "model_id": self.model_id,
            },
        )

    def estimate_cost(self, *, n: int, size: tuple[int, int]) -> float:
        return self.cost_per_call * n


@pytest.fixture
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
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
        json.dumps({"scene_anchor": "scene_waystation_of_iron_oath", "nodes": {}}),
        encoding="utf-8",
    )

    pending_root = tmp_path / "content" / "visuals" / "_pending"
    pending_root.mkdir(parents=True)
    reference_dir = tmp_path / "content" / "visuals" / "_reference"
    reference_dir.mkdir(parents=True)

    image_log = tmp_path / "image_cost_log.jsonl"
    monkeypatch.setenv("FORGEWRIGHT_IMAGE_COST_LOG", str(image_log))
    monkeypatch.setenv("FORGEWRIGHT_PER_CALL_IMAGE_BUDGET_USD", "1.00")
    monkeypatch.setenv("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", "5.00")

    return {
        "ontology_path": ontology_path,
        "scene_path": scene_path,
        "pending_root": pending_root,
        "reference_dir": reference_dir,
        "out_root": tmp_path / "experiments",
    }


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_manual_character_sheet_batch_writes_results_summary_and_packages(
    isolated_paths: dict[str, Path],
) -> None:
    provider = ManualImportProvider(pending_root=isolated_paths["pending_root"])
    batch_dir = run_visual_experiment(
        batch_name="t158_test",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        n=3,
        mode="manual",
        provider=provider,
        expressions=["neutral", "smiling", "wary"],
        poses=["torso_up"],
        out_root=isolated_paths["out_root"],
        timestamp="20260502T120000Z",
        progress=False,
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
    )

    assert batch_dir == isolated_paths["out_root"] / "20260502T120000Z_t158_test"
    results = _read_jsonl(batch_dir / "results.jsonl")
    assert len(results) == 3
    assert all(r["result"]["success"] for r in results)
    assert all(r["batch_name"] == "t158_test" for r in results)
    assert all(r["target_ref"] == "char_vellin" for r in results)
    assert all(r["mode"] == "manual" for r in results)
    assert all(r["result"]["cost_usd"] == 0.0 for r in results)

    summary = (batch_dir / "summary.txt").read_text(encoding="utf-8")
    assert "results:" in summary
    assert "successful:" in summary
    assert "100.0%" in summary
    assert "stopped early" not in summary

    # prompt_packages/ mirrors _pending/<stub>/
    pkgs = batch_dir / "prompt_packages"
    assert pkgs.is_dir()
    mirrored = sorted(p.name for p in pkgs.iterdir())
    assert len(mirrored) == 3
    for name in mirrored:
        # Either a symlink resolving into _pending or a copy that contains
        # the same prompt.md/meta.json files.
        link_or_dir = pkgs / name
        assert (link_or_dir / "meta.json").is_file()
        assert (link_or_dir / "prompt.md").is_file()


def test_budget_exceeded_stops_batch_and_marks_summary(
    isolated_paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Tiny daily ceiling so the second variant trips the cap.
    monkeypatch.setenv("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", "0.50")
    provider = _ExpensiveFakeProvider(cost_per_call=0.40)

    batch_dir = run_visual_experiment(
        batch_name="t158_budget",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        n=3,
        mode="api",
        provider=provider,
        expressions=["neutral", "smiling", "wary"],
        poses=["torso_up"],
        out_root=isolated_paths["out_root"],
        timestamp="20260502T120100Z",
        progress=False,
        ontology_path=isolated_paths["ontology_path"],
        reference_dir=isolated_paths["reference_dir"],
    )

    rows = _read_jsonl(batch_dir / "results.jsonl")
    # First variant succeeds, second variant trips daily cap → no third call.
    assert len(rows) == 2
    assert rows[0]["result"]["success"] is True
    assert rows[1]["result"]["success"] is False
    assert rows[1]["result"]["failure_reason"].startswith("budget_exceeded")
    assert len(provider.calls) == 1, "second variant must not reach provider"

    summary = (batch_dir / "summary.txt").read_text(encoding="utf-8")
    assert "stopped early due to image_budget_exceeded" in summary


def test_role_type_mismatch_raises_before_provider_call(
    isolated_paths: dict[str, Path],
) -> None:
    provider = ManualImportProvider(pending_root=isolated_paths["pending_root"])
    with pytest.raises(ValueError, match="character_sheet"):
        run_visual_experiment(
            batch_name="bad",
            target_ref="char_vellin",
            target_type="scene",  # mismatched
            asset_role="character_sheet",
            n=1,
            mode="manual",
            provider=provider,
            out_root=isolated_paths["out_root"],
            ontology_path=isolated_paths["ontology_path"],
            reference_dir=isolated_paths["reference_dir"],
        )


def test_n_must_be_positive(isolated_paths: dict[str, Path]) -> None:
    provider = ManualImportProvider(pending_root=isolated_paths["pending_root"])
    with pytest.raises(ValueError, match="n must be"):
        run_visual_experiment(
            batch_name="bad",
            target_ref="char_vellin",
            target_type="character",
            asset_role="character_sheet",
            n=0,
            mode="manual",
            provider=provider,
            out_root=isolated_paths["out_root"],
            ontology_path=isolated_paths["ontology_path"],
            reference_dir=isolated_paths["reference_dir"],
        )


def test_help_smoke() -> None:
    """`python -m generator.visual_experiment --help` must not crash.

    Defensive: catches module-name drift / import errors before the author
    discovers them by trying to launch a real batch.
    """
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, "-m", "generator.visual_experiment", "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--batch-name" in completed.stdout
    assert "--target" in completed.stdout
    assert "--target-type" in completed.stdout
    assert "--asset-role" in completed.stdout
    assert "--n" in completed.stdout
    assert "--mode" in completed.stdout
