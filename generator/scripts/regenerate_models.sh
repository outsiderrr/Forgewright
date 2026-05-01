#!/usr/bin/env bash
# Regenerate /generator/models/_generated/*.py from /schema/*.json via datamodel-code-generator.
#
# Source of truth: /schema/*.json (CLAUDE.md rule 6 + ADR-003).
# Do NOT hand-edit anything in /generator/models/_generated/.
#
# Strategy (two-pass; T-1.5.3 carryover from T-1.5.2 #4.1):
#   1. Wipe stale generated .py files once, before any codegen run.
#   2. Codegen pass #1 — entry = dialogue_graph.schema.json (multi-file via
#      $ref). With `--output dir/ --class-name DialogueGraph`, codegen names
#      the entry root file after the class (dialogue_graph.py) and emits
#      sibling files for each $ref'd schema (node, option, state_effect,
#      state_condition).
#   3. Codegen pass #2 — entry = image_asset.schema.json (standalone; no
#      $refs). For a single-root, no-$ref entry, codegen needs an explicit
#      output FILE (not a directory) — passing the directory triggers an
#      IsADirectoryError inside its writer.
#   4. _postprocess_models.py renames the codegen-default `Schema` /
#      `SchemaModel*` classes in pass-#1 outputs to their schema-title-derived
#      names (Node, Option, StateEffect, StateConditionLeaf/AllOf/AnyOf/Not,
#      StateCondition). image_asset.py is already correctly named via
#      `--class-name ImageAsset` and needs no class rename — postprocess
#      leaves it alone and just writes the marker __init__.py.
#   5. A "do not edit" header is prepended to each .py file.
#
# Usage: bash generator/scripts/regenerate_models.sh   (run from anywhere; paths
# are resolved relative to this script's location).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCHEMA_DIR="$REPO_ROOT/schema"
OUT_DIR="$REPO_ROOT/generator/models/_generated"

mkdir -p "$OUT_DIR"

# Wipe stale generated .py files (single wipe, before any codegen run).
find "$OUT_DIR" -maxdepth 1 -type f -name '*.py' -delete

echo "[regenerate_models] codegen #1: dialogue_graph (multi-file via \$ref) -> $OUT_DIR"
datamodel-codegen \
  --input "$SCHEMA_DIR/dialogue_graph.schema.json" \
  --input-file-type jsonschema \
  --output "$OUT_DIR/" \
  --output-model-type pydantic_v2.BaseModel \
  --use-schema-description \
  --use-double-quotes \
  --target-python-version 3.11 \
  --use-standard-collections \
  --use-union-operator \
  --formatters black isort \
  --disable-timestamp \
  --class-name DialogueGraph

echo "[regenerate_models] codegen #2: image_asset (standalone) -> $OUT_DIR/image_asset.py"
datamodel-codegen \
  --input "$SCHEMA_DIR/image_asset.schema.json" \
  --input-file-type jsonschema \
  --output "$OUT_DIR/image_asset.py" \
  --output-model-type pydantic_v2.BaseModel \
  --use-schema-description \
  --use-double-quotes \
  --target-python-version 3.11 \
  --use-standard-collections \
  --use-union-operator \
  --formatters black isort \
  --disable-timestamp \
  --class-name ImageAsset

echo "[regenerate_models] post-processing class names"
python3 "$SCRIPT_DIR/_postprocess_models.py" "$OUT_DIR"

# Prepend a hard "do not edit" header to every generated .py (skip __init__.py;
# the post-processor already wrote a minimal marker comment there).
HEADER_PREFIX="# Auto-generated from /schema"
HEADER_SUFFIX=".json by datamodel-code-generator. DO NOT EDIT MANUALLY. Re-run /generator/scripts/regenerate_models.sh"

for f in "$OUT_DIR"/*.py; do
  base="$(basename "$f")"
  case "$base" in
    __init__.py) continue ;;
  esac
  schema_stem="${base%.py}"
  header="${HEADER_PREFIX}/${schema_stem}.schema${HEADER_SUFFIX}"
  tmp="$f.tmp"
  { echo "$header"; cat "$f"; } > "$tmp"
  mv "$tmp" "$f"
done

echo "[regenerate_models] done. files in $OUT_DIR:"
ls "$OUT_DIR"
