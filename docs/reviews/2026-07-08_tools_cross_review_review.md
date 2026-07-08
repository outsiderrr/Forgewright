# Code Review — PR #85 feat(tools): cross_review.py

评审者：gpt-5.5 via relay API  
日期：2026-07-08  
范围：PR #85 `tools/cross-review`（base = `main`），新增 `tools/cross_review.py` 与 `tools/tests/test_cross_review.py`  
结论：需要修改后再合并

## 摘要

- Finding 总数：4
- 严重度分布：🔴 1 / 🟡 3 / 🟢 0
- Top 1 priority：先修复 `collect_context_files()` 未打包治理模板要求的必读上下文，否则该工具产出的 B 阶段评审报告天然缺上下文、不符合 governance v0.6 §13 的评审输入契约。

## Findings

### 🔴 F-01 [ARCH] 自动化工具没有打包评审模板声明的必读上下文，导致 B 阶段报告上下文不完整

- 位置：`tools/cross_review.py:282-299`, `tools/cross_review.py:311-323`
- 相关代码：
  - `collect_context_files()` 只收集根 `CLAUDE.md`、diff 触及模块的 `CLAUDE.md`、以及 `--task-prompt` 指定文件。
  - `run_review()` 随后直接把这些文件交给 `pack_prompt()`。

问题：本工具的 `_API_PREAMBLE` 明确告诉评审模型：模板正文里“启动前必读”的材料“已由工具打包附上”。但实际实现没有打包模板要求的关键项目上下文：

- `/docs/ROADMAP.md`
- `/docs/DECISIONS.md`
- `/docs/SCHEMA_v0.md`
- 最新一份 `/docs/HANDOFF_STAGE_*.md`
- `/docs/STAGE_1_ACCEPTANCE.md` §4 R1–R8
- 以及本任务直接相关的 `/docs/governance.md` / governance v0.6 §13 内容（如果不通过 `--task-prompt` 手动传入，就不会出现）

这不是普通“信息少一点”的问题。该工具的目标就是替代交互式 reviewer 自己读文件；如果工具声称“对应材料已打包”但实际漏打包，后续所有由它生成的 B 阶段报告都可能在 ADR、阶段定位、已知遗留项、治理规则上误判。尤其本 PR 自身就是 governance v0.6 §13 的工具载体，输入契约不完整会直接破坏该治理流程的可信度。

建议修复：

1. 在 `collect_context_files()` 中无条件加入模板要求的固定上下文文件：`CLAUDE.md`、`docs/ROADMAP.md`、`docs/DECISIONS.md`、`docs/SCHEMA_v0.md`、`docs/STAGE_1_ACCEPTANCE.md`、`docs/governance.md`。
2. 自动查找日期最新的 `docs/HANDOFF_STAGE_*.md` 并打包；如果不存在，应在 prompt 中明确写“未找到 latest HANDOFF”，不要静默省略。
3. 保留当前模块级 `CLAUDE.md` 与 `--task-prompt` 机制。
4. 增加测试：构造临时 repo 或 monkeypatch 文件读取，断言 packed prompt 中包含上述固定上下文标头；至少覆盖 latest handoff 的选择逻辑。

---

### 🟡 F-02 [SAFETY] Claude 系模型拦截只检查字符串 `claude`，容易被中转站别名绕过

- 位置：`tools/cross_review.py:169-173`
- 相关代码：

```python
if "claude" in model.lower():
    raise CrossReviewError(...)
```

问题：governance §13 的硬要求是 B 阶段使用“非 Claude 系”模型，以保证 cross-LLM 独立性。当前校验只拒绝 model id 中包含 `claude` 的情况，但中转站模型名常见别名可能不含该字符串，例如：

- `anthropic/sonnet-4`
- `sonnet-4`
- `opus-4`
- `haiku-3.5`
- relay 自定义别名如 `reviewer-primary`，背后实际指向 Claude

这会让工具在形式上通过检查，但实质上仍可能调用 Claude 系模型，破坏 B 阶段“第二意见”的独立性。

建议修复：

1. 至少扩展 denylist：`claude`、`anthropic`、`sonnet`、`opus`、`haiku`。
2. 更稳妥的方式：改成 allowlist，只允许明确的非 Claude family 前缀或模型族，例如 `gpt`、`o1`、`o3`、`o4`、`gemini`、`deepseek`、`qwen` 等，并把 allowlist 写在代码常量与文档里。
3. 如果 relay 支持模型元数据查询，优先根据 provider/family 校验，而不是只根据字符串猜。
4. 补测试：`sonnet-4`、`anthropic/opus` 应被拒绝；明确允许的非 Claude 模型应通过。

---

### 🟡 F-03 [ERR] budget 已预扣后，API 调用失败不会 reconcile，留下不一致记账记录

- 位置：`tools/cross_review.py:264-275`, `tools/cross_review.py:335-344`
- 相关代码：

