"""Tests for visual_metrics (T-1.5.8).

All counts must come from the structured logs (results.jsonl /
import_log.jsonl / visual_review_log.jsonl / image_cost_log.jsonl) — no
directory scanning. The tests fabricate the four logs in tmp_path,
override the env vars used by import_log + image_cost_log, and assert
the returned dict.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.visual_metrics import compute_visual_metrics


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


@pytest.fixture
def metrics_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Create a synthetic batch dir with realistic results.jsonl + reviews,
    plus a sibling import_log + image_cost_log carrying matching rows.

    Layout per the data-source map in the module docstring of
    visual_metrics: import_log + cost_log are env-overridable global files;
    results + visual_review live inside the batch dir.
    """
    batch_dir = tmp_path / "20260502T120000Z_t158_metrics"
    batch_dir.mkdir(parents=True)

    # 5 successful manual results (5 prompt packages)
    results: list[dict] = []
    for i, stub in enumerate(
        [
            "img_vellin_a",
            "img_vellin_b",
            "img_vellin_c",
            "img_vellin_d",
            "img_vellin_e",
        ]
    ):
        results.append(
            {
                "iter_id": i,
                "batch_name": "t158_metrics",
                "target_ref": "char_vellin",
                "target_type": "character",
                "asset_role": "character_sheet",
                "mode": "manual",
                "result": {
                    "success": True,
                    "asset_id_stub": stub,
                    "prompt_package_path": f"content/visuals/_pending/{stub}",
                    "image_bytes_size": 0,
                    "failure_reason": None,
                    "cost_usd": 0.0,
                    "raw_metadata": {},
                },
                "generated_at": "2026-05-02T00:00:00+00:00",
            }
        )
    _write_jsonl(batch_dir / "results.jsonl", results)

    # Override the env-vars before any visual_metrics read happens.
    import_log_path = tmp_path / "import_log.jsonl"
    cost_log_path = tmp_path / "image_cost_log.jsonl"
    monkeypatch.setenv("FORGEWRIGHT_IMPORT_LOG", str(import_log_path))
    monkeypatch.setenv("FORGEWRIGHT_IMAGE_COST_LOG", str(cost_log_path))

    # 3 imported, 2 rejected (PNG missing + alpha violation).
    _write_jsonl(
        import_log_path,
        [
            {
                "asset_id_stub": "img_vellin_a",
                "batch_name": "t158_metrics",
                "status": "imported",
                "rejected_reason": None,
                "validation_errors": [],
            },
            {
                "asset_id_stub": "img_vellin_b",
                "batch_name": "t158_metrics",
                "status": "imported",
                "rejected_reason": None,
                "validation_errors": [],
            },
            {
                "asset_id_stub": "img_vellin_c",
                "batch_name": "t158_metrics",
                "status": "imported",
                "rejected_reason": None,
                "validation_errors": [],
            },
            {
                "asset_id_stub": "img_vellin_d",
                "batch_name": "t158_metrics",
                "status": "rejected",
                "rejected_reason": "PNG missing",
                "validation_errors": [],
            },
            {
                "asset_id_stub": "img_vellin_e",
                "batch_name": "t158_metrics",
                "status": "rejected",
                "rejected_reason": "image_validator: has_alpha mismatch",
                "validation_errors": ["alpha_mismatch"],
            },
            # A row from another batch — must NOT count.
            {
                "asset_id_stub": "img_other",
                "batch_name": "another_batch",
                "status": "rejected",
                "rejected_reason": "noise",
                "validation_errors": [],
            },
        ],
    )

    # cost log: 5 manual rows ($0) + 1 unrelated batch row ($0.04).
    _write_jsonl(
        cost_log_path,
        [
            {
                "timestamp": "2026-05-02T00:00:00+00:00",
                "mode": "manual",
                "provider_id": "manual_import",
                "asset_kind": "character_sheet",
                "asset_id_stub": stub,
                "batch_name": "t158_metrics",
                "n": 1,
                "size_w": 1024,
                "size_h": 1024,
                "input_tokens": None,
                "cost_usd": 0.0,
            }
            for stub in [
                "img_vellin_a",
                "img_vellin_b",
                "img_vellin_c",
                "img_vellin_d",
                "img_vellin_e",
            ]
        ]
        + [
            {
                "timestamp": "2026-05-02T00:00:00+00:00",
                "mode": "api",
                "provider_id": "openai_image_gpt-image-1",
                "asset_kind": "character_sheet",
                "asset_id_stub": "img_other",
                "batch_name": "another_batch",
                "n": 1,
                "size_w": 1024,
                "size_h": 1024,
                "input_tokens": None,
                "cost_usd": 0.04,
            }
        ],
    )

    # author review log: A, A, R("face inconsistent")
    _write_jsonl(
        batch_dir / "visual_review_log.jsonl",
        [
            {
                "asset_id": "img_vellin_a",
                "accepted": True,
                "reason": None,
                "reviewed_at": "2026-05-02T01:00:00+00:00",
                "mechanical_check_passed": True,
            },
            {
                "asset_id": "img_vellin_b",
                "accepted": True,
                "reason": None,
                "reviewed_at": "2026-05-02T01:00:00+00:00",
                "mechanical_check_passed": True,
            },
            {
                "asset_id": "img_vellin_c",
                "accepted": False,
                "reason": "face inconsistent",
                "reviewed_at": "2026-05-02T01:00:00+00:00",
                "mechanical_check_passed": True,
            },
        ],
    )

    return {"batch_dir": batch_dir}


