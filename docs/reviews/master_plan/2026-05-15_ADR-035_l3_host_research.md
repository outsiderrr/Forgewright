# ADR-035 调研报告：第一款游戏 L3 宿主程序选型

> **本文件 = 调研档；不立 ADR；不修改 DECISIONS.md。** 给 L1 续接会话拍板 ADR-035 时阅读。
>
> **结构**：§1 背景 → §2 4 候选能力清单 → §3 3 distinct 方案 → §4 7 维评分表 → §5 推荐 + 反对 → §6 ADR-035 完整草案 → §7 拍板指引 → 附录。
>
> **v3 提示词关键变更**：(1) §2 升级 4 候选 ### 子段；(2) §3 三 distinct 立场方案（v_godot_custom 激进 / v_renpy 保守 / v_godot_dialogic 折衷）；(3) §4 7 维评分（21 评分 + 21 理由）；(4) T-3Y 草案 schema fold 进 §1.4 + §3 估时。
>
> **v0.3 关键修订**（作者 2026-05-18 口头拍板）：(1) **主推荐切换 v_renpy → v_godot_custom**；(2) §4 评分表加 AI 加速后工时校准；(3) §3.2 Ren'Py 劣势段重写——强化"可扩展性限制"细节（能做物品 / 技能 / 简单库存；偏弱在复杂 UI / 实时操作 / 探索范式 / DND 风格库存装备槽）；(4) §5 / §6 / §7 重写以匹配新主决策；(5) §8 加 AI 加速工时校准表。

**日期**：2026-05-15（调研启动）→ 2026-05-18（v0.4 demo 实测 + ADR-035 立项落地）·**版本**：v0.4 ·**产出方**：L3 宿主调研会话（claude/vigorous-varahamihira-f6f2f6 worktree）
**触发**：2026-05-15 T-3Y L2 综合规划师会话讨论"工具生态扫描"时作者覆盖"Ren'Py 推荐"→ 选 Godot 4.x；L2 提议立 ADR-035 候选（Godot 4.x + Dialogic 2.x）；作者要求详细调研后再决定立不立
**v0.2 触发**：补充提示词 v3 + 必读 T-3Y 设计进展报告 v0.1（2026-05-15）；重组结构 + fold 进 T-3Y 字段集影响
**v0.3 触发**（2026-05-18 作者口头拍板后）：(1) 作者明示**"保留可扩展性"硬约束** —— 克苏鲁 / 探案 / 极乐迪斯科 / 未来 DND 都含物品 + 技能 + 检定，不是纯 VN；(2) 作者经验判断 AI 加速可缩工时 ~10x（综合校准为 3x；含调试 / 跨平台导出 / 学习曲线等不可加速段；详 §8）；(3) **主推荐从 v_renpy swap 为 v_godot_custom**；v_renpy 降级为"最低成本上线 + 接受扩展性限制"备选；Dialogic 仍明确否决
**v0.4 触发**（2026-05-18 demo 实测 + ADR-035 立项）：(1) Godot demo 5 分钟跑通 —— 远低于调研预估 1-2 小时；详 §8.4；(2) 估时校准：v_godot_custom 完整版 1-2 天作者经验估时**高度可信**；(3) **ADR-035 正式立项到 `/docs/DECISIONS.md`**（作者明示授权 → CLAUDE.md 规则 10 例外）；本调研档使命完成
**截止时点**：2026-05-18（外部事实抓取时点；版本号 / release 日期均以此日为准）

---

## 1. 调研背景 + 任务

### 1.1 调研触发与争议

2026-05-15 T-3Y L2 综合规划师会话讨论"工具生态扫描"时，原"工具生态扫描"提示词推荐 **Ren'Py** 作 L3 宿主（视觉小说事实标准）。作者明确**覆盖原推荐**选 **Godot 4.x**；L2 进一步建议立 **ADR-035 候选**：第一款游戏 L3 宿主 = Godot 4.x + Dialogic 2.x 插件。

作者要求**详细调研后再决定立不立**，担忧三点：

1. **工程量风险**：Godot 比 Ren'Py 多约 2-4 周工作量做 Forgewright → Godot 适配层；这值得吗？
2. **Dialogic 成熟度**：插件维护状态？是否真能消费 Forgewright JSON？已知限制？
3. **集成方案风险**：工程层有什么坑？

### 1.2 与既定架构的关系（必读）

本 ADR 候选必须严守以下既定原则：

| ADR | 含义 | 对 L3 宿主选择的约束 |
|---|---|---|
| ADR-002 运行时不调用 LLM | `/engine` 是纯确定性 JSON 对话图播放器；无 LLM、无网络 | L3 宿主同样**不得引入运行时 LLM**——硬约束 |
| ADR-004 运行时与生产期严格分离 | `/engine` ≤ 500 行；生产期工具链不进运行时 | L3 宿主可有自己的代码量预算（独立于 500 行约束）；但 L3 是消费者，**不修改** schema / state / engine |
| ADR-027 World-Agnostic Principle | 框架代码不假设单一世界观 | L3 宿主的样板代码本身世界无关；具体游戏 instance 可绑特定世界 |
| ADR-028 引擎与宿主分离原则（2026-05-10） | **引擎核心不实现任何具体 IO 形态**；宿主是适配层 | **本 ADR-035 落地的就是 ADR-028 描述的"第一款游戏的参考宿主"**——首次具体化 ADR-028 抽象原则 |
| ADR-029 技能体系作为项目配置层 | 引擎核心不预设技能体系 | L3 宿主需能呈现项目配置的技能数值 / 检定结果，但不内置技能列表 |
| ADR-030 AestheticPreference schema（字段集预留） | 偏好档作用于生成期，运行时不感知 | L3 宿主不需要感知 aesthetic_preference 字段——零耦合 |
| ADR-031 GM 抉择空间结构化方案（混合 A+B） | F2 NPC 反应用 NPC 状态机；F7 即兴预生成多变体 | L3 宿主需消费 dialogue_graph 已编排的 narration 变体；NPC 状态机由 engine 层执行 |
| ROADMAP 阶段 4 切换协议 | 北极星 = A 完成度；警惕"做工具滑回继续做工具"失败模式 | **L3 宿主选择应最低成本启动**——避免"造适配层 → 继续完善适配层 → 滑回造工具" |
| ROADMAP 阶段 4 完成定义 | (b) 作者本人玩通 → (c) 3-5 朋友玩通 → (d) itch.io 免费发布；跳过 Steam | **L3 宿主必须能多平台分发**（itch.io HTML5 / Windows / macOS binary）；安装门槛要低 |

**核心张力**：作者偏好 Godot 4.x（次世代游戏引擎；个人技术栈兴趣）VS ROADMAP 阶段 4 失败模式警示（最低成本 + 不滑回做工具）。两者拉扯方向相反；本调研产推荐 + 利弊由作者签字。

### 1.3 本调研的边界（不做的事）

- **不修改** `/docs/DECISIONS.md`（严守 CLAUDE.md 规则 10）
- **不修改** `/engine/` 代码（仅评估其未来命运 a/b/c；见 §6）
- **不在 Godot / Ren'Py 上写真实游戏**——仅做工程量 estimation（demo 见 §6 子段）
- **不替作者拍板**——给推荐 + 利弊 + 等作者签字
- **不扩展到 ADR-034**（schema IR 选择；平行任务；§5 + 附录 A 给跨任务协同输入）

### 1.4 Forgewright 对 L3 宿主的真实需求清单（两栏拆分）

**v0.2 关键修订**：T-3Y 设计进展报告 v0.1（2026-05-15）引入了大量场景级 + 节点级新字段；其中大部分是**生成期产物**（运行时 L3 宿主不消费），但少数字段进入运行时数据契约，影响 L3 宿主复杂度。下表拆**两栏**：

| 能力 | v0.3 当前 schema 需求 | T-3Y 草案 schema 新增需求 |
|---|---|---|
| 读外部 JSON 文件 | ✓ `dialogue_graph.json` 入口加载 | ⚠ **可能升级为多文件层级**：scene.json → dialogue_graph.json |
| 渲染 narration 文本（中文）| ✓ `node.narration` 字符串 | ✓ 不变 |
| 显示 speaker_ref / location_ref display_name | ✓ 本体注入 | ✓ 不变 |
| 列表化呈现 options 数组 | ✓ `node.options` | ✓ 不变 |
| unavailable_behavior 枚举处理 | ✓ hide / disable / disable_with_hint | ✓ 不变 |
| 应用 on_enter_effects + option.effects | ✓ state_effect 数组 | ✓ 不变 |
| 评估 reachability_condition + option.condition | ✓ state_condition 树 | ✓ 不变 |
| 节点跳转（target_node_id） | ✓ option 字段 | ✓ 不变 |
| end 节点终止呈现 | ✓ `node.type = end` | ✓ 不变 |
| 富文本（粗体 / 斜体 / 颜色） | — 阶段 4 未来增量 | — 同 |
| 中文字体渲染 | ✓ 核心 | ✓ 不变 |
| 多平台分发（Windows / macOS / Web） | ✓ itch.io | ✓ 不变 |
| **场景间跳转（scene_branches）** | ❌ 当前不支持 | ✓ **新增**：scene_branches → 跨 dialogue_graph 跳转 |
| **scene_metaparams 运行时查表** | ❌ 不存在 | ⚠ **新增**：culprit_id / difficulty_level / apparition_level 影响节点变体路由 |
| **scene_actual_inputs 计算** | ❌ 不存在 | ⚠ **新增**：进入场景时基于上一场景 state 算一次 |
| **scene_actual_outputs 记录** | ❌ 不存在 | ⚠ **新增**：离场记录到 save state |
| **included_node_ids 索引** | ❌ 不存在 | ⚠ **新增**：场景 → 节点 list 索引 |
| **player_known_info 双层结构** | ❌ 不存在 | ➖ **纯生成期产物**——baimiao-rpg-node skill 输入；运行时不消费 |
| **foreground_goal / background_seeds** | ❌ 不存在 | ➖ **纯生成期产物**——同上 |
| **scene_reveals (progressive disclosure)** | ❌ 不存在 | ➖ **纯生成期产物**——编剧期编排进节点变体；运行时是预生成结果 |
| **scene_seeds (coverage_strategy)** | ❌ 不存在 | ➖ **纯生成期产物**——同上 |
| **skill_check_input** | ❌ 不存在（在 option 里隐式表达）| ➖ **纯生成期产物**——运行时 option.effects 应用即可 |

