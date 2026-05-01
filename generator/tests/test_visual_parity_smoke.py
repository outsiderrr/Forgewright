"""Tests for visual_parity_smoke — pure DI, no real API calls.

Covers:
  - Happy path: fake api_provider returns image_bytes ⇒ report contains
    ok rows + cost log line written
  - No-key degradation: api_provider=None ⇒ report marks every row
    "skipped: no OPENAI_API_KEY", cost log NOT touched, exit 0
  - Partial fail: api_provider raises ImageProviderError ⇒ report marks
    "partial fail: <reason>", does not propagate, cost log NOT touched
  - validate_prompts rejects malformed input
  - main() CLI path: file-load → run → exit 0; no-key path leaves
    report with skipped rows
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator import visual_parity_smoke
from generator.image_provider import ImageGenerationResult, ImageProvider, ImageProviderError
from generator.visual_parity_smoke import (
    _PairResult,
    main,
    run_parity_smoke,
    validate_prompts,
)


_PROMPTS_FIXTURE = [
    {
        "prompt_id": "vellin_neutral",
        "prompt": (
            "## English\nA character sheet of Vellin, neutral expression, painterly."
        ),
        "asset_kind": "character_sheet",
        "target_ref": "char_vellin",
        "target_type": "character",
        "asset_role": "character_sheet",
        "asset_id_stub": "img_vellin_neutral",
    },
    {
        "prompt_id": "corvan_neutral",
        "prompt": "## English\nA character sheet of Corvan, neutral, painterly.",
        "asset_kind": "character_sheet",
        "target_ref": "char_corvan",
        "target_type": "character",
        "asset_role": "character_sheet",
        "asset_id_stub": "img_corvan_neutral",
    },
    {
        "prompt_id": "waystation_dusk",
        "prompt": "## English\nA dusk view of the Waystation of Iron Oath.",
        "asset_kind": "scene_background",
        "target_ref": "scene_waystation_of_iron_oath",
        "target_type": "scene",
        "asset_role": "scene_background",
        "asset_id_stub": "img_waystation_dusk",
    },
]


_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c63000100000005000100"
    "0d0a2db40000000049454e44ae426082"
)


class _FakeApiProvider:
    """Mirrors the OpenAIImageProvider surface; returns canned bytes."""

    def __init__(
        self,
        *,
        image_bytes: bytes = _PNG_BYTES,
        cost_usd: float = 0.17,
        raises: Exception | None = None,
    ) -> None:
        self.image_bytes = image_bytes
        self.cost_usd = cost_usd
        self.raises = raises
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        if self.raises is not None:
            raise self.raises
        return ImageGenerationResult(
            mode="api",
            asset_id_stub=kwargs["asset_id_stub"],
            image_bytes=self.image_bytes,
            prompt_package_path=None,
            cost_usd=self.cost_usd,
            raw_metadata={
                "target_ref": kwargs["target_ref"],
                "target_type": kwargs["target_type"],
                "asset_role": kwargs["asset_role"],
            },
        )

    def estimate_cost(self, *, n: int, size: tuple[int, int]) -> float:
        return n * self.cost_usd


def _make_dirs(tmp_path: Path) -> dict[str, Path]:
    return {
        "output_root": tmp_path / "experiments",
        "pending_root": tmp_path / "pending",
        "cost_log": tmp_path / "image_cost_log.jsonl",
    }


def test_validate_prompts_rejects_non_list() -> None:
    with pytest.raises(ValueError, match="non-empty JSON list"):
        validate_prompts({})


def test_validate_prompts_rejects_empty_list() -> None:
    with pytest.raises(ValueError, match="non-empty JSON list"):
        validate_prompts([])


def test_validate_prompts_rejects_missing_field() -> None:
    incomplete = {**_PROMPTS_FIXTURE[0]}
    del incomplete["asset_kind"]
    with pytest.raises(ValueError, match="missing required fields"):
        validate_prompts([incomplete])


def test_validate_prompts_rejects_unsafe_prompt_id() -> None:
    bad = {**_PROMPTS_FIXTURE[0], "prompt_id": "../escape"}
    with pytest.raises(ValueError, match="prompt_id"):
        validate_prompts([bad])


def test_happy_path_writes_report_and_cost_log(tmp_path: Path) -> None:
    dirs = _make_dirs(tmp_path)
    fake_api = _FakeApiProvider()

    result = run_parity_smoke(
        _PROMPTS_FIXTURE,
        output_root=dirs["output_root"],
        pending_root=dirs["pending_root"],
        cost_log_path=dirs["cost_log"],
        api_provider=fake_api,
    )

    # All 3 calls happened.
    assert fake_api.calls == 3
    assert result["api_total_cost_usd"] == pytest.approx(0.51)

    # Report exists; rows exist; api ok status appears.
    report_text = result["report_path"].read_text(encoding="utf-8")
    assert "parity_report.md" in report_text
    for entry in _PROMPTS_FIXTURE:
        assert entry["prompt_id"] in report_text
    assert "**api status**: ok" in report_text
    assert "api ok: 3" in report_text

    # API images were saved as PNG bytes.
    api_dir = result["run_dir"] / "api"
    assert (api_dir / "vellin_neutral.png").read_bytes() == _PNG_BYTES

    # Manual prompt packages were materialized in <pending_root>/parity/.
    manual_dir = dirs["pending_root"] / "parity" / "img_vellin_neutral"
    assert (manual_dir / "prompt.md").is_file()
    assert (manual_dir / "meta.json").is_file()

    # Cost log has exactly one line and tracks 3 api calls.
    cost_lines = dirs["cost_log"].read_text(encoding="utf-8").splitlines()
    assert len(cost_lines) == 1
    record = json.loads(cost_lines[0])
    assert record["source"] == "visual_parity_smoke"
    assert record["n_api_calls"] == 3
    assert record["total_cost_usd"] == pytest.approx(0.51)


def test_no_api_key_degrades_gracefully(tmp_path: Path) -> None:
    dirs = _make_dirs(tmp_path)

    result = run_parity_smoke(
        _PROMPTS_FIXTURE,
        output_root=dirs["output_root"],
        pending_root=dirs["pending_root"],
        cost_log_path=dirs["cost_log"],
        api_provider=None,
    )

    report_text = result["report_path"].read_text(encoding="utf-8")
    assert "skipped: no OPENAI_API_KEY" in report_text
    assert "api ok: 0" in report_text
    assert f"skipped: 3" in report_text

    # No API images.
    api_dir = result["run_dir"] / "api"
    assert list(api_dir.iterdir()) == []

    # Manual half ran for all 3 (FS only).
    for entry in _PROMPTS_FIXTURE:
        manual_dir = dirs["pending_root"] / "parity" / entry["asset_id_stub"]
        assert (manual_dir / "prompt.md").is_file()

    # Cost log untouched.
    assert not dirs["cost_log"].exists()
    assert result["api_total_cost_usd"] == 0.0


def test_api_call_exception_marks_partial_fail(tmp_path: Path) -> None:
    dirs = _make_dirs(tmp_path)
    fake_api = _FakeApiProvider(raises=ImageProviderError("rate limited"))

    # Should NOT propagate — partial fail must be captured in the report.
    result = run_parity_smoke(
        _PROMPTS_FIXTURE,
        output_root=dirs["output_root"],
        pending_root=dirs["pending_root"],
        cost_log_path=dirs["cost_log"],
        api_provider=fake_api,
    )

    report_text = result["report_path"].read_text(encoding="utf-8")
    assert "partial fail: rate limited" in report_text
    assert "partial fail: 3" in report_text

    # No images saved, no cost charged.
    api_dir = result["run_dir"] / "api"
    assert list(api_dir.iterdir()) == []
    assert result["api_total_cost_usd"] == 0.0
    assert not dirs["cost_log"].exists()

    # All 3 attempted (smoke shouldn't short-circuit on first failure).
    assert fake_api.calls == 3


def test_api_provider_returning_none_image_bytes_is_partial_fail(tmp_path: Path) -> None:
    """A misbehaving provider that returns mode="api" but image_bytes=None
    must NOT crash the smoke — the report records partial fail."""
    dirs = _make_dirs(tmp_path)

    class _NoBytesProvider:
        def generate(self, **kwargs):
            return ImageGenerationResult(
                mode="api",
                asset_id_stub=kwargs["asset_id_stub"],
                image_bytes=None,
                prompt_package_path=None,
                cost_usd=0.17,
                raw_metadata={},
            )

        def estimate_cost(self, *, n, size):
            return 0.17 * n

    result = run_parity_smoke(
        _PROMPTS_FIXTURE[:1],
        output_root=dirs["output_root"],
        pending_root=dirs["pending_root"],
        cost_log_path=dirs["cost_log"],
        api_provider=_NoBytesProvider(),
    )

    text = result["report_path"].read_text(encoding="utf-8")
    assert "partial fail: API result had no image_bytes" in text


def test_n_clamps_via_main_cli(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    prompts_path = tmp_path / "prompts.json"
    prompts_path.write_text(json.dumps(_PROMPTS_FIXTURE), encoding="utf-8")

    rc = main(["--prompts", str(prompts_path), "--n", "2"])

    assert rc == 0
    # Find the run dir under the default experiments root.
    runs = list((tmp_path / "generator" / "experiments").glob("parity_smoke_*"))
    assert len(runs) == 1
    report_text = (runs[0] / "parity_report.md").read_text(encoding="utf-8")
    # Only 2 prompt_ids should appear in pair sections; the 3rd (waystation)
    # was sliced off.
    assert "vellin_neutral" in report_text
    assert "corvan_neutral" in report_text
    assert "waystation_dusk" not in report_text


def test_main_rejects_missing_prompts_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    rc = main(["--prompts", str(tmp_path / "nope.json")])
    assert rc == 2


def test_main_rejects_invalid_n(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    prompts_path = tmp_path / "prompts.json"
    prompts_path.write_text(json.dumps(_PROMPTS_FIXTURE), encoding="utf-8")
    rc = main(["--prompts", str(prompts_path), "--n", "0"])
    assert rc == 2


def test_main_rejects_malformed_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    prompts_path = tmp_path / "prompts.json"
    prompts_path.write_text("[{not json}]", encoding="utf-8")
    rc = main(["--prompts", str(prompts_path)])
    assert rc == 2


def test_pair_result_dataclass_carries_expected_fields() -> None:
    pr = _PairResult(
        prompt_id="x",
        asset_kind="character_sheet",
        manual_path=Path("/tmp/manual"),
        api_image_path=Path("/tmp/api.png"),
        api_status="ok",
        api_cost_usd=0.17,
    )
    assert pr.api_status == "ok"
    assert pr.api_cost_usd == pytest.approx(0.17)


def test_fake_api_provider_satisfies_image_provider_protocol() -> None:
    fake = _FakeApiProvider()
    assert isinstance(fake, ImageProvider)
