# STAGE_1_TASKS.md — 阶段 1 任务清单与执行会话提示词

> 阶段 1 规划师会话的产出物。每个任务的提示词为**可直接复制到新执行会话的自包含输入**。
>
> **使用方式**：作者按 wave 顺序开 Claude Code 执行会话，从下方对应任务直接复制 ` ```text` 代码块全文作为首条消息。

**日期**：2026-04-25 · **版本**：v0.1 · **产出方**：阶段 1 规划师会话

---

## 阶段 1 目标回顾

来自 `/docs/ROADMAP.md` 阶段 1：

- 函数 `generate_node(context, requirements) -> DialogueNode`
- Schema 合格率 ≥ 95%
- 人工接受率 ≥ 50%
- 首次引入 LLM；`/generator/` 模块在此诞生
- 运行时 `/engine/` 永远不引入 LLM（ADR-002）

## 锁定的架构决策（在本计划中执行）

| 决策 | 内容 | ADR |
|---|---|---|
| LLM 提供商 | 默认 Google Gemini 3.1 Pro；通过 `LLMProvider` Protocol 可插拔 | ADR-011 |
| 成本治理 | 环境变量密钥；`/generator/budget.py` 硬卡（每日 $10、单次 $0.50）；`cost_log.jsonl` 落盘 | ADR-012 |
| Structured Output | Gemini `response_schema` + `response_mime_type=application/json`；最多 2 次重试，失败回喂 validator 错误 | ADR-013 |
| Pydantic 绑定 | 由 `datamodel-code-generator` 从 `/schema/*.json` 自动生成到 `/generator/models/_generated/`；手写 Pydantic 类作为数据结构定义 = 禁止 | CLAUDE.md 规则 6 |
| 上下文粒度 | **B+**：场景锚点 + 当前节点要求 + 同图前 3 节点 + **当前节点出场角色**本体卡 + 阵营时钟当前值 | 本规划 Q7 |
| Few-shot | 先用《铁誓驿站》5 节点全量；过拟合再补 | 本规划 Q6 |
| 接受率判定 | 作者本人逐节点过；产出 `review_log.jsonl` | 本规划 Q8 |
| 重试 | 最多 2 次（共 3 次），失败标记 `generation_failed` 不抛异常 | ADR-013 |

## 工作 wave 与依赖

```
Wave A (并行):  T-1.0  T-1.1
                 │     │
Wave B:         T-1.2 (/generator 骨架; 必须先于一切代码)
                 │
Wave C (并行):  T-1.3  T-1.4  T-1.5
                 │     │     │
Wave D:                 T-1.6 (generate_node 主函数)
                         │
Wave E:                 T-1.7 (实验脚本 + review CLI)
                         │
                  [作者手动跑实验 + 审阅]
                         │
Wave F:                 T-1.8 (阶段 1 验收报告)
```

**前置作者侧准备**：
- T-1.4 启动前需要 **Gemini API key**（已就绪）
- 执行 T-1.4 时若 `gemini-3.1-pro` 这个 model id 在你账号下不可用，让该执行会话先列出 `list_models()` 输出，由作者拍板真实 model id

---

## T-1.0 ｜ 起手清理 PATCH（文档对齐）

```text
你的任务是完成阶段 1 起手的文档清理 PATCH，已由作者授权。

# 模块边界（硬性）
只允许修改：
  - /docs/SCHEMA_v0.md
  - /docs/STAGE_0_ACCEPTANCE.md
严禁修改：/schema/、/state/、/engine/、/validator/、/content/、CLAUDE.md、DECISIONS.md
也严禁碰 /schema/*.json 里的 schema_version 字段。

# 背景
T-0.7 状态总线任务已固定 D5（path 表示法 = 点分字符串）和 D6（op 白名单）。
但 SCHEMA_v0.md §3.4/§3.5/§6/§7.4 仍写"推迟至状态总线 Schema 任务"。
此外 STAGE_0_ACCEPTANCE.md 表格末行 hash `ad1e7f5` 是 amend 前的 hash，非真实 commit hash。

# 待修改点
1. SCHEMA_v0.md §3.4 StateEffect.op 行：去掉"推迟"措辞，改为"已固定（见 /state/ 实现）；候选枚举：set / inc / dec / add / remove"
2. SCHEMA_v0.md §3.5 StateCondition.op 行：同上，候选枚举改为 eq / neq / gt / gte / lt / lte / has / has_not
3. SCHEMA_v0.md §3.4/§3.5 path 行：去掉占位符 `<state_bus_path>` 措辞，改为"已固定：点分字符串（见 /state/ 实现）"
4. SCHEMA_v0.md §6.D5 / §6.D6 决议状态：从 "⏸ 推迟" 改为 "✅ 已决议（在 /state/ 状态总线实现中固定）"，并补一段说明
5. SCHEMA_v0.md §7.4 表格 D5 / D6 状态符号同步更新
6. SCHEMA_v0.md §7.5 解锁状态注释更新
7. SCHEMA_v0.md §变更历史 + 版本号：新增 v0.1.2 行，注明"文档澄清，措辞与 /state/ 实际实现对齐；**schema_version 字段保持 0.1.1（不属于结构性变更，不联动 /schema/*.json）**"
8. STAGE_0_ACCEPTANCE.md 表格末行 "验收" hash 改为"见 git log 最新记录"

# 不要做的事
- 不要碰 /schema/*.json 文件里的 schema_version 常量
- 不要碰 /content/test_scene_v0/scene.json 里的 schema_version 字段
- 不要新增其他章节
- 不要重写已有内容（只做局部澄清）

# 完成报告
git diff 摘要 + commit hash + push 确认。
commit message: `docs: align SCHEMA_v0.md D5/D6 wording with /state/ implementation; fix STAGE_0_ACCEPTANCE hash`
末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## T-1.1 ｜ 写入 ADR-011 / 012 / 013 + ROADMAP 阶段 1.5 占位

```text
你的任务是把阶段 1 的三条架构决策写入 DECISIONS.md，并在 ROADMAP.md 增加阶段 1.5 占位段。
作者已通过 2026-04-25 规划会话明确授权修改 DECISIONS.md（CLAUDE.md 规则 10 例外）。

# 模块边界（硬性）
只允许修改：
  - /docs/DECISIONS.md
  - /docs/ROADMAP.md
严禁修改：CLAUDE.md、SCHEMA_v0.md、DEBATE_NOTES.md、HANDOFF_STAGE_0_TO_1.md、STAGE_0_ACCEPTANCE.md
严禁修改任何代码模块。

# ADR-011：LLM 提供商默认 Gemini 3.1 Pro + LLMProvider 可插拔接口
- 状态：已接受（2026-04-25）
- 背景：阶段 1 首次引入 LLM；项目长期目标是开源框架，开源用户必须能换模型
- 决策：默认提供商 = Google Gemini 3.1 Pro；/generator/ 内部定义最小 LLMProvider Protocol（generate_structured + estimate_cost 两个方法），阶段 1 实现 GeminiProvider；OpenAI / Anthropic / 本地模型由后续/社区实现
- 替代方案及否决理由：
  - 直接绑定单一 SDK（无 Protocol）：阻碍开源用户换模型，违反长期目标
  - 引入 LangChain / LiteLLM 重抽象：违反 ADR-004 极简精神
- 后果：/generator/llm_provider.py 是新关键接口；阶段 1 任务清单含一条专门"接口设计"工作

# ADR-012：成本治理与密钥管理
- 状态：已接受（2026-04-25）
- 背景：阶段 1 首次产生 API 调用成本；需早期防失控
- 决策：
  - 密钥：环境变量 GEMINI_API_KEY；开发期通过 .env 文件加载（gitignore），仓库提供 .env.example 模板
  - 硬卡：/generator/budget.py 模块；默认每日 $10 / 单次调用 $0.50，可由配置覆盖；超额抛 BudgetExceeded 异常
  - 落地日志：/generator/cost_log.jsonl（gitignore）每次调用一行，含 timestamp / model / input_tokens / output_tokens / cost_usd
  - 阶段 1 总盘子建议：$30
- 替代方案及否决理由：
  - 不做硬卡，靠云控制台预警：反应慢、可能凌晨耗尽预算
  - 把密钥写入仓库（即便加密）：开源后社区无法自行替换
- 后果：每个 LLM 调用必须经 budget.check_and_charge() 拦一次

# ADR-013：Structured Output 策略
- 状态：已接受（2026-04-25）
- 背景：阶段 1 目标 Schema 合格率 ≥ 95%；不靠重试堆 token
- 决策：
  - 主策略：Gemini response_mime_type="application/json" + response_schema=<DialogueNode JSON Schema>
  - 重试：最多 2 次（共 3 次），失败时把 validator 错误回喂模型
  - 重试不换 prompt（保持可重现）；3 次都失败 → 标记 generation_failed，写日志，**不抛异常**
  - 其他 provider 实现 LLMProvider 时各自映射本平台的结构化输出能力（OpenAI json_schema / Anthropic tool use / 本地模型 free-text + 校验）
- 替代方案及否决理由：
  - 自由文本 + 校验重试为主：烧 token，不可预测
  - 不重试：阶段 1 95% 合格率难达标
- 后果：generate_node 有清晰的"3 次试错预算"语义；超时由调用方决定是否人工介入

# ROADMAP.md 修改
在"阶段 1"和"阶段 2"之间插入：

## 阶段 1.5：视觉资产生成（VN 立绘 + 场景背景）

### 目标
为 MVP 范围内的角色和场景，生成可入库的 VN 立绘 + 场景背景资产库。
风格：类视觉小说（VN）= 场景背景静态 + 角色立绘叠加。
未来扩展性：立绘可由 PNG 升级为 5 秒短视频循环（schema 钩子预留）。

### 完成标志
- generate_character_sheet(character_ref) → N 张表情/姿势立绘
- generate_scene_background(location_ref) → 1–3 张背景
- 资产入库 /content/visuals/ + manifest.json
- Schema 已扩展：本体角色实体新增 visual_assets 字段（已授权动 Schema，路径 C）

### 重点工作
- NPC 分级：轻档（4–6 张）+ 重档（10–15 张）双档可选
- 视觉提供商选择（暂未拍板；候选 GPT-Image / Imagen / Midjourney API）
- 资产清单（manifest）格式：asset_id 间接引用，未来切换 PNG → 视频不动 schema

### 禁止事项
- 不做实时合成（违反 ADR-002）
- 不做立绘内 PSD 分层套娃（保持完整 PNG）
- 不做审阅 UI（阶段 3）

### 依赖
- 阶段 1 完成（generate_node 跑通；本体桩仍可用）
- 详细任务在阶段 1 验收后由专门规划师会话产出

# 顺带更新
- ROADMAP.md 「阶段概览」表格新增一行 "1.5 | 视觉资产生成 | 2–3 周 | 是"
- 总估计行更新

# 完成报告
git diff 摘要 + commit hash + push 确认。
commit message: `docs: add ADR-011/012/013 and Stage 1.5 ROADMAP placeholder`
末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## T-1.2 ｜ /generator/ 模块骨架 + 依赖

```text
你的任务是建立 /generator/ 模块的目录骨架、依赖清单、配置文件。**不写任何业务逻辑代码**，只做脚手架。

# 模块边界（硬性）
允许新建：/generator/ 下任何文件；根目录的 .env.example
允许修改：pyproject.toml、.gitignore
严禁修改：/schema/、/state/、/state/ontology/（沿用桩）、/engine/、/validator/、/content/、/docs/

# 必读
- /CLAUDE.md
- /docs/DECISIONS.md（特别是新加的 ADR-011 / 012 / 013）
- /pyproject.toml（看现有依赖结构）

# 待建文件
/generator/
  __init__.py            # 空
  CLAUDE.md              # 模块级指引；见下方"CLAUDE.md 内容"
  README.md              # 极简，3-5 行说明本模块用途
  prompts/__init__.py    # 空
  providers/__init__.py  # 空
  models/__init__.py     # 空
  models/_generated/__init__.py  # 空
  models/_generated/.gitkeep     # 占位（防止空目录被 git 忽略）

根目录新增：
  .env.example           # 模板，单行 GEMINI_API_KEY=your-gemini-api-key-here

# pyproject.toml 新增依赖
- google-genai          (Google 新统一 SDK；执行时确认最新稳定版)
- datamodel-code-generator (用于 T-1.3 自动生成 Pydantic)
- python-dotenv         (加载 .env)

# .gitignore 新增条目
.env
/generator/cost_log.jsonl
/generator/experiments/

# /generator/CLAUDE.md 内容（用中文写）
- 本模块是开发期 LLM 调用层；运行时（/engine）严禁依赖本模块（ADR-002 / 004）
- LLM 调用必须走 LLMProvider 接口（ADR-011），不得直接 import google.genai 到业务代码
- 任何 API 调用前必须经 budget.check_and_charge()（ADR-012）
- /generator/models/_generated/ 由 datamodel-code-generator 从 /schema/*.json 自动生成；**不得手动编辑**
- 提示词模板放 /generator/prompts/，按节点类型分文件
- 阶段 1 严禁修改 /state/ontology/（沿用桩）；视觉资产相关（阶段 1.5）严禁出现
- 提交前确认：`pytest` 通过、不引入 /engine 对本模块的 import

# 完成报告
- 目录树 + 新增 / 修改文件清单
- pyproject.toml diff
- 确认 `pip install -e .` 能跑通
- commit + push（commit message: `feat(generator): scaffold /generator/ module skeleton (T-1.2)`）
末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## T-1.3 ｜ Pydantic 模型自动生成（从 JSON Schema）

```text
你的任务是用 datamodel-code-generator 把 /schema/*.json 转成 Pydantic 模型，并验证 roundtrip。

# 模块边界（硬性）
允许修改：/generator/models/_generated/、/generator/scripts/（如需 helper 脚本）
严禁修改：/schema/*.json（CLAUDE.md 规则 6 + 2）、/state/、/engine/、/validator/、/content/

# 必读
- /CLAUDE.md（规则 6：JSON Schema 是唯一定义方式）
- /generator/CLAUDE.md
- /schema/*.json（5 个 schema 文件）
- /docs/SCHEMA_v0.md（理解字段语义）

# 待做
1. 写一个生成脚本 /generator/scripts/regenerate_models.sh（或 .py），调用 datamodel-code-generator 把每个 /schema/*.json 转成 Pydantic v2 模型
2. 输出落地到 /generator/models/_generated/，每个 schema 一个 .py 文件
3. 每个生成文件头加注释："# Auto-generated from /schema/<name>.json by datamodel-code-generator. DO NOT EDIT MANUALLY. Re-run /generator/scripts/regenerate_models.sh"
4. /generator/models/__init__.py 重导出常用类型（DialogueGraph, Node, Option, StateEffect, StateCondition）
5. 写一个 roundtrip 测试 /generator/tests/test_models_roundtrip.py：
   - 加载 /content/test_scene_v0/scene.json
   - 解析为 DialogueGraph Pydantic 实例
   - .model_dump_json() 序列化
   - 与原始 JSON 对比（去除 key 顺序与空白差异）
   - 必须 1:1 匹配
6. 运行该测试，必须通过

# 不要做的事
- 不要手写 Pydantic 类（CLAUDE.md 规则 6）
- 不要修改 /schema/ 任何文件
- 不要为通过测试而修改原始 scene.json

# 已知坑提醒
- datamodel-code-generator 默认对 JSON Schema 2020-12 的 $ref 处理可能需要 --use-schema-description 等额外参数；执行时若遇到 $ref 解析失败请调试参数，不要修改 schema 文件
- StateCondition 的两形态互斥（叶 vs 复合）在 Pydantic 里通常需要 Discriminated Union 或 model_validator；保留生成器原始输出 + 必要时在 _generated/ 外补一层薄 wrapper（不修改自动生成的文件）

# 完成报告
- 生成脚本路径
- 生成文件清单
- roundtrip 测试输出
- commit + push（commit message: `feat(generator): auto-generate Pydantic models from JSON Schema (T-1.3)`）
末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## T-1.4 ｜ LLMProvider Protocol + GeminiProvider 实现

```text
你的任务是实现 ADR-011 定义的 LLMProvider 可插拔接口及其 Gemini 实现。

# 模块边界（硬性）
允许修改：/generator/llm_provider.py、/generator/providers/、/generator/tests/
严禁修改：/schema/、/state/、/engine/、/validator/、/content/、其他 /generator/ 子模块

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-011 / ADR-013

# 待做

## 1. /generator/llm_provider.py
定义 Protocol（typing.Protocol）：

class LLMProvider(Protocol):
    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> StructuredResponse: ...

    def estimate_cost(
        self, input_tokens: int, output_tokens: int
    ) -> float: ...

# 配套 dataclass：
@dataclass
class StructuredResponse:
    content: dict           # 解析后的 JSON dict
    raw_text: str           # 模型原始输出（debug 用）
    input_tokens: int
    output_tokens: int
    model_id: str
    finish_reason: str

注意：Protocol 本身不实现重试和 budget；这两件由更上层的 generate_node 负责（T-1.6）。

## 2. /generator/providers/gemini.py
class GeminiProvider 实现 LLMProvider：
- 构造接受 api_key（默认从 os.environ["GEMINI_API_KEY"] 取）+ model_id（默认 "gemini-3.1-pro-preview"，但允许 override；作者已确认这是当前可用的 preview 版 model id）
- generate_structured 用 google.genai SDK；config 传 response_mime_type="application/json" + response_schema=json_schema
- 单次调用失败（API 错误 / 网络）→ 抛 ProviderError；不在此层重试
- estimate_cost 按 Gemini 3.1 Pro 当前公开单价（执行时从官方文档查到，硬编码为常量 + 注释来源 URL + 取数日期）；如未来调价由后续 PR 更新

## 3. /generator/providers/__init__.py
重导出 GeminiProvider

## 4. Smoke test /generator/tests/test_gemini_smoke.py
- 标记 @pytest.mark.smoke（默认 pytest 不跑，需 `pytest -m smoke`）
- 跳过条件：无 GEMINI_API_KEY 时 pytest.skip
- 单次调用最小 schema（如 {"type": "object", "properties": {"echo": {"type": "string"}}}）
- 校验：返回 StructuredResponse；content 是 dict；input/output_tokens > 0
- 这条会真的烧钱（< $0.01），跑一次就够；CI 不挂

## 5. /generator/tests/test_llm_provider_contract.py
- 不调真实 API；用一个 FakeProvider（写在测试文件内）验证 Protocol 接口契约
- 确保 GeminiProvider 满足 isinstance check 或类型 hint 兼容（typing.runtime_checkable）

# 前置作者侧准备
- 你（执行会话）开始前应假设作者已设置 GEMINI_API_KEY 环境变量
- 如果 smoke test 跑不通且原因是 model_id 错误，**不要自己改 model_id 猜**；停下来在完成报告里列出 SDK list_models() 的输出，由作者拍板真实 model id

# 不要做的事
- 不要在 GeminiProvider 内部做 budget 检查（那是 budget.py 的职责）
- 不要在 GeminiProvider 内部做重试（那是 generate_node 的职责）
- 不要写"如果 Anthropic 那就……"的分支代码（YAGNI）

# 完成报告
- 接口签名 + GeminiProvider 类骨架
- smoke test 输出（含真实 token / cost 数字）
- 失败时列出 list_models() 结果
- commit + push（commit message: `feat(generator): add LLMProvider Protocol and GeminiProvider (T-1.4)`）
末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## T-1.5 ｜ budget.py 成本守卫 + cost_log

```text
你的任务是实现 ADR-012 的成本治理：硬卡 + 日志。

# 模块边界（硬性）
允许修改：/generator/budget.py、/generator/cost_log.py、/generator/tests/
严禁修改：其他 /generator/ 子模块、/schema/、/state/、/engine/、/validator/、/content/

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-012

# 待做

## 1. /generator/budget.py
- 配置：从环境变量或默认值读
  - DAILY_BUDGET_USD（默认 10.0）
  - PER_CALL_BUDGET_USD（默认 0.50）
- 状态：从 cost_log.jsonl 重建当日累计花费（懒计算，每次 check 时扫今天的行）
- 接口：
  class BudgetExceeded(Exception): ...
  def check_and_charge(estimated_cost_usd: float, *, model_id: str, input_tokens: int, output_tokens: int) -> None
  - 若 estimated_cost > PER_CALL_BUDGET 或 today_total + estimated_cost > DAILY_BUDGET → raise BudgetExceeded
  - 否则把这一笔写入 cost_log（通过 cost_log.append）

## 2. /generator/cost_log.py
- 写入路径：/generator/cost_log.jsonl（已在 .gitignore）
- append(record: dict) → 一行 JSON，append-only，必须 fsync
- 字段：timestamp (ISO8601), model_id, input_tokens, output_tokens, cost_usd
- read_today() → list[dict]，扫今天的行（按 timestamp 过滤）
- 文件不存在时 read_today 返回 []

## 3. /generator/tests/test_budget.py
覆盖：
- 单次超 PER_CALL → raise
- 累计超 DAILY → raise
- 正常通过 → 写入 log
- 跨日重置（mock 时间）
- 文件不存在时 read_today 返回 []
- 并发写入不破坏 JSONL 格式（基础原子性，单进程内顺序写够用）

测试用 tmp_path fixture 隔离 log 文件，不污染真实 cost_log.jsonl。

# 不要做的事
- 不要在 budget.py 里调 LLM API（职责分离）
- 不要做异步写入（同步 + fsync 即可）
- 不要做 SQLite / DB 化（JSONL 简单且足够）

# 完成报告
- 接口签名
- 测试输出（pytest -v）
- commit + push（commit message: `feat(generator): add budget guard and cost_log (T-1.5)`）
末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## T-1.6 ｜ generate_node() 主函数 + prompt 模板 + 重试循环

```text
你的任务是实现阶段 1 核心目标函数 generate_node()。这是阶段 1 的主交付物。

# 模块边界（硬性）
允许修改：/generator/generate_node.py、/generator/prompts/、/generator/context_assembler.py、/generator/tests/
**允许只读**导入：/validator/、/generator/models/、/generator/llm_provider.py、/generator/budget.py
严禁修改：/schema/、/state/、/state/ontology/（仍是桩）、/engine/、/validator/、/content/、其他 /generator/ 子模块

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /docs/DECISIONS.md ADR-011 / 012 / 013
- /docs/SCHEMA_v0.md（DialogueNode 字段语义）
- /content/test_scene_v0/scene.json（5 节点 few-shot 来源）
- /validator/ 已实现的三层校验（schema / graph / consistency）

# 待做

## 1. /generator/generate_node.py
def generate_node(
    *,
    graph_context: GraphContext,         # B+ 上下文输入
    node_requirement: NodeRequirement,   # 期望节点类型 / 说话者 / 节奏标签
    provider: LLMProvider,
    max_retries: int = 2,                # 总尝试 = 1 + 2 = 3
) -> GenerationResult

# GenerationResult dataclass:
@dataclass
class GenerationResult:
    success: bool
    node: Node | None              # success=True 时填
    failure_reason: str | None     # success=False 时填（"schema_invalid" / "budget_exceeded" / "provider_error"）
    attempts: list[AttemptRecord]  # 每次尝试的 raw_text + validator error + cost
    total_cost_usd: float

# 流程：
1. budget.check_and_charge(预估成本, ...)（用 provider.estimate_cost 预估）
2. 拼 prompt = system_prompt + few_shot_block + context_block(graph_context) + requirement_block(node_requirement)
3. 调 provider.generate_structured(...)
4. 用 /validator/ 校验返回的 node JSON（schema 层 + 必要时 graph 层"独立节点"子集校验）
5. 通过 → return success=True
6. 失败 → 把 validator 错误回喂模型，再调一次（最多 max_retries 次）
7. 全失败 → return success=False，附 failure_reason
8. 任何阶段抛 BudgetExceeded → return success=False, failure_reason="budget_exceeded"
9. 任何阶段抛 ProviderError → return success=False, failure_reason="provider_error"
**不抛异常给调用方**（除非编程错误）

## 2. /generator/prompts/system.py
SYSTEM_PROMPT 字符串常量，中文，描述：
- 你是 RPG 对话节点生成器
- 输出必须是符合给定 schema 的 JSON
- 要保持与 few-shot 示例的语气、节奏一致
- 角色对白应反映本体卡里给出的性格与状态
- 不要捏造本体未定义的角色名 / 地点名

## 3. /generator/prompts/few_shot.py
def load_iron_oath_few_shot() -> list[dict]:
- 从 /content/test_scene_v0/scene.json 读 5 个节点
- 转成 (input_context, expected_node) 对，作为示例对
- 输入侧重构为"如果让模型生成这个节点，它应该看到什么 context"——即模拟 B+ 输入

## 4. /generator/context_assembler.py（B+ 上下文）
@dataclass
class GraphContext:
    scene_anchor: str              # 场景锚点 ID
    location_card: dict            # 场景地点卡（从本体桩取）
    parent_chain: list[Node]       # 直接父链前 3 节点（如不足 3 个则有几个塞几个；入口节点位置时为空）
    involved_characters: list[dict]  # 当前节点出场角色的本体卡（仅当前节点）
    faction_clocks: dict[str, int] # 阵营时钟当前值（key = 时钟 ID, value = 当前格数）；阶段 0 桩可能为空 dict

@dataclass
class NodeRequirement:
    node_type: Literal["dialogue", "end"]
    expected_speaker_ref: str | None
    narrative_intent: str          # 自然语言描述："承接告白主题，引出选择压力"

assemble_context_block(graph_context, node_requirement) -> str
# 输出一个结构化 markdown 风格 prompt 片段；阶段 0 本体桩字段不全时优雅降级（缺啥说啥，不报错）

## 5. 重试时的"错误回喂"
attempt 2/3 在 user_prompt 末尾追加：
"上次生成失败，错误：<validator 错误信息>。请基于以下要求修正后重新输出完整节点 JSON。"

## 6. 测试 /generator/tests/test_generate_node.py
不调真实 API；用 FakeProvider 注入：
- scenario_1: 第一次返回合法 JSON → success
- scenario_2: 第一次返回非法 JSON，第二次合法 → success，attempts 长度 = 2
- scenario_3: 三次全非法 → success=False, failure_reason="schema_invalid"
- scenario_4: provider 抛 BudgetExceeded → failure_reason="budget_exceeded"
- scenario_5: provider 抛 ProviderError → failure_reason="provider_error"
- scenario_6: 入口节点位置（parent_chain 空）→ 不报错，prompt 拼接正常

不要在此任务中调真实 Gemini API（那是 T-1.7 的实验范围）。

# 不要做的事
- 不要扩展 schema（CLAUDE.md 规则 2）
- 不要给 generate_node 增加 model_id / 温度等参数（隐藏在 provider 内）
- 不要做 batch 生成（那是 T-1.7）
- 不要预读整图（违反 B+，会变成 C）

# 完成报告
- generate_node 签名 + 流程图（文字描述）
- prompt 模板节选
- 测试输出（6 scenarios 全过）
- commit + push（commit message: `feat(generator): implement generate_node() with B+ context and retry loop (T-1.6)`）
末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## T-1.7 ｜ 实验脚本 + 作者审阅 CLI

```text
你的任务是为阶段 1 验收提供"实验执行 + 作者审阅"工具链。

# 模块边界（硬性）
允许修改：/generator/experiment.py、/generator/review_cli.py、/generator/metrics.py、/generator/tests/
严禁修改：其他模块

# 必读
- /CLAUDE.md
- /generator/CLAUDE.md
- /docs/ROADMAP.md 阶段 1 完成标志
- /docs/DECISIONS.md ADR-009（评测分层背景）

# 待做

## 1. /generator/experiment.py
CLI: `python -m generator.experiment --batch-name <name> --count <N>`
- 跑 N 次 generate_node（默认 N=20）
- 每次的 graph_context / node_requirement 从一个内置 fixture 集合采样（覆盖：dialogue 入口节点 / dialogue 中间节点 / end 节点 / 不同说话者）
- 输出落地：/generator/experiments/<timestamp>_<batch_name>/
  - results.jsonl（每行一个 GenerationResult 的序列化）
  - summary.txt（schema 合格率、平均成本、失败原因分布）
- 启动时打印当日剩余预算
- 任何一次抛 BudgetExceeded → 立即停止并落地已完成结果

## 2. /generator/review_cli.py
CLI: `python -m generator.review --batch-dir <path>`
- 终端 UI（rich 或纯 print 都可）依次展示 results.jsonl 里 success=True 的节点
- 每个节点显示：context（精简）、生成的 node JSON、玩家可见 narration / options 文本
- 操作：[A]ccept / [R]eject / [S]kip
- Reject 时提示输入一行原因（如"对白突兀"、"选项重复"）
- 输出：与 batch-dir 同级的 review_log.jsonl，每行 {iter_id, node_id_or_idx, schema_pass, accepted, reason, reviewed_at}
- 可中断、可继续（已审过的跳过）

## 3. /generator/metrics.py
def compute_metrics(batch_dir: Path) -> dict
返回：
- total_attempts
- schema_pass_rate
- mean_cost_per_attempt
- failure_reason_distribution
- (若 review_log.jsonl 存在) acceptance_rate
- (若存在) reject_reason_top_5

CLI: `python -m generator.metrics --batch-dir <path>`

## 4. 测试 /generator/tests/test_experiment_smoke.py
- 用 FakeProvider 跑 experiment，验证 results.jsonl 格式正确、summary.txt 生成
- review_cli 的非交互测试（mock stdin）
- metrics 计算的单元测试

# 不要做的事
- 不要做 Web UI（CLI 即可）
- 不要做 LLM-as-judge（阶段 2/3）
- 不要让实验脚本默认烧很多钱（默认 N=20，约 $0.5–$1.5）

# 完成报告
- CLI 用法说明
- 一次 dry-run（用 FakeProvider）的输出截图（文本）
- commit + push（commit message: `feat(generator): add experiment harness, review CLI, and metrics (T-1.7)`）
末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## ⏸ 作者侧手工任务（介于 T-1.7 和 T-1.8 之间）

```text
T-1.7 落地后，由你（作者）执行：
1. 设置 GEMINI_API_KEY 环境变量
2. 跑 `python -m generator.experiment --batch-name baseline_001 --count 20`（约 $0.5–$1.5）
3. 跑 `python -m generator.review --batch-dir generator/experiments/<刚才的目录>`
4. 逐节点 [A]/[R]，必要时记原因
5. 跑 `python -m generator.metrics --batch-dir <同上>`
6. 把 metrics 输出贴到下一个会话作为 T-1.8 输入

如果 schema_pass_rate < 95% 或 acceptance_rate < 50%：
- 不要立刻判失败
- 反向阅读 review_log 的 reject 原因；常见模式 → 反馈给规划师调 prompt 模板（开新一轮 T-1.6.x）
- 调几轮后再跑 T-1.8 验收
```

---

## T-1.8 ｜ 阶段 1 验收报告

```text
你的任务是写阶段 1 验收报告。**仅在 T-1.7 跑完且作者已完成手工审阅后启动**。

# 模块边界（硬性）
允许新建：/docs/STAGE_1_ACCEPTANCE.md
允许修改：/docs/ROADMAP.md（更新记录）
严禁修改：其他 docs / 任何代码

# 必读
- /docs/STAGE_0_ACCEPTANCE.md（参照格式）
- /docs/ROADMAP.md 阶段 1 完成标志
- 最新 batch-dir 下的 results.jsonl + review_log.jsonl + metrics 输出

# 待做
按 STAGE_0_ACCEPTANCE.md 的格式写 STAGE_1_ACCEPTANCE.md，包含：

1. 阶段 1 完成判定核对
   - schema_pass_rate ≥ 95%（实测值）
   - acceptance_rate ≥ 50%（实测值）

2. 实验数据
   - 总尝试数 / 通过数 / 失败原因分布
   - 总成本 USD
   - reject 原因 top 5 + 出现频次

3. 工作量速览（T-1.0 ~ T-1.7 的 commit hash 表格）

4. 遗留问题（若任何指标未达标但作者签字接受 → 在此说明 + 下一阶段补齐计划）

5. 阶段 2 启动前置条件（参考 STAGE_0_ACCEPTANCE.md 的"阶段 1 启动前置条件"段，提示需要由专门规划师产 HANDOFF_STAGE_1_TO_2.md）

# 不要做的事
- 不要伪造数据
- 不要替作者签字（签字行留空，作者填）
- 不要规划阶段 2（那是阶段 2 规划师的事）

# 完成报告
- 文件路径 + 关键指标
- commit + push（commit message: `docs: stage 1 acceptance report`）
末尾附 Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## 版本

本文件版本：v0.1
最后更新：2026-04-25
产出方：阶段 1 规划师会话（基于 2026-04-25 与作者的 4 轮校准对话）
