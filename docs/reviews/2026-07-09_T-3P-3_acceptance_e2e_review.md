# Code Review — PR #90 T-3P-3 acceptance E2E

**Review target**: PR #90 / branch `claude/t3p3-acceptance-e2e`（T-3P-3｜回流验收管线接线 + E2E 闭环实测）  
**Reviewer**: gpt-5.5 via relay API  
**Date**: 2026-07-09

---

## Summary

本次 review 发现 **2 条 findings**：🔴 1 / 🟡 1 / 🟢 0。

Top priority：**验收闸目前没有把 `validator.validate()` 的一致性层本体解析错误作为硬拦，导致正例 scene 在 37 条 consistency issue 存在时仍 PASS 并 `--land`；这违反 T-3P-3 对“三层 schema/graph/cons 硬拦”的任务规格。**

---

## Findings

### 🔴 F-1 [ERR/ARCH] 一致性层本体解析错误被降级为 note，导致“三层校验”没有硬拦

**位置**：

- `generator/promptpack/acceptance.py:24-35`
- `generator/promptpack/acceptance.py:151-161`（`_split_consistency()`）
- `content/_e2e_writer_loop/lucy_roadhouse/scene.acceptance.json:6-199`
- `docs/reviews/master_plan/2026-07-09_pa_pb_e2e_report.md:20-27`, `:116-140`

**问题**：

T-3P-3 规格明确要求验收管线接上：

> `validator.validate(graph)`（三层：schema / graph / cons）  
> `validate_graph_mechanical(..., generation_source="human")`  
> AP flag 记录不拦截

L2 重点也特别要求确认“三层(schema/graph/cons)+机械预检+AP 记录是否都接上且 pass/fail 硬拦层正确”。

但当前实现把 consistency 层拆成：

- `consistency_closure_errors`：硬拦
- `consistency_ontology_notes`：只记录，不影响 `passed`

`acceptance.py` 注释与逻辑都明确写了本体解析错误不阻断：

```python
_ONTOLOGY_RESOLUTION_MARKER = "does not resolve in ontology"
...
if _ONTOLOGY_RESOLUTION_MARKER in issue.message:
    ontology_notes.append(issue)
else:
    closure_errors.append(issue)
```

结果是正例 `scene.acceptance.json` 显示：

```json
{
  "passed": true,
  "blocking_error_count": 0,
  "guidance": "验收通过...（另有 37 条本体解析待挂...不拦落地）",
  "consistency_ontology_notes": [ ... 37 items ... ]
}
```

这意味着当前“验收 PASS”并不等于 `validator.validate()` 的三层全部通过；而是把 consistency 层的一类真实 issue 改成了非阻断 note。这个行为不只是文案差异，而是验收闸语义变化。

**为什么严重**：

1. 任务要求的硬拦层是“三层 + 机械”，只有 AP 明确“不拦截”。本体解析属于 consistency 层，不在 AP 豁免范围内。
2. `/content/CLAUDE.md` 也写明 content 文件必须通过 `/validator` 校验后才能入库。即使 `_e2e_writer_loop` 是隔离目录，本任务也要求用它作为 E2E 落地证据；落地证据不能建立在“validator consistency issue 被改成 note”的口径上。
3. ADR-006 / CLAUDE.md 规则 5 的核心是“世界本体是真相之源”。回流验收如果允许 `scene_anchor` / `character_refs` / `location_ref` 全部 unresolved 仍 PASS，就不能称为“本体一致性守门”。
4. E2E 报告因此把一个三层 consistency 未全过的场景声明为 ADR-039 完成口径达标，证据口径不成立。

**建议修法**：

让 `validator.validate(graph)` 的三层 issue 全部参与硬拦，至少在 T-3P-3 首版中不要私自降级 consistency 本体解析错误：

- `schema_errors`、`graph_errors`、`consistency_errors` 全部计入 `blocking_error_count`。
- AP flags 继续只记录不阻断。
- 机械预检继续按 `generation_source="human"` 只豁免 monotonic，其余硬拦。

