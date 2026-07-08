# Code Review — PR #82 T-3P-0 beat_split

评审者：gpt-5.5 via relay API  
评审日期：2026-07-08  
评审目标：PR #82 `feat(generator): T-3P-0 确定性拆拍器 + structure-only 模式 + 回流格式契约（软地基）`  
范围：打包 diff（base = main；分支 `claude/affectionate-jones-d29ee2`）

## 摘要

- Findings：2
- 严重度：🔴 1 / 🟡 1 / 🟢 0
- Top priority：先处理 🔴 F-001：`.gitignore` 是 allowed 白名单外改动；按任务 B 阶段规则属于停批项，需要撤回或取得显式授权后重审。

## 总体判断

这版主体实现方向基本贴合 T-3P-0：

- `beats_plan` 采用 dict 按链分组，契约清晰；
- `run_config` 已随 structure-only design 落盘；
- `format_spec` 把 E1–E8 边界写成可测试常量，且补了 C 批关注的 0 条 options、重复 key、多行值范围等边界；
- 两个 loader 明确冻结 wrapper，并补了坏输入、legacy、失败运行、topology↔beats_plan、choice 出边覆盖复算；
- `--structure-only` 只产 design/metrics 的形态有测试钉住；
- `assemble.py` 公开别名未改变原函数行为；
- `writer_ingest` 枚举扩值有既有值回归测试。

但有一个治理层硬问题：PR 修改了根 `.gitignore`，不在本任务 allowed 白名单内；任务单明确要求 B 阶段见到越界 diff 即 🔴 停批。另有一个契约边界问题：`run_config` loader 只检查字段存在，不检查叶类型/额外字段，作为 P-A/P-B 共同输入契约还不够硬。

## Findings

### 🔴 F-001 [ARCH] `.gitignore` 是 allowed 白名单外改动，按任务规则应停批

**位置**：`.gitignore:59-68`

**问题**

本 PR 修改了仓库根 `.gitignore`：

```diff
-/generator/experiments/
+/generator/experiments/*
+!/generator/experiments/multipass_structure/
+/generator/experiments/multipass_structure/*
+!/generator/experiments/multipass_structure/2026-06-29_t3p_fixture/
```

但 T-3P-0 的硬边界 allowed 白名单只授权了：

- `/generator/multipass/`
- `/generator/scripts/run_multipass_scene.py`
- `/generator/promptpack/`
- `/generator/version_recorder.py`
- 两处 tests
- 拆拍样例/fixture 落盘目录

没有授权修改仓库根 `.gitignore`。任务单 B 阶段还明确写了：diff 是否越出 allowed 白名单，**越出即 🔴 停批**。

我理解这处修改的意图：让 `generator/experiments/multipass_structure/2026-06-29_t3p_fixture/` 未来新增 golden 文件不再依赖 `git add -f`，避免漏提交。这个理由工程上合理，但它仍然是白名单外文件修改。A 阶段 PR 描述也已自报该点，B 阶段应按硬规则裁断为越界。

**影响**

- 违反本任务的硬边界/allowed 白名单。
- 如果本次放过，会削弱后续软地基任务的“只在授权文件内浇筑契约”的治理约束。
- `.gitignore` 是仓库级行为，影响的不只是本 PR 的 fixture；它改变了整个 `generator/experiments/multipass_structure/` 下文件被 git 追踪的默认行为。

**建议修复**

二选一：

1. **保守修复（推荐）**：撤回 `.gitignore` 改动，保留 fixture 文件本身通过 `git add -f` 强制提交；并在 fixture `README.md` 里写明未来新增 golden 需要 `git add -f`。
2. **如作者确实要长期放行该 fixture 目录**：让作者/规划会话显式追加授权 `.gitignore` 为本 PR allowed 文件，然后本 PR 更新任务说明或 PR 描述，再重新进入 B 审。不要在当前授权下静默合入。

---

### 🟡 F-002 [ERR] `run_config` loader 只校验字段存在，未校验叶类型/额外字段；共同输入契约仍可被坏 design 穿透

**位置**：`generator/promptpack/io.py:203-212`

**问题**

