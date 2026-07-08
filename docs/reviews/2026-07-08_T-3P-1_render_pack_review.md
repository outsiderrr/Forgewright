# Code Review — PR #88 T-3P-1 promptpack render pack

评审者：gpt-5.5 via relay API  
日期：2026-07-08  
Review target：PR #88 `claude/t3p1-render-pack`（T-3P-1 P-A 场景级写作提示词包渲染器，0 LLM）

## 0. 结论

本 PR 基本符合 T-3P-1 的主目标：新增的 P-A 渲染器是确定性代码、没有引入 LLM/provider/budget 调用，主要输入经 T-3P-0 loader，输出格式段看起来由 `format_spec` 常量驱动，lucy pack 验收物也覆盖了作者要求的 concrete 审阅面。

但有 1 条需要 C 阶段处理的 🟡 finding：渲染器在 `design.contract` 缺失/半缺失时静默降级为空文本，会直接生成缺少场景目标/禁则的可交付 pack。这不是普通 cosmetic 问题；P-A 的 pack 是编剧唯一输入，场景契约缺失会让结构锁定和防写崩能力失效。

## 1. Findings

### 🟡 IMPORTANT / ERR — `design.contract` 缺失时静默产出空场景契约，坏输入会变成“看似成功”的 pack

**位置**：`generator/promptpack/render_pack.py:226-237`（`_render_contract`）

```python
def _render_contract(contract: dict[str, Any]) -> str:
    forbidden = contract.get("forbidden") or []
    return f"""## 二、场景契约

- **玩家目标**：{contract.get('player_goal', '')}
- **NPC 目标**：{contract.get('npc_goal', '')}
- **NPC 恐惧**：{contract.get('npc_fear', '')}
- **禁则（本场不许发生 / 不许写出的事）**：
{_bullets(list(forbidden))}"""
```

**问题**：T-3P-1 规格把“场景契约（`design.contract` 的 `player_goal / npc_goal / npc_fear / forbidden`）”列为 pack 六段之一；这是编剧避免写崩结构、越界揭示、误写 NPC 动机的核心约束。当前实现对缺字段全部用空字符串/空列表降级，CLI 仍会成功产出 pack。

这会造成一个隐蔽失败模式：如果上游 `design.json` 因 fixture 版本、T-3P-0 loader 漏校验或手工修改导致 `contract` 缺失/半缺失，P-A 不会报错，反而生成一份“二、场景契约”为空的正式交付物。编剧拿到后仍会按 pack 开写，但关键目标、恐惧和禁则已经丢失。

**为什么应修**：

- ADR-039 路线 A 的核心是“我们锁结构，编剧只填正文”；场景契约是锁结构之外给编剧的人类约束面。
- T-3P-1 明确要求输出“场景契约（design.contract 的 player_goal / npc_goal / npc_fear / forbidden）”。
- 这属于边界输入校验问题，不应依赖作者 concrete 验收时“肉眼看见空白”。作者不会编程，坏 pack 一旦进入真实工作流，最可能在编剧回稿后才暴露。

**建议修法**：在渲染入口或 `_render_contract()` 前增加 P-A 本地校验；不需要改 T-3P-0 loader，也不需要改 schema。

最小规则建议：

- `design["contract"]` 必须是 dict。
- `player_goal` / `npc_goal` / `npc_fear` 必须是非空字符串。
- `forbidden` 必须是 list，且每项为非空字符串；是否允许空列表由作者/任务口径决定，但如果 lucy fixture 和真实结构层都应有禁则，建议空列表也报 `PromptpackInputError`。
- 报错走现有 CLI 输入错误路径，退出码 2。
- 加 1–2 个测试：缺 `contract`、缺 `player_goal` 或空 `npc_fear` 时 `main()` 返回 `EXIT_USAGE`，stderr 含 `contract`。

## 2. 自报越界裁断

### `.gitignore` 放行验收物目录

**裁断**：接受，不作为 finding。

理由：T-3P-1 完成标准要求 lucy 整场真 pack 落盘作为作者 concrete 验收物；T-3P-0 的 ignore 块已经采用“忽略 experiments 下内容，但显式 `!` 放行固定 fixture/验收目录”的模式。本 PR 只新增：

```gitignore
!/generator/experiments/multipass_structure/2026-07-08_t3p1_pack/
```

这是为了让 golden/验收物可被正常 commit，而不是用 `git add -f` 绕过仓库约定。该越界有任务完成标准支撑，风险低。

### 防搬运守卫措辞放宽

**裁断**：接受，不作为 finding。

