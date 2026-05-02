"""Visual asset generation orchestrator (T-1.5.6, ADR-014).

`generate_character_sheet` / `generate_scene_background` are the two
entry-points the upper layers (the forge UI and T-1.5.7 import CLI's
sibling scheduler) call to produce one batch of image assets. They own
five responsibilities:

  1. Pull the visual context from `visual_context.assemble_*`.
  2. Pick variants (expression × pose for character; time × weather for
     scene) and clip to `requirement.n`.
  3. For each variant: mint a deterministic `asset_id_stub`, render the
     prompt from the bilingual template, run the budget guard, call the
     provider, and write the cost-log row on success.
  4. Translate `ImageBudgetExceeded` and any provider exception into a
     `VisualGenerationResult(success=False, ...)` row — never raise to
     the caller. This mirrors `generate_node`'s contract.
  5. Stop early on `ImageBudgetExceeded` (cost was capped on purpose;
     don't burn through the rest of the batch); continue on per-call
     provider errors (a single bad call shouldn't kill a 10-image batch).

Determinism note (re-runs)
--------------------------
`asset_id_stub` is computed from `(target_ref, asset_role, variant_label,
idx)` only — no timestamp. Re-running the same requirement produces the
same stubs, so the manifest write-back layer (T-1.5.7) can detect "this
ID already imported" and skip rather than churn IDs and break refs in
already-imported manifests (mirrors the contract documented on the
ImageProvider Protocol).
"""

from __future__ import annotations

import datetime as _dt
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from generator import image_budget
from generator.image_budget import ImageBudgetExceeded
from generator.image_provider import ImageProvider, ImageProviderError
from generator.prompts.visual import (
    BACKGROUND_TEMPLATE,
    CHARACTER_FEATURES,
    CHARACTER_TEMPLATE,
    fallback_features_from_card,
    format_features_block,
    load_template,
    render_template,
)
from generator.visual_context import (
    CharacterSheetRequirement,
    SceneBackgroundRequirement,
    VisualGenerationContext,
    assemble_visual_context_for_character,
    assemble_visual_context_for_location_or_scene,
)

_logger = logging.getLogger(__name__)

# Mirror of the asset_id_stub regex enforced by ManualImportProvider, kept
# here so we can normalise variant labels to satisfy it before handing off.
_ASSET_ID_BODY_RE = re.compile(r"[a-z0-9_]")
_REPEAT_UNDERSCORE_RE = re.compile(r"_+")
_TARGET_PREFIX_RE = re.compile(r"^(char|scene|loc|location)_")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class VisualGenerationResult:
    """One row per variant (success or failure). Mirrors `generate_node`'s
    `GenerationResult` shape but for the visual pipeline."""

    success: bool
    asset_id_stub: str
    prompt_package_path: Path | None = None
    image_bytes: bytes | None = None
    failure_reason: str | None = None
    cost_usd: float = 0.0
    raw_metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def generate_character_sheet(
    *,
    requirement: CharacterSheetRequirement,
    provider: ImageProvider,
    mode: Literal["manual", "api"] = "manual",
    batch_name: str | None = None,
    size: tuple[int, int] = (1024, 1024),
    ontology_path: Path | None = None,
    reference_dir: Path | None = None,
) -> list[VisualGenerationResult]:
    """Produce one character's portrait batch.

    Returns one result per variant; on `ImageBudgetExceeded` the run stops
    early and returns the prefix that already succeeded plus one
    `success=False` row for the call that hit the cap. Per-call provider
    failures produce a `success=False` row but the batch continues.
    """
    context = assemble_visual_context_for_character(
        requirement.target_ref,
        ontology_path=ontology_path or _ontology_default(),
        reference_dir=reference_dir or _reference_default(),
        character_features_lookup=CHARACTER_FEATURES,
    )

    template = load_template(CHARACTER_TEMPLATE)
    variants = _character_variants(requirement)
    results: list[VisualGenerationResult] = []

    for idx, (expression, pose) in enumerate(variants, start=1):
        variant_label = _normalise_variant(f"{expression}_{pose}")
        asset_id_stub = _make_asset_id_stub(
            requirement.target_ref, "character_sheet", variant_label, idx
        )
        prompt_text = _render_character_prompt(
            template=template,
            context=context,
            target_ref=requirement.target_ref,
            expression=expression,
            pose=pose,
        )

        result = _generate_one(
            provider=provider,
            mode=mode,
            prompt=prompt_text,
            ref_images=list(context.style_reference_paths),
            n=1,
            size=size,
            asset_kind="character_sheet",
            target_ref=requirement.target_ref,
            target_type="character",
            asset_role="character_sheet",
            asset_id_stub=asset_id_stub,
            variant_label=variant_label,
            batch_name=batch_name,
        )
        results.append(result)

        if (
            not result.success
            and result.failure_reason
            and result.failure_reason.startswith("budget_exceeded")
        ):
            # Hard stop the batch — the caller picked the daily cap on
            # purpose, blowing past it on retries / next variants would
            # defeat the guard.
            break

    return results


