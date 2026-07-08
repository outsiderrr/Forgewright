# T-3P-3 端到端闭环实测产物（作者验收物）

ADR-039 首版核心闭环的**收官实测**：结构 → 写作提示词包 → 回流 → 验收 → 落地 → 终端播放。
本目录是 E2E 中间产物（experiments 惯例）。

**口径（C 阶段 / 作者 2026-07-09 拍板 Option 1；ADR-006）**：验收闸的
`validator.validate` **三层全部硬拦**——含**本体解析**（`does not resolve in ontology`）。
lucy fixture 引用 `char_lucy` / `scene_hibo_roadhouse` **未在 `/state/ontology/` 发布**，
故 lucy 正例**验收 FAIL、不落地**（守门在工作，不是缺陷）。隔离目录
`/content/_e2e_writer_loop/lucy_roadhouse/` 因此**只有 FAIL 验收报告、无 scene.json**。
完整叙述见
[`/docs/reviews/master_plan/2026-07-09_pa_pb_e2e_report.md`](../../../../docs/reviews/master_plan/2026-07-09_pa_pb_e2e_report.md)。

## 文件

| 文件 | 是什么 | 怎么来的 |
|---|---|---|
| `lucy_roadhouse_multipass.pack.md` | P-A 渲染的整场写作提示词包（35 节点块） | `render_pack --design <fixture> --spec <lucy spec>`（rc=0） |
| `reply_good.md` | 合法编剧回流（35 节点全交齐） | 复用 T-3P-2 演示物 `../2026-07-08_t3p2_ingest_demo/reply_good.md`（正文=旧露西实测正文按新 beats_plan 手工改写） |
| `reply_bad.md` | **格式层反例**：含 4 类 E 错误（E1 漏块 / E4 序号 1,2,3,5 / E6 end 带 options / E8 游离行） | `make_negatives.py` 从 reply_good.md 确定性变异 |
| `reply_bad.reject.md` | **真实退回单**（4 处需修改，未产 scene.json） | ingest CLI（rc=1） |
| `illegal_scene.json` | **语义层反例**：lucy 合并产物上再注入闭合违规 + 机械违规 | `make_negatives.py`（从 fixture design × reply_good 合并产物派生） |
| `illegal_scene.acceptance.{md,json}` | 该非法 graph 的验收报告（**FAIL**，硬拦 41 条：37 本体 + 1 闭合 + 1 schema + 2 机械） | `run_acceptance` |
| `make_negatives.py` | 两层反例的确定性再生脚本（0 LLM） | — |

**两层反例的性质区别（务必如实读）**：
- 格式层（reply_bad）= 对**编剧真实错误**的拦截面（编剧手填时会犯的错，P-B 解析/对齐阶段拦）。
- 语义层（illegal_scene）= **技术负路径测试**，**不是**编剧回流模拟——路线 A 下编剧
  触不到 speaker_ref / effects 这些结构字段。它验证验收闸对"管线 bug / 被手改的
  scene.json / 配置错 / 本体不全"这条防线硬拦。详见 E2E 报告「如实边界说明」。

## 复现（从仓库根跑）

```bash
# ① P-A 渲染写作提示词包
python -m generator.promptpack.render_pack \
  --design generator/experiments/multipass_structure/2026-06-29_t3p_fixture/lucy/design.json \
  --spec   generator/experiments/multipass_structure/specs/lucy.json \
  --out    generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/lucy_roadhouse_multipass.pack.md

# ② P-B 合并 + 验收 + 落地（lucy 正例；因引用未发布本体 → 验收 FAIL、不落地、rc=1）
#    隔离目录只留 FAIL 验收报告（scene.acceptance.md/.json），无 scene.json/version.json。
python -m generator.promptpack.ingest \
  generator/experiments/multipass_structure/2026-06-29_t3p_fixture/lucy/design.json \
  generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/reply_good.md \
  --land content/_e2e_writer_loop/lucy_roadhouse

# ③ 播放链路演示（直接喂合并产物，不经验收闸；lucy 验收 FAIL 不落地，故用合并产物临时落盘）
#    入口 = engine/__main__.py，不是 engine.player（critique F-1）。
#    见测试 test_lucy_merge_product_plays_through_engine（喂 4→1→1→1→1 玩到结局）。

# ④ 两层反例
python generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/make_negatives.py
python -m generator.promptpack.ingest \
  generator/experiments/multipass_structure/2026-06-29_t3p_fixture/lucy/design.json \
  generator/experiments/multipass_structure/2026-07-09_t3p3_e2e/reply_bad.md   # rc=1，产退回单
```
