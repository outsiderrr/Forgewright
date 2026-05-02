"""Tests for visual_review_cli (T-1.5.8).

Cover the contracts the CLI must honour:

  1. Walk results.jsonl × manifest, prompt A/R/S, and write a resumable
     visual_review_log.jsonl with the expected schema fields.
  2. Skip imports that aren't in the manifest yet (mechanical not run).
  3. `python -m generator.visual_review_cli --help` returns 0 (defends
     against a future module-name drift, per spec).

The viewer callback is injected so the test can run on any platform — we
never call macOS `open`.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from generator.manifest import Manifest, save_manifest
from generator.models._generated.image_asset import ImageAsset
from generator.visual_review_cli import run_visual_review


def _make_asset(
    asset_id: str,
    *,
    target_ref: str = "char_vellin",
    target_type: str = "character",
    asset_role: str = "character_sheet",
    asset_kind: str = "character_sheet",
) -> ImageAsset:
    return ImageAsset(
        schema_version="0.2.0",
        asset_id=asset_id,
        asset_kind=asset_kind,
        target_ref=target_ref,
        target_type=target_type,
        asset_role=asset_role,
        character_ref=target_ref if target_type == "character" else None,
        location_ref=target_ref if target_type != "character" else None,
        source_mode="manual",
        format="png",
        width=1024,
        height=1024,
        file_size_bytes=1024,
        has_alpha=(asset_role == "character_sheet"),
        file_path=f"content/visuals/vellin/{asset_id}.png",
        prompt_hash="a" * 64,
        created_at="2026-05-02T00:00:00+00:00",
    )


def _envelope(asset_id: str, *, success: bool = True, target_ref: str = "char_vellin") -> dict:
    return {
        "iter_id": 0,
        "batch_name": "t158_review",
        "target_ref": target_ref,
        "target_type": "character",
        "asset_role": "character_sheet",
        "mode": "manual",
        "result": {
            "success": success,
            "asset_id_stub": asset_id,
            "prompt_package_path": "content/visuals/_pending/" + asset_id,
            "image_bytes_size": 0,
            "failure_reason": None if success else "provider_error",
            "cost_usd": 0.0,
            "raw_metadata": {"variant_label": "neutral_torso_up"},
        },
        "generated_at": "2026-05-02T00:00:00+00:00",
    }


@pytest.fixture
def review_setup(tmp_path: Path) -> dict[str, Path]:
    """Build a synthetic batch dir + manifest with two imported assets and
    one not-yet-imported asset."""
    batch_dir = tmp_path / "20260502T120000Z_t158_review"
    batch_dir.mkdir(parents=True)
    results = [
        _envelope("img_vellin_a"),
        _envelope("img_vellin_b"),
        _envelope("img_vellin_c"),  # not in manifest → must be skipped
    ]
    (batch_dir / "results.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
        encoding="utf-8",
    )

    manifest_path = tmp_path / "manifest.json"
    manifest = Manifest(
        schema_version="0.2.0",
        assets={
            "img_vellin_a": _make_asset("img_vellin_a"),
            "img_vellin_b": _make_asset("img_vellin_b"),
        },
    )
    save_manifest(manifest, manifest_path)

    return {"batch_dir": batch_dir, "manifest_path": manifest_path}


def test_accept_then_reject_writes_two_decisions(review_setup: dict[str, Path]) -> None:
    inputs = iter(["A", "R", "missing reference image quality"])
    viewed: list[str] = []

    written = run_visual_review(
        review_setup["batch_dir"],
        manifest_path=review_setup["manifest_path"],
        viewer=lambda fp: viewed.append(fp),
        input_fn=lambda prompt: next(inputs),
        output=io.StringIO(),
    )

    assert written == 2
    log = (review_setup["batch_dir"] / "visual_review_log.jsonl").read_text()
    rows = [json.loads(line) for line in log.splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["asset_id"] == "img_vellin_a"
    assert rows[0]["accepted"] is True
    assert rows[0]["mechanical_check_passed"] is True
    assert rows[0]["reason"] is None
    assert rows[1]["asset_id"] == "img_vellin_b"
    assert rows[1]["accepted"] is False
    assert rows[1]["reason"] == "missing reference image quality"
    # The viewer must be called for every reviewed asset.
    assert viewed == [
        "content/visuals/vellin/img_vellin_a.png",
        "content/visuals/vellin/img_vellin_b.png",
    ]


def test_skip_writes_no_record(review_setup: dict[str, Path]) -> None:
    inputs = iter(["S", "S"])  # skip both imported assets
    written = run_visual_review(
        review_setup["batch_dir"],
        manifest_path=review_setup["manifest_path"],
        viewer=lambda _: None,
        input_fn=lambda prompt: next(inputs),
        output=io.StringIO(),
    )
    assert written == 0
    assert not (review_setup["batch_dir"] / "visual_review_log.jsonl").exists()


def test_resumable_skips_already_reviewed(review_setup: dict[str, Path]) -> None:
    log_path = review_setup["batch_dir"] / "visual_review_log.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "asset_id": "img_vellin_a",
                "accepted": True,
                "reason": None,
                "reviewed_at": "2026-05-02T00:00:00+00:00",
                "mechanical_check_passed": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    inputs = iter(["A"])
    written = run_visual_review(
        review_setup["batch_dir"],
        manifest_path=review_setup["manifest_path"],
        viewer=lambda _: None,
        input_fn=lambda prompt: next(inputs),
        output=io.StringIO(),
    )
    assert written == 1
    rows = [
        json.loads(line) for line in log_path.read_text().splitlines() if line.strip()
    ]
    assert {r["asset_id"] for r in rows} == {"img_vellin_a", "img_vellin_b"}


def test_unimported_asset_is_skipped(review_setup: dict[str, Path]) -> None:
    """img_vellin_c is in results.jsonl but not in the manifest — the CLI
    must surface it in the header but not prompt the author for it."""
    inputs = iter(["A", "A"])  # only the two imported assets

    out = io.StringIO()
    written = run_visual_review(
        review_setup["batch_dir"],
        manifest_path=review_setup["manifest_path"],
        viewer=lambda _: None,
        input_fn=lambda prompt: next(inputs),
        output=out,
    )
    assert written == 2
    text = out.getvalue()
    assert "awaiting import:     1" in text
    assert "pending review:      2" in text


def test_help_smoke() -> None:
    """`python -m generator.visual_review_cli --help` must succeed.

    Defends against module-name drift; STAGE_1.5_TASKS.md T-1.5.8 §2
    explicitly demands this test (GPT-5.5 L2 critique 4.10 — the module
    used to be named `visual_review`).
    """
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, "-m", "generator.visual_review_cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--batch-dir" in completed.stdout
    assert "--web" in completed.stdout