如果 lucy E2E fixture 确实引用未发布本体，那么应二选一：

1. **给 E2E fixture 配套最小本体**，让 `char_lucy` / `scene_hibo_roadhouse` 可解析后再声明 PASS；或
2. **把“本体解析降级为 note”上提为单独设计决策/任务规格变更**，经作者明确授权后再改验收口径，而不能在 T-3P-3 的施工任务里直接改变 cons 层硬拦语义。

---

### 🟡 F-2 [TEST] E2E 报告的“完成口径达标”结论依赖 F-1 的放宽口径，不能作为当前 PR 的有效收官证据

**位置**：

- `docs/reviews/master_plan/2026-07-09_pa_pb_e2e_report.md:20-27`
- `docs/reviews/master_plan/2026-07-09_pa_pb_e2e_report.md:165-185`
- `docs/reviews/master_plan/2026-07-09_pa_pb_e2e_report.md:187-193`

**问题**：

E2E 报告在 TL;DR 与 ROADMAP 对照表中写：

- 验收闸 PASS（硬拦 0；37 条本体解析待挂）
- `--land` 成功
- ADR-039 首版核心闭环达标

但该 PASS 的前提是 F-1 中的“本体解析不阻断”。如果按任务规格原本要求的三层校验硬拦，当前正例应当 fail，而不是 pass。因此报告里的“完成标志新口径达标”目前是建立在错误验收口径上的。

这会给 L2 验收和作者造成误导：看起来 P-A → P-B → 验收 → 落地 → 播放已经完整闭环，但实际上“验收”环节没有证明 consistency 层通过。

**建议修法**：

在修复 F-1 后重跑 E2E，并同步改报告：

- 如果补齐最小本体后三层全过：保留“达标”，并把 `consistency_ontology_notes` 变为 0 或明确 validator 三层无 issue。
- 如果暂时无法补齐本体：报告应改为“播放链路可跑通，但 ADR-039 完成口径未达标 / consistency 层仍待补齐”，不能写“完成标志达标”。

---

## Non-findings / 已核对重点

- `--land` 只应在验收 pass 后写入并记录 `generation_method="writer_ingest"`：PR 描述和测试说明显示已覆盖，未在 diff 片段中发现相反证据。
- AP flag “记录不拦截”符合任务规格与 multipass 先例。
- E2E 报告如实写明路线 A 下验收闸对“纯正文错误”基本恒 pass，这一点是合规的；问题不在诚实边界说明，而在把 consistency 本体解析错误降级为非阻断。
- 终端播放命令使用 `python -m engine content/_e2e_writer_loop/lucy_roadhouse/scene.json`，不是 `python -m engine.player`，符合任务要求。
- 未见 `/engine`、`/validator`、`/schema`、`/state` 被修改的证据；`/validator` 以只读 import 调用，边界本身 OK。

---

## Required C-stage action

1. 先修 F-1：恢复 `validator.validate()` 三层 issue 的硬拦语义，或上提并获得作者明确授权后再改变 cons 层口径。
2. 用可通过 consistency 层的 fixture 重跑正例 E2E。
3. 更新 `scene.acceptance.{md,json}` 与 `2026-07-09_pa_pb_e2e_report.md`，确保“PASS / 达标”只在 schema + graph + cons + mechanical 全部硬拦层通过时出现。

---

## 3-line author summary

总 finding 数：2。  
严重度分布：🔴 1 / 🟡 1 / 🟢 0。  
Top priority：修正验收闸对 consistency 本体解析错误的非阻断处理；当前 E2E PASS 口径不满足 T-3P-3 “三层 schema/graph/cons 硬拦”要求。


<!-- delivered via tools/cross_review.py (governance v0.6 §13); model=gpt-5.5; prompt_chars=241070; usage={"completion_tokens": 4361, "total_tokens": 123669, "prompt_tokens": 119308, "prompt_tokens_details": {"cached_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0}} -->
