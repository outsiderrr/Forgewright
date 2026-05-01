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

from generator import image_budget, image_cost_log, visual_parity_smoke
from generator.image_provider import ImageGenerationResult, ImageProvider, ImageProviderError
from generator.visual_parity_smoke import (
    _PairResult,
    main,
    run_parity_smoke,
    validate_prompts,
)


@pytest.fixture(autouse=True)
def _isolated_image_cost_log(tmp_path_factory, monkeypatch):
    """Redirect image_cost_log writes/reads to a per-test tmp file so daily
    totals don't leak between tests and tests don't pollute the repo log."""
    log = tmp_path_factory.mktemp("cost_log") / "image_cost_log.jsonl"
    monkeypatch.setenv("FORGEWRIGHT_IMAGE_COST_LOG", str(log))
    return log


@pytest.fixture(autouse=True)
def _generous_daily_budget(monkeypatch):
    """Daily ceiling defaults to $5.00; tests usually want plenty of head
    room. Individual tests override this when exercising budget exhaustion."""
    monkeypatch.setenv("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", "100.0")


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


def test_validate_prompts_rejects_non_string_prompt_id() -> None:
    """Non-string prompt_id must yield a clean ValueError, not an
    uncaught TypeError from re.fullmatch (review of T-1.5.9 #4.2)."""
    bad = {**_PROMPTS_FIXTURE[0], "prompt_id": 123}
    with pytest.raises(ValueError, match="prompt_id"):
        validate_prompts([bad])


def test_validate_prompts_rejects_empty_prompt() -> None:
    bad = {**_PROMPTS_FIXTURE[0], "prompt": "   "}
    with pytest.raises(ValueError, match="'prompt'"):
        validate_prompts([bad])


def test_validate_prompts_rejects_invalid_asset_id_stub() -> None:
    """asset_id_stub mirrors ImageAsset.asset_id pattern; CLI should reject
    early so ManualImportProvider doesn't have to (review of T-1.5.9 #4.2)."""
    bad = {**_PROMPTS_FIXTURE[0], "asset_id_stub": "../escape"}
    with pytest.raises(ValueError, match="asset_id_stub"):
        validate_prompts([bad])


def test_validate_prompts_rejects_invalid_asset_kind() -> None:
    bad = {**_PROMPTS_FIXTURE[0], "asset_kind": "concept_art"}
    with pytest.raises(ValueError, match="asset_kind"):
        validate_prompts([bad])


def test_validate_prompts_rejects_invalid_target_type() -> None:
    bad = {**_PROMPTS_FIXTURE[0], "target_type": "faction"}
    with pytest.raises(ValueError, match="target_type"):
        validate_prompts([bad])


def test_validate_prompts_rejects_invalid_asset_role() -> None:
    bad = {**_PROMPTS_FIXTURE[0], "asset_role": "concept_art"}
    with pytest.raises(ValueError, match="asset_role"):
        validate_prompts([bad])


