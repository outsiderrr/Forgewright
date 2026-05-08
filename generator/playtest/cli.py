"""Playtest CLI entry point (T-3.4 / ADR-022).

Two execution modes:

  * **calibration** (``--calibration``): 1 scene × 1 persona × 5 paths
    smoke run. Writes ``calibration_report.md`` with avg calls/path,
    cost/path, seconds/path, plus a recommended ``max_paths`` derived
    from the requested cost / wall-clock budgets. F9 mandatory.
  * **full batch** (default): N personas × M paths/persona over the
    requested scene. Writes ``worst_paths.jsonl`` (path-level rank,
    F21) + ``worst_scenes.md`` / ``worst_scenes.json`` (scene-level
    aggregate, F21) + ``run_manifest.json`` (replay metadata, F20).

Three-way budget guard (F9): every full batch enforces
``--max-cost-usd``, ``--max-calls``, and ``--max-wall-clock-min``;
any single trip aborts the batch, flushes whatever paths completed,
and exits with a non-zero status.

Cost log redirection: by default, every LLM call's cost record lands
in ``generator/playtest_cost_log.jsonl`` (independent from
``cost_log.jsonl``). Override with ``--cost-log`` for tests.

Module boundary (T-3.4): does not modify ``budget.py``; the
``FORGEWRIGHT_COST_LOG`` env var hook is the existing ADR-012
mechanism for redirecting cost log output without patching the
budget module.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from generator import budget
from generator.budget import BudgetExceeded
from generator.llm_provider import LLMProvider, ProviderError
from generator.playtest import judge as judge_mod
from generator.playtest import runner as runner_mod
from generator.playtest.judge import (
    JUDGE_RUBRIC_VERSION,
    SceneAggregate,
    aggregate_scene_summary,
    rank_paths_worst_first,
    render_worst_scenes_json,
    render_worst_scenes_markdown,
)
from generator.playtest.personas import (
    Persona,
    hash_personas,
    load_all_personas,
    load_persona,
)
from generator.playtest.runner import (
    PlaytestPath,
    path_to_jsonl_dict,
    run_path,
)

_LOG = logging.getLogger(__name__)


EXPERIMENTS_ROOT = Path(__file__).resolve().parent.parent / "experiments"
PLAYTEST_COST_LOG_PATH = (
    Path(__file__).resolve().parent.parent / "playtest_cost_log.jsonl"
)


# ---------------------------------------------------------------------------
# Three-way guard
# ---------------------------------------------------------------------------


class GuardTripped(Exception):
    """Raised when any of the three batch guards trips.

    Carries the ``which`` field (``cost``/``calls``/``wall_clock``) so
    the CLI can surface a precise reason in the partial-flush log.
    """

    def __init__(self, which: str, message: str) -> None:
        super().__init__(message)
        self.which = which


@dataclasses.dataclass
class GuardState:
    """Live counters consulted before/after every LLM call.

    The CLI installs this as the ``CallObserver`` plumbed through the
    runner and judge layers. ``check()`` is called between paths so a
    trip can interrupt the batch cleanly without aborting an in-flight
    LLM call (which would leave a budget reservation unreconciled).
    """

    max_cost_usd: float
    max_calls: int
    max_wall_clock_min: float
    started_monotonic: float
    total_calls: int = 0
    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    last_trip_reason: str | None = None

    def observe(self, cost: float, input_tokens: int, output_tokens: int) -> None:
        self.total_calls += 1
        self.total_cost += cost
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def elapsed_min(self) -> float:
        return (time.monotonic() - self.started_monotonic) / 60.0

    def check(self) -> None:
        if self.total_cost >= self.max_cost_usd:
            self.last_trip_reason = (
                f"cost: ${self.total_cost:.4f} >= cap ${self.max_cost_usd:.4f}"
            )
            raise GuardTripped("cost", self.last_trip_reason)
        if self.total_calls >= self.max_calls:
            self.last_trip_reason = (
                f"calls: {self.total_calls} >= cap {self.max_calls}"
            )
            raise GuardTripped("calls", self.last_trip_reason)
        if self.elapsed_min() >= self.max_wall_clock_min:
            self.last_trip_reason = (
                f"wall_clock: {self.elapsed_min():.2f} min >= "
                f"cap {self.max_wall_clock_min:.2f} min"
            )
            raise GuardTripped("wall_clock", self.last_trip_reason)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_prompt_template_hash() -> str:
    """SHA-256 of the runner+judge prompt-shaping constants.

    Captures any logic change that affects what the LLMs see — system
    prompts, severity definitions, dimension keys. The actual user
    prompt is rendered per-call from these constants + scene/persona
    inputs, so this hash is the meaningful "template" identity for
    replay.
    """
    pieces = [
        runner_mod._PERSONA_SYSTEM_PROMPT,
        judge_mod._JUDGE_SYSTEM_PROMPT,
        json.dumps(judge_mod._SEVERITY_DEFINITIONS, sort_keys=True),
        json.dumps(judge_mod._DIMENSION_KEYS),
        JUDGE_RUBRIC_VERSION,
    ]
    payload = "\n--\n".join(pieces).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def next_playtest_dir(root: Path) -> Path:
    """Return the next ``playtest_NNN`` directory under ``root``.

    Numbering starts at 001 and counts up to whatever's already present
    (skipping non-matching siblings cleanly). Creates the directory.
    """
    root.mkdir(parents=True, exist_ok=True)
    existing = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if not name.startswith("playtest_"):
            continue
        suffix = name[len("playtest_"):]
        if suffix.isdigit():
            existing.append(int(suffix))
    next_n = max(existing) + 1 if existing else 1
    new_dir = root / f"playtest_{next_n:03d}"
    new_dir.mkdir(parents=True, exist_ok=False)
    return new_dir


def _select_personas(
    selector: str | None,
    *,
    root: Path | None = None,
) -> list[Persona]:
    """Resolve the ``--personas`` flag.

    ``None`` or ``"all"`` → every persona in the bundled directory.
    Comma-separated list → load each by id; raise on any unknown id so
    a typo fails fast at batch start.
    """
    if not selector or selector == "all":
        personas = load_all_personas(root=root)
        if not personas:
            raise FileNotFoundError(
                f"no persona files in {root or 'bundled directory'}"
            )
        return personas
    ids = [s.strip() for s in selector.split(",") if s.strip()]
    return [load_persona(pid, root=root) for pid in ids]


def _load_scene(scene_path: Path) -> dict:
    """Load a dialogue graph JSON from disk.

    Surface-level validation only; topology / schema validation is the
    /validator/ module's job and a malformed scene at this layer would
    blow up the runner mid-path with a confusing error. We catch the
    obvious case (missing entry / nodes) early.
    """
    if not scene_path.exists():
        raise FileNotFoundError(f"scene file not found: {scene_path}")
    data = json.loads(scene_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"scene file {scene_path}: top-level must be object")
    if not isinstance(data.get("nodes"), dict):
        raise ValueError(f"scene file {scene_path}: missing 'nodes' object")
    if not isinstance(data.get("entry_node_id"), str):
        raise ValueError(f"scene file {scene_path}: missing 'entry_node_id' string")
    return data


def _ensure_cost_log_env(cost_log_path: Path) -> None:
    """Point the cost log writer at the playtest log file.

    Sets ``FORGEWRIGHT_COST_LOG`` so every ``budget.check_and_charge``
    call from this point on lands in ``cost_log_path`` without
    modifying ``budget.py``. Tests pass ``--cost-log`` to redirect to
    a tmp_path; production uses :data:`PLAYTEST_COST_LOG_PATH`.
    """
    cost_log_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["FORGEWRIGHT_COST_LOG"] = str(cost_log_path)


# ---------------------------------------------------------------------------
# Batch loop
# ---------------------------------------------------------------------------


def _run_persona_paths_sequential(
    *,
    scene: dict,
    persona: Persona,
    n_paths: int,
    provider: LLMProvider,
    initial_state: dict | None,
    guard: GuardState,
    progress_label: str,
    paths_out: list[PlaytestPath],
) -> None:
    """Run ``n_paths`` for one persona one at a time, checking the
    three-way guard between each path.

    Sequential by design (B-review 3.2): per-path ``guard.check()``
    means abort fires within ~1 path of crossing a cap. Paths are
    appended to ``paths_out`` AS THEY COMPLETE so the caller can
    inspect what made it through after a guard / budget trip
    re-raises out of this function. Per-path :class:`ProviderError`
    is captured by the runner as ``path.error`` so a single bad
    transport does not abort the batch.

    Concurrent execution via ``run_paths_async`` is still available
    in the runner module for T-3.5's RateLimitedProvider integration;
    the CLI explicitly opts for sequential here so the guard signal
    can land between paths.
    """

    def _observer(cost: float, input_tokens: int, output_tokens: int) -> None:
        guard.observe(cost, input_tokens, output_tokens)

    print(f"  [paths] {progress_label} running {n_paths} paths …", flush=True)
    for path_idx in range(n_paths):
        guard.check()  # before each path — bound abort lag at ≤ 1 path
        path = run_path(
            scene,
            persona,
            provider=provider,
            initial_state=initial_state,
            observer=_observer,
            path_id=f"{persona.persona_id}-{path_idx:03d}-{uuid.uuid4().hex[:6]}",
        )
        paths_out.append(path)
        # Re-check after the path's calls landed so the next path
        # never starts past a cap.
        guard.check()


def _judge_paths(
    *,
    scene: dict,
    persona_lookup: dict[str, Persona],
    paths: list[PlaytestPath],
    provider: LLMProvider,
    guard: GuardState,
) -> list[PlaytestPath]:
    """Score every path with the judge layer; mutates paths in place.

    Per-path :class:`ProviderError` is captured on the path (judge_score
    stays None, error appended) so the rest of the batch finishes.
    :class:`BudgetExceeded` and :class:`GuardTripped` propagate.
    """

    def _observer(cost: float, in_tok: int, out_tok: int) -> None:
        guard.observe(cost, in_tok, out_tok)

    for idx, path in enumerate(paths, start=1):
        # Skip paths that already errored out in the runner — judging a
        # path with no steps and an error message would just burn
        # another LLM call to confirm "yes this is bad".
        if path.error and not path.steps:
            continue
        persona = persona_lookup.get(path.persona_id)
        if persona is None:
            path.error = (
                (path.error + " | " if path.error else "")
                + f"persona_id={path.persona_id!r} not in lookup"
            )
            continue
        try:
            judge_mod.judge_path(
                path,
                scene=scene,
                persona=persona,
                provider=provider,
                observer=_observer,
            )
        except ProviderError as exc:
            path.error = (path.error + " | " if path.error else "") + (
                f"judge ProviderError: {exc}"
            )
            _LOG.warning("judge failed for path %s: %s", path.path_id, exc)
        guard.check()
        if idx % 10 == 0:
            print(
                f"    [judge] judged {idx}/{len(paths)} paths "
                f"(running cost ${guard.total_cost:.4f})",
                flush=True,
            )
    return paths


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class CalibrationData:
    """Result of a 1×1×5 calibration run.

    Stored verbatim in ``run_manifest.json`` so a replay session can
    confirm the per-path ceilings the actual batch ran under.
    """

    n_paths: int
    avg_calls_per_path: float
    avg_input_tokens_per_path: float
    avg_output_tokens_per_path: float
    avg_cost_per_path: float
    avg_seconds_per_path: float
    started_at: str
    completed_at: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


CALIBRATION_PATHS = 5


def run_calibration(
    *,
    scene: dict,
    persona: Persona,
    provider: LLMProvider,
    output_dir: Path,
    initial_state: dict | None = None,
    guard: GuardState | None = None,
) -> CalibrationData:
    """Run ``CALIBRATION_PATHS`` paths for ``persona`` on ``scene``.

    Computes per-path averages and writes ``calibration_report.md``
    to ``output_dir``. The guard is reused if provided so the
    calibration phase counts toward the same overall ceilings as the
    full batch — calibration ought to be cheap (≤ $0.10) but treating
    it as free would defeat the safety net.
    """
    started_at = _utc_now_iso()
    g = guard or GuardState(
        max_cost_usd=10.0,
        max_calls=10_000,
        max_wall_clock_min=60.0,
        started_monotonic=time.monotonic(),
    )

    # Snapshot guard counters before the calibration so per-path
    # averages cover BOTH the persona-decision calls and the judge
    # calls (B-review 3.1 fix; F9 spec: "每决策节点 + judge"). Using
    # the delta also lets the same guard be reused for the full batch
    # without aliasing the calibration averages.
    before_calls = g.total_calls
    before_cost = g.total_cost
    before_input_tokens = g.total_input_tokens
    before_output_tokens = g.total_output_tokens

    paths: list[PlaytestPath] = []
    try:
        _run_persona_paths_sequential(
            scene=scene,
            persona=persona,
            n_paths=CALIBRATION_PATHS,
            provider=provider,
            initial_state=initial_state,
            guard=g,
            progress_label=f"calibration[{persona.persona_id}]",
            paths_out=paths,
        )
    except (BudgetExceeded, GuardTripped) as exc:
        _LOG.warning("calibration aborted mid-runner: %s", exc)

    # Judge whatever paths the runner produced — F9 demands judge
    # calls land in the calibration accounting (B-review 3.1).
    if paths:
        try:
            _judge_paths(
                scene=scene,
                persona_lookup={persona.persona_id: persona},
                paths=paths,
                provider=provider,
                guard=g,
            )
        except (BudgetExceeded, GuardTripped) as exc:
            _LOG.warning("calibration aborted mid-judge: %s", exc)

    completed_at = _utc_now_iso()

    n = len(paths)
    if n == 0:
        avg_calls = avg_in = avg_out = avg_cost = avg_sec = 0.0
    else:
        # Derive averages from the guard delta so judge calls land in
        # the per-path numbers (B-review 3.1).
        avg_calls = (g.total_calls - before_calls) / n
        avg_cost = (g.total_cost - before_cost) / n
        avg_in = (g.total_input_tokens - before_input_tokens) / n
        avg_out = (g.total_output_tokens - before_output_tokens) / n
        avg_sec = sum(p.duration_seconds for p in paths) / n

    cal = CalibrationData(
        n_paths=n,
        avg_calls_per_path=avg_calls,
        avg_input_tokens_per_path=avg_in,
        avg_output_tokens_per_path=avg_out,
        avg_cost_per_path=avg_cost,
        avg_seconds_per_path=avg_sec,
        started_at=started_at,
        completed_at=completed_at,
    )

    _write_calibration_report(cal, paths=paths, output_dir=output_dir, persona=persona)
    return cal


def _write_calibration_report(
    cal: CalibrationData,
    *,
    paths: list[PlaytestPath],
    output_dir: Path,
    persona: Persona,
) -> None:
    """Write a single ``calibration_report.md`` under ``output_dir``.

    Includes an explicit recommended ``max_paths`` line derived from
    the typical ADR-022 ceilings so the author can read a number
    instead of doing the math themselves.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cost_budget = 10.0
    wall_budget_min = 30.0
    rec_paths_cost = (
        int(cost_budget / cal.avg_cost_per_path)
        if cal.avg_cost_per_path > 0
        else 0
    )
    rec_paths_wall = (
        int((wall_budget_min * 60.0) / cal.avg_seconds_per_path)
        if cal.avg_seconds_per_path > 0
        else 0
    )
    rec_paths = min(rec_paths_cost, rec_paths_wall) if rec_paths_cost and rec_paths_wall else (
        rec_paths_cost or rec_paths_wall
    )

    lines = []
    lines.append("# Playtest calibration report")
    lines.append("")
    lines.append(f"_Generated at {cal.completed_at}._")
    lines.append("")
    lines.append(f"- persona: `{persona.persona_id}` ({persona.display_name})")
    lines.append(f"- paths run: {cal.n_paths}")
    lines.append("")
    lines.append("## Per-path averages")
    lines.append("")
    lines.append(f"- calls/path:           {cal.avg_calls_per_path:.2f}")
    lines.append(f"- input tokens/path:    {cal.avg_input_tokens_per_path:.0f}")
    lines.append(f"- output tokens/path:   {cal.avg_output_tokens_per_path:.0f}")
    lines.append(f"- cost/path:            ${cal.avg_cost_per_path:.4f}")
    lines.append(f"- seconds/path:         {cal.avg_seconds_per_path:.2f}")
    lines.append("")
    lines.append("## Recommended max_paths")
    lines.append("")
    lines.append(
        f"- against $10 cost budget:        {rec_paths_cost} paths"
    )
    lines.append(
        f"- against 30 min wall-clock:      {rec_paths_wall} paths"
    )
    lines.append(
        f"- conservative recommendation:    **{rec_paths} paths total**"
    )
    lines.append("")
    lines.append(
        "> ADR-022 / F9: re-run calibration after any prompt or persona "
        "change. The full batch should not exceed the conservative "
        "recommendation without raising the three-way guards."
    )
    lines.append("")
    lines.append("## Per-path detail")
    lines.append("")
    lines.append("| path_id | reached_end | llm_calls | cost_usd | seconds | failure_reason |")
    lines.append("|---|---|---|---|---|---|")
    for p in paths:
        failure = (p.failure_reason or p.error or "—")
        failure = str(failure).replace("|", "/").replace("\n", " ")[:60]
        lines.append(
            f"| `{p.path_id}` | "
            f"{'yes' if p.reached_end else 'no'} | "
            f"{p.llm_calls} | ${p.cost_usd:.4f} | "
            f"{p.duration_seconds:.2f} | {failure} |"
        )
    lines.append("")

    (output_dir / "calibration_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Manifest writer
# ---------------------------------------------------------------------------


def write_run_manifest(
    *,
    output_dir: Path,
    playtest_id: str,
    started_at: str,
    completed_at: str,
    provider: LLMProvider,
    personas: list[Persona],
    calibration: CalibrationData | None,
    n_paths_per_persona: int,
    scenes_played: list[str],
    guard: GuardState,
    aborted: bool,
    abort_reason: str | None,
) -> Path:
    """Serialise the F20 run_manifest.json next to the report files.

    The manifest is the single source of truth for replaying or
    auditing this batch. Every field that influences worst-list output
    is captured here.
    """
    manifest = {
        "playtest_id": playtest_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "model_id": getattr(provider, "model_id", "unknown"),
        "temperature": getattr(provider, "temperature", None),
        "prompt_template_hash": _compute_prompt_template_hash(),
        "judge_rubric_version": JUDGE_RUBRIC_VERSION,
        "persona_hashes": hash_personas(personas),
        "personas": [p.to_canonical_dict() for p in personas],
        "n_paths_per_persona": n_paths_per_persona,
        "scenes_played": list(scenes_played),
        # F20 single-path replay (B-review 4.1): worst_paths.jsonl is
        # the choice trace — every PathStep carries option_set +
        # raw_choice + reasoning. Pointing at the file rather than
        # inlining keeps the manifest small and stable.
        "choice_trace_file": "worst_paths.jsonl",
        "choice_trace_format": (
            "PathStep.option_set lists the option_id/text/target_node_id "
            "set the LLM saw; PathStep.raw_choice is the provider's raw "
            "JSON response. Together they let a future replay re-issue "
            "the call without requiring the live persona prompt."
        ),
        "guard": {
            "max_cost_usd": guard.max_cost_usd,
            "max_calls": guard.max_calls,
            "max_wall_clock_min": guard.max_wall_clock_min,
            "total_calls": guard.total_calls,
            "total_cost_usd": guard.total_cost,
            "total_input_tokens": guard.total_input_tokens,
            "total_output_tokens": guard.total_output_tokens,
            "elapsed_min": guard.elapsed_min(),
        },
        "aborted": aborted,
        "abort_reason": abort_reason,
        "calibration_data": calibration.to_dict() if calibration else None,
    }
    path = output_dir / "run_manifest.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def write_worst_paths_jsonl(
    *,
    output_dir: Path,
    paths: list[PlaytestPath],
) -> Path:
    """Write the F21 ``worst_paths.jsonl`` (one row per path, ranked
    worst-first).
    """
    ranked = rank_paths_worst_first(paths)
    out_path = output_dir / "worst_paths.jsonl"
    with open(out_path, "w", encoding="utf-8") as fh:
        for p in ranked:
            fh.write(
                json.dumps(
                    path_to_jsonl_dict(p), ensure_ascii=False, separators=(",", ":")
                )
                + "\n"
            )
    return out_path