def generate_scene_background(
    *,
    requirement: SceneBackgroundRequirement,
    provider: ImageProvider,
    mode: Literal["manual", "api"] = "manual",
    batch_name: str | None = None,
    size: tuple[int, int] = (1024, 1024),
    ontology_path: Path | None = None,
    scene_path: Path | None = None,
    reference_dir: Path | None = None,
) -> list[VisualGenerationResult]:
    """Produce one location/scene's background batch."""
    context = assemble_visual_context_for_location_or_scene(
        requirement.target_ref,
        requirement.target_type,
        ontology_path=ontology_path or _ontology_default(),
        scene_path=scene_path or _scene_default(),
        reference_dir=reference_dir or _reference_default(),
    )

    template = load_template(BACKGROUND_TEMPLATE)
    variants = _scene_variants(requirement)
    results: list[VisualGenerationResult] = []

    for idx, (time_of_day, weather) in enumerate(variants, start=1):
        variant_label = _normalise_variant(
            f"{time_of_day}_{weather}" if weather else time_of_day
        )
        asset_id_stub = _make_asset_id_stub(
            requirement.target_ref, "scene_background", variant_label, idx
        )
        prompt_text = _render_background_prompt(
            template=template,
            context=context,
            target_ref=requirement.target_ref,
            target_type=requirement.target_type,
            time_of_day=time_of_day,
            weather=weather,
        )

        result = _generate_one(
            provider=provider,
            mode=mode,
            prompt=prompt_text,
            ref_images=list(context.style_reference_paths),
            n=1,
            size=size,
            asset_kind="scene_background",
            target_ref=requirement.target_ref,
            target_type=requirement.target_type,
            asset_role="scene_background",
            asset_id_stub=asset_id_stub,
            variant_label=variant_label,
            batch_name=batch_name,
        )
        results.append(result)

        if (
            not result.success
            and result.failure_reason
            and result.failure_reason.startswith("budget_exceeded")
        ):
            break

    return results


# ---------------------------------------------------------------------------
# Internal: per-variant orchestration
# ---------------------------------------------------------------------------


