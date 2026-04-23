"""T-0.8 一次性核验脚本。非业务代码，仅用于验收 /content/test_scene_v0/ 四个 JSON。

注意：JSON Schema 只覆盖结构 / 枚举 / 正则层。图论问题——
  - scene_broken_dangling.json 的 target_node_id 指向不存在节点
  - scene_broken_unreachable.json 的孤岛节点
这些 scene_broken_dangling / scene_broken_unreachable 在 schema 层仍会通过，
留给 T-0.9 validator 的图论层抓。本脚本对这两个文件断言 schema PASS，
并以注释标注它们应被 T-0.9 拒收。scene_broken_schema.json 的 graph_id 违反 D7
正则，schema 层直接拒收。
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schema"
SCHEMAS = ["dialogue_graph.schema.json", "node.schema.json", "option.schema.json",
           "state_effect.schema.json", "state_condition.schema.json"]
HERE = Path(__file__).resolve().parent

reg = Registry()
for n in SCHEMAS:
    s = json.loads((SCHEMA_DIR / n).read_text(encoding="utf-8"))
    reg = reg.with_resource(uri=s["$id"], resource=Resource.from_contents(s))
root = json.loads((SCHEMA_DIR / "dialogue_graph.schema.json").read_text(encoding="utf-8"))
V = Draft202012Validator(root, registry=reg)

def passes(p: Path) -> bool:
    return V.is_valid(json.loads(p.read_text(encoding="utf-8")))

pos = neg = 0
# scene.json: schema 层通过
assert passes(HERE / "scene.json"), "scene.json should pass schema validation"; pos += 1
# scene_broken_dangling.json: 图论问题，schema 层仍通过（T-0.9 validator 抓）
assert passes(HERE / "scene_broken_dangling.json"), "dangling variant should still pass schema layer (graph-layer reject belongs to T-0.9)"; pos += 1
# scene_broken_unreachable.json: 图论问题，schema 层仍通过（T-0.9 validator 抓）
assert passes(HERE / "scene_broken_unreachable.json"), "unreachable variant should still pass schema layer (graph-layer reject belongs to T-0.9)"; pos += 1
# scene_broken_schema.json: graph_id 违反 D7 正则，schema 层即拒收
assert not passes(HERE / "scene_broken_schema.json"), "schema variant must be rejected by JSON Schema layer"; neg += 1

print(f"OK: positive assertions={pos}, negative assertions={neg}")
sys.exit(0)
