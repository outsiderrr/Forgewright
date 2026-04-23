"""T-0.7 本体桩加载器。

阶段 0 最小实现：扫描本目录下所有 `*.json` 文件，把每个文件中 `entities` 数组里的
条目按 `id` 建索引。**正式本体 Schema 将在后续任务定义**；当前仅作为阶段 0 最小实现
用以解析 SCENE_v0.md 场景中出现的 `char_*` / `scene_*` / `loc_*` ref 字符串。
"""
from __future__ import annotations

import json
from pathlib import Path

_ONTOLOGY_DIR = Path(__file__).resolve().parent
_CACHE: dict[str, dict] | None = None


def _load_all() -> dict[str, dict]:
    global _CACHE
    if _CACHE is None:
        index: dict[str, dict] = {}
        for json_file in sorted(_ONTOLOGY_DIR.glob("*.json")):
            payload = json.loads(json_file.read_text(encoding="utf-8"))
            for entity in payload.get("entities", []):
                entity_id = entity["id"]
                if entity_id in index:
                    raise ValueError(
                        f"duplicate ontology id {entity_id!r} "
                        f"(second occurrence in {json_file.name})"
                    )
                index[entity_id] = entity
        _CACHE = index
    return _CACHE


def get_entity(entity_id: str) -> dict | None:
    return _load_all().get(entity_id)


def _reset_cache_for_tests() -> None:
    global _CACHE
    _CACHE = None