**关键洞察**：T-3Y 草案对 L3 宿主**新增 4 项运行时职责**（scene 跳转 / scene_metaparams / scene_actual_inputs/outputs / included_node_ids）；其他生成期字段对 L3 宿主**零影响**。这意味着 L3 宿主复杂度从"单 JSON 播放器"升级到"两层级 scene + node 播放器"，每方案估时**保守 +30-50%**。

### 1.5 跨调研协同（ADR-034 / ADR-031）

- **与 ADR-034 schema IR 选择**：本 ADR-035 推荐方案对 schema IR 形态**有反向约束**——例如 Ren'Py 偏好脚本式数据 vs Godot 偏好 Resource/JSON 结构；详 §5.3 + 附录 A
- **与 ADR-031 GM 抉择空间**：F2 NPC 反应（NPC 状态机查表）+ F7 即兴预生成多变体 → L3 宿主只消费"预编排完的"dialogue_graph；NPC 状态机执行由 `/engine/` 或宿主内嵌的等价代码完成；本 ADR 不影响 ADR-031 决策

---

## 2. 候选宿主能力清单（4 候选）

### 2.1 Godot 4.x（候选 1）

**当前版本**：

- **Godot 4.6.2 stable**（2026-04-01 发布；维护版本；推荐生产用）
- **Godot 4.6 stable**（2026-01 发布；含 Modern UI / Jolt 物理默认 / SSR 重写 / LibGodot 库化 / 调试器升级）
- **来源**：[godotengine.org/releases/4.6/](https://godotengine.org/releases/4.6/) + [github.com/godotengine/godot/releases](https://github.com/godotengine/godot/releases)

**核心能力 confirm**（对 §1.4 需求清单逐项）：

| 需求 | Godot 4.6 支持 | 备注 |
|---|---|---|
| 读外部 JSON | ✓ | `FileAccess.open()` + `JSON.parse_string()`；零依赖 |
| 渲染中文文本 | ✓ | `Label` + `RichTextLabel` + `FontFile`（Noto Sans SC）；TextServer 支持 CJK |
| BBCode 富文本 | ✓ | `RichTextLabel` 原生 BBCode |
| 列表化选项呈现 | ✓ | `VBoxContainer` + `Button` 节点动态生成 |
| 状态机执行 | ✓ | 纯 GDScript；JSON 状态 dict + match/if 控制流 |
| 多平台导出：Windows / macOS / Linux | ✓ | 原生（macOS 需 codesigning） |
| 多平台导出：Web (HTML5/WebAssembly) | ✓ | Web export 模板；可上 itch.io |
| 多平台导出：iOS / Android | ✓ | iOS 需 Mac + Xcode；Android 需 SDK |
| 多语言（CSV → tr()） | ✓ | `TranslationServer` 原生 |
| 中文字体（DynamicFont） | ✓ | 4.x 起 FontFile 资源 |
| 场景间跳转 | ✓（自写） | SceneTree.change_scene_to_packed / 自定义 router |

**学习曲线**：

- 基础语法（GDScript Python-like）：**1-2 天**上手
- 场景树 / Control 节点 / 信号系统：**3-5 天**系统学
- Resource 系统 / @export：**2-3 天** onboard
- 真实项目首版 ship-ready 宿主：**保守 2-4 周** 全职（无 Godot 经验背景）；如有经验减 1-2 周

**维护状态**：

- Godot Foundation 维护；2026-01 发 4.6；2026-04 发 4.6.2；持续维护
- GitHub 主仓库 25-30 万 commits；Discord 数十万用户；Bus factor 高
- 大版本节奏：约 6-12 月一个 4.x 增量；3.x → 4.x 重写已完成
- 商业作品：《Cygnus Enterprise》（已发售）/ 多个 Steam 上架独立游戏

**中文社区资源**：

- 官方中文文档：[docs.godotengine.org/zh-cn](https://docs.godotengine.org/zh-cn/4.x/)；社区翻译；完整度高
- B 站 / 知乎 / 掘金：4.0 起爆发；大量 VN / RPG / 平台游戏教程；社区比 Ren'Py 大 5-10x
- Discord 中文区 / 国内 KOL 持续输出

**主要劣势 / 坑**：

- GDScript 性能比 C# 慢 2-3x（对 Forgewright 文本场景不重要）
- macOS notarization 工作流偏麻烦
- Resource 系统对外部 JSON 不友好——纯 JSON 时需自写"JSON → 对象"转换层（30-50 行）
- Web export 体积 5-15 MB；首次加载慢
- 中文字体打包 10-15 MB 增加 export size

### 2.2 Ren'Py 8.5.x（候选 2）

**当前版本**：

- **Ren'Py 8.5.3 "We Can Go to the Moon"**（**2026-05-15 发布；本调研落档前 3 天**）
- **来源**：[renpy.org/latest.html](https://www.renpy.org/latest.html) + [renpy.org/release_list.html](https://www.renpy.org/release_list.html)

**核心能力 confirm**：

| 需求 | Ren'Py 8.5 支持 | 备注 |
|---|---|---|
| 读外部 JSON | ✓ | Python 层 `json.load()`；JSONDB 内置；可在 init / runtime 任意点加载 |
| 渲染中文文本 | ✓ | `define style.default = Style(font="NotoSansSC.ttf")`；一行配置 |
| 富文本（粗体 / 斜体 / 颜色） | ✓ | 内置 text tags `{b}`/`{i}`/`{color=#ff0000}` |
| 选项列表（menu） | ✓ | `menu:` 语句原生；条件分支 `menu (if condition):` |
| 状态机执行 | ✓ | Python 全功能；store.* 变量；`$ flag = True` |
| 多平台导出 | ✓✓ | Windows / macOS / Linux / Android (RAPT) / iOS (Renios) / Web (Renpyweb) / OpenBSD |
| 多语言（gettext） | ✓ | `translate` 语句 + `.rpyt` 翻译文件 |
| 中文字体 | ✓ | 内置 TrueType 支持；零配置 |
| 场景间跳转 | ✓✓ | `label` + `jump` / `call` 原生；天然支持 scene DAG |
| 存档 / 读档 / 倒带 | ✓✓ | 内置 save / load / rollback；玩家可点"返回上一选项"——这是 Ren'Py 22 年的招牌功能 |

**学习曲线**：

- 基础 Ren'Py 语法（.rpy 缩进式）：**3-5 小时** 上手（比 Godot 快得多）
- Python 嵌入：**1-2 天** 玩转
- 真实项目首版 ship-ready 宿主：**1-2 周** 全职（含 Forgewright JSON 适配层）

**维护状态**：

- 2003 年起；22 年历史；PyTom（Tom Rothamel）持续维护
- 发版节奏密集：2026-05-15 发 8.5.3；近 12 月内 6+ 个 minor releases
- GitHub 仓库 ~5k stars；社区 LemmaSoft Forums 活跃 20 年
- 商业作品案例千计——《Doki Doki Literature Club!》/《Eternum》/ 大量 Steam 商业 VN

**中文社区资源**：

- 官方中文教程少（不及 Godot）
- 国内 VN 圈用 Ren'Py 多年；B 站有教程；中文 wiki 散乱但够用
- 中文字体打包零配置（define 一行）

**主要劣势 / 坑**：

- `.rpy` 脚本是天然数据源——Forgewright JSON-native 哲学下需要写 JSON → .rpy 转换器（约 200-300 行 Python；one-shot）
- Python 2 → Python 3 迁移完成（8.x 全 Python 3）；老资源可能过时
- 自定义 UI 不及 Godot 灵活（但 Forgewright 阶段 4 不需要花哨 UI）
- 中文社区比 Godot 小 5-10x

### 2.3 Dialogic 2.x（候选 3）

**当前版本**：

- **2.0-alpha-19**（**发布于 2025-01-12；截至本调研日（2026-05-18）已 16 个月无新 release**）
- **仓库**：[github.com/dialogic-godot/dialogic](https://github.com/dialogic-godot/dialogic)（从 coppolaemilio/dialogic 迁移到 dialogic-godot 组织）
- **GitHub 数据**：⭐ 5.6k stars / 326 forks / 154 open issues / 2243 commits

**历史发版节奏**：

| 版本 | 日期 | 距上版本 |
|---|---|---|
| 2.0-alpha-19 | 2025-01-12 | 4 个月 |
| 2.0-alpha-18 | 2024-09-29 | 3 天 |
| 2.0-alpha-17 | 2024-09-26 | 11 个月 |
| 2.0-alpha-16 | 2023-10-27 | 1.5 个月 |
| 2.0-alpha-15 | 2023-09-09 | 4 个月 |

**关键观察**：

- **从未发过 Beta 或 stable 1.0**（自 2022-12 Alpha 12 起 28 个月全程 Alpha）
- **主分支仍有 commit**但**没有打 tag** —— 用户要么 pin Alpha 19（陈旧）要么追主分支（不稳）
- 至少两位主维护者（Jowan-Spooner + Emilio Coppola）但均为志愿者
- Alpha 19 release notes 预告"下次更新带 save state 系统变更"—— 即破坏性变更

**核心能力**：

| 需求 | Dialogic 支持 | Forgewright 需要 | 匹配度 |
|---|---|---|---|
| 对白 + speaker | ✓ | ✓ | 完美 |
| 选项分支 | ✓（choice event） | ✓（options） | 完美 |
| 变量条件分支 | ✓（branch + condition） | ✓（state_condition） | 需写转换层 |
| Character / portrait | ✓（编辑器管理） | ❌ 阶段 4 不需要 | 用不到 |
| 多语言（CSV i18n） | ✓ | ❌ | 用不到 |
| 音频 | ✓ | ❌ | 用不到 |
| **直接消费外部 JSON** | ✗ | ✓ | **核心缺口** |

**数据格式**：

- 物理格式：`*.dtl` 文件（Dialogic Timeline 自定义文本格式；**不是 JSON**）
- 代码 API：[docs.dialogic.pro](https://docs.dialogic.pro/) 文档明示 "Creating timelines in code"——可纯代码构造 timeline
- 外部 JSON 注入：文档未明确记载；要做需自写 Forgewright JSON → Dialogic timeline 转换层

**学习曲线**：

- Godot 基础（前置）：见 §2.1
- Dialogic 编辑器熟悉：**2-3 天**
- 适配层 RE：**3-7 天**（含 Alpha 19 已知 bug 绕坑）

**维护状态**：

- ⚠ **红旗**：16 月停滞 tag；存档系统重写预告；Alpha 全程未出 Beta
- main 分支 active 但不稳；社区报道 2026-02 仍在 commit

**中文社区资源**：

- Dialogic 国内使用者极少；中文教程稀疏
- 国内 KOL 用 Dialogic 做完整项目案例 < 5 个

**主要劣势 / 坑**：

- §1.4 + §1.5 + 上述：80% 功能用不到 + 数据格式不匹配 + Alpha 16 月停滞 + 存档重写预告

### 2.4 自研宿主（候选 4：三种子类型）

**子类型 A：Godot + 自写最小 Control 节点（不依赖任何 dialogue 插件）**

| 维度 | 状态 |
|---|---|
| 核心能力 | 全自写；Godot RichTextLabel + VBoxContainer + Button 完整 cover §1.4 需求 |
| 学习曲线 | Godot 基础（同 §2.1）+ 自写约 400-500 行 GDScript（含 scene 间跳转 + state 引擎逻辑移植自 `/engine/player.py`）|
| 维护状态 | bus factor = 作者本人；代码量小完全可控 |
| 中文社区 | N/A（无插件依赖）|

**子类型 B：自研 Web（Vite + vanilla TS / React）**

| 维度 | 状态 |
|---|---|
| 核心能力 | 浏览器原生；JSON / fetch / DOM 渲染零摩擦；CJK 字体走 web font (woff2) 或 system font |
| 学习曲线 | 作者 web 技术栈背景未知；如有 web 经验 1 周可起步 |
| 维护状态 | bus factor = 作者；依赖前端工具链稳定（Vite / TS 都成熟）|
| 跨平台 | HTML5 原生跨；可 Tauri 包成 native binary |
| 中文社区 | 适用（中文前端社区超大）|

**子类型 C：保留现有 Python CLI 播放器（`/engine/player.py`）**

| 维度 | 状态 |
|---|---|
| 核心能力 | 仅终端文本；无图形 UI；无 itch.io HTML5 发布支持 |
| 学习曲线 | 已完成（189 行；阶段 0 已通过验收）|
| 维护状态 | 作者本人；< 200 行；稳定 |
| 跨平台 | ❌ 需 Python runtime；朋友 3-5 玩通需先装 Python；分发门槛高 |
| 中文社区 | N/A |

**自研子类型对比**：

| 子类型 | 工程量（含 T-3Y） | 阶段 4 (d) itch.io 适配 | 推荐 |
|---|---|---|---|
| A. Godot 自写 | 3-4.5 周 | ✓ HTML5 / Win / Mac | ⚪ 备选 |
| B. Web 自研 | 1.5-3 周 | ✓✓ itch.io HTML5 直接 | ⚪ 备选 |
| C. Python CLI 保留 | 0 周 | ❌ 不可发布 | ❌ 否决（分发难） |

---

## 3. 三个 distinct 立场的候选方案

### 3.1 方案 v_godot_custom（激进 / Godot 4.6 + 自定义 Control nodes / 绕过 Dialogic）

**设计哲学**：**与 ADR-004/028 哲学最对齐 + 长期技术栈投资**。Forgewright 引擎极薄（189 行），宿主也应极薄。Godot 4.6 的 Control 节点系统（RichTextLabel + VBoxContainer + Button + Tween）足以 cover 所有 §1.4 需求；引入 Dialogic 等于背了 80% 用不到的负担。同时作者学 Godot = 长期收益（未来想做"非 VN 范式"的 RPG / 探索 / 战斗时已有技术储备）。

**集成方案**：

宿主目录：`/host/godot_first_game/`

GDScript 文件清单（估约 5-7 个文件，~500-700 行总）：

| 文件 | 职责 | 行数估 |
|---|---|---|
| `main.gd` + `main.tscn` | 入口 + 场景树 + 初始 state 加载 | 50-80 |
| `dialogue_player.gd` | 读 dialogue_graph.json → 渲染节点 → 处理选项 | 150-200 |
| `world_state.gd` | state path read/write / condition / effect（移植 Python `state/conditions.py` + `state/effects.py`）| 120-150 |
| `ontology_resolver.gd` | speaker_ref / location_ref → display_name | 50 |
| `scene_router.gd` | **新增**（T-3Y）：scene_branches 跨场景跳转 + scene_actual_inputs 计算 + scene_metaparams 查表 | 80-120 |
| `font_loader.gd` | 中文字体打包 + TextServer 配置 | 30 |
| `forgewright_to_godot_resource.py`（生产期工具）| JSON → Godot Resource (.tres) 转换（可选；初版可纯 JSON）| 100-200 |

**工程量 estimation（含 T-3Y 字段集影响）**：

| 子任务 | 估时（v0.3 基线） | 估时（+T-3Y 调整） |
|---|---|---|
| Godot 项目骨架 + 中文字体打包 | 1-2 天 | 1-2 天 |
| `dialogue_player.gd`（读 JSON + 渲染节点 + 处理选项） | 2-3 天 | 2-3 天 |
| `world_state.gd`（移植 Python state 引擎） | 2-3 天 | 2-3 天 |
| `ontology_resolver.gd` | 1 天 | 1 天 |
| UI 布局 + 选项呈现（hide / disable / disable_with_hint） | 1-2 天 | 1-2 天 |
| **新增**：`scene_router.gd`（T-3Y scene_branches + scene_metaparams + actual_inputs/outputs） | — | 3-5 天 |
| **新增**：多文件层级数据加载（act → scene → dialogue_graph） | — | 1-2 天 |
| 多平台导出 + macOS notarization | 1-2 天 | 1-2 天 |
| 一致性测试（跑 `/content/test_scene_v0/scene.json` 完整） | 1-2 天 | 2-3 天 |
| **合计** | **9-15 天（2-3 周）** | **14-23 天（3-4.5 周）** |

**优点**：

1. **代码完全可控**——bus factor = 作者；无插件兼容性焦虑
2. **与 ADR-004/028 哲学最对齐**——宿主是适配层而非"消费 80% 用不到的功能"
3. **Godot 技术栈长期收益**——未来"非 VN 范式"扩展（地图 / 探索 / 简单战斗 / VFX）已有基础
4. **Resource 系统可选**——可逐步从纯 JSON 迁移到 .tres Godot Resource（编辑器内可视化）
5. **完全无外部插件依赖**——Godot Asset Library 兼容性问题不影响本项目

**劣势**：

- **代码量最大**——4-5 周（含 T-3Y）vs Ren'Py 2-3 周
- **无现成 VN 模板**——存档 / 读档 / rollback / 文本动画 全要自写（或 skip）
- **macOS notarization + iOS export 工作流偏麻烦**——阶段 4 (d) itch.io HTML5 是 fastest path 但 native binary 上架仍要做
- **作者非编程背景**（CLAUDE.md "outsider"；不写代码角色）——自写大量 GDScript 与作者画像不匹配；除非 AI 辅助代写大部分

**风险**：

- **R1**：T-3Y 字段集仍在 v0.1 进展中——§8 4 个问题还没拍板；如 scene_reveals 改成需要运行时支持渐进揭露（虽然当前设计是生成期产物），scene_router.gd 需要重写
- **R2**：作者对 Godot 学习投入未知——如作者 0 Godot 经验 + AI 代写比例高，估时可能 +1-2 周
- **R3**：自写宿主在"开源框架剥离"时（ROADMAP 阶段 4 后期）成为参考实现——别人可能学不会；Ren'Py 路径有现成生态更容易复用
- **R4**：阶段 4 (d) itch.io HTML5 export 实测可能遇到中文字体在 WebAssembly 上的渲染坑（Godot 4.6 已修复多个但不能保证 100%）；macOS notarization 流程是新工作量
- **R5**：作者首次接触 Godot 时学习曲线可能误判——估时 +1-2 周 buffer 是必要的；作者本机做 §6 demo 是降低 R5 的最低成本方式

**何时选 v_godot_custom（决策辅助）**：作者本身偏好 Godot 不可推翻 + 接受多 1-2 周工程量 + 不打算用 Dialogic / Dialogue Manager 等插件 + 希望未来扩展非 VN 范式（探索 / 战斗）—— 四条都成立时 v_godot_custom 是合理选择。

---

### 3.2 方案 v_renpy（保守 / 推翻原 Godot 决定 / 改用 Ren'Py 8.5.x）

**设计哲学**：**Forgewright 哲学 = 内容是核心 / 工具最小化**。Ren'Py 是 VN 事实标准（22 年成熟）；选 Ren'Py 等于"不造工具"——避开 ROADMAP 阶段 4 警示的"做工具滑回继续做工具"失败模式。作者真正的目标是**完成作品**（北极星 = A 完成度），不是"建立 Forgewright 引擎 + 宿主技术栈"。Ren'Py 的 label/jump/call 天然支持 T-3Y 设计的 scene DAG navigation；存档 / 读档 / rollback 22 年成熟功能无须自写。

**集成方案**：

宿主目录：`/host/renpy_first_game/`

文件清单：

| 文件 | 职责 | 行数估 |
|---|---|---|
| `forgewright_to_renpy.py`（生产期工具；放 `/tools/`）| JSON dialogue_graph + 本体 → 生成 .rpy 脚本；含 scene → label 映射 + node → menu 转换 + state path → store.* 变量映射 | 200-300 |
| `game/script.rpy` | 生成产物——含全部场景 label / 节点 menu / state init | 自动 |
| `game/options.rpy` | Ren'Py 全局配置（标题 / 主菜单 / 字体） | 30-50 |
| `game/screens.rpy` | 自定义 screens（如显示当前 state debug；可选） | 50-100 |
| `game/state_helpers.rpy` | Python 函数：评估 state_condition / 应用 state_effect（移植 `/engine/state/` 逻辑） | 100-150 |
| `game/scene_router.rpy` | **新增**（T-3Y）：scene_branches 路由（Ren'Py 原生 `jump` 即可）+ scene_metaparams 注入 store | 50-80 |
| `assets/fonts/NotoSansSC.ttf` | 中文字体 | — |

**Ren'Py 天然优势对 T-3Y 字段集的映射**：

| T-3Y 字段 | Ren'Py 原生机制 | 工作量影响 |
|---|---|---|
| scene_branches | `jump scene_xxx` + `call scene_xxx` | **零额外工作**（原生）|
| scene_metaparams | store.scene_metaparams.culprit_id 等 | 几行代码 |
| scene_actual_inputs/outputs | store.* 变量自动持久化（Ren'Py save 内置）| **零额外工作**（save 自带）|
| included_node_ids | Ren'Py label 命名约定即可表达 | 转换器输出格式 |
| dialogue_graph 节点 | `label node_xxx:` + `menu:` | 转换器 1:1 映射 |
| option.condition | `menu (if condition):` 或 Python `if` | 转换器映射 |
| option.unavailable_behavior | Ren'Py menu native 隐藏不满足项；可显式 disable | 直接 cover |
| state_condition / state_effect | Python helper 函数即可 | 移植 `/engine/state/` 逻辑 |

**工程量 estimation**：

| 子任务 | 估时（v0.3 基线） | 估时（+T-3Y 调整） |
|---|---|---|
| Ren'Py 项目骨架 + 中文字体配置 | 0.5 天 | 0.5 天 |
| `forgewright_to_renpy.py` 转换器核心（节点 / menu / state） | 3-4 天 | 3-4 天 |
| state_helpers.rpy（移植 Python state 引擎） | 1-2 天 | 1-2 天 |
| **新增**：scene_router.rpy（T-3Y scene_branches；多用 Ren'Py jump native）| — | 1-2 天 |
| **新增**：scene_metaparams + scene_actual_inputs/outputs（store.* 直接表达）| — | 1 天 |
| 多平台导出 + itch.io HTML5 跑通 | 1 天 | 1 天 |
| 一致性测试 + 反向 dry-run | 1-2 天 | 1-2 天 |
| **合计** | **6.5-10.5 天（1-2 周）** | **8.5-13.5 天（1.5-3 周）** |

**优点**：

1. **工程量最低**——不论 v0.3 基线还是 +T-3Y 都比其他方案少 30-50%
2. **22 年成熟生态**——VN 事实标准；最近发版 3 天前；千计商业作品案例
3. **多平台分发最强**——原生 Win/Mac/Linux/iOS/Android/Web；阶段 4 (d) itch.io 工作流 fastest path
4. **scene DAG 哲学匹配**——T-3Y "所有场景在编剧期枚举为 DAG"恰好对应 Ren'Py label/jump 模型；零阻抗
5. **存档 / 读档 / rollback 免费**——Ren'Py 招牌功能；玩家可点"返回上一选项"——这对 Forgewright "玩家点选项" 交互模式天然友好
6. **避免"造工具滑回"**——Ren'Py 主打"作者只写脚本就上线"
7. **`/engine/player.py` 哲学一致**——同样"运行时极薄 + 状态管理 + 脚本驱动"

**劣势**：

- **`.rpy` 是次级数据源**——Forgewright JSON 仍是 SOT（事实之源），但要写一次性转换器；转换器维护成本要算
- **中文社区比 Godot 小 5-10x**——但 Ren'Py 中文 VN 圈 20 年成熟，资源够用
- **作者技术栈倾向 Godot**（已声明覆盖原 Ren'Py 推荐）——选 Ren'Py 是"客观最优但作者偏好相左"
- **🔴 可扩展性硬约束（v0.3 强化；主推荐切换关键）** —— Ren'Py 范式细分：
  - **能做（够用）**：物品系统（Python 数据结构 + 自定义 screens）/ 技能 + 检定（Python 全功能）/ 简单库存 UI / 骰子动画 / **极乐迪斯科那种"对话 + 调查 + 检定 + 内心独白"范式 100% 可做**——有先例（《Long Live the Queen》《Doki Doki Literature Club!》等）
  - **偏弱（能做但不优雅）**：复杂库存 UI（拖拽 / 装备槽 / DND 风格角色卡）/ 即时战斗 / 实时操作 / 自由探索 / 地图行走 / 复杂动画 / VFX / 3D
  - **真心 DND 复杂度场景下 Godot 全面碾压**——UI 完全自由 / 实时渲染 / 物理引擎 / 3D
  - **作者明示约束**（2026-05-18）：克苏鲁 / 探案 / 极乐迪斯科 / 未来 DND 都含物品 + 技能 + 检定；DND 还有职业 + 库存 + 装备槽——超出 Ren'Py 舒适区
  - **结论**：v0.3 推荐切换的关键原因——可扩展性硬约束 > 工时差距（AI 加速后已可忽略）

**风险**：

- **R1**：作者偏好覆盖——立 ADR-035 = Ren'Py 等于打作者第一选择的脸；需要作者签字明示接受"知情覆盖"
- **R2**：Ren'Py 8 Python 3 升级完成；如未来 Ren'Py 9 重大变更，转换器可能 break；但 Ren'Py 22 年向后兼容传统强，风险低
- **R3**：Forgewright 开源剥离时（阶段 4 后期），Ren'Py 路径作为"第一个参考宿主"——别的开发者如不熟 Ren'Py，借鉴价值减半；但同时增加"Forgewright 框架可用于多种 VN 引擎"的证据链

---

### 3.3 方案 v_godot_dialogic（折衷 / Godot 4.6 + Dialogic 2.x 插件 / 原方案）

**设计哲学**：**作者偏好 + 现成插件 + 中文社区**。Godot 是作者第一选择技术栈；Dialogic 是 Godot 生态最知名的 dialogue 插件（5.6k stars）；中文社区可借力。理论上 Dialogic 提供 character / portrait / 音频 / 多语言现成功能，未来如 Forgewright 想扩展立绘可启用。

**集成方案**：

宿主目录：`/host/godot_dialogic_first_game/`

文件清单：

| 文件 | 职责 | 行数估 |
|---|---|---|
| Dialogic 插件 | 编辑器 + 运行时 timeline player（5.6k stars 现成） | — |
| `forgewright_to_dialogic.gd` | **关键**：JSON dialogue_graph → Dialogic timeline 转换器（Dialogic API 调用 + .dtl 文件输出）| 250-400 |
| `state_bridge.gd` | Forgewright state path ↔ Dialogic 变量系统映射 | 100-150 |
| `condition_translator.gd` | state_condition 树 → Dialogic 表达式翻译 | 100-150 |
| `effect_applier.gd` | state_effect 数组 → Dialogic 变量写入翻译 | 80-120 |
| `ontology_resolver.gd` | speaker_ref / location_ref → Dialogic character name | 50-80 |
| `scene_router.gd` | **新增**（T-3Y）：scene_branches 跨 Dialogic timeline 切换 + scene_metaparams | 100-150 |
| `main.gd` + `main.tscn` | 入口 + Dialogic 配置 | 50-80 |

**T-3Y 字段集对 Dialogic timeline 的映射分析**：

| T-3Y 字段 | Dialogic timeline 原生支持 | 适配层工作量 |
|---|---|---|
| scene_branches | ❌ Dialogic 一个 timeline = 一个场景；跨 timeline 跳转需自写 router | **中等**（100-150 行） |
| scene_metaparams（culprit_id / difficulty_level / apparition_level）| ⚠ 通过 Dialogic 变量可表达；但 timeline 间共享变量需配置 | **中等** |
| scene_actual_inputs/outputs | ⚠ Dialogic save state 系统正在重写（Alpha 19 release notes 预告）；自写更稳 | **高风险**（依赖未发布的 save 系统）|
| included_node_ids | Dialogic timeline 内部 event 序列；可映射但不直观 | **中等** |
| dialogue_graph 节点 → Dialogic say/choice events | 1:1 映射 | 主体工作（已在 §3.3 工作量内）|
| option.unavailable_behavior 三态 | Dialogic choice event 不原生支持 disable_with_hint；自写 | **中等** |
| state_condition / state_effect | Dialogic 内置变量 + condition 表达式（但与 Forgewright JSON 表达力不完全等价）| **高**（条件树嵌套语义对齐复杂）|

**工程量 estimation（含 T-3Y 字段集影响）**：

| 子任务 | 估时（v0.3 基线） | 估时（+T-3Y 调整） |
|---|---|---|
| Godot + Dialogic 环境搭建（学习 timeline 模型） | 2-3 天 | 2-3 天 |
| Forgewright JSON → Dialogic timeline 字段映射 | 3-5 天 | 3-5 天 |
| state_condition 树 → Dialogic 表达式翻译 | 2-3 天 | 2-3 天 |
| state_effect 数组 → Dialogic 变量写入翻译 | 2-3 天 | 2-3 天 |
| unavailable_behavior 三态映射 | 1-2 天 | 1-2 天 |
| 本体引用解析层 | 1-2 天 | 1-2 天 |
| Dialogic Alpha 19 已知 bug 绕坑 + 文档不全部位 RE | 3-7 天 | 3-7 天 |
| **新增**：scene_router.gd（跨 Dialogic timeline 切换） | — | 3-5 天 |
| **新增**：scene_metaparams 注入 Dialogic 变量 | — | 1-2 天 |
| **新增**：scene_actual_inputs/outputs 持久化（Dialogic save 重写 hedge）| — | 2-4 天 |
| 中文字体打包 + 多平台导出 | 2-4 天 | 2-4 天 |
| Forgewright validator + Dialogic timeline 一致性测试 | 2-3 天 | 2-3 天 |
| **合计** | **20-37 天（4-7 周）** | **26-48 天（5-10 周）** |

**优点**：

1. **Godot 技术栈匹配作者偏好** —— 满足作者第一意愿
2. **Dialogic 现成 character / portrait / 音频** —— 如阶段 4 后期想扩展立绘 / 音效 / 多语言，原生可启用
3. **5.6k stars + 双维护者** —— 比纯个人项目 bus factor 略好（虽然有 §2.3 红旗）
4. **可视化编辑器** —— Dialogic timeline 编辑器内可看可调；调试时直观

**劣势**：

- **Alpha 状态**：自 2022-12 Alpha 12 起 **28 个月全程 Alpha**；从未发 Beta / 1.0
- **16 月发版停滞**：Alpha 19 是 2025-01-12；截至 2026-05-18 已 16 个月无新 release
- **存档系统重写预告**：Alpha 19 release notes 明示存档将变；如选 Dialogic 阶段 4 实测期可能强制升级 → 重做适配层
- **80% 能力用不到**：character / portrait / 音频 / i18n CSV / visual editor 等 Forgewright 全用不到
- **数据格式不匹配**：`.dtl` 自定义文本 vs Forgewright JSON；必须写适配层（与 v_godot_custom 适配层 + 80% 浪费）
- **scene 间跳转**：Dialogic 一个 timeline = 一个场景；T-3Y scene_branches 跨 timeline 切换需自写 router——Dialogic 帮不上忙
- **scene_actual_inputs/outputs**：依赖 Dialogic save 系统但 save 即将重写——双重风险
- **工程量最高**：含 T-3Y **5-10 周** vs v_renpy 1.5-3 周 / v_godot_custom 3-4.5 周
- **未来 Dialogic 跳到 stable 1.0 时可能 break API**：Alpha 19 与 1.0 之间的兼容性承诺 = 0

**风险**：

- **R1（关键）**：Dialogic save 系统重写期间立项 = 半年内可能强制重写 scene_actual_inputs/outputs 持久化层
- **R2（关键）**：Dialogic 从未发 stable；Forgewright 阶段 4 周期内可能仍在 Alpha；项目周期跨主版本风险高
- **R3**：Dialogic 表达式 vs Forgewright 条件树语义对齐——嵌套 not / 类型边界 / null path 容易踩坑；调试成本高
- **R4**：T-3Y v0.1 仍 in progress；如未来 scene_metaparams 增字段（如 emotion_state / ambience），Dialogic 变量系统需重新映射

---

## 4. 7 维度评分对比表

每维度 0-10 分；10 = 最好；分数后括号内 1 句理由。

| 维度 | v_godot_custom | v_renpy | v_godot_dialogic |
|---|---|---|---|
| **工程量（首版） — 越低越好（10 = 最少工作量；括号 = 人工估 / AI 3x 加速后；v0.3 加 AI 加速）** | **6**（3-4.5 周 / **5-10 天**；中等；自写 scene_router 是新增工作；作者经验判断 2-3 天）| **9**（1.5-3 周 / **3-7 天**；最少；scene_branches 走 Ren'Py jump native；存档免费）| **3**（5-10 周 / **10-20 天**；最多；含 Dialogic 学习 + 适配层 + Alpha 绕坑 + T-3Y 新增 scene_router）|
| **与 Forgewright 架构兼容性 — 与 ADR-004/028 哲学对齐度** | **9**（宿主极薄 + 全自写 + 无插件依赖 = 最对齐"宿主是适配层"原则） | **8**（Ren'Py 也是脚本驱动 + 状态管理；.rpy 转换器是生产期工具 = 与 ADR-004 生产期/运行时分离同源） | **5**（Dialogic 引入大量用不到的功能 = 违背 ADR-004 极简原则；但插件本身世界无关 = 不违 ADR-027）|
| **Future-proof（5 年视角）** | **8**（Godot 4.x 主流 + 自写代码 < 1000 行完全可控；Godot 5 来时升级路径明确） | **9**（Ren'Py 22 年向后兼容传统强；Python 3 已升级完；最近发版 3 天前；千计商业作品验证） | **3**（Alpha 28 个月未出 Beta；存档重写预告；Forgewright 阶段 4 期间 Dialogic 可能跨主版本 break） |
| **学习曲线 — 作者总学习成本（10 = 最低）** | **5**（Godot 全套 + GDScript + Resource + scene system；作者 0 经验估 2-3 周纯学习） | **8**（Ren'Py 语法 3-5 小时上手；Python 嵌入 1-2 天；总学习 1 周内） | **3**（Godot 全套 + Dialogic 编辑器 + 适配层 RE + Alpha 文档不全 RE；总学习 3-4 周）|
| **集成风险 — 已知 unknown unknown / 阻断性风险（10 = 最低风险）** | **7**（自写 = unknown 全在作者可控范围；T-3Y 仍 in progress 是 medium 风险，scene_router 可能改） | **8**（Ren'Py 22 年稳定 + scene DAG 哲学匹配 + 存档免费；唯一风险是 Ren'Py 9 未来变更但 Ren'Py 兼容传统强）| **2**（Dialogic Alpha + 存档重写 + scene_metaparams 映射不直观 + T-3Y 字段集对 Dialogic timeline event types 适配度低；三重风险叠加）|
| **跨平台分发 — itch.io HTML5 + Win/Mac/Linux native** | **8**（Godot 全平台支持；HTML5 export 5-15 MB；macOS notarization 偏麻烦但可做）| **10**（Ren'Py SDK 原生含 RAPT/Renios/Renpyweb；itch.io HTML5 一键发布；阶段 4 (d) fastest path） | **7**（同 Godot 但 Dialogic HTML5 export 可能有未知 bug；中文字体 + Dialogic UI 双层打包风险） |
| **中文社区资源** | **8**（Godot 中文社区大 5-10x；B 站 / 知乎 / 中文官方文档；GDScript 教程千计） | **5**（Ren'Py 国内 VN 圈 20 年用但社区比 Godot 小；中文教程散乱但够用；中文字体配置一行）| **4**（Dialogic 国内使用者极少；中文教程稀疏；Godot 部分中文社区可借力但 Dialogic 段无中文资源）|
| **加权总分**（简单平均；非加权）| **7.3** | **8.1** | **3.9** |

**评分约束声明**：

- 每维度评分基于 §2 + §3 文档证据；非主观；可由作者推翻
- "加权总分"只是简单平均做参考；真实加权由作者按个人优先级签字
- 7 维度故意**不含"作者偏好"维度 + "可扩展性硬约束"维度** —— 这两维度由 §5.6 + §7 拍板指引 处理
- **v0.3 关键修订**：作者 2026-05-18 明示"保留可扩展性"硬约束（克苏鲁 / 探案 / 极乐迪斯科 / 未来 DND 都含物品 + 技能 + 检定）+ 接受 v_godot_custom 工时（AI 加速后 5-10 天，作者经验 2-3 天）—— **简单平均总分 v_renpy（8.1） > v_godot_custom（7.3） > v_godot_dialogic（3.9）但最终决策权重转移到"可扩展性"维度（不在表内）**；主推荐切换 v_godot_custom；详 §5

---

## 5. 调研 agent 推荐 + 反对意见（v0.3 重写）

### 5.1 主推荐：v_godot_custom（Godot 4.6 + 自写最小 Control nodes / 不用任何 dialogue 插件）

**v0.3 切换说明**：v0.1 / v0.2 主推荐曾是 v_renpy；2026-05-18 作者口头反馈两条硬约束推翻原推荐 ——

- **可扩展性硬约束**：克苏鲁 / 探案 / 极乐迪斯科 / 未来 DND 都含物品 + 技能 + 检定，**不是纯 VN**；DND 还有职业 + 库存 + 装备槽 = 超出 Ren'Py 舒适区
- **工时不再是决定因素**：AI 加速后 v_godot_custom 5-10 天 vs v_renpy 3-7 天；绝对差距只 2-5 天，相对于"5 年视角扩展空间"可忽略
- **作者签字**：2026-05-18 口头明示"那就确定方案二吧，就是 Godot 自写"

**推荐理由 5 条**：

1. **可扩展性最高** —— Godot UI 完全自由 / 实时渲染 / 物理引擎 / 3D 全栈；未来加 DND 风格库存 / 装备槽 / 复杂角色卡 UI 无阻碍
2. **代码量小完全可控** —— 5-7 个 GDScript 文件总 ~500-700 行（含 T-3Y 新增 scene_router）；bus factor = 作者；无插件兼容性焦虑
3. **与 ADR-004/028 哲学最对齐** —— 宿主极薄 + 全自写 + 无插件依赖 = "宿主是适配层"原则的标准实现
4. **避免 Dialogic Alpha 风险** —— Dialogic 16 月停滞 + Alpha 28 个月未出 Beta + 存档系统重写预告；自写零风险
5. **作者技术栈匹配** —— 作者 2026-05-15 明示选 Godot 4.x；v0.3 拍板 v_godot_custom 是知情贯彻而非妥协

**AI 加速后估时**：5-10 天全职等效（作者经验判断可压到 **2-3 天**）；详 §3.1 + §8

### 5.2 备选 A（Godot 系；如不想完全自写对话演出）：Godot 4.6 + Dialogue Manager 4

**位置**：v_godot_custom 的 plugin-assisted hybrid 形态；不是独立第 4 方案

**是什么**：[Dialogue Manager 4 (nathanhoad)](https://github.com/nathanhoad/godot_dialogue_manager) 是 Nathan Hoad 维护的 Godot 4.6+ 对话插件——与 Dialogic 关键区别：

- **活跃维护**（不是 16 月停滞；v3.9.1 + v4 for Godot 4.6+ 持续发版）
- **stateless branching**（无状态分支）—— 只管对话演出，不管你的物品 / 技能 / state；跟 Forgewright "运行时 state 由独立 world_state 管理" 哲学同源
- **小而专注** —— 跟 Dialogic 的"全功能 VN 厨房"相反；只做"显示对话 + 处理选项"
- **能与你自写的物品 / 技能 / 库存 UI 共存** —— 井水不犯河水；扩展性不被插件锁定

**适用场景**：作者愿意接受一点插件依赖换"对话演出代码"的省力；约 **6-12 天**（v_godot_custom + 2-3 天插件熟悉）

### 5.3 备选 B（最低成本退路；如改主意接受扩展性限制）：v_renpy（Ren'Py 8.5.x）

**适用场景**：仅"克苏鲁 / 极乐迪斯科风格纯文本 + 调查 + 简单检定 + 简单物品系统"（不做 DND 复杂库存 / 装备槽 / 实时探索） —— Ren'Py 完全够用且最快

**何时改主意**：作者阶段 4 实测中如发现"自写 Godot 进度卡了 + 复杂 UI 短期内不需要" → 可切回 v_renpy 路径；本备选保留为**安全退路**

**AI 加速后估时**：3-7 天

### 5.4 明确否决：v_godot_dialogic（原 L2 ADR-035 候选）

**否决理由 5 条**（详 §3.3 + §2.3）：

1. Dialogic 2 截至 2026-05-18 仍是 **Alpha 19**（2025-01-12 发版）；16 个月无新 release
2. Dialogic 从未发 Beta / 1.0 stable；自 2022-12 Alpha 12 起 **28 个月全程 Alpha**
3. **80% 功能用不到**：character / portrait / 音频 / i18n CSV / visual editor 等
4. **数据格式不匹配**：`.dtl` 自定义文本 vs Forgewright JSON；必须写适配层
5. **存档系统重写预告**：Alpha 19 release notes 明示存档将变；阶段 4 实测期可能强制升级

### 5.5 反对意见 / 风险 / 调研发现的设计争议点

**反对 v_godot_custom 的可能立场（v0.3 新增）**：

1. **作者画像与"自写 GDScript"不匹配** —— CLAUDE.md 说 outsiderrr "不会编程"；自写 500-700 行 GDScript 完全靠 AI 协作 → 如 AI 协作中遇到边界问题，作者难自查
   - 缓解：作者已实证过用 AI 协作完成 Forgewright 阶段 0-3 工程（含 `/engine/player.py` 189 行 Python）；GDScript 难度同阶；本调研接受
2. **学习曲线** —— Godot 全套 + GDScript + Resource + scene system；作者 0 经验估 2-3 周纯学习（AI 加速后 5-7 天）
   - 缓解：作者经验判断 2-3 天可完成全流程；可信；本调研接受
3. **T-3Y 仍 in progress** —— scene_router.gd 设计依赖 T-3Y §8 4 个待 ADR-034 后拍板的设计问题；如 scene_metaparams / progressive disclosure / coverage_strategy 形态改变，scene_router 需要重写
   - 缓解：v_godot_custom 自写代码可控；改起来比 Dialogic 适配层改起来轻；T-3Y 字段变化由 §5.6 争议点 4 跟进

**反对 Dialogue Manager 4 hybrid（备选 A）的立场**：

- 插件 bus factor = nathanhoad 个人维护（虽多年活跃；不及 Dialogic 双维护者）
- 多一个依赖；增加阶段 4 实测期 unknown unknown 概率

**反对 v_renpy（备选 B）的立场**（v0.2 主推荐时已分析；v0.3 退化为备选；详 v0.2 §5.3）：

- 可扩展性弱（作者明示硬约束推翻）—— 这是 v0.3 主推荐切换的关键原因
- 作者偏好相左（Godot 是作者第一意愿）

### 5.6 调研中发现的设计争议点（提作者拍板，本调研不替决；与 v0.2 同）

| # | 争议点 | 影响 | 提作者拍板 |
|---|---|---|---|
| 1 | T-3Y §6.3 暗示**运行时进入场景时算 scene_actual_inputs/outputs** —— 是确定性计算还是隐含运行时复杂度升级？ | L3 宿主复杂度 | 需作者明确：是否所有 scene_actual 字段都是"进场算一次 + 离场记录"，不超出？|
| 2 | T-3Y §4 "运行时三字段"（scene_actual_inputs / outputs / included_node_ids）**写入位置不清晰** —— 是 scene 文件内字段 / 进 save state / 运行时计算不持久化？ | L3 宿主存档实现 | 需作者拍板 ADR-034 时一并明示 |
| 3 | T-3Y 设计的 **scene DAG 层级**对 ADR-034 schema IR 选择有反向约束 —— v_godot_custom 路径下 Godot 偏好 Resource/JSON 结构 → ADR-034 应考虑此输入 | ADR-034 与 ADR-035 协同 | 需 ADR-034 调研与本 ADR-035 互引；附录 A 给跨任务输入 |
| 4 | T-3Y §8 4 个待 ADR-034 后回头拍板的设计问题（scene_metaparams / progressive disclosure / coverage_strategy / scene_static_inputs 范围）—— 如其中一项设计形态改变，本 ADR-035 估时需要修订 | ADR-035 v0.x 修订触发 | 本 ADR-035 立 v0.3 后，ADR-034 拍板后需评估 v0.x 修订必要 |

### 5.7 作者偏好维度 + 可扩展性硬约束（不进 §4 评分表）

**v0.3 新增**：作者 2026-05-18 口头明示两条硬约束：

1. **保留可扩展性** —— 克苏鲁 / 探案 / 极乐迪斯科 / 未来 DND 都含物品 + 技能；超出纯 VN 范式
2. **AI 加速工时不是决定因素** —— 绝对工时差距已被 AI 加速压到几天级

基于此两条 + 作者技术栈偏好（Godot 4.x；2026-05-15 已明示），**本调研 v0.3 主推荐切换为 v_godot_custom**。

---

## 6. ADR-035 完整草案

```markdown
## ADR-035：第一款游戏 L3 宿主程序选型

**状态**：草案（v0.1）

**日期**：[作者签字日]

**Deciders**：作者 outsiderrr（本 ADR 涉及个人偏好层；非纯技术决策）

### 背景

ADR-028（引擎与宿主分离原则；2026-05-10 立）规定 Forgewright 引擎不实现任何具体 IO 形态；宿主是适配层。本 ADR-035 是 ADR-028 的首次具体化——**为第一款游戏（克苏鲁版极乐迪斯科 spiritual successor）选定一个具体 L3 宿主程序**。

调研背景 + 详细分析见 [/docs/reviews/master_plan/2026-05-15_ADR-035_l3_host_research.md](reviews/master_plan/2026-05-15_ADR-035_l3_host_research.md) v0.2。

报告 §2 4 候选能力清单 + §3 3 distinct 立场方案（v_godot_custom 激进 / v_renpy 保守 / v_godot_dialogic 折衷）+ §4 7 维度评分表 + §5 推荐 + 反对意见。

T-3Y 设计进展报告 v0.1（2026-05-15）的字段集影响 fold 进报告 §1.4（v0.3 vs T-3Y 草案两栏需求清单）+ §3 各方案估时（+30-50% T-3Y 调整）。

### 决策

**主决策（v0.3 作者 2026-05-18 拍板）**：第一款游戏 L3 宿主 = **Godot 4.6 + 自定义 Control nodes**（方案 v_godot_custom；不使用任何 dialogue 插件）

具体规定：

1. Godot 4.6.2（2026-04-01 发布）或更高版本作为第一款游戏的 L3 宿主程序
2. 新建 `/host/godot_first_game/` 子目录（与 `/engine` 平行；不在 ADR-004 极薄运行时约束内；与 ROADMAP 阶段 4 "游戏内容填充" 同期落地）
3. 5-7 个 GDScript 文件（~500-700 行总）：`main.gd` + `main.tscn` 入口 / `dialogue_player.gd` 节点渲染 + 选项 / `world_state.gd` state 引擎（移植自 `/engine/state/`） / `ontology_resolver.gd` 本体引用解析 / `scene_router.gd` T-3Y scene_branches + scene_metaparams + scene_actual_inputs/outputs / `font_loader.gd` 中文字体打包
4. **不使用 Dialogic 插件**（详否决理由见 §3.3 + §5.4）；如需 dialogue 插件辅助，候选为 Dialogue Manager 4 (nathanhoad) 作为 hybrid 形态（备选 A；详 §5.2）
5. T-3Y 字段集映射由自写代码实现：scene_branches → SceneTree 切换；scene_metaparams → store dict 查表；scene_actual_inputs/outputs → save state 自管；included_node_ids → 文件命名约定
6. Godot 项目内承担：富文本渲染（RichTextLabel + BBCode）/ 选项呈现（VBoxContainer + Button）/ state 内部表达 / 多平台导出（itch.io HTML5 + macOS + Windows binary + 可选 iOS/Android）
7. 第一款游戏的"参考宿主"地位明确——开源框架剥离时（阶段 4 后期），Godot 宿主作为 Forgewright 的**第一个参考适配实现**
8. **可扩展性预留**：自写代码完全可控；未来扩展物品系统 / 技能 UI / DND 风格库存装备槽 / 探索范式时无插件锁定阻碍

**次决策（备选退路；如阶段 4 实测发现自写 Godot 进度严重卡了 + 复杂 UI 短期不需要）**：第一款游戏 L3 宿主 = **Ren'Py 8.5.x**（方案 v_renpy）

具体规定：

1. Ren'Py 8.5.3（2026-05-15 发布）或更高版本
2. 新建 `/host/renpy_first_game/` 子目录
3. 实现 `forgewright_to_renpy.py`（生产期工具；放 `/tools/` 下；约 200-300 行）：消费 dialogue_graph.json + scene.json + 本体 → 生成 .rpy 脚本文件
4. T-3Y 字段集映射：scene_branches → Ren'Py `jump` native；scene_metaparams → store.* 变量；scene_actual_inputs/outputs → Ren'Py save state 自动持久化
5. **触发条件**：阶段 4 起手期 2 周内 v_godot_custom 进度未达 50% + 作者明示接受扩展性限制 → 切换到本备选

### 替代方案及否决理由

- **v_godot_dialogic（Godot 4.6 + Dialogic 2 Alpha 19）**：Alpha 状态 + 16 月发版停滞 + 80% 能力用不到 + 存档系统重写预告 + scene 间跳转 Dialogic 帮不上忙——综合工程量 5-10 周；详调研报告 §3.3 + §5.2。**明确否决**
- **保留现有 Python CLI 播放器**：分发难（朋友 3-5 玩通 + itch.io 发布均做不到）—— 否决
- **自研 Web / Electron**：性价比低于上述方案；Web 子类型在阶段 4 之后可作为 secondary 宿主（如开源框架剥离后社区参考）—— 本 ADR 不主选
- **Dialogue Manager 4 (nathanhoad)**：可行 Godot 系备选；如作者选 Godot 路径但希望有插件辅助，可作为 v_godot_custom 的 hybrid 形态；本 ADR 主决策不含但 v_godot_custom 实现细节可演化为此形态

### 后果

#### `/engine/` 模块命运（关键判断）

**a/b/c 三选 → 推荐 (a) + (b) 合并：保留为 dry-run 工具 + reference player 参考实现**

| 候选 | 命运 | 是否推荐 |
|---|---|---|
| (a) 改作 reference player 参考实现 | 作为 Forgewright JSON 规范的事实参考实现；任何新宿主（含 Ren'Py / Godot / 第三方）可拿 `/engine/player.py` 作 cross-check 黄金参考 | ✓ **推荐** |
| (b) 改作 generator 期 dry-run 工具 | generator / validator / scene_review_cli 的本地 dry-run 工具——快速跑 dialogue_graph 验证逻辑通过/失败、状态变更对齐预期，**不需 Godot/Ren'Py 项目环境** | ✓ **推荐** |
| (c) deprecated 废弃 | 删除或归档；新宿主作为唯一运行时入口 | ❌ **否决**（理由：(a) + (b) 的双重价值远超维护成本；189 行 Python 几乎无维护负担；ADR-004 极薄运行时约束继续生效）|

**最终决策**：`/engine/` **保留为 (a) reference player + (b) dry-run 工具的双重角色**。具体：
- `/engine/player.py` 继续作为生产期工具链（generator / validator / scene_review_cli）的 dry-run 后端
- 同时作为 Forgewright JSON 规范的事实参考实现，给阶段 4 开源框架剥离时第三方开发者用
- **不 deprecated**；ADR-004 极薄运行时约束（≤ 500 行）继续生效
- 第一款游戏的真正 L3 宿主 = `/host/renpy_first_game/`（或如选次决策 → `/host/godot_first_game/`）

#### 工程任务建议

- 不立即拆 T-3.x（阶段 3 完成定义不含 L3 宿主交付；阶段 3 仍在 T-3X 实测期）
- 阶段 3 → 4 切换期：HANDOFF_STAGE_3_TO_4.md 标注 L3 宿主决策 + 起手工程预算
- 阶段 4 起手期第一个 task block：**T-4.1 Godot 项目骨架 + 中文字体打包 + T-4.2 dialogue_player.gd + world_state.gd + ontology_resolver.gd + T-4.3 scene_router.gd（T-3Y 字段集消费）+ T-4.4 多平台导出 + itch.io HTML5 跑通**
- 总工程量预算（主决策 v_godot_custom）：**5-10 天**（AI 加速后；作者经验判断 2-3 天；详 §8.1.1）
- 阶段 4 完成定义 (d) itch.io 发布：Godot HTML5 export 路径；预期阶段 4 末可达

#### 未来宿主多样化

- ADR-028 已留接口；如未来出现"直播叙事 / VR 体验"等场景，可写新 host（不一定 Ren'Py 或 Godot）
- 本 ADR-035 不限制未来宿主多样性
- 第一款游戏的"参考宿主"地位 ≠ "唯一宿主"

### 关联讨论

- 与 ADR-002（运行时无 LLM）协同 —— Godot 自写代码不引入 LLM 调用
- 与 ADR-004（运行时与生产期分离）协同 —— L3 宿主属运行时；如未来加 forgewright_to_godot_resource.py 转换器属生产期
- 与 ADR-028（引擎与宿主分离原则）协同 —— 本 ADR 是 ADR-028 的首次具体化
- 与 ADR-027（World-Agnostic Principle）协同 —— Godot 框架本身世界无关；具体游戏 instance 绑特定世界
- 与 ADR-029（技能体系作为项目配置层）协同 —— Godot 宿主消费项目 skills.json；不内置技能列表
- 与 ADR-031（GM 抉择空间结构化）协同 —— L3 宿主消费"预编排完的"dialogue_graph；NPC 状态机执行由 engine 层或宿主内嵌的等价代码完成
- 与 **ADR-034（schema IR 选择；平行任务）有反向约束** —— v_godot_custom 路径下 Godot 偏好 Resource/JSON 结构；ADR-034 调研应考虑此输入；详 §5.6 争议点 3 + 附录 A
- 与 ROADMAP 阶段 4 切换协议协同 —— 北极星 = A 完成度；可扩展性硬约束下选 v_godot_custom 是 5 年视角的合理决策
- 与 ROADMAP 阶段 4 失败模式警示（"造工具滑回"）的平衡 —— v_godot_custom 自写代码 < 1000 行；不构成"造工具"；自写不依赖插件 = 避免 Dialogic 类的"插件适配滑回"

### 修订触发条件

本 ADR v0.1 立项后，以下情况触发 v0.2 修订评估：

1. ADR-034 schema IR 拍板（特别是 T-3Y §8 4 个设计问题的决策）——评估本 ADR 估时 / 适配层细节是否需修订
2. T-3Y v0.2+ 进展（特别是 scene_metaparams / scene_reveals / scene_seeds 形态变化）
3. 备选宿主重大版本变化：Dialogic 发 Beta / Ren'Py 发 8.6+ / Godot 5.0
4. 阶段 4 实测中遇到 L3 宿主阻断性问题（如选 v_renpy 后发现 Ren'Py 无法表达某 T-3Y 字段）
```

---

## 7. 拍板指引（v0.3 已完成第 1 步；剩余 3 步未拍）

→ **第 1 步：圈选偏好层级（v0.3 已拍）**：

- ✓ **作者 2026-05-18 口头拍板**：选 **v_godot_custom**（Godot 4.6 + 自写最小 Control nodes / 不用 Dialogic）
- 其他选项保留为备选 / 否决：
  - 备选 A（hybrid）：Godot + Dialogue Manager 4 nathanhoad
  - 备选 B（退路）：v_renpy；触发条件见 §6 次决策
  - 否决：v_godot_dialogic
- 本步骤已关；进入 fixation 会话签字 ADR-035 + 改 DECISIONS.md

→ **第 2 步：决定是否做 minimum demo（推荐做；未拍）**：

- 推荐 Godot demo（**3-6 小时**；AI 加速后可能 1-2 小时）：装 Godot 4.6.2 → 新 project → 用 `FileAccess` 读 `/content/test_scene_v0/scene.json` → 用 `RichTextLabel` 渲染 narration → 用 Button 列表呈现 options → 看 macOS 上跑
- 选项 a：**做 Godot demo 后再签 ADR-035** —— 给 5-10 天估时一个体感校准；本调研推荐
- 选项 b：**skip demo 直接签 ADR-035** —— 调研报告证据足够；作者经验判断 2-3 天可信；接受调研推荐
- 选项 c：**做 Ren'Py demo 作横向对照**（1-2 小时）—— 给"退路价值"一个体感；可选

→ **第 3 步：决定 `/engine/` 模块命运（v0.3 已拍）**：

- ✓ **作者 2026-05-18 口头拍板**：选 **选项 g (a) + (b) 合并保留** —— `/engine/player.py` 不删；同时承担"reference player 参考实现"+"generator 期 dry-run 工具"双重角色
- 具体含义：
  - **(a) Reference player**：作 Forgewright JSON 规范的"最小可执行说明书"；v_godot_custom 实施时 GDScript 1:1 翻译参照；未来开源剥离时第三方宿主的"对照黄金参考"
  - **(b) Dry-run 工具**：生产期 generator / validator / scene_review_cli / T-3.6 审阅 UI 调用的底层 dry-run 后端；`python -m engine /path/to/scene.json` 不需开 Godot 项目即可玩通
  - **ADR-004 极薄运行时约束（≤ 500 行）继续生效**；`/engine/` 仍是 Forgewright 的极薄运行时定义
  - **但它不是第一款游戏的真实运行时** —— 真实运行时是 `/host/godot_first_game/`（v_godot_custom）
- 其他选项不选：(c) 删除 / (i) 仅 dry-run / (j) 仅 reference

→ **第 4 步：决定立项时机 + 工程任务（v0.3 暂搁；待 Godot demo 反馈后拍）**：

- ✓ **作者 2026-05-18 拍板顺序**：先做 Godot demo + 看反馈 → 如无新增讨论再立 ADR-035；不立即立项
- demo 位置：[/docs/reviews/master_plan/2026-05-18_godot_demo/](2026-05-18_godot_demo/)（throwaway 原型；80 行 GDScript + scene）
- demo 完成判定：作者反馈三问（装 Godot 用时 / F5 是否一次跑通 / 是否玩到结局）；详 demo README §四
- 反馈后选项：
  - 选项 k：**阶段 3 内立 ADR-035（文档级）+ 阶段 4 起手期拆 T-4.1 ~ T-4.4 工程任务**（demo 顺利时调研推荐）
  - 选项 l：**推迟到 ADR-034 拍板后再立** —— 理由：T-3Y §8 4 个设计问题影响 schema IR；schema IR 影响 L3 宿主估时
  - 选项 m：**阶段 3 内立 ADR-035 + 同步启动 T-3.x mini prototype**（如 1 天 Godot demo 计 T-3.x；不算阶段 3 完成定义）
  - 选项 n（demo 卡顿时）：**调研 v0.4 修订**——补"demo 实测发现"段；调整估时 + 风险段；再决定立项时机

---

## 8. 调研工时实测 + 版本变更

### 8.1 调研工时（本会话）

| 阶段 | 估时 | 实际 |
|---|---|---|
| Forgewright 上下文回读 v0.1 | 1 小时 | ~50 分钟 |
| 外部 web research（Godot / Dialogic / Ren'Py / Dialogue Manager） | 2-3 小时 | ~30 分钟（Agent 沙箱 fail 后主会话 WebSearch + WebFetch；5 次成功调用） |
| 集成方案 estimation v0.1 + 对比表 + ADR 草案 + 推荐 | 5-7 小时 | ~90 分钟 |
| **v0.2 修订**：fold T-3Y 字段集影响 + 重组 §1-7 + 7 维评分表 + 拍板指引 + ADR 草案重写 | 2-3 小时 | ~80 分钟 |
| **v0.3 修订**：主推荐 swap v_renpy → v_godot_custom + AI 加速校准 + 可扩展性强化段 + §5/6/7 重写 | 1-2 小时 | ~50 分钟 |
| Godot demo 实测 | 1-2 天 | **SKIP**（理由见 §8.3）|
| **合计** | 11-19 小时（含 demo）/ 8-12 小时（不含 demo）| **~5 小时**（不含 demo）|

### 8.1.1 v_godot_custom 实施工时（AI 加速校准；v0.3 新增）

**本表是阶段 4 起手期 T-4.1 ~ T-4.4 工程任务的工时基线**：

| 子任务 | 人工估时（v0.2 原估） | AI 3x 加速后估时 | 作者经验判断 |
|---|---|---|---|
| Godot 项目骨架 + 中文字体打包 | 1-2 天 | 0.3-0.7 天 | 1 小时 |
| `dialogue_player.gd`（读 JSON + 渲染节点 + 处理选项） | 2-3 天 | 0.7-1 天 | 半天 |
| `world_state.gd`（移植 Python state 引擎） | 2-3 天 | 0.7-1 天 | 半天 |
| `ontology_resolver.gd` | 1 天 | 0.3 天 | 0.5 小时 |
| UI 布局 + 选项呈现（hide / disable / disable_with_hint） | 1-2 天 | 0.3-0.7 天 | 0.5 小时 |
| **T-3Y 新增**：`scene_router.gd`（scene_branches + scene_metaparams + actual_inputs/outputs） | 3-5 天 | 1-1.7 天 | 半天 |
| **T-3Y 新增**：多文件层级数据加载（act → scene → dialogue_graph） | 1-2 天 | 0.3-0.7 天 | 0.5 小时 |
| 多平台导出 + macOS notarization | 1-2 天 | 1-1.5 天（不可加速段） | 半天 |
| 一致性测试（跑 `/content/test_scene_v0/scene.json` 完整） | 2-3 天 | 1-1.5 天（不可加速段） | 半天 |
| **合计** | **14-23 天（3-4.5 周）** | **5-10 天** | **2-3 天** |

**AI 加速因子说明**：

- **写代码段**：5-10x 加速（GDScript / Python 转换器 AI 能一次给 80-90% 正确）
- **调试 / 跨平台导出测试 / 中文字体打包验证 / itch.io 上传 / macOS notarization**：1-2x 加速（人手验证不可省）
- **学习曲线**（看 Godot 文档 / 建立心智模型）：2-3x 加速（AI 能讲但作者要理解）
- 综合 **3x 加速** —— 基于"已有 Forgewright 阶段 0-3 实证（作者用 AI 协作完成 `/engine/player.py` 189 行 Python；GDScript 难度同阶）"的估算
- **作者经验判断 2-3 天** = 综合 ~10x 加速 —— 调研接受；最终以作者阶段 4 起手期实测为准
- 阶段 4 起手期实测后如发现工时偏差 > 2x，触发本 ADR v0.4 修订

### 8.2 版本修订记录

**v0.1 → v0.2 主要修订**：

- **结构**：§1-9 → §1-7 + 附录；§3 升级为 3 个 distinct 立场方案（v_godot_custom / v_renpy / v_godot_dialogic）；§4 升级为 7 维评分表
- **T-3Y fold**：§1.4 需求清单拆 v0.3 vs T-3Y 草案两栏；§3 每方案估时 +30-50% 含 T-3Y 字段集影响；§3.3 新增"T-3Y 字段映射 Dialogic timeline 能力分析"
- **核心结论不变（v0.2）**：主推荐 Ren'Py / 否决 Dialogic / `/engine/` 保留为 (a)+(b)
- **新增**：§5.3 调研中发现的设计争议点 4 条；§7 拍板指引 4 步骤；§6 ADR 草案重写

**v0.2 → v0.3 主要修订**（作者 2026-05-18 口头拍板）：

- **主推荐 swap**：v_renpy → **v_godot_custom**；理由：作者明示"保留可扩展性"硬约束（克苏鲁 / 探案 / 极乐迪斯科 / 未来 DND 都含物品 + 技能 + 检定）+ AI 加速后工时差距压到几天级（可忽略）
- **§3.2 v_renpy 劣势段强化**：能做 vs 偏弱细分；明示"Ren'Py 不擅长 DND 风格复杂 UI"
- **§4 评分表加 AI 加速后工时**：人工估 / AI 3x 加速 / 作者经验三栏
- **§5 重写**：v_godot_custom 升主推荐；Dialogue Manager 4 作 hybrid 备选 A；v_renpy 降退路备选 B；Dialogic 否决不变
- **§6 ADR 草案 swap**：主决策 v_godot_custom / 次决策 v_renpy（带触发条件）
- **§7 第 1 步标记已拍板**；剩余 3 步未拍
- **§8.1.1 新增**：v_godot_custom 实施工时 AI 加速校准表（阶段 4 工程基线）
- **不变**：§5.6 4 个设计争议点 / `/engine/` 命运 (a)+(b) / 与 ADR-034 协同输入 / 附录

**v0.3 → v0.4 主要修订**（2026-05-18 demo 实测 + ADR-035 立项）：

- **§8.4 新增**：Demo 实测结果（5 分钟跑通；远低于预估 1-2 小时；估时校准）
- **§7 第 2-3 步标记已拍板**：做 Godot demo + `/engine/` (a)+(b) 合并保留
- **§7 第 4 步标记已拍板**：阶段 3 内立 ADR-035；阶段 4 起手期拆 T-4.x 工程任务（推到阶段 3 → 4 切换会话）
- **本调研使命完成**：ADR-035 已落到 `/docs/DECISIONS.md`（参作者明示授权 → CLAUDE.md 规则 10 例外；详 DECISIONS.md 变更历史 2026-05-18 段）；本档此后作为调研物证保留，不再修订

### 8.4 Demo 实测结果（v0.4 新增）

**实测日期**：2026-05-18（作者本机；macOS）
**实测者**：作者 outsiderrr
**实测时长**：约 **5 分钟**（含装 Godot + Import + Cmd+B 跑通）；**远低于本调研预估 1-2 小时**；作者反馈"熟悉流程的话，有现成的脚本，两分钟就能做完"

**三问反馈**：

| # | 问 | 答 |
|---|---|---|
| Q1 | 装 Godot + Import project 总共多久？ | < 5 分钟；流程顺畅 |
| Q2 | Cmd+B 是否一次跑通？ | 一次跑通；无报错 |
| Q3 | 是否完整玩到 "—— 结局 ——"？ | 是 |

**对 v_godot_custom 完整版估时校准**：

调研报告原估 5-10 天（AI 3x 加速）/ 作者经验 2-3 天。Demo 实测显示：

- Godot 装 + Import 实际工作流极简（远低于预估 5-15 分钟段位）
- 作者熟悉 AI 协作模式 + Forgewright 阶段 0-3 实证 → 综合加速因子可能 > 10x（非保守 3x）
- v_godot_custom 完整版 **1-2 天作者经验估时高度可信**；最快可能压到 0.5-1 天

**结论**：实测验证 v_godot_custom 路径可行 + 估时可信；§7 第 4 步进入立 ADR-035 阶段（2026-05-18 已立到 DECISIONS.md）。

### 8.3 Godot minimum demo SKIP 原因

**SKIP 三条理由**：

1. 本调研会话本机（macOS / `/Users/outsider`）**未安装 Godot**（`which godot` 返回 not found；`/Applications/` 无 Godot；Homebrew 未装）
2. 本调研定位"文档级评估 + 工程量 estimation"；按用户任务边界明示 "不在 Godot / Ren'Py 上写真实游戏"
3. Godot 4.6.2 macOS 安装 + 完整 demo（读 JSON + 渲染节点 + 选项 + 跳转）需要 1-2 天投入；超出调研期 ROI

**替代验证**：基于公开文档 + 现有 `/engine/player.py` 推算；§6.3 给作者签字前自行做 minimum demo 的建议（Ren'Py 1-2h + Godot 3-6h）。

---

## 附录 A：对 ADR-034 schema IR 调研的输入

本 ADR-035 调研中发现以下 ADR-034 协同问题，建议 ADR-034 调研会话纳入：

1. **scene 层级 schema 文件是否需要新建** —— T-3Y §4 11 字段需要落 `/schema/scene.schema.json`？或者扩 dialogue_graph 字段？影响 L3 宿主消费的"单 JSON" vs "多 JSON 层级"
2. **scene_actual_inputs/outputs 持久化位置** —— 是 scene 文件内 field / 进 save state / 运行时计算不持久化？影响 L3 宿主存档实现
3. **L3 宿主 native 数据结构倾向作为反向输入维度** —— Ren'Py 偏好脚本式数据 vs Godot 偏好 Resource/JSON 结构；ADR-034 schema IR 选择是否考虑这个维度？
4. **T-3Y §8 4 个待 ADR-034 后回头拍板的设计问题**（scene_metaparams / progressive disclosure / coverage_strategy / scene_static_inputs 范围）—— 这些决策结果反过来影响 ADR-035 估时

## 附录 B：来源

**外部来源**：

- [godotengine.org/releases/4.6](https://godotengine.org/releases/4.6/)
- [Godot 4.6.2 maintenance release SteamDB](https://steamdb.info/patchnotes/22608060/)
- [Dialogic 2 docs (docs.dialogic.pro)](https://docs.dialogic.pro/)
- [Dialogic 2 getting started](https://docs.dialogic.pro/getting-started.html)
- [Dialogic 2 GitHub releases](https://github.com/dialogic-godot/dialogic/releases)
- [Dialogic 2 main repo](https://github.com/dialogic-godot/dialogic)
- [Ren'Py latest 8.5.3 (2026-05-15)](https://www.renpy.org/latest.html)
- [Ren'Py main site](https://www.renpy.org/)
- [Ren'Py JSONDB doc](https://www.renpy.org/doc/html/screen_actions.html)
- [Dialogue Manager GitHub (nathanhoad)](https://github.com/nathanhoad/godot_dialogue_manager)
- [Dialogue Manager site](https://dialogue.nathanhoad.net/)

**Forgewright 内部**：

- `/docs/DECISIONS.md` ADR-002 / 004 / 027 / 028 / 029 / 030 / 031
- `/docs/ROADMAP.md` 阶段 4 切换协议
- `/docs/DEBATE_NOTES.md` 主题 5（极简运行时原则）
- `/docs/reviews/master_plan/2026-05-15_T-3Y_design_progress.md` v0.1（T-3Y 字段集 + 已拍板项 + 4 个待 ADR-034 设计问题；本 v0.2 必读输入）
- `/schema/*.schema.json`
- `/engine/player.py`
- `/content/test_scene_v0/scene.json`

## 附录 C：版本时点声明

本报告所有版本号 / 发版日期 / GitHub 数字**截至 2026-05-18**抓取。未来如：

- Dialogic 发 Beta / 1.0 stable → §3.3 红旗段需修订
- Ren'Py 发 8.6 / 9.x → §3.2 + §5.1 主推荐需评估更新
- Godot 发 5.0 → §2.1 整段需评估兼容性
- Dialogue Manager 发 v5 → §5.2 hybrid 选项需更新

均触发本报告 v0.3 修订；不修改本 v0.2 文件。

---

**v0.4 状态**：**调研使命完成** ✓ ——

- §7 第 1 步 ✓（拍板 v_godot_custom）
- §7 第 2 步 ✓（demo 5 分钟跑通；§8.4）
- §7 第 3 步 ✓（`/engine/` (a)+(b) 合并保留）
- §7 第 4 步 ✓（ADR-035 立项；2026-05-18 落到 `/docs/DECISIONS.md`）

**ADR-035 落地位置**：`/docs/DECISIONS.md` ADR-035 段（2026-05-18 立）
**Godot demo 位置**：[/docs/reviews/master_plan/2026-05-18_godot_demo/](2026-05-18_godot_demo/)（80 行 GDScript + scene + README 三问；实测产物）
**本调研档此后**：作为调研物证保留；不再修订；下一步行动推到阶段 3 → 4 切换会话（拆 T-4.1 ~ T-4.4 工程任务 + 改 ROADMAP / HANDOFF）