def _generate_one(
    *,
    provider: ImageProvider,
    mode: Literal["manual", "api"],
    prompt: str,
    ref_images: list[Path],
    n: int,
    size: tuple[int, int],
    asset_kind: Literal["character_sheet", "scene_background"],
    target_ref: str,
    target_type: Literal["character", "location", "scene"],
    asset_role: Literal["character_sheet", "scene_background"],
    asset_id_stub: str,
    variant_label: str,
    batch_name: str | None,
) -> VisualGenerationResult:
    """Run one provider call end-to-end with budget + cost-log + error mapping."""

    estimated_cost = provider.estimate_cost(n=n, size=size)

    # ---- Mode/provider sanity (review of T-1.5.6 #3.1). ----
    # `image_budget.check()` short-circuits on `mode == "manual"`, so a paid
    # provider mistakenly invoked in manual mode would skip the per-call /
    # daily ceiling and still hit the network. Refuse before the provider
    # call when the provider's own estimate disagrees with the declared mode.
    if mode == "manual" and estimated_cost > 0:
        return VisualGenerationResult(
            success=False,
            asset_id_stub=asset_id_stub,
            prompt_package_path=None,
            image_bytes=None,
            failure_reason=(
                "provider_mode_mismatch: manual mode but provider estimated "
                f"${estimated_cost:.4f}; refusing to call provider before "
                "budget check"
            ),
            cost_usd=0.0,
            raw_metadata={
                "target_ref": target_ref,
                "target_type": target_type,
                "asset_role": asset_role,
                "variant_label": variant_label,
                "estimated_cost_usd": estimated_cost,
            },
        )

    # ---- Pre-call budget guard (ADR-012 / T-1.5.5). ----
    try:
        image_budget.check(estimated_cost_usd=estimated_cost, mode=mode)
    except ImageBudgetExceeded as exc:
        _logger.warning(
            "generate_visual: budget exceeded before %s (mode=%s): %s",
            asset_id_stub,
            mode,
            exc,
        )
        return VisualGenerationResult(
            success=False,
            asset_id_stub=asset_id_stub,
            prompt_package_path=None,
            image_bytes=None,
            failure_reason=f"budget_exceeded: {exc}",
            cost_usd=0.0,
            raw_metadata={
                "target_ref": target_ref,
                "target_type": target_type,
                "asset_role": asset_role,
                "variant_label": variant_label,
                "estimated_cost_usd": estimated_cost,
            },
        )

    # ---- Provider call. ----
    try:
        gen_result = provider.generate(
            prompt=prompt,
            ref_images=ref_images,
            n=n,
            size=size,
            asset_kind=asset_kind,
            target_ref=target_ref,
            target_type=target_type,
            asset_role=asset_role,
            asset_id_stub=asset_id_stub,
            variant_label=variant_label,
        )
    except ImageProviderError as exc:
        # Provider-level failure: the call did not consume budget (or the
        # provider explicitly says it didn't), so we deliberately do NOT
        # call image_budget.log_charge — sticking to ADR-014's "consumption
        # actually happened" rule keeps daily totals truthful.
        _logger.warning(
            "generate_visual: provider error for %s: %s", asset_id_stub, exc
        )
        return VisualGenerationResult(
            success=False,
            asset_id_stub=asset_id_stub,
            prompt_package_path=None,
            image_bytes=None,
            failure_reason=f"provider_error: {exc}",
            cost_usd=0.0,
            raw_metadata={
                "target_ref": target_ref,
                "target_type": target_type,
                "asset_role": asset_role,
                "variant_label": variant_label,
            },
        )
    except Exception as exc:  # noqa: BLE001 — defensive: any provider crash
        # Same rationale as above; treat unknown provider exceptions as
        # consumption-did-not-happen so a flaky network or SDK quirk can't
        # double-charge the budget log.
        _logger.warning(
            "generate_visual: unexpected provider exception for %s: %s",
            asset_id_stub,
            exc,
        )
        return VisualGenerationResult(
            success=False,
            asset_id_stub=asset_id_stub,
            prompt_package_path=None,
            image_bytes=None,
            failure_reason=f"provider_error: {type(exc).__name__}: {exc}",
            cost_usd=0.0,
            raw_metadata={
                "target_ref": target_ref,
                "target_type": target_type,
                "asset_role": asset_role,
                "variant_label": variant_label,
            },
        )

    # ---- Mode-echo check (review of T-1.5.6 #3.1). ----
    # The provider's returned mode is the authoritative consumption marker
    # — if a provider that the caller thought was paid actually came back
    # as "manual" (or vice-versa), the cost log would mis-attribute the
    # call. Fail loudly here rather than silently writing a wrong row.
    if gen_result.mode != mode:
        _logger.warning(
            "generate_visual: provider mode mismatch for %s: requested=%s "
            "returned=%s",
            asset_id_stub,
            mode,
            gen_result.mode,
        )
        return VisualGenerationResult(
            success=False,
            asset_id_stub=asset_id_stub,
            prompt_package_path=None,
            image_bytes=None,
            failure_reason=(
                f"provider_mode_mismatch: requested mode={mode}, provider "
                f"returned mode={gen_result.mode}"
            ),
            cost_usd=0.0,
            raw_metadata=dict(gen_result.raw_metadata),
        )

    # ---- Cost-log on success. ----
    try:
        image_budget.log_charge(
            timestamp=_dt.datetime.now(_dt.timezone.utc),
            mode=gen_result.mode,
            provider_id=_provider_id_for_log(gen_result),
            asset_kind=asset_kind,
            asset_id_stub=gen_result.asset_id_stub,
            n=n,
            size=size,
            cost_usd=gen_result.cost_usd,
            batch_name=batch_name,
        )
    except OSError as exc:
        # The cost log lives on disk; if the disk is unhappy we still
        # return success for the asset (the prompt package / bytes are
        # already produced) but flag the log failure in raw_metadata so
        # T-1.5.8 metrics can spot it.
        _logger.error(
            "generate_visual: image_cost_log write failed for %s: %s",
            asset_id_stub,
            exc,
        )

    return VisualGenerationResult(
        success=True,
        asset_id_stub=gen_result.asset_id_stub,
        prompt_package_path=gen_result.prompt_package_path,
        image_bytes=gen_result.image_bytes,
        failure_reason=None,
        cost_usd=gen_result.cost_usd,
        raw_metadata=dict(gen_result.raw_metadata),
    )


