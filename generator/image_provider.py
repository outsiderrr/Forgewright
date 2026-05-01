"""ImageProvider Protocol — see ADR-014.

Mirrors the shape of `LLMProvider` (ADR-011): a single generate call plus a
cost estimator. Retry, budget, prompt assembly, and manifest write-back all
live one layer up (`generate_visual.py`, `image_budget.py`, `image_import.py`
in later T-1.5.x tasks). Concrete providers live under `generator/providers/`
and are the only place where vendor SDKs may be imported.

The signature carries `target_ref` / `target_type` / `asset_role` /
`asset_id_stub` end-to-end so manifest write-back (T-1.5.7) doesn't have to
re-derive them from filenames. `asset_id_stub` is the *final* asset_id;
deterministic generation + uniqueness is the caller's responsibility (so
re-runs of the same character don't churn IDs and break references in
already-imported manifests).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable


class ImageProviderError(RuntimeError):
    """Raised by an ImageProvider when a single generate call fails. Callers
    decide whether to retry; the Protocol itself is retry-free."""


@dataclass
class ImageGenerationResult:
    mode: Literal["manual", "api"]
    asset_id_stub: str
    image_bytes: bytes | None
    prompt_package_path: Path | None
    cost_usd: float
    raw_metadata: dict


@runtime_checkable
class ImageProvider(Protocol):
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
    ) -> ImageGenerationResult: ...

    def estimate_cost(
        self, *, n: int, size: tuple[int, int]
    ) -> float: ...