def test_main_returns_exit_2_on_invalid_enum(tmp_path: Path, monkeypatch) -> None:
    """CLI must surface validation errors as exit 2, not a stack trace."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    bad = [{**_PROMPTS_FIXTURE[0], "asset_kind": "concept_art"}]
    prompts_path = tmp_path / "prompts.json"
    prompts_path.write_text(json.dumps(bad), encoding="utf-8")
    rc = main(["--prompts", str(prompts_path)])
    assert rc == 2


def test_happy_path_writes_report_and_cost_log(
    tmp_path: Path, _isolated_image_cost_log: Path
) -> None:
    dirs = _make_dirs(tmp_path)
    fake_api = _FakeApiProvider()

    result = run_parity_smoke(
        _PROMPTS_FIXTURE,
        output_root=dirs["output_root"],
        pending_root=dirs["pending_root"],
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

    # Cost log has exactly one line and tracks 3 api calls (review of
    # T-1.5.9 #3.1: the row uses `cost_usd`, not `total_cost_usd`, so
    # image_budget.today_total_usd() can see the spend).
    cost_lines = _isolated_image_cost_log.read_text(encoding="utf-8").splitlines()
    assert len(cost_lines) == 1
    record = json.loads(cost_lines[0])
    assert record["source"] == "visual_parity_smoke"
    assert record["mode"] == "api"
    assert record["provider_id"] == "openai_image"
    assert record["n_api_calls"] == 3
    assert record["cost_usd"] == pytest.approx(0.51)
    # Visible to image_budget.today_total_usd(): the canonical field.
    assert image_budget.today_total_usd() == pytest.approx(0.51)


def test_no_api_key_degrades_gracefully(
    tmp_path: Path, _isolated_image_cost_log: Path
) -> None:
    dirs = _make_dirs(tmp_path)

    result = run_parity_smoke(
        _PROMPTS_FIXTURE,
        output_root=dirs["output_root"],
        pending_root=dirs["pending_root"],
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
    assert not _isolated_image_cost_log.exists()
    assert result["api_total_cost_usd"] == 0.0


def test_api_call_exception_marks_partial_fail(
    tmp_path: Path, _isolated_image_cost_log: Path
) -> None:
    dirs = _make_dirs(tmp_path)
    fake_api = _FakeApiProvider(raises=ImageProviderError("rate limited"))

    # Should NOT propagate — partial fail must be captured in the report.
    result = run_parity_smoke(
        _PROMPTS_FIXTURE,
        output_root=dirs["output_root"],
        pending_root=dirs["pending_root"],
        api_provider=fake_api,
    )

    report_text = result["report_path"].read_text(encoding="utf-8")
    assert "partial fail: rate limited" in report_text
    assert "partial fail: 3" in report_text

    # No images saved, no cost charged.
    api_dir = result["run_dir"] / "api"
    assert list(api_dir.iterdir()) == []
    assert result["api_total_cost_usd"] == 0.0
    assert not _isolated_image_cost_log.exists()

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


def test_image_budget_check_called_before_api(
    tmp_path: Path, monkeypatch
) -> None:
    """With an API provider, image_budget.check must run before any API
    call (review of T-1.5.9 #3.1: budget guard mandated by /generator/CLAUDE.md
    阶段 1.5 硬规则)."""
    dirs = _make_dirs(tmp_path)
    fake_api = _FakeApiProvider()

    calls: list[dict] = []

    real_check = image_budget.check

    def _spy_check(**kwargs):
        calls.append(kwargs)
        return real_check(**kwargs)

    monkeypatch.setattr(visual_parity_smoke.image_budget, "check", _spy_check)

    run_parity_smoke(
        _PROMPTS_FIXTURE,
        output_root=dirs["output_root"],
        pending_root=dirs["pending_root"],
        api_provider=fake_api,
    )

    assert len(calls) == 1
    # 3 prompts × $0.17 estimated upper bound
    assert calls[0]["estimated_cost_usd"] == pytest.approx(0.51)
    assert calls[0]["mode"] == "api"


def test_image_budget_skipped_when_no_api_provider(
    tmp_path: Path, monkeypatch
) -> None:
    """Manual-only path doesn't bill anything, so image_budget.check should
    not be invoked — keeps the manual workflow free of API budget concerns."""
    dirs = _make_dirs(tmp_path)
    calls: list[dict] = []

    monkeypatch.setattr(
        visual_parity_smoke.image_budget,
        "check",
        lambda **kw: calls.append(kw),
    )

    run_parity_smoke(
        _PROMPTS_FIXTURE,
        output_root=dirs["output_root"],
        pending_root=dirs["pending_root"],
        api_provider=None,
    )

    assert calls == []


def test_image_budget_exceeded_blocks_api_calls(
    tmp_path: Path, monkeypatch, _isolated_image_cost_log: Path
) -> None:
    """When image_budget.check raises ImageBudgetExceeded, the API
    provider must NOT be invoked and the exception propagates so the
    operator sees a real budget failure (review of T-1.5.9 #3.1)."""
    dirs = _make_dirs(tmp_path)
    # Squeeze the daily ceiling below the smoke's $0.51 estimate.
    monkeypatch.setenv("FORGEWRIGHT_DAILY_IMAGE_BUDGET_USD", "0.20")
    fake_api = _FakeApiProvider()

    with pytest.raises(image_budget.ImageBudgetExceeded):
        run_parity_smoke(
            _PROMPTS_FIXTURE,
            output_root=dirs["output_root"],
            pending_root=dirs["pending_root"],
            api_provider=fake_api,
        )

    # Provider was never called; no cost log line written.
    assert fake_api.calls == 0
    assert not _isolated_image_cost_log.exists()


def test_cost_log_record_uses_iso_timestamp_for_today_total(
    tmp_path: Path, _isolated_image_cost_log: Path
) -> None:
    """`image_cost_log.read_today()` parses timestamps via fromisoformat;
    the parity smoke summary row must use ISO format so its spend counts
    toward today's total (review of T-1.5.9 #3.1)."""
    dirs = _make_dirs(tmp_path)
    fake_api = _FakeApiProvider()

    run_parity_smoke(
        _PROMPTS_FIXTURE[:1],
        output_root=dirs["output_root"],
        pending_root=dirs["pending_root"],
        api_provider=fake_api,
    )

    today_records = image_cost_log.read_today()
    assert len(today_records) == 1
    # cost_usd present and positive ⇒ counted by image_budget.today_total_usd.
    assert today_records[0]["cost_usd"] == pytest.approx(0.17)