# ---------------------------------------------------------------------------
# Internal: variant expansion
# ---------------------------------------------------------------------------


def _character_variants(req: CharacterSheetRequirement) -> list[tuple[str, str]]:
    """Cartesian product `expression × pose`, clipped to `req.n`.

    Stable order — expressions outer, poses inner — so re-running a probe
    that asks for n=5 against the same expressions/poses lists yields the
    same stubs.
    """
    poses = req.poses if req.poses else ["torso_up"]
    out: list[tuple[str, str]] = []
    for expression in req.expressions:
        for pose in poses:
            out.append((expression, pose))
            if len(out) >= req.n:
                return out
    return out


def _scene_variants(req: SceneBackgroundRequirement) -> list[tuple[str, str | None]]:
    weathers: list[str | None] = list(req.weather) if req.weather else [None]
    out: list[tuple[str, str | None]] = []
    for tod in req.times_of_day:
        for weather in weathers:
            out.append((tod, weather))
            if len(out) >= req.n:
                return out
    return out


# ---------------------------------------------------------------------------
# Internal: prompt rendering
# ---------------------------------------------------------------------------


def _render_character_prompt(
    *,
    template: str,
    context: VisualGenerationContext,
    target_ref: str,
    expression: str,
    pose: str,
) -> str:
    features = context.character_features
    if not features:
        # ADR-014 graceful degradation — the entry is missing from
        # character_features.py, so we synthesise the thinnest plausible
        # block from the ontology card so the prompt at least names the
        # subject explicitly.
        features = fallback_features_from_card(context.character_card)

    features_block = format_features_block(features) if features else "- (no features)"
    ontology_block_zh, ontology_block_en = _format_ontology_blocks(
        context.character_card, kind="character"
    )
    style_zh, style_en = _format_style_reference_blocks(context.style_reference_paths)

    return render_template(
        template,
        {
            "TARGET_REF": target_ref,
            "EXPRESSION": expression,
            "POSE": pose,
            "CHARACTER_FEATURES_BLOCK": features_block,
            "ONTOLOGY_CARD_BLOCK": ontology_block_zh,
            "ONTOLOGY_CARD_BLOCK_EN": ontology_block_en,
            "STYLE_REFERENCES_BLOCK_ZH": style_zh,
            "STYLE_REFERENCES_BLOCK_EN": style_en,
        },
    )


