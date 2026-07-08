# 回流验收报告：lucy_roadhouse_multipass

**判定**：❌ 未通过（FAIL）　|　节点数 35　|　硬拦错误 41

> 验收未通过，未落地：schema 层 1 错（scene.json 结构不合 Schema）；一致性层 38 错（说话人闭合 / option_id 唯一 / 本体引用未解析）；机械预检 2 错（effects / condition 形态违规）。闭合 / 机械 / schema / graph 类是编剧改不到的结构字段（核对 design.json / 合并流程 / 是否有人手改 scene.json）；本体解析类是场景引用了当前未加载的本体条目（补齐本体或修正 ref 后重跑；本体一致性 = 真相之源守门 ADR-006）。

---

## 硬拦层（决定 pass/fail）

### Schema 层：1

- `/nodes/opening/options/0/effects/0/op`：'not_a_real_op' is not one of ['set', 'inc', 'dec', 'add', 'remove']

### Graph 层（图论）：0

### 一致性层（说话人闭合 / option_id 唯一 / 本体引用解析）：38

- `scene_anchor`：scene_anchor 'scene_hibo_roadhouse' does not resolve in ontology
- `character_refs[0]`：character_refs entry 'char_lucy' does not resolve in ontology
- `opening/dialogue[3]`：dialogue[3].speaker_ref 'char_ghost_writer' is not declared in character_refs
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

### 机械预检（source=human）：2

- `opening` [EFFECT_OP_INVALID] `options[0].effects[0].op`：state_effect.op 'not_a_real_op' not in ('set', 'inc', 'dec', 'add', 'remove')
- `opening` [PATH_NS_INVALID] `options[0].effects[0].path`：state path 'flags.some_flag' first segment 'flags' not in namespaces ('world', 'faction', 'relationship', 'flag', 'player', 'knowledge')

---

## 只记录层（不影响 pass/fail）

### 反模式 flag（AP 记录）：0