def test_full_metrics_dict(metrics_setup: dict) -> None:
    m = compute_visual_metrics(metrics_setup["batch_dir"])

    assert m["batch_name"] == "t158_metrics"
    assert m["total_assets_attempted"] == 5
    assert m["total_pending_packages_generated"] == 5
    assert m["total_imported"] == 3
    assert m["total_rejected"] == 2
    assert m["mechanical_check_pass_rate"] == pytest.approx(3 / 5)

    # rejected_reason_top_5 surfaces both the human reason and the
    # validation_error code (visual_metrics merges them so a coarse-grained
    # author can still see the offending error code at a glance).
    reasons = dict(m["rejected_reason_top_5"])
    assert reasons["PNG missing"] == 1
    assert reasons["image_validator: has_alpha mismatch"] == 1
    assert reasons["validation_error:alpha_mismatch"] == 1

    # acceptance_rate denominator = imported, numerator = accepted.
    assert m["acceptance_rate"] == pytest.approx(2 / 3)
    assert m["reviewed_count"] == 3

    reject_reasons = dict(m["reject_reason_top_5"])
    assert reject_reasons["face inconsistent"] == 1

    # cost is 0 for the manual batch; unrelated batch row must not leak in.
    assert m["total_cost_usd"] == pytest.approx(0.0)

    # parity_smoke_status forward-compat slot for T-1.5.9.
    assert m["parity_smoke_status"] == "not_ran"