理由：原“样例来自其他场景”在 lucy pack 中可能为假，因为部分锚点恰好来自 lucy 已验收文本。改为“样例里的人名、地名、道具、事实细节不一定属于本场景；事实以本包锁定内容为准”更诚实，也更符合防搬运目的。该改动仍在 pack 内做最小重述，没有扩展到 P-E 的完整文风资产重打包。

## 3. “有意不改”清单逐条裁断

1. **`render_pack(preset=…)` 未知 preset 触发 KeyError**：接受。CLI v1 不暴露 `--preset`，当前只有内部默认路径；现在加完整参数面校验收益低。
2. **`load_anchors()` 仓库资产损坏裸 traceback**：接受。仓库内常量/资产损坏属于开发环境破损，不是用户输入面；可后续统一处理，不阻塞本 PR。
3. **`design["beats_plan"][nid]` 直接下标**：接受。T-3P-0 loader 已把 beats_plan/run_config 作为地基契约校验；重复防御不是本任务重点。
4. **loader 不校验 `contract`、渲染端空值降级**：不接受；已上报为本报告唯一 finding。P-A 本地应在渲染前拒收空 contract，而不是产出空 pack。
5. **防搬运守卫措辞放宽**：接受，见上节。
6. **node kind 三分派散布多函数 / 本地复制量化常量**：接受。白名单只允许新建 `render_pack.py`，把只读来源重构成共享常量会越界；注释标来源即可。
7. **`_tree_order` 卫兵未沉入共享 `io.py`**：接受。`io.py` 属 T-3P-0 只读边界；P-A 渲染期卫兵本地实现合理。
8. **小规模重复计算 `_nodes_by_id` 等效率项**：接受。35 节点规模无性能问题，当前保持函数局部纯粹更可读。

## 4. L2 重点关注项核对

- **输出格式段与 `generator/promptpack/format_spec.py` 对偶一致性**：未发现 blocker。代码片段显示 key 名、node header、错误表、分类 required/optional keys 都从 `format_spec` 常量生成；测试也覆盖 E1–E8 与分类 key 描述。由于 diff 中 `render_pack.py` 后半截被截断，本轮只能基于可见实现、golden 输出和测试断言裁断；未看到手写 E 表或手写 key 名漂移。
- **文风段是否越界做 P-E**：未发现越界。当前是 role_rules/AP/白描预设/锚点/量化契约的 pack 内说明书化重述，未引入 14 维 taxonomy、judge 或完整资产重打包。
- **输入是否只经 T-3P-0 loader**：主路径看起来合规，导入并使用 `load_design_artifact` / `load_scene_spec`；测试 fixture 也从 loader 读。未发现自写 JSON 解析主路径。
- **0 LLM 约束**：合规。未见 provider、budget、LLM 调用；`scene_summary_writer.read_summary_sidecar` 只是读取 sidecar，不现场生成摘要。
- **树序填空单与 fixture beats_plan 对齐**：测试覆盖逐拍顺序、reveal 原文、末拍标记；golden 中 lucy 每拍 1 条线索与作者拍板一致。
- **白名单边界**：核心代码/测试在白名单内；验收物目录和 `.gitignore` 放行属于自报越界，已接受。

## 5. 测试评价

新增测试覆盖面总体扎实：

- golden-file 固定 lucy pack；
- 结构正确性覆盖 choice options、beats_plan、树序、template 块数、E1–E8；
- 确定性覆盖同输入重复渲染和 `FORGEWRIGHT_STYLE_ANCHORS=off`；
- 边界覆盖 legacy design、坏 summary sidecar、悬空 next、不可达节点。

建议 C 阶段只补本报告 finding 对应的 contract 负路径测试，不需要大改测试结构。

## 6. 最终建议

**结论：Request changes（需 C 阶段修 1 条 🟡）。**

修完 `design.contract` 缺失/半缺失时报 `PromptpackInputError` 并补测试后，本 PR 可以进入 L2 验收；无需因 `.gitignore` 放行或防搬运措辞放宽阻塞。

## 7. 三行摘要

总 findings：1  
严重度统计：🔴 0 / 🟡 1 / 🟢 0  
Top priority：修复 `design.contract` 静默空值降级，坏输入必须在 P-A 渲染期硬报错，不能生成缺场景契约的正式 pack。


<!-- delivered via tools/cross_review.py (governance v0.6 §13); model=gpt-5.5; prompt_chars=176563; usage={"completion_tokens": 5466, "total_tokens": 96718, "prompt_tokens": 91252, "prompt_tokens_details": {"cached_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0}} -->
