# 回流验收报告：lucy_roadhouse_multipass

**判定**：✅ 通过（PASS）　|　节点数 35　|　硬拦错误 0

> 验收通过：结构完整、闭合无违规、机械预检干净。（另有 37 条本体解析待挂——引用了当前未加载的本体条目，属 fixture/环境依赖，不拦落地）

---

## 硬拦层（决定 pass/fail）

### Schema 层：0

### Graph 层（图论）：0

### 一致性层 · 闭合违规（说话人闭合 / option_id 唯一）：0

### 机械预检（source=human）：0

---

## 只记录层（不影响 pass/fail）

### 本体解析待挂：37

> 这些引用未在**当前加载的本体**里解析——属 fixture / 环境依赖（隔离目录 E2E 场景刻意引用未发布本体）。正式内容入库时对着已发布本体重跑才是本体守门；此处不拦落地。

- `scene_anchor`：scene_anchor 'scene_hibo_roadhouse' does not resolve in ontology
- `character_refs[0]`：character_refs entry 'char_lucy' does not resolve in ontology
- `opening`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `soft_private_line_b1`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `soft_private_line_b2`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `soft_private_line_b3`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `soft_private_line_b4`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `soft_private_line_b5`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `soft_private_line_b6`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `soft_private_line_b7`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `soft_private_line_b8`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `end_soft_leave`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `money_line_b1`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `money_line_b2`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `money_line_b3`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `money_line_b4`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `money_line_b5`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `money_line_b6`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `end_money_leave`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `watch_corner`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `observed_soft_line_b1`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `observed_soft_line_b2`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `observed_soft_line_b3`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `observed_soft_line_b4`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `observed_soft_line_b5`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `observed_soft_line_b6`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `end_observed_leave`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `basement_line_b1`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `basement_line_b2`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `basement_line_b3`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `basement_line_b4`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `end_basement_leave`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `pressure_line_b1`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `pressure_line_b2`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `pressure_line_b3`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `pressure_line_b4`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology
- `end_pressure_leave`：location_ref 'scene_hibo_roadhouse' does not resolve in ontology

### 反模式 flag（AP 记录）：0