def test_no_logs_yields_none_rates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A freshly-generated batch with no import_log / no review yet must
    return None for the rate fields — not 0.0 (which would be misleading)."""
    monkeypatch.setenv("FORGEWRIGHT_IMPORT_LOG", str(tmp_path / "missing.jsonl"))
    monkeypatch.setenv(
        "FORGEWRIGHT_IMAGE_COST_LOG", str(tmp_path / "missing_cost.jsonl")
    )
    batch_dir = tmp_path / "20260502T120000Z_fresh"
    batch_dir.mkdir(parents=True)
    _write_jsonl(
        batch_dir / "results.jsonl",
        [
            {
                "iter_id": 0,
                "batch_name": "fresh",
                "target_ref": "char_vellin",
                "target_type": "character",
                "asset_role": "character_sheet",
                "mode": "manual",
                "result": {
                    "success": True,
                    "asset_id_stub": "img_x",
                    "prompt_package_path": "p",
                    "image_bytes_size": 0,
                    "failure_reason": None,
                    "cost_usd": 0.0,
                    "raw_metadata": {},
                },
                "generated_at": "2026-05-02T00:00:00+00:00",
            }
        ],
    )

    m = compute_visual_metrics(batch_dir)
    assert m["total_assets_attempted"] == 1
    assert m["total_imported"] == 0
    assert m["total_rejected"] == 0
    assert m["mechanical_check_pass_rate"] is None
    assert m["acceptance_rate"] is None
    assert m["total_cost_usd"] == 0.0


def test_unbatched_import_rows_are_correlated_via_results_stubs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """review of T-1.5.8 #3.2: when the author runs
    `image_import --all-pending` (no --batch-name), the import_log rows
    carry `batch_name: null`. metrics must still associate them to this
    batch via asset_id_stub overlap from results.jsonl. Rows belonging
    to a different *named* batch must NOT bleed in.
    """
    batch_dir = tmp_path / "20260502T120000Z_unbatched"
    batch_dir.mkdir(parents=True)
    _write_jsonl(
        batch_dir / "results.jsonl",
        [
            {
                "iter_id": i,
                "batch_name": "unbatched",
                "target_ref": "char_vellin",
                "target_type": "character",
                "asset_role": "character_sheet",
                "mode": "manual",
                "result": {
                    "success": True,
                    "asset_id_stub": stub,
                    "prompt_package_path": f"p/{stub}",
                    "image_bytes_size": 0,
                    "failure_reason": None,
                    "cost_usd": 0.0,
                    "raw_metadata": {},
                },
                "generated_at": "2026-05-02T00:00:00+00:00",
            }
            for i, stub in enumerate(["img_a", "img_b", "img_c"])
        ],
    )

    import_log_path = tmp_path / "import_log.jsonl"
    monkeypatch.setenv("FORGEWRIGHT_IMPORT_LOG", str(import_log_path))
    monkeypatch.setenv("FORGEWRIGHT_IMAGE_COST_LOG", str(tmp_path / "no_cost.jsonl"))
    _write_jsonl(
        import_log_path,
        [
            # Rows produced by `image_import --all-pending` — no batch_name.
            {
                "asset_id_stub": "img_a",
                "batch_name": None,
                "status": "imported",
                "rejected_reason": None,
                "validation_errors": [],
            },
            {
                "asset_id_stub": "img_b",
                "batch_name": None,
                "status": "imported",
                "rejected_reason": None,
                "validation_errors": [],
            },
            {
                "asset_id_stub": "img_c",
                "batch_name": None,
                "status": "rejected",
                "rejected_reason": "PNG missing",
                "validation_errors": [],
            },
            # Row from a *different* named batch — must not be associated
            # even though its stub doesn't appear in our results either.
            {
                "asset_id_stub": "img_other",
                "batch_name": "another_batch",
                "status": "imported",
                "rejected_reason": None,
                "validation_errors": [],
            },
            # Bare row with a stub we don't own — must not be associated.
            {
                "asset_id_stub": "img_orphan",
                "batch_name": None,
                "status": "imported",
                "rejected_reason": None,
                "validation_errors": [],
            },
        ],
    )
    _write_jsonl(
        batch_dir / "visual_review_log.jsonl",
        [
            {
                "asset_id": "img_a",
                "accepted": True,
                "reason": None,
                "reviewed_at": "2026-05-02T01:00:00+00:00",
                "mechanical_check_passed": True,
            },
            {
                "asset_id": "img_b",
                "accepted": False,
                "reason": "noise",
                "reviewed_at": "2026-05-02T01:00:00+00:00",
                "mechanical_check_passed": True,
            },
        ],
    )

    m = compute_visual_metrics(batch_dir)
    assert m["total_imported"] == 2  # img_a + img_b; orphan / another_batch excluded
    assert m["total_rejected"] == 1  # img_c
    assert m["mechanical_check_pass_rate"] == pytest.approx(2 / 3)
    assert m["acceptance_rate"] == pytest.approx(1 / 2)


def test_help_smoke() -> None:
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, "-m", "generator.visual_metrics", "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--batch-dir" in completed.stdout
