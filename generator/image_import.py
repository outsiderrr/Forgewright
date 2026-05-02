"""manual-mode image asset ingestion CLI (T-1.5.7).

Bridges `_pending/<asset_id_stub>/` prompt packages (written by
`ManualImportProvider`; in T-1.5.9+ also by api-mode result paths) into
the canonical `content/visuals/` tree, the manifest index, and — for
character assets — the matching ontology entity's `visual_assets` array.

CLI shapes::

    python -m generator.image_import --asset-id img_vellin_neutral
    python -m generator.image_import --all-pending
    python -m generator.image_import --dry-run --all-pending

Per-asset flow (validate → ingest → log; see STAGE_1.5_TASKS.md T-1.5.7)::

    1. Locate `<stub>.png` in `_pending/<stub>/` — reject if missing or
       multiple matches.
    2. Parse `meta.json` — reject if any required key is absent (upstream
       provider-contract violation; ManualImportProvider always writes
       all required keys, so absence means tampered or hand-built).
    3. Run `validate_image_asset` — reject on any `severity=error`.
    4. Mirror-field consistency (target_ref vs character_ref/location_ref
       per `target_type`).
    5. Compute target dir (`char_`/`scene_` prefix trimmed; `location`
       uses `target_ref` verbatim).
    6. Probe the PNG for width/height/has_alpha/file_size_bytes.
    7. Build `ImageAsset` (Pydantic enforces enums + file_path pattern).
    8. `shutil.move` PNG → final path; `manifest.add_asset`; if
       `target_type == "character"`, append the full `ImageAsset` dict to
       the matching entity's `visual_assets` in `waystation.json`
       (path A; ADR-014 / SCHEMA_v0.2.md §3).
    9. `save_manifest` (atomic + fsync) → save ontology (4-space + final
       newline) → `import_log` row → `shutil.rmtree _pending/<stub>/`.

Failed runs leave the prompt package in `_pending/_rejected/<stub>/` for
the author to inspect rather than deleting it.

Dry-run mode skips steps 5–9 (no disk mutation; only writes a single
`status="dry_run"` row to `import_log.jsonl`).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image, UnidentifiedImageError

from generator import import_log
from generator.manifest import (
    DEFAULT_MANIFEST_PATH,
    Manifest,
    add_asset,
    load_manifest,
    save_manifest,
)
from generator.models._generated.image_asset import ImageAsset
from validator.image_validator import validate_image_asset

_logger = logging.getLogger(__name__)

PENDING_ROOT = Path("content/visuals/_pending")
VISUALS_ROOT = Path("content/visuals")
DEFAULT_ONTOLOGY_PATH = Path("state/ontology/waystation.json")

# Mirrored from ManualImportProvider's contract; T-1.5.7 spec lists these
# as the keys the provider always writes. Absence = upstream contract
# violation, so we reject rather than default.
_REQUIRED_META_KEYS: tuple[str, ...] = (
    "target_ref",
    "target_type",
    "asset_role",
    "asset_kind",
    "source_mode",
    "variant_label",
    "prompt_hash",
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ImportOutcome:
    """One per-asset CLI decision (programmatic mirror of the import_log row)."""

    asset_id_stub: str
    status: Literal["imported", "rejected", "dry_run"]
    rejected_reason: str | None = None
    validation_errors: list[str] | None = None
    final_path: str | None = None


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _target_dir_for(target_type: str, target_ref: str, visuals_root: Path) -> Path:
    """Resolve the on-disk subdir under content/visuals/.

    char_<X>      → content/visuals/<X>/
    scene_<X>     → content/visuals/<X>/
    <target_ref>  → content/visuals/<target_ref>/  (target_type=location)

    Raises ValueError on degenerate input (empty body / wrong prefix).
    """
    if target_type == "character":
        if not target_ref.startswith("char_"):
            raise ValueError(
                f"character target_ref must start with 'char_': {target_ref!r}"
            )
        sub = target_ref[len("char_"):]
    elif target_type == "scene":
        if not target_ref.startswith("scene_"):
            raise ValueError(
                f"scene target_ref must start with 'scene_': {target_ref!r}"
            )
        sub = target_ref[len("scene_"):]
    elif target_type == "location":
        sub = target_ref
    else:
        raise ValueError(f"unknown target_type {target_type!r}")
    if not sub:
        raise ValueError(f"empty target_ref body after prefix strip: {target_ref!r}")
    return visuals_root / sub


def _check_meta_consistency(meta: dict) -> str | None:
    """Return None on pass, or a free-form rejection reason.

    Cross-field rules from SCHEMA_v0.2.md §2.2 / T-1.5.7 step 4:
      - target_type=character ⇒ character_ref==target_ref AND location_ref is null
      - target_type=location  ⇒ location_ref==target_ref AND character_ref is null
      - target_type=scene     ⇒ location_ref==target_ref AND character_ref is null
      - asset_kind == asset_role (current schema rule; both enums overlap)
    """
    target_ref = meta["target_ref"]
    target_type = meta["target_type"]
    char_ref = meta.get("character_ref")
    loc_ref = meta.get("location_ref")
    if target_type == "character":
        if char_ref != target_ref:
            return (
                f"character_ref {char_ref!r} != target_ref {target_ref!r} "
                f"(target_type=character)"
            )
        if loc_ref is not None:
            return "location_ref must be null when target_type=character"
    elif target_type == "location":
        if loc_ref != target_ref:
            return (
                f"location_ref {loc_ref!r} != target_ref {target_ref!r} "
                f"(target_type=location)"
            )
        if char_ref is not None:
            return "character_ref must be null when target_type=location"
    elif target_type == "scene":
        if loc_ref != target_ref:
            return (
                f"location_ref {loc_ref!r} != target_ref {target_ref!r} "
                f"(target_type=scene)"
            )
        if char_ref is not None:
            return "character_ref must be null when target_type=scene"
    else:
        return f"unknown target_type {target_type!r}"
    if meta["asset_kind"] != meta["asset_role"]:
        return (
            f"asset_kind {meta['asset_kind']!r} != asset_role "
            f"{meta['asset_role']!r}"
        )
    return None


def _move_to_rejected(stub_dir: Path, pending_root: Path) -> Path:
    """Move `<pending_root>/<stub>/` → `<pending_root>/_rejected/<stub>/`.

    Appends a UTC timestamp suffix on collision rather than overwriting,
    so the author can compare runs.
    """
    rejected_root = pending_root / "_rejected"
    rejected_root.mkdir(parents=True, exist_ok=True)
    target = rejected_root / stub_dir.name
    if target.exists():
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = rejected_root / f"{stub_dir.name}_{ts}"
    shutil.move(str(stub_dir), str(target))
    return target


def _entity_exists(ontology_path: Path, target_ref: str) -> bool:
    """Probe whether a `type=character` entity with id==target_ref exists."""
    if not ontology_path.exists():
        return False
    with ontology_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for entity in data.get("entities") or []:
        if entity.get("id") == target_ref and entity.get("type") == "character":
            return True
    return False


def _ontology_append_visual_asset(
    ontology_path: Path, target_ref: str, asset: ImageAsset
) -> None:
    """Atomically append asset dict to entity.visual_assets where the entity
    id == target_ref AND type == 'character'.

    Read whole file → mutate the matching entity's `visual_assets` only →
    write back via temp file + replace + fsync. **Touches no other field**
    on any entity (boundary in the spec). 4-space indent + trailing newline
    per spec.
    """
    with ontology_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    matched = False
    for entity in data.get("entities") or []:
        if entity.get("id") == target_ref and entity.get("type") == "character":
            visual_assets = entity.setdefault("visual_assets", [])
            visual_assets.append(asset.model_dump(mode="json", exclude_none=False))
            matched = True
            break
    if not matched:
        raise ValueError(
            f"no character entity {target_ref!r} found in ontology {ontology_path}"
        )

    text = json.dumps(data, ensure_ascii=False, indent=4) + "\n"
    fd, tmp_path = tempfile.mkstemp(
        prefix=ontology_path.name + ".", suffix=".tmp", dir=str(ontology_path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, ontology_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _probe_png(png_path: Path) -> tuple[int, int, bool, int]:
    """Return (width, height, has_alpha, file_size_bytes).

    Raises OSError / UnidentifiedImageError on a broken PNG (caller turns
    that into a rejection — should not happen because validate_image_asset
    runs first, but defended for future re-orderings).
    """
    file_size = png_path.stat().st_size
    with Image.open(png_path) as img:
        width, height = img.size
        mode = img.mode
        has_alpha = "A" in mode
    return width, height, has_alpha, file_size


# ---------------------------------------------------------------------------
# Per-asset processor
# ---------------------------------------------------------------------------


def _process_one(
    stub_dir: Path,
    *,
    pending_root: Path,
    visuals_root: Path,
    manifest: Manifest,
    manifest_path: Path,
    ontology_path: Path,
    dry_run: bool,
) -> tuple[Manifest, ImportOutcome, dict | None]:
    """Validate + (unless dry-run) ingest one stub directory.

    Returns (possibly-updated manifest, outcome, parsed-meta-or-None). The
    parsed meta is returned so the caller can include target_ref /
    target_type / asset_role in the import_log row even on early rejection.

    Per-asset failures become outcomes with status="rejected" /
    "dry_run"; never raises out of band.
    """
    stub = stub_dir.name

    def reject(
        reason: str,
        *,
        validation_errors: list[str] | None = None,
        move: bool = True,
    ) -> ImportOutcome:
        if move and not dry_run:
            try:
                _move_to_rejected(stub_dir, pending_root)
            except OSError as exc:
                _logger.warning("failed to move %s to _rejected/: %s", stub_dir, exc)
        return ImportOutcome(
            asset_id_stub=stub,
            status="dry_run" if dry_run else "rejected",
            rejected_reason=reason,
            validation_errors=validation_errors,
        )

    # --- 1. Locate PNG ---
    pngs = sorted(stub_dir.glob("*.png"))
    if not pngs:
        # No PNG yet (author hasn't dropped the file in) — leave the dir in
        # place so they can retry once they download the image. We do not
        # move-to-rejected here.
        return manifest, reject("PNG missing", move=False), None
    if len(pngs) > 1:
        # Author needs to pick one; preserve dir for them to clean up.
        return (
            manifest,
            reject(
                f"multiple PNGs found ({len(pngs)}); expected exactly one named "
                f"{stub}.png",
                move=False,
            ),
            None,
        )
    png_path = pngs[0]
    if png_path.name != f"{stub}.png":
        return (
            manifest,
            reject(
                f"PNG {png_path.name!r} does not match expected name {stub}.png",
                move=False,
            ),
            None,
        )

    # --- 2. Parse meta.json ---
    meta_path = stub_dir / "meta.json"
    if not meta_path.exists():
        return manifest, reject("meta.json missing"), None
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return manifest, reject(f"meta.json malformed: {exc}"), None
    if not isinstance(meta, dict):
        return manifest, reject("meta.json root must be an object"), None

    missing = [k for k in _REQUIRED_META_KEYS if k not in meta]
    if missing:
        return (
            manifest,
            reject(f"meta.json missing required keys: {missing}"),
            meta,
        )

    asset_kind = meta["asset_kind"]
    if asset_kind not in ("character_sheet", "scene_background"):
        return manifest, reject(f"unsupported asset_kind {asset_kind!r}"), meta

    # --- 3. Mechanical validation (PIL + magic bytes + alpha rule) ---
    val_errors = validate_image_asset(png_path, asset_kind=asset_kind)
    blocking = [e for e in val_errors if e.severity == "error"]
    if blocking:
        return (
            manifest,
            reject(
                "image_validator: " + "; ".join(e.message for e in blocking),
                validation_errors=[e.code for e in blocking],
            ),
            meta,
        )

    # --- 4. Mirror-field consistency ---
    inconsistency = _check_meta_consistency(meta)
    if inconsistency:
        return manifest, reject(f"meta consistency: {inconsistency}"), meta

    target_ref = meta["target_ref"]
    target_type = meta["target_type"]

    # --- 5. Compute final path ---
    try:
        target_dir = _target_dir_for(target_type, target_ref, visuals_root)
    except ValueError as exc:
        return manifest, reject(f"target_ref/target_type: {exc}"), meta
    final_png_path = target_dir / f"{stub}.png"
    # The Pydantic file_path field has a strict pattern anchored at
    # "content/visuals/" — we always express it as a forward-slash relative
    # path regardless of platform.
    visuals_root_resolved = visuals_root.resolve()
    try:
        rel_to_visuals = final_png_path.resolve().relative_to(visuals_root_resolved)
    except ValueError:
        return (
            manifest,
            reject(
                f"final path escapes visuals root: {final_png_path}", move=False
            ),
            meta,
        )
    final_relpath = "content/visuals/" + rel_to_visuals.as_posix()

    # --- Ontology entity existence (only for character target) ---
    if target_type == "character":
        if not _entity_exists(ontology_path, target_ref):
            return (
                manifest,
                reject(
                    f"ontology has no character entity with id={target_ref!r}"
                ),
                meta,
            )

    # --- 6. Probe PNG ---
    try:
        width, height, has_alpha, file_size = _probe_png(png_path)
    except (OSError, UnidentifiedImageError) as exc:
        return manifest, reject(f"PIL probe failed: {exc}"), meta

    # --- 7. Build ImageAsset (Pydantic enforces enums + patterns) ---
    try:
        asset = ImageAsset(
            schema_version="0.2.0",
            asset_id=stub,
            asset_kind=asset_kind,
            target_ref=target_ref,
            target_type=target_type,
            asset_role=meta["asset_role"],
            character_ref=meta.get("character_ref"),
            location_ref=meta.get("location_ref"),
            source_mode=meta["source_mode"],
            format="png",
            width=width,
            height=height,
            file_size_bytes=file_size,
            has_alpha=has_alpha,
            file_path=final_relpath,
            prompt_hash=meta["prompt_hash"],
            generation_metadata=meta.get("generation_metadata"),
            style_reference_id=meta.get("style_reference_id"),
            reference_ids=meta.get("reference_ids", []),
            reference_license_note=meta.get("reference_license_note", ""),
            open_source_ok=meta.get("open_source_ok", False),
            commercial_ok=meta.get("commercial_ok", False),
            created_at=meta.get("created_at") or _now_iso(),
        )
    except Exception as exc:
        # Pydantic ValidationError or other construction failure — surface
        # as rejection so the author sees the offending field and can fix
        # the upstream meta.json / regenerate the prompt package.
        return manifest, reject(f"ImageAsset validation: {exc}"), meta

    # --- Idempotency: refuse duplicate asset_id ---
    if stub in manifest.assets:
        # Don't move to _rejected/: author may have re-run by mistake; the
        # prompt package should stay accessible for inspection.
        return (
            manifest,
            reject(
                f"asset_id {stub!r} already in manifest; remove it first to "
                f"re-import",
                move=False,
            ),
            meta,
        )

    # --- Dry-run: short-circuit before any disk mutation ---
    if dry_run:
        return (
            manifest,
            ImportOutcome(
                asset_id_stub=stub,
                status="dry_run",
                final_path=final_relpath,
            ),
            meta,
        )

    # --- 8. Mutate disk: move PNG, update manifest, update ontology ---
    if final_png_path.exists():
        # Disk-level collision (manifest didn't have it, but file did) —
        # something's off; preserve both so the author can investigate.
        return (
            manifest,
            reject(
                f"final path already exists on disk: {final_relpath} "
                f"(possible orphan from a prior partial run)",
                move=False,
            ),
            meta,
        )
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(png_path), str(final_png_path))

    new_manifest = add_asset(manifest, asset)
    save_manifest(new_manifest, manifest_path)
    if target_type == "character":
        _ontology_append_visual_asset(ontology_path, target_ref, asset)

    # --- 9. Cleanup _pending dir (best-effort) ---
    try:
        shutil.rmtree(stub_dir)
    except OSError as exc:
        _logger.warning(
            "imported %s but failed to rmtree %s: %s", stub, stub_dir, exc
        )

    return (
        new_manifest,
        ImportOutcome(
            asset_id_stub=stub,
            status="imported",
            final_path=final_relpath,
        ),
        meta,
    )


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def _write_log_row(
    outcome: ImportOutcome, *, meta: dict | None, batch_name: str | None
) -> None:
    """Write one import_log.jsonl row reflecting `outcome`."""
    record: dict = {
        "timestamp": _now_iso(),
        "asset_id_stub": outcome.asset_id_stub,
        "batch_name": batch_name,
        "target_ref": (meta or {}).get("target_ref"),
        "target_type": (meta or {}).get("target_type"),
        "asset_role": (meta or {}).get("asset_role"),
        "status": outcome.status,
        "validation_errors": outcome.validation_errors or [],
        "rejected_reason": outcome.rejected_reason,
        "final_asset_id": (
            outcome.asset_id_stub if outcome.status == "imported" else None
        ),
        "final_path": outcome.final_path,
        "imported_at": _now_iso() if outcome.status == "imported" else None,
    }
    import_log.append(record)


def run_import(
    *,
    asset_id: str | None,
    all_pending: bool,
    dry_run: bool,
    pending_root: Path = PENDING_ROOT,
    visuals_root: Path = VISUALS_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    ontology_path: Path = DEFAULT_ONTOLOGY_PATH,
    batch_name: str | None = None,
) -> list[ImportOutcome]:
    """Programmatic entry-point used by the CLI and the tests.

    Exactly one of `asset_id` / `all_pending` must be given (matches the
    mutually-exclusive argparse group).
    """
    if (asset_id is None) == (not all_pending):
        raise ValueError("specify exactly one of asset_id or all_pending=True")

    if asset_id:
        stub_dirs = [pending_root / asset_id]
    elif pending_root.exists():
        # Skip _underscore-prefixed entries (`_rejected/`, future `_archive/`).
        stub_dirs = sorted(
            d for d in pending_root.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        )
    else:
        stub_dirs = []

    manifest = load_manifest(manifest_path)
    outcomes: list[ImportOutcome] = []

    for stub_dir in stub_dirs:
        if not stub_dir.exists() or not stub_dir.is_dir():
            outcome = ImportOutcome(
                asset_id_stub=stub_dir.name,
                status="dry_run" if dry_run else "rejected",
                rejected_reason="pending stub directory missing",
            )
            _write_log_row(outcome, meta=None, batch_name=batch_name)
            outcomes.append(outcome)
            continue

        manifest, outcome, meta = _process_one(
            stub_dir,
            pending_root=pending_root,
            visuals_root=visuals_root,
            manifest=manifest,
            manifest_path=manifest_path,
            ontology_path=ontology_path,
            dry_run=dry_run,
        )
        _write_log_row(outcome, meta=meta, batch_name=batch_name)
        outcomes.append(outcome)

    return outcomes


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m generator.image_import",
        description=(
            "Ingest manual-mode image assets from content/visuals/_pending/ "
            "into content/visuals/<sub>/, the manifest, and (for character "
            "assets) the matching ontology entity's visual_assets array."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--asset-id",
        help="Process the single _pending/<asset_id>/ stub directory.",
    )
    group.add_argument(
        "--all-pending",
        action="store_true",
        help=(
            "Process every non-_underscore-prefixed subdir of _pending/ "
            "(skips _rejected/)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate + plan only; do not move PNG, mutate manifest / "
            "ontology, or remove the _pending stub directory."
        ),
    )
    parser.add_argument(
        "--batch-name",
        default=None,
        help=(
            "Optional batch label written to each import_log.jsonl row "
            "(matches T-1.5.8 visual_experiment batch directories)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    args = _build_arg_parser().parse_args(argv)
    outcomes = run_import(
        asset_id=args.asset_id,
        all_pending=args.all_pending,
        dry_run=args.dry_run,
        batch_name=args.batch_name,
    )
    n_imp = sum(1 for o in outcomes if o.status == "imported")
    n_rej = sum(1 for o in outcomes if o.status == "rejected")
    n_dry = sum(1 for o in outcomes if o.status == "dry_run")
    print(
        f"image_import: imported={n_imp} rejected={n_rej} dry_run={n_dry}"
    )
    for o in outcomes:
        marker = {"imported": "OK", "rejected": "FAIL", "dry_run": "DRY"}.get(
            o.status, "??"
        )
        line = f"  [{marker}] {o.asset_id_stub}"
        if o.final_path:
            line += f" -> {o.final_path}"
        if o.rejected_reason:
            line += f"  ({o.rejected_reason})"
        print(line)
    return 0 if n_rej == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
