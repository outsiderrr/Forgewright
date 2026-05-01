"""OpenAI implementation of ImageProvider — ADR-014 API mode (T-1.5.9).

Per ADR-014: this is the "production / batch" path; manual is the dev-default.
This module is the only place in the repo that imports `openai`.

No retry, no budget, no manifest writeback — those belong upstairs:
  - Budget: `generate_visual.py` calls `image_budget.check()` / `log_charge()`
    (see ADR-014 + T-1.5.5 / T-1.5.6).
  - Retry: out of scope (mirrors GeminiProvider; ADR-013 retry semantics are
    text-only; image retries are author-decided).
  - Manifest: T-1.5.7 `image_import` consumes the returned `image_bytes`.

The signature carries `target_ref` / `target_type` / `asset_role` /
`asset_id_stub` end-to-end so caller can write back without re-deriving them
(see image_provider.py docstring; identical to ManualImportProvider).

Reference-image handling: this task implements **fallback mode** only — when
the caller passes `ref_images=[...]`, we append their paths to the prompt
text as a textual hint. Actual binary upload via gpt-image-1's reference
input is deferred to a later PR (per task spec).
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Literal

from openai import OpenAI, OpenAIError

from generator.image_provider import ImageGenerationResult, ImageProviderError

DEFAULT_MODEL_ID = "gpt-image-1"

# httpx default is 5s read timeout, which is too short for image generation
# (gpt-image-1 routinely takes 10–30s). Mirrors the Gemini provider's stance.
# OpenAI SDK takes seconds (float), unlike google.genai which takes ms.
_HTTP_TIMEOUT_SEC = 120.0

# GPT-Image-1 public pricing per generated image, conservative (HD/high tier)
# upper bound. Source:
#   https://platform.openai.com/docs/pricing  (gpt-image-1 row)
#   https://openai.com/api/pricing/             (image generation)
# Captured: 2026-05-01.
#
# Tier headlines (per call, 1024×1024):
#   low    ≈ $0.011
#   medium ≈ $0.042
#   high   ≈ $0.167
#
# We deliberately use the high-tier value as the *estimate* so the upstream
# image_budget never under-charges. Rationale (see T-1.5.9 §2 review notes):
# avoid the baseline_001 0%-success-rate burn pattern from text generation —
# better to over-reserve and refund nothing than to over-spend.
_USD_PER_IMAGE_HIGH_TIER = 0.17


class OpenAIImageProvider:
    """Single-call wrapper around `openai.images.generate` for gpt-image-1.

    Constructor is keyword-only by spec. `api_key` defaults to the
    `OPENAI_API_KEY` environment variable; missing-key is a startup-time
    `ImageProviderError`, not a lazy surprise mid-batch.

    `model_id` defaults to "gpt-image-1" per ADR-014. Do not silently fall
    back to dall-e-3 — if the model is unavailable, the API will surface a
    clear error and the author decides.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_id: str = DEFAULT_MODEL_ID,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ImageProviderError(
                "OPENAI_API_KEY is not set; pass api_key= or set the env var."
            )
        self.model_id = model_id
        self._api_key = key
        self._client_cache: OpenAI | None = None

    @property
    def _client(self) -> OpenAI:
        # Lazy: avoid network setup at construction so tests can build the
        # provider without side effects (mirrors GeminiProvider).
        # Wrap construction failures (e.g. missing optional `socksio` under
        # `all_proxy=socks5://...`, or any other ImportError/RuntimeError
        # the SDK may raise at __init__) in ImageProviderError so callers
        # never see a bare SDK exception — Protocol contract.
        if self._client_cache is None:
            try:
                self._client_cache = OpenAI(
                    api_key=self._api_key,
                    timeout=_HTTP_TIMEOUT_SEC,
                )
            except Exception as exc:
                raise ImageProviderError(
                    f"OpenAI client setup failed: {exc}"
                ) from exc
        return self._client_cache

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
        # ImageGenerationResult carries a single `image_bytes` payload, so
        # n>1 would silently discard the extras while still being billed for
        # them. Reject up front; estimate_cost still scales linearly so the
        # upstream budget can pre-reserve for batched manual workflows.
        if n != 1:
            raise ImageProviderError(
                f"OpenAIImageProvider currently supports n=1 only "
                f"(got n={n}); ImageGenerationResult carries a single "
                f"image_bytes payload, so additional images would be billed "
                f"but discarded."
            )

        # Fallback ref-image handling: append textual paths to the prompt so
        # the model gets a hint without us uploading bytes (deferred to a
        # later PR; ADR-014 calls character-reference upload "Strategy A" not
        # in 1.5 scope).
        final_prompt = _compose_prompt_with_ref_paths(prompt, ref_images)
        size_str = _size_tuple_to_openai(size)

        try:
            response = self._client.images.generate(
                model=self.model_id,
                prompt=final_prompt,
                n=n,
                size=size_str,
            )
        except OpenAIError as exc:
            # Wrap any OpenAI-level error (auth, network, rate, content
            # policy) so callers can branch on a single repo-local exception
            # type. The original exception is chained for debugging.
            raise ImageProviderError(f"OpenAI image generation failed: {exc}") from exc

        image_bytes = _extract_image_bytes(response)
        cost_usd = self.estimate_cost(n=n, size=size)

        # Pull whatever metadata the SDK gave us, plus the upstream tracing
        # fields. We dump the response to a plain dict (model_dump) so it
        # round-trips through json without surprising pydantic types.
        try:
            response_dict = response.model_dump(mode="json")
        except Exception:
            # If a future SDK version changes the response object shape,
            # don't crash the whole batch — record at least the type name.
            response_dict = {"_response_type": type(response).__name__}

        return ImageGenerationResult(
            mode="api",
            asset_id_stub=asset_id_stub,
            image_bytes=image_bytes,
            prompt_package_path=None,
            cost_usd=cost_usd,
            raw_metadata={
                "model_id": self.model_id,
                "size_requested": list(size),
                "n": n,
                "target_ref": target_ref,
                "target_type": target_type,
                "asset_role": asset_role,
                "asset_kind": asset_kind,
                "variant_label": variant_label,
                "openai_response": response_dict,
            },
        )

    def estimate_cost(self, *, n: int, size: tuple[int, int]) -> float:
        # Conservative: always charge the high tier per image, regardless of
        # size. Stage-1.5 budget is small ($20–$40 total; ADR-014); we'd
        # rather over-reserve than under-charge. A future PR can refine
        # tier-aware pricing once we standardise on a quality setting.
        return n * _USD_PER_IMAGE_HIGH_TIER