`load_design_artifact()` 会调用 `_check_run_config_shape()`，但当前实现只检查：

```python
if not isinstance(run_config, dict):
    ...
missing = [f for f in RUN_CONFIG_FIELDS if f not in run_config]
if missing:
    ...
```

它没有校验这五个冻结字段的叶类型，也没有拒绝额外字段。例如下面这些 design 会通过 `load_design_artifact()`：

```json
{
  "run_config": {
    "graph_id": 123,
    "scene_anchor": null,
    "speaker_ref": ["char_lucy"],
    "character_refs": "char_lucy",
    "npc_name": {"name": "露西"},
    "extra_future_field": "unexpected"
  }
}
```

但 T-3P-0 的契约目标是把 `run_config` 冻结成 P-A/P-B 的共享载体：

```python
{graph_id, scene_anchor, speaker_ref, character_refs, npc_name}
```

且 PR 自述也说 loader 做了“载体形态+叶类型校验”。目前这个承诺对 `beats_plan` 成立，对 `run_config` 不成立。

**影响**

- P-A 渲染器可能把非字符串字段渲进 prompt，或把字符串 `character_refs` 当 iterable 逐字符处理。
- P-B 回流合并可能用坏 `graph_id` / `scene_anchor` / `speaker_ref` 生成错误 scene 图级字段。
- 额外字段会让“冻结五字段”变成宽松 dict；后续并行任务可能误以为可以消费额外字段，造成契约漂移。

**建议修复**

在 `_check_run_config_shape()` 内补完整形态校验，并加测试：

```python
if set(run_config) != set(RUN_CONFIG_FIELDS):
    raise PromptpackInputError(...)

for field in ("graph_id", "scene_anchor", "speaker_ref", "npc_name"):
    if not isinstance(run_config[field], str):
        raise PromptpackInputError(...)

if not isinstance(run_config["character_refs"], list) or not all(
    isinstance(x, str) for x in run_config["character_refs"]
):
    raise PromptpackInputError(...)
```

对应测试建议至少覆盖：

- `character_refs` 是字符串时拒收；
- `graph_id` / `scene_anchor` / `speaker_ref` / `npc_name` 非 str 时拒收；
- 出现额外 key 时拒收；
- 正常五字段通过。

## 白名单自报项裁断

- `.gitignore`：见 F-001，判定为 🔴 越界。
- `generator/multipass/__init__.py` docstring：不单独报 finding。它位于 `/generator/multipass/` 下，内容是解释 structure-only 路径与产物，不改行为、不新增导出、不影响运行时；在“`/generator/multipass/` allowed”大框内可以接受。但如果作者想极严执行“括号内列举即全部文件清单”，也可要求撤回该 docstring；我不建议因此停批。

## L2 关注点逐项核对

- `format_spec` E1–E8：边界总体清楚，尤其 options 整块缺失 E5、序号缺/多/不连续 E4、end 带 options E6、空 options 块 E7、多行值仅 narration E8，测试覆盖到位。
- 两个 loader：wrapper/status/legacy/cross-check/坏输入覆盖较完整；但 `run_config` 叶类型仍需补硬校验（F-002）。
- `.gitignore` 三行放行写法：写法本身可工作，但文件越出 allowed 白名单（F-001）。
- structure-only 与全量模式：默认全量模式不带 `beats_plan/run_config`，structure-only 不产 scene，正文调用跳过；测试覆盖合理。
- 三项“有意不改”：理由可接受，未形成 finding。
- C 批参数 2→1：实现、测试、样张一致；默认 `DEFAULT_MAX_REVEALS_PER_BEAT == 1` 已钉住。

## 建议结论

当前不建议合入。先处理 F-001：撤回 `.gitignore` 或取得作者显式授权；再补 F-002 的 `run_config` 类型/额外字段校验。修完后此 PR 的地基契约基本可供 T-3P-1/T-3P-2 消费。


<!-- delivered via tools/cross_review.py (governance v0.6 §13); model=gpt-5.5; prompt_chars=135947; usage={"completion_tokens": 8192, "total_tokens": 64185, "prompt_tokens": 55993, "prompt_tokens_details": {"cached_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0}} -->
