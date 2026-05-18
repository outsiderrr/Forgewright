# Godot Demo — ADR-035 v_godot_custom 体感验证

> **目的**：验证 Forgewright JSON → Godot 渲染 → 玩家按按钮 → 跳下一节点 的逻辑通路。
> **性质**：throwaway 原型；跑完即丢；**不是**正式 `/host/godot_first_game/` 实施。
> **预期工时**：装 Godot 5 分钟 + 跑 demo 5 分钟 = **总共 < 15 分钟**。

---

## 一、装 Godot 4.6.2（5 分钟）

**方式 A（推荐；最快）**：

1. 浏览器打开 <https://godotengine.org/download/macos/>
2. 下载 **Godot Engine - Standard version**（macOS Universal；约 100 MB）
3. 解压；把 `Godot.app` 拖进 `/Applications/`
4. 第一次打开可能被 macOS Gatekeeper 拦——右键 → 打开 → 允许

**方式 B（Homebrew）**：

```bash
brew install --cask godot
```

---

## 二、跑 Demo（5 分钟）

1. 打开 Godot 应用 → 进入 Project Manager
2. 点击 **Import** 按钮
3. 浏览到本目录的 `project.godot` 文件 → 选中 → Open
4. 进入项目编辑器后 → 按 **F5**（或菜单 Project → Run Project）
5. 弹出窗口应该显示：
   - 上半屏：场景叙述文字（"黄昏时分你策马抵达铁誓驿站..."）
   - 下半屏：3 个按钮（3 个选项）
6. 点任意按钮 → 跳下一节点 → 继续渲染
7. 玩到 "—— 结局 ——" 表示 demo 通过

---

## 三、Demo 故意不做（避免 scope creep）

| 故意省略 | 完整版（v_godot_custom）会做 |
|---|---|
| 中文字体打包（可能显示方块） | 完整版打包 Noto Sans SC |
| 评估 `condition`（demo 版全显示所有选项） | 完整版 state_condition 树评估 |
| 应用 `effects`（demo 版只跳节点；不改 state） | 完整版 state_effect 应用 |
| 解析 `speaker_ref` → display_name（demo 显示 ID 如 `char_vellin`） | 完整版本体解析 |
| `unavailable_behavior` 三态（hide / disable / disable_with_hint） | 完整版按枚举处理 |
| scene 间跳转 / scene_metaparams / T-3Y 字段集 | 完整版 scene_router.gd 处理 |
| 多平台导出 / itch.io 上传 | 阶段 4 工程任务 T-4.4 |

---

## 四、验证什么 + 反馈给作者

跑完后请反馈以下三点：

| # | 问 | 怎么答 |
|---|---|---|
| 1 | **装 Godot + Import project 总共花了多久？** | 写实际分钟数 |
| 2 | **F5 是否一次跑通？** 如果没有，报错是什么？ | 写报错截图或文字 |
| 3 | **是否能完整玩到 "—— 结局 ——"？** | 是 / 否 |

这三个答案给"v_godot_custom 完整版 2-3 天作者经验估时"一个**体感校准**：

- 1 + 2 + 3 都顺利 → 2-3 天估时**可信**；进入立 ADR-035 + 阶段 4 T-4.x 工程任务
- 任意一项卡住 → 卡了什么，分析下一步：是 Godot 装坑 / GDScript bug / scene format 不兼容；估时可能需要 +1-2 天 buffer

---

## 五、文件清单

```
2026-05-18_godot_demo/
├── README.md          # 本文件
├── project.godot      # Godot 项目配置（10 行）
├── main.tscn          # 主场景（25 行；UI 节点树）
├── main.gd            # GDScript 核心（55 行；读 JSON + 渲染 + 按钮）
├── scene.json         # 拷贝自 /content/test_scene_v0/scene.json
└── .gitignore         # 忽略 Godot 缓存（.godot/ 等）
```

**核心代码量**：55 行 GDScript + 25 行 scene = **80 行**。
v_godot_custom 完整版预估 ~500-700 行 GDScript（含 condition / effects / 本体 / scene_router / 多平台导出）—— **demo 是完整版的 10-15%**。

---

## 六、下一步（demo 跑通后）

1. **反馈跑 demo 的三问回答** → 给作者决定立不立 ADR-035 提供体感校准数据
2. **如果体感顺利** → 进入 fixation 会话签字 ADR-035 + 改 `/docs/DECISIONS.md` 立 ADR-035 + 改 `/docs/ROADMAP.md` 阶段 4 起手任务列表
3. **如果体感卡了** → 在调研报告 v0.4 里加 "demo 实测发现" 段；调整估时 + 风险段

**本 demo 目录跑完后可保留作历史档**（不删；放在 `/docs/reviews/master_plan/` 同位置，作为 ADR-035 v0.3 调研物证）。