def _compose_prompt_with_ref_paths(prompt: str, ref_images: list[Path] | None) -> str:
    """Fallback ref-image handling: append textual paths to the prompt.

    Real binary upload is deferred (ADR-014 Strategy A, stage 2). Until then,
    the prompt template is expected to already describe the character's
    fixed features (eye/hair/clothing colour) — the path list is just an
    additional cue for the human reviewer when comparing the generated
    image against the reference."""
    if not ref_images:
        return prompt
    lines = [str(p) for p in ref_images]
    return (
        f"{prompt}\n\n"
        "Reference images (for comparison; not uploaded to model):\n"
        + "\n".join(f"- {line}" for line in lines)
    )


def _size_tuple_to_openai(size: tuple[int, int]) -> str:
    # OpenAI's `size` is a string like "1024x1024". The SDK validates the
    # exact set per model; we don't pre-validate here — letting the API
    # surface the canonical error is more honest than mirroring its allow
    # list (which drifts as new models ship).
    w, h = size
    return f"{w}x{h}"


def _extract_image_bytes(response) -> bytes:
    data = getattr(response, "data", None)
    if not data:
        raise ImageProviderError("OpenAI response has no `data` field")
    first = data[0]
    b64 = getattr(first, "b64_json", None)
    if b64:
        try:
            return base64.b64decode(b64)
        except (ValueError, TypeError) as exc:
            raise ImageProviderError(
                f"OpenAI returned malformed base64 image: {exc}"
            ) from exc
    # gpt-image-1 always returns b64_json; if a future caller switches to a
    # url-returning model we'd need to download via httpx. Out of scope here.
    raise ImageProviderError(
        "OpenAI image data has neither b64_json nor a supported url field; "
        "if you switched models, update OpenAIImageProvider to handle url-mode."
    )
