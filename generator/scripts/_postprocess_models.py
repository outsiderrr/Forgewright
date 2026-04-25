"""Post-process datamodel-code-generator output for /generator/models/_generated/.

Why this exists:
    Directory-mode codegen produces one .py per source .schema.json, but it
    names every per-file root class `Schema` (and the StateCondition oneOf
    variants `Schema`, `SchemaModel`, `SchemaModel1`, `SchemaModel2`,
    `SchemaModel3`). --use-title-as-name fixes the names but causes
    datamodel-codegen to inline the referenced schemas into __init__.py,
    collapsing the per-file layout we want. So we generate first, then rename
    here.

Renames performed:
    state_effect.py
        Schema             -> StateEffect
    state_condition.py
        Schema             -> StateConditionLeaf
        SchemaModel        -> StateConditionAllOf
        SchemaModel1       -> StateConditionAnyOf
        SchemaModel2       -> StateConditionNot
        SchemaModel3       -> StateCondition       (the public RootModel union)
    option.py
        Schema             -> Option
    node.py
        Schema             -> Node
    dialogue_graph.py
        (just renamed from __init__.py; DialogueGraph already correctly named)

Cross-file references like `state_condition.SchemaModel3` are rewritten to
`state_condition.StateCondition` consistently.

Renaming uses tokenize so we touch identifiers only, never strings (docstrings
mention "JSON Schema" as a concept and must survive untouched) or comments.

Driven by /generator/scripts/regenerate_models.sh — do not run by hand outside
that flow; the pre-conditions on input filenames are not validated here.
"""

from __future__ import annotations

import io
import sys
import token
import tokenize
from pathlib import Path

OUT_DIR = Path(sys.argv[1]).resolve()

# Per-file identifier renames. Order matters: longer SchemaModel<N> must come
# before bare `SchemaModel` and `Schema`, so we apply each file's mapping as a
# dict (already keyed by exact identifier).
LOCAL_RENAMES: dict[str, dict[str, str]] = {
    "state_effect.py": {
        "Schema": "StateEffect",
    },
    "state_condition.py": {
        "Schema": "StateConditionLeaf",
        "SchemaModel": "StateConditionAllOf",
        "SchemaModel1": "StateConditionAnyOf",
        "SchemaModel2": "StateConditionNot",
        "SchemaModel3": "StateCondition",
    },
    "option.py": {
        "Schema": "Option",
    },
    "node.py": {
        "Schema": "Node",
    },
}

# Cross-file references: an attribute access `module.OldName` -> `module.NewName`.
# These are applied as token-pair rewrites (NAME `module` + OP `.` + NAME `OldName`).
CROSS_RENAMES: dict[tuple[str, str], str] = {
    ("state_condition", "SchemaModel3"): "StateCondition",
    ("state_effect", "Schema"): "StateEffect",
    ("option", "Schema"): "Option",
    ("node", "Schema"): "Node",
}


def rewrite_source(source: str, local_map: dict[str, str]) -> str:
    """Rename NAME tokens via local_map; rewrite `module.Name` per CROSS_RENAMES.

    Strings and comments are passed through verbatim because tokenize emits them
    as separate token types (STRING / COMMENT) that we never modify.
    """
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))

    # Walk tokens; when we see a NAME that is a known module followed by '.' and
    # another NAME that matches a CROSS_RENAMES key, rewrite the third token.
    # Otherwise apply local_map to NAME tokens.
    new_tokens: list[tokenize.TokenInfo] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if (
            tok.type == token.NAME
            and i + 2 < len(tokens)
            and tokens[i + 1].type == token.OP
            and tokens[i + 1].string == "."
            and tokens[i + 2].type == token.NAME
            and (tok.string, tokens[i + 2].string) in CROSS_RENAMES
        ):
            new_name = CROSS_RENAMES[(tok.string, tokens[i + 2].string)]
            new_tokens.append(tok)
            new_tokens.append(tokens[i + 1])
            new_tokens.append(tokens[i + 2]._replace(string=new_name))
            i += 3
            continue

        if tok.type == token.NAME and tok.string in local_map:
            new_tokens.append(tok._replace(string=local_map[tok.string]))
        else:
            new_tokens.append(tok)
        i += 1

    return tokenize.untokenize(new_tokens)


def process_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    local_map = LOCAL_RENAMES.get(path.name, {})
    new_text = rewrite_source(text, local_map)
    path.write_text(new_text, encoding="utf-8")


def main() -> None:
    # Codegen emits the dialogue_graph root into __init__.py because it was the
    # entry input. Move it to dialogue_graph.py so each schema gets its own file.
    init_py = OUT_DIR / "__init__.py"
    dg_py = OUT_DIR / "dialogue_graph.py"
    if init_py.exists():
        init_py.replace(dg_py)

    for fname in (
        "state_effect.py",
        "state_condition.py",
        "option.py",
        "node.py",
        "dialogue_graph.py",
    ):
        target = OUT_DIR / fname
        if target.exists():
            process_file(target)

    # Re-emit a minimal package marker — the curated re-exports live in
    # /generator/models/__init__.py, not here.
    (OUT_DIR / "__init__.py").write_text(
        "# Auto-generated marker file. DO NOT EDIT MANUALLY.\n"
        "# Re-run /generator/scripts/regenerate_models.sh to refresh this package.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
