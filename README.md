# Forgewright

Forgewright 是一条 AI 辅助的分支叙事内容生产流水线：运行时是极薄的 JSON 对话图播放器（无 LLM），所有生成与校验在开发期完成。

---

> ## 🎮 给独立 RPG 开发者的承诺
>
> Forgewright 的 license 看起来复杂（运行时 Apache 2.0 + 开发期工具 AGPL v3 + 等），但你**不需要理解这些细节**就能放心用。简化版承诺:
>
> - ✓ 用 Forgewright 制作的游戏**可以闭源商业销售**
> - ✓ **不需要付任何 license 费**（不管你做免费 / 付费 / 开源 / 闭源游戏）
> - ✓ **不需要开源你的游戏**（不管你用什么 license 做你的游戏）
> - ✓ 你**自由地**用 Forgewright 做游戏，把游戏卖给玩家
>
> **为什么可以放心**: 你 export 出的 game binary 只含运行时模块（Apache 2.0 宽松 license），不含 AI 生成 / 校验 / 工具等开发期模块。AGPL 模块是 Forgewright 自己防止 vendor 抢工具 IP 的设计，**不传染你的游戏**。
>
> 多模块 license 是 Forgewright 项目自己的可持续设计，**不影响你制作的游戏**。
>
> 详细问题见 [docs/FAQ-LICENSE.md](docs/FAQ-LICENSE.md)。技术细节见下面 [License section](#license)。

---

## 当前阶段

**阶段 0：基座搭建**。目标是在无 LLM 参与下搭起 Schema、播放器、状态总线与一个手写测试场景。尚未进入阶段 1（单节点 AI 生成），因此本仓库暂不包含任何 LLM 调用、prompt 模板或生成代码。

## 了解更多

- [`/CLAUDE.md`](./CLAUDE.md)：项目硬性规则，任何 Claude 会话必读。
- [`/docs/ROADMAP.md`](./docs/ROADMAP.md)：五阶段路线图与各阶段完成标志。

## License

> **🎮 重申给开发者**: 用 Forgewright 做的游戏**可以闭源商业销售**，**不需付费**，**不需开源**。多模块 license 是 Forgewright 自己的设计，不影响你的游戏。详见 [docs/FAQ-LICENSE.md](docs/FAQ-LICENSE.md)。

Forgewright 是多模块许可项目，不同模块采用不同 license。

| 模块类型     | License        | 模块                              |
|--------------|----------------|-----------------------------------|
| 运行时模块   | Apache 2.0     | `/engine`, `/state`, `/schema`    |
| 开发期工具   | AGPL v3        | `/generator`, `/validator`, `/tools` |
| 文档         | CC-BY 4.0      | `/docs`                           |
| 私人创作内容 | CC-BY-NC 4.0   | `/content`                        |
| 作者游戏实例 | Proprietary    | `/game`                           |

总览: [LICENSE](LICENSE) · 各模块详情见模块目录下 LICENSE 文件。

依赖: [dialogue-flow-skill](https://github.com/outsiderrr/dialogue-flow-skill)（AGPL v3 + Commercial Dual）—— 用作 `/generator` 内部 spec（规范），不进入 game binary。