def write_worst_scenes(
    *,
    output_dir: Path,
    aggregates: list[SceneAggregate],
    playtest_id: str,
) -> tuple[Path, Path]:
    """Write the F21 ``worst_scenes.md`` and ``worst_scenes.json``.

    Returns ``(md_path, json_path)``.
    """
    md = render_worst_scenes_markdown(aggregates, playtest_id=playtest_id)
    payload = render_worst_scenes_json(aggregates, playtest_id=playtest_id)
    md_path = output_dir / "worst_scenes.md"
    json_path = output_dir / "worst_scenes.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return md_path, json_path


# ---------------------------------------------------------------------------
# Public batch driver
# ---------------------------------------------------------------------------


def run_full_batch(
    *,
    scenes: list[tuple[str, dict]],          # (scene_id, scene_dict)
    personas: list[Persona],
    n_paths_per_persona: int,
    provider: LLMProvider,
    output_dir: Path,
    guard: GuardState,
    initial_state: dict | None = None,
    calibration: CalibrationData | None = None,
) -> tuple[list[PlaytestPath], list[SceneAggregate], bool, str | None]:
    """Run every (persona, scene) combination, judge each path, write reports.

    Returns ``(all_paths, scene_aggregates, aborted, abort_reason)``.
    Aborts cleanly on :class:`BudgetExceeded` or any guard trip; in
    that case ``aborted=True`` and the partial output is still
    flushed to ``output_dir``. Already-completed paths are persisted
    to ``all_paths`` / ``scene_paths`` BEFORE the judge phase so a
    judge-stage trip can never lose them (B-review 3.2).
    """
    persona_lookup = {p.persona_id: p for p in personas}
    all_paths: list[PlaytestPath] = []
    scene_aggregates: list[SceneAggregate] = []
    aborted = False
    abort_reason: str | None = None

    for scene_id, scene in scenes:
        scene_paths: list[PlaytestPath] = []
        for persona in personas:
            persona_paths: list[PlaytestPath] = []
            persisted = False
            try:
                guard.check()
                _run_persona_paths_sequential(
                    scene=scene,
                    persona=persona,
                    n_paths=n_paths_per_persona,
                    provider=provider,
                    initial_state=initial_state,
                    guard=guard,
                    progress_label=f"{scene_id}/{persona.persona_id}",
                    paths_out=persona_paths,
                )
                # Persist runner output BEFORE the judge phase so a
                # judge-stage trip can't lose paths the runner already
                # paid for (B-review 3.2).
                scene_paths.extend(persona_paths)
                all_paths.extend(persona_paths)
                persisted = True
                _judge_paths(
                    scene=scene,
                    persona_lookup=persona_lookup,
                    paths=persona_paths,
                    provider=provider,
                    guard=guard,
                )
            except (BudgetExceeded, GuardTripped) as exc:
                # Persist whatever the runner appended to persona_paths
                # before the trip if we hadn't already (mid-runner trip).
                if not persisted and persona_paths:
                    scene_paths.extend(persona_paths)
                    all_paths.extend(persona_paths)
                aborted = True
                if isinstance(exc, GuardTripped):
                    abort_reason = f"guard tripped ({exc.which}): {exc}"
                else:
                    abort_reason = f"BudgetExceeded: {exc}"
                _LOG.warning(abort_reason)
                break
        scene_aggregates.append(
            aggregate_scene_summary(scene_id, scene_paths)
        )
        if aborted:
            break
    return all_paths, scene_aggregates, aborted, abort_reason


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_default_provider() -> LLMProvider:
    from generator.providers import get_default_provider

    return get_default_provider()


