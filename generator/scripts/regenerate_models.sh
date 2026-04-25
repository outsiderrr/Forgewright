#!/usr/bin/env bash
# Regenerate /generator/models/_generated/*.py from /schema/*.json via datamodel-code-generator.
#
# Source of truth: /schema/*.json (CLAUDE.md rule 6 + ADR-003).
# Do NOT hand-edit anything in /generator/models/_generated/.
#
# Strategy:
#   1. datamodel-codegen runs in directory-output mode against the entry schema
#      (dialogue_graph.schema.json). It follows $ref to the other 4 schemas and
#      emits one .py per schema (the entry one ends up in __init__.py).
#   2. _postprocess_models.py renames the codegen-default `Schema` /
#      `SchemaModel*` classes to their schema-title-derived names (Node, Option,
#      StateEffect, StateConditionLeaf/AllOf/AnyOf/Not, StateCondition) and
#      moves the entry root from __init__.py to dialogue_graph.py.
#   3. A "do not edit" header is prepended to each .py file.
#
# Usage: bash generator/scripts/regenerate_models.sh   (run from anywhere; paths
# are resolved relative to this script's location).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCHEMA_DIR="$REPO_ROOT/schema"
OUT_DIR="$REPO_ROOT/generator/models/_generated"

mkdir -p "$OUT_DIR"

# Wipe stale generated .py files (we'll re-emit __init__.py at the end).
find "$OUT_DIR" -maxdepth 1 -type f -name '*.py' -delete

echo "[regenerate_models] running datamodel-codegen -> $OUT_DIR"
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