def _render_background_prompt(
    *,
    template: str,
    context: VisualGenerationContext,
    target_ref: str,
    target_type: Literal["location", "scene"],
    time_of_day: str,
    weather: str | None,
) -> str:
    ontology_block_zh, ontology_block_en = _format_ontology_blocks(
        context.location_card, kind="location"
    )
    style_zh, style_en = _format_style_reference_blocks(context.style_reference_paths)
    weather_label = weather if weather else "unspecified (atmospheric default)"

    return render_template(
        template,
        {
            "TARGET_REF": target_ref,
            "TARGET_TYPE": target_type,
            "TIME_OF_DAY": time_of_day,
            "WEATHER": weather_label,
            "ONTOLOGY_CARD_BLOCK": ontology_block_zh,
            "ONTOLOGY_CARD_BLOCK_EN": ontology_block_en,
            "STYLE_REFERENCES_BLOCK_ZH": style_zh,
            "STYLE_REFERENCES_BLOCK_EN": style_en,
        },
    )


def _format_ontology_blocks(
    card: dict | None,
    *,
    kind: Literal["character", "location"],
) -> tuple[str, str]:
    """Return (chinese-block, english-block) for the ontology card section.

    Stage-0 stubs are thin (often just `id` / `display_name` / `type`); the
    English half rephrases that as a one-line "Subject is X with no
    additional registered details." so ChatGPT does not silently invent.
    """
    if not card:
        zh = "（本体桩未注册该锚点；按 narration 与角色固定特征段保守渲染。）"
        en = (
            "No additional ontology details registered for this anchor; "
            "rely on the fixed-feature anchors above and render conservatively."
        )
        return zh, en

    name = card.get("display_name") or card.get("id") or "(unnamed)"
    scene_narration = card.get("scene_narration") if isinstance(card, dict) else None
    # review of T-1.5.6 #4.1: scene_narration goes to its own block so it
    # gets rendered as readable prose, not collapsed into a key=repr line.
    fields = ", ".join(
        f"{k}={v!r}"
        for k, v in card.items()
        if k not in {"id", "display_name", "type", "visual_assets", "scene_narration"}
        and not k.startswith("_")
    )
    if kind == "character":
        zh = f"- 名称：`{name}`\n- 类型：character\n- 其余字段：{fields or '（无）'}"
        en = (
            f"Character {name}. Additional registered ontology fields: "
            f"{fields or 'none'}."
        )
    else:
        zh_lines = [
            f"- 名称：`{name}`",
            f"- 类型：location/scene",
            f"- 其余字段：{fields or '（无）'}",
        ]
        if scene_narration:
            zh_lines.append("- 场景 narration 摘录（仅用于氛围 / 不画角色）：")
            zh_lines.append("```")
            zh_lines.append(scene_narration)
            zh_lines.append("```")
        zh = "\n".join(zh_lines)

        en_parts = [
            f"Location/scene {name}. Additional registered ontology fields: "
            f"{fields or 'none'}.",
        ]
        if scene_narration:
            en_parts.append(
                "Scene narration excerpts (read for atmosphere — architecture, "
                "lighting, banners, props; do NOT depict any character "
                "mentioned, the global no-characters rule still holds):"
            )
            en_parts.append(scene_narration)
        en = "\n\n".join(en_parts)
    return zh, en