def main(
    argv: list[str] | None = None,
    *,
    provider: LLMProvider | None = None,
    experiments_root: Path | None = None,
) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        prog="python -m generator.playtest",
        description=(
            "Playtest bots framework (T-3.4 / ADR-022). Runs personas × paths "
            "× scenes through an LLM, scores each path with a judge, ranks the "
            "worst-10% per scene, and writes the F20/F21 artifact set."
        ),
    )
    parser.add_argument("scene_path", type=Path, help="Path to a scene JSON file")
    parser.add_argument(
        "--n-paths", type=int, default=20, help="paths per persona (default: 20)"
    )
    parser.add_argument(
        "--personas",
        type=str,
        default="all",
        help="comma-separated persona ids or 'all' (default: all)",
    )
    parser.add_argument(
        "--calibration",
        action="store_true",
        help="run only the F9 calibration smoke (1 scene × 1 persona × 5 paths)",
    )
    parser.add_argument(
        "--skip-calibration",
        action="store_true",
        help="skip the pre-batch calibration smoke (author-acknowledged)",
    )
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        default=10.0,
        help="abort the batch when cumulative cost exceeds this (default: 10.0)",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=1000,
        help="abort the batch when LLM call count exceeds this (default: 1000)",
    )
    parser.add_argument(
        "--max-wall-clock-min",
        type=float,
        default=30.0,
        help="abort the batch when elapsed wall-clock exceeds this (default: 30)",
    )
    parser.add_argument(
        "--cost-log",
        type=Path,
        default=None,
        help=(
            f"override the playtest cost log path "
            f"(default: {PLAYTEST_COST_LOG_PATH})"
        ),
    )
    parser.add_argument(
        "--initial-state",
        type=Path,
        default=None,
        help="optional JSON file with the persona's initial WorldState dict",
    )
    args = parser.parse_args(argv)

    if args.calibration and args.skip_calibration:
        print(
            "error: --calibration and --skip-calibration are mutually exclusive",
            file=sys.stderr,
        )
        return 2
    if not args.scene_path.exists():
        print(f"error: scene path missing: {args.scene_path}", file=sys.stderr)
        return 2

    cost_log_path = args.cost_log or PLAYTEST_COST_LOG_PATH
    _ensure_cost_log_env(cost_log_path)

    try:
        scene = _load_scene(args.scene_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    initial_state: dict | None = None
    if args.initial_state:
        try:
            initial_state = json.loads(args.initial_state.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"error: --initial-state: {exc}", file=sys.stderr)
            return 2

    try:
        personas = _select_personas(args.personas)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    provider = provider or _build_default_provider()
    root = experiments_root or EXPERIMENTS_ROOT
    output_dir = next_playtest_dir(root)
    playtest_id = output_dir.name

    started_at = _utc_now_iso()
    guard = GuardState(
        max_cost_usd=args.max_cost_usd,
        max_calls=args.max_calls,
        max_wall_clock_min=args.max_wall_clock_min,
        started_monotonic=time.monotonic(),
    )

    print(f"[playtest] writing to {output_dir}")
    print(
        f"[playtest] guards: cost ≤ ${args.max_cost_usd:.2f} / "
        f"calls ≤ {args.max_calls} / wall ≤ {args.max_wall_clock_min:.1f} min"
    )

    if args.calibration:
        cal = run_calibration(
            scene=scene,
            persona=personas[0],
            provider=provider,
            output_dir=output_dir,
            initial_state=initial_state,
            guard=guard,
        )
        write_run_manifest(
            output_dir=output_dir,
            playtest_id=playtest_id,
            started_at=started_at,
            completed_at=_utc_now_iso(),
            provider=provider,
            personas=personas,
            calibration=cal,
            n_paths_per_persona=0,
            scenes_played=[scene.get("graph_id") or args.scene_path.stem],
            guard=guard,
            aborted=False,
            abort_reason=None,
        )
        print(f"[playtest] calibration complete; report at {output_dir}/calibration_report.md")
        return 0

    cal: CalibrationData | None = None
    if not args.skip_calibration:
        cal = run_calibration(
            scene=scene,
            persona=personas[0],
            provider=provider,
            output_dir=output_dir,
            initial_state=initial_state,
            guard=guard,
        )
    else:
        print("[playtest] --skip-calibration set; running batch without smoke run")

    scenes = [(scene.get("graph_id") or args.scene_path.stem, scene)]
    paths, aggregates, aborted, abort_reason = run_full_batch(
        scenes=scenes,
        personas=personas,
        n_paths_per_persona=args.n_paths,
        provider=provider,
        output_dir=output_dir,
        guard=guard,
        initial_state=initial_state,
        calibration=cal,
    )
    completed_at = _utc_now_iso()

    write_worst_paths_jsonl(output_dir=output_dir, paths=paths)
    write_worst_scenes(
        output_dir=output_dir, aggregates=aggregates, playtest_id=playtest_id
    )
    write_run_manifest(
        output_dir=output_dir,
        playtest_id=playtest_id,
        started_at=started_at,
        completed_at=completed_at,
        provider=provider,
        personas=personas,
        calibration=cal,
        n_paths_per_persona=args.n_paths,
        scenes_played=[s[0] for s in scenes],
        guard=guard,
        aborted=aborted,
        abort_reason=abort_reason,
    )

    if aborted:
        print(
            f"[playtest] aborted: {abort_reason}; partial output at {output_dir}",
            file=sys.stderr,
        )
        return 3
    print(
        f"[playtest] done; {len(paths)} paths, "
        f"${guard.total_cost:.4f} total. Output at {output_dir}/"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())


__all__ = [
    "CALIBRATION_PATHS",
    "CalibrationData",
    "EXPERIMENTS_ROOT",
    "GuardState",
    "GuardTripped",
    "PLAYTEST_COST_LOG_PATH",
    "main",
    "next_playtest_dir",
    "run_calibration",
    "run_full_batch",
    "write_run_manifest",
    "write_worst_paths_jsonl",
    "write_worst_scenes",
]
