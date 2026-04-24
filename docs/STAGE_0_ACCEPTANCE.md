# STAGE_0_ACCEPTANCE.md — 阶段 0 验收报告

**文档版本**：v0.1
**阶段**：0（基座：Schema + 播放器 + 状态总线）
**签字日期**：2026-04-24
**签字人**：outsiderrr

## 1. 阶段 0 完成判定核对

依据 `/docs/ROADMAP.md` 「阶段 0 § 完成标志」：

- ✅ 作者能在终端里玩通一个手写的五节点场景
- ✅ 校验器对手写场景给出"通过"

## 2. 作者手工验收数据

- **玩通路径**：选项序列 `1→1`
- **经过节点**：`arrival_waystation` → `vellin_confession` → `end_silent_ally`
- **结局标识**：`end_silent_ally`（「沉默的同盟」）
- **其他 3 条可能路径作者选择不手工玩，理由**：ROADMAP 要求"玩通一个"已满足；T-0.6 pytest 的 7/7 自动覆盖了多条路径（包括路径 B、路径 C 的状态守卫可见性、非法输入、schema 失败、MAJOR 版本不匹配）

## 3. Validator 四样本跑通

- `scene.json` → PASS ✅
- `scene_broken_schema.json` → FAIL（schema 层）✅
- `scene_broken_dangling.json` → FAIL（graph 层）✅
- `scene_broken_unreachable.json` → FAIL（graph 层）✅

备注：与 T-0.9 完成报告输出一致。

## 4. 阶段 0 工作量速览

| 任务 | Commit | 一句话成果 |
|---|---|---|
| T-0.1 | 97cc933 | 阶段 0 文档基线（CLAUDE.md / ROADMAP / DECISIONS / DEBATE_NOTES）|
| T-0.2 | 857ce96 | SCHEMA_v0.md D1–D8 决议并入，schema_version → 0.1.1 |
| T-0.3 | 5ef9a38 | SCENE_v0.md《铁誓驿站》五节点场景规约 |
| T-0.4 | fc5fd2c | Python 项目骨架（pyproject、目录、依赖）|
| T-0.5 | 46c392e | JSON Schema 源文件（Draft 2020-12）落地 `/schema/` |
| T-0.6 | 297fd53 | 终端播放器 `/engine/` + 7/7 pytest |
| T-0.7 | d1485aa | 状态总线 + 本体 stub `/state/` |
| T-0.8 | afa4cd5 | 手写测试场景 JSON 落地 `/content/` |
| T-0.9 | 3bd7a58 | 三层 validator（schema / graph / consistency）|
| 验收 | ad1e7f5 | 本验收报告签字 |

## 5. 遗留问题

无。

## 6. 阶段 1 启动前置条件

本验收通过后，阶段 0 架构共识冻结。阶段 1 开始前需由专门的规划师会话产出 `/docs/HANDOFF_STAGE_0_TO_1.md`（不在本任务范围）。