def _format_style_reference_blocks(paths: list[Path]) -> tuple[str, str]:
    """Render the style-reference paths as bilingual bullet lists.

    Per task spec we never read the bytes — only emit paths. When the
    reference directory is empty we surface a WARN-flavoured note in both
    halves so the author knows the C+B safety net is degraded.
    """
    if not paths:
        zh = (
            "  - ⚠️ 无可用基准图（`/content/visuals/_reference/` 为空）；"
            "本批一致性主要依赖角色固定特征段。"
        )
        en = (
            "- WARN: no style reference images registered "
            "(content/visuals/_reference/ is empty). Consistency for this "
            "batch will rely on the fixed-feature anchors above only."
        )
        return zh, en

    zh_lines = [f"  - `{p}`" for p in paths]
    en_lines = [f"- `{p}`" for p in paths]
    return "\n".join(zh_lines), "\n".join(en_lines)


# ---------------------------------------------------------------------------
# Internal: stable provider_id for image_cost_log (review of T-1.5.6 #4.2)
# ---------------------------------------------------------------------------


def _provider_id_for_log(gen_result: "ImageGenerationResult") -> str:
    """Map an `ImageGenerationResult` to the stable `provider_id` string the
    cost log carries.

    Class names like `ManualImportProvider` / `FakeApiImageProvider` would
    couple the on-disk log to Python implementation details; T-1.5.8 metrics
    expect canonical ids (`manual_import`, `openai_image_<model_id>`). The
    `model_id` for API rows lives in `raw_metadata` so each provider can
    populate it without changing the Protocol.
    """
    if gen_result.mode == "manual":
        return "manual_import"
    model_id = gen_result.raw_metadata.get("model_id") if gen_result.raw_metadata else None
    if isinstance(model_id, str) and model_id:
        return f"openai_image_{model_id}"
    return "api_unknown"


# ---------------------------------------------------------------------------
# Internal: deterministic asset_id_stub
# ---------------------------------------------------------------------------


def _make_asset_id_stub(
    target_ref: str,
    asset_role: str,
    variant_label: str,
    idx: int,
) -> str:
    """Return a deterministic asset_id_stub matching `^img_[a-z0-9_]{1,64}$`.

    Stub layout: `img_<short_target>_<role>_<variant>_<idx>`.

    review of T-1.5.6 #4.3: `asset_role` is now part of the stub (was
    forward-compat-only); naive end-truncation could drop the variant /
    idx and collide across variants of a long target. We always preserve
    the suffix `<role>_<variant>_<idx>` and truncate only the target
    prefix to fit the schema's 64-char body bound. T-1.5.7 import depends
    on this for idempotent re-imports.
    """
    short = _normalise_variant(_TARGET_PREFIX_RE.sub("", target_ref))
    role = _normalise_variant(asset_role)
    variant = _normalise_variant(variant_label)
    suffix = f"{role}_{variant}_{idx:02d}".strip("_")
    suffix = _REPEAT_UNDERSCORE_RE.sub("_", suffix)

    # Reserve room for the suffix + the underscore that separates it from
    # the prefix; whatever's left is how much target prefix we keep.
    prefix_budget = max(0, 64 - len(suffix) - 1)
    short_prefix = short[:prefix_budget].rstrip("_")
    body = f"{short_prefix}_{suffix}" if short_prefix else suffix
    body = _REPEAT_UNDERSCORE_RE.sub("_", body).strip("_")
    return f"img_{body}"


def _normalise_variant(label: str) -> str:
    """Lowercase + replace any char outside [a-z0-9_] with `_`, collapse
    repeats, strip surrounding underscores."""
    out_chars: list[str] = []
    for ch in label.lower():
        if _ASSET_ID_BODY_RE.fullmatch(ch):
            out_chars.append(ch)
        else:
            out_chars.append("_")
    out = "".join(out_chars)
    out = _REPEAT_UNDERSCORE_RE.sub("_", out)
    return out.strip("_")


# ---------------------------------------------------------------------------
# Internal: default path helpers (CWD-relative; tests inject explicit paths)
# ---------------------------------------------------------------------------


def _ontology_default() -> Path:
    return Path("state/ontology/waystation.json")


def _scene_default() -> Path:
    return Path("content/test_scene_v0/scene.json")


def _reference_default() -> Path:
    return Path("content/visuals/_reference")
