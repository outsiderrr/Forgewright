# test_scene_v0 — T-0.8 手写测试场景《铁誓驿站》

本目录是阶段 0 的手写测试内容，把 `docs/SCENE_v0.md` §3 的五节点场景落成真 JSON，并把 §6 的三种错误变体各自独立成文件，供 T-0.9 validator 后续消费。

## 文件清单

| 文件 | 内容 | 预期校验结果 |
|---|---|---|
| `scene.json` | SCENE_v0.md §3 完整 5 节点场景（N1–N5，8 选项） | schema 层 **PASS**；后续 T-0.9 图论层亦 PASS |
| `scene_broken_dangling.json` | §6 E1 例一：N3.opt_reveal_to_corvan.target_node_id 改为 `end_iron_gallows`（不存在） | schema 层仍 **PASS**（正则合法），**T-0.9 图论层拒收**（target 不在 nodes 映射中） |
| `scene_broken_unreachable.json` | §6 E2：新增孤岛节点 `orphan_warning_from_vellin`，无任何入边 | schema 层仍 **PASS**（节点本身合法），**T-0.9 图论层拒收**（从 entry 不可达） |
| `scene_broken_schema.json` | §6 E3c：`graph_id` 改为 `Glades.WayStation#01`（违反 D7 正则） | **schema 层直接拒收**（`pattern` 关键字） |
| `verify.py` | 一次性核验脚本，断言上述预期。仅供人工验收，不是业务代码 | — |

## 与规范文档的对应

- 节点文本、选项文本、StateEffect、StateCondition 严格复刻 `docs/SCENE_v0.md` §3；未自创内容。
- 字段名、枚举取值、必需字段依据 `docs/SCHEMA_v0.md` v0.1.1 + `/schema/*.schema.json`。
- 架构决策落地（作者 2026-04-24 裁定）：D5 采用点分字符串 `"relationship.vellin.trust"`；D6 采用 SCHEMA_v0.md §3.4/§3.5 候选起点（`set`/`inc`/`dec` 与 `eq`/`gte`/`has`）。

## 使用

```
python content/test_scene_v0/verify.py
```

期望输出：`OK: positive assertions=3, negative assertions=1`。
