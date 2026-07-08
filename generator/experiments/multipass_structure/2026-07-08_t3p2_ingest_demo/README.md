# T-3P-2 回流合并演示（作者验收物）

P-B 回流合并器（`generator/promptpack/ingest.py`）对 **augmented lucy fixture**
（`../2026-06-29_t3p_fixture/lucy/design.json`）的一次真实合并 + 一张真实退回单。
请按两个问题批：① 好回流合并出的场景读起来通不通（看 `scene.md`）？
② 编剧拿到退回单知不知道怎么改（看 `reply_bad.reject.md`）？

## 文件

| 文件 | 是什么 | 怎么来的 |
|---|---|---|
| `reply_good.md` | 合法编剧回流（35 节点全交齐） | 手写：choice/end 沿用旧露西实测正文；**beats 链按 T-3P-0 新 beats_plan（8/6/6/4/4 拍、每拍 1 条锁定线索）手工微改写**（旧正文是 LLM 按 6 拍写的，无机械映射——拆解 §5.3 口径） |
| `scene.json` | 合并产物（35 节点 dialogue_graph） | `python -m generator.promptpack.ingest <fixture design.json> reply_good.md --out scene.json`（rc=0；真实 CLI 输出） |
| `scene.md` | 可读投影（剧本式 markdown） | scene.json 经 `render_scene_md` 渲染 |
| `reply_bad.md` | 坏回流（构造 5 种错：E1 漏块 / E4 序号 1,2,3,5 / E6 end 带 options / E7 空 narration / E8 continue 续行） | 从 reply_good.md 改坏 |
| `reply_bad.reject.md` | **真实退回单**（5 处需修改，未产 scene.json） | `python -m generator.promptpack.ingest <fixture design.json> reply_bad.md`（rc=1；真实 CLI 输出） |

## 合并产物校验证据（诚实记录）

`scene.json` 过 validator 各层：schema 0 错 / graph 0 错 / 机械预检
（generation_source="human"）0 错 / AP 预检 0 flag / consistency **无任何
speaker_ref / dialogue 闭合违规**；剩余 37 条 consistency 均为本体解析
（露西场景 refs 不在已加载本体内——与 `test_reassemble_lucy_adr040` 同口径，
与合并器正交）。ADR-040 不变量成立：narration=纯旁白、对白在
`dialogue=[{speaker_ref,line}]`、节点级 `speaker_ref=null`、`schema_version`
保持 `"0.1.1"` 不 bump；全部 node + option 带 `generation_trace.source="human"`。

## 复现

```bash
# 好回流 → scene.json（rc=0）
python3 -m generator.promptpack.ingest \
  generator/experiments/multipass_structure/2026-06-29_t3p_fixture/lucy/design.json \
  generator/experiments/multipass_structure/2026-07-08_t3p2_ingest_demo/reply_good.md \
  --out generator/experiments/multipass_structure/2026-07-08_t3p2_ingest_demo/scene.json

# 坏回流 → 退回单（rc=1，不产 scene.json）
python3 -m generator.promptpack.ingest \
  generator/experiments/multipass_structure/2026-06-29_t3p_fixture/lucy/design.json \
  generator/experiments/multipass_structure/2026-07-08_t3p2_ingest_demo/reply_bad.md
```

注：正文来源审计——`reply_good.md` 是旧 LLM 实测正文的人工改写（挂 human 标
只是管线角色标记），本目录是演示物，不入正式内容库（与拆解 §8 确认项 7 的
E2E 隔离目录口径一致；正式 E2E 闭环 = T-3P-3）。