```python
budget_mod, record_id = _charge_budget(len(packed), model)
report, usage = call_relay(...)
if budget_mod is not None and record_id is not None:
    budget_mod.reconcile_after_call(...)
```

问题：`_charge_budget()` 在 API 调用前执行；如果 `call_relay()` 因连接失败、HTTP 错误、空 content、响应形态异常、超时等原因抛异常，`reconcile_after_call()` 不会执行。结果是：

- cost log 可能留下“预估成功 / 未对账”的记录；
- 后续周对账或治理审计无法区分“实际未产生有效报告”与“产生报告但 usage 丢失”；
- 如果 `generator.budget.check_and_charge()` 有额度扣减副作用，会造成失败调用也被永久算入预算。

当前注释说“费用异常由 cost_log 周对账兜底”，但这里不是单纯费用异常，而是失败路径没有被记录成失败状态。

建议修复：

1. 将 `call_relay()` 包进 `try/except/finally`。
2. 如果 `generator.budget` 已有失败对账/撤销 API，失败时调用它。
3. 如果没有现成 API，至少在失败时用 `reconcile_after_call(record_id, actual_input_tokens=..., actual_output_tokens=0, actual_cost_usd=0.0)` 或新增明确的 failure marker，保证 audit trail 可解释。
4. 增加测试：transport 抛 `ConnectionError` 或返回空 content 时，断言 budget 记录不会停留在未对账状态。

---

### 🟡 F-04 [TEST] 实际 SSE 流式聚合逻辑没有单测覆盖，最新修复点容易回归

- 位置：`tools/cross_review.py:219-258`, `tools/tests/test_cross_review.py:105-123`, `tools/tests/test_cross_review.py:179-196`
- 相关代码：
  - `_http_transport()` 实现 SSE `data:` 帧解析与 content 聚合。
  - 现有 `call_relay()` 测试都通过注入 fake `transport`，没有测试 `_http_transport()` 本身。

问题：PR 描述与代码注释都说明，本 PR 最新两个 commit 的重点修复包含 `max_tokens`、重试、SSE 流式取回。`max_tokens` 与 retry 已有测试，但 SSE 聚合的关键行为没有覆盖：

- 多个 `data:` chunk 是否按顺序拼接；
- `[DONE]` 是否正确终止；
- `finish_reason` 是否保留；
- usage chunk 是否被捕获；
- 非 JSON 心跳/异常行是否跳过；
- 空 delta 但最终有 finish_reason 的情况是否仍按预期报空 content。

这部分是工具能否绕过“中转站非流式聚合器损坏”的核心修复点。没有测试的话，后续很容易把 `stream=True`、delta content 聚合或 usage 处理改坏，而普通 transport 注入测试不会发现。

建议修复：

1. 给 `_http_transport()` 加无网络单测：monkeypatch `urllib.request.urlopen` 返回一个可迭代 fake response，内容包含多行 SSE 帧。
2. 至少覆盖：两个 content chunk 拼接、`finish_reason=stop`、usage 捕获、`data: [DONE]` 终止。
3. 再补一个异常/边界测试：非 JSON `data:` 行被跳过，最终仍能聚合有效内容。

## 非 finding 但已检查

- 密钥处理：当前没有把 `LLM_API_KEY` 写入 prompt、报告 footer 或显式日志；`Authorization` header 只传给 transport。未发现直接泄漏 key 的路径。
- diff 截断：截断告示会嵌入 diff 文本本身，也会打印 stderr；reviewer 能看到“该文件/总 diff 已截断”。该方向未发现必须阻塞的问题。
- 退出码三态：`CrossReviewError` 与 `gh` 输入/环境错误返回 2，API/运行/格式失败返回 1，成功与 dry-run 返回 0；整体语义基本符合 docstring。
- `max_tokens`：`call_relay()` 已显式设置 `_MAX_OUTPUT_TOKENS`，并有单测覆盖。
- 连接级重试：`call_relay()` 对 `OSError` / `URLError` 有重试，并有单测覆盖；是否重试 HTTP 4xx/5xx 可后续细化，但本轮不作为 finding。

## 建议合并条件

合并前建议至少修复 F-01。F-02 与 F-03 也会直接影响 governance §13 的可信度和审计质量，建议同轮修复。F-04 可与 SSE 修复一起补测试，避免本工具第一次投入使用后在 relay 行为上回归。

<!-- delivered via tools/cross_review.py (governance v0.6 §13); model=gpt-5.5; prompt_chars=packed-by-relay; usage={} -->


<!-- delivered via tools/cross_review.py (governance v0.6 §13); model=gpt-5.5; prompt_chars=29859; usage={"completion_tokens": 5138, "total_tokens": 17135, "prompt_tokens": 11997, "prompt_tokens_details": {"cached_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0}} -->
