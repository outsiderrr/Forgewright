# Forgewright License FAQ

> 简短回答开发者关于 Forgewright multi-module license（多模块许可）的常见疑问。

---

## 给独立 RPG 开发者

### Q1 · 我用 Forgewright 做的游戏可以卖钱吗？

✓ 可以。卖多少钱 / 卖给谁都行。不需要付任何 license 费给作者。

### Q2 · 我用 Forgewright 做的游戏需要开源吗？

✗ 不需要。你的游戏只 link Forgewright 的运行时模块（Apache 2.0 宽松 license），你的游戏 license 完全由你自己决定（闭源 / 开源 / 任何 license 都可以）。

### Q3 · Forgewright 不是有 AGPL 模块吗？AGPL 不是要求开源吗？

✓ AGPL 只影响 Forgewright 自己的开发期工具（`/generator`, `/validator`, `/tools` 等），这些模块**不进入你的 game binary**。你的玩家拿到的游戏只含运行时模块（Apache 2.0），不含 AGPL 模块。所以 AGPL 不传染你的游戏。

类比: 用 Blender (GPL) 做的 3D 模型不是 GPL 衍生作品；用 GCC (GPL) 编译的 binary（二进制文件）不是 GPL 衍生作品。Forgewright 同理。

### Q4 · 我可以修改 Forgewright 自己的代码吗？

✓ 可以，但要看你修改哪个模块:

- 修改运行时模块（Apache 2.0）→ 修改自由，你的修改版可以闭源商业用
- 修改开发期工具（AGPL v3）→ 修改自由，但**你的修改版如果分发或作为 SaaS（软件即服务）提供，必须开源 AGPL v3**（仅自己用没限制）

### Q5 · 我用 Forgewright 生成的对话内容 / 世界设定 是我的吗？

✓ 是你的。Forgewright `/generator` (AGPL) 是工具，工具产生的输出（对话 JSON / 角色卡 / 世界设定文件）是**你的作品**，不受 AGPL 传染。你可以闭源商业用、贩售、修改这些输出。

### Q6 · 我可以 fork Forgewright 做我自己的工具卖钱吗？

△ 取决于你 fork 哪部分:

- fork 运行时模块（Apache 2.0）→ 你的衍生工具可以闭源商业
- fork 开发期工具（AGPL v3）→ 你的衍生工具必须开源 AGPL v3，作为 SaaS（软件即服务）也必须开源
  - 若想闭源商业 fork → 需要付费 commercial license（商业许可）（联系 dialogue-flow-skill 作者）

### Q7 · 我可以拿 Forgewright 的代码做我自己的 RPG 引擎吗？

✓ 看哪部分:

- 运行时模块（Apache 2.0）→ 自由拿走用
- 开发期工具（AGPL v3）→ 拿走可以但必须 AGPL 发布

### Q8 · 我可以用 `/content` 模块下的世界设定吗？

✗ `/content` 是作者私人创作（CC-BY-NC 4.0）。你可以**学习 / 参考**，但**不能直接商业用**。你的游戏需要自己写世界设定（这本来也是你的创作责任）。

---

## 给商业机构

### Q9 · 我们公司想拿 Forgewright `/generator` 做闭源 AI 服务卖给游戏开发者，可以吗？

✗ 不可以（除非买 commercial license（商业许可））。`/generator` 是 AGPL v3，作为 SaaS（软件即服务）提供也必须开源。想做闭源商业 → 联系 [dialogue-flow-skill](https://github.com/outsiderrr/dialogue-flow-skill) 作者协商 commercial license（商业许可）（dialogue-flow-skill 是 `/generator` 的核心依赖）。

### Q10 · 我们公司用 Forgewright 做内部游戏开发，公司游戏不开源可以吗？

✓ 可以（前提同 Q1-Q3）。公司用 Forgewright 做游戏不需付费、不需开源你们的游戏。

---

## 给学术 / 研究者

### Q11 · 我可以用 Forgewright 做研究 + 发表论文吗？

✓ 完全可以。学术 / 研究 / 非商业用途完全免费，符合 AGPL 精神。请在论文中 cite（引用）Forgewright。

---

## 其他问题

如果上面没回答你的问题，请到 Forgewright 仓库开 issue 询问。
