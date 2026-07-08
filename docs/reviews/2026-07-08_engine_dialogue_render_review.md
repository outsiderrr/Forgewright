# Code Review — PR #83 feat(engine): 终端播放器渲染 ADR-040 dialogue[]（按说话人）

评审者：gpt-5.5 via relay API  
日期：2026-07-08  
评审目标：PR #83 / branch `claude/player-dialogue-adr040`（base = `main`）  
报告路径：`/docs/reviews/2026-07-08_engine_dialogue_render_review.md`

## 总览

本次 diff 范围很小：`engine/player.py` 在节点 narration 后渲染 optional `dialogue[]`，并在 `engine/tests/test_player.py` 增加 2 条回归测试。

结论：实现本身符合 ADR-040 的方向：`line` 保持裸正文，终端呈现层统一施加 `「」`；`dialogue` 缺失时运行时代码路径不会额外输出；未新增 LLM / 网络依赖；`engine/player.py` 仍远低于 500 行目标。

但有 1 个测试层面的缺口：PR 自述中“legacy 无 dialogue 场景输出零变化”没有被测试真正钉死。目前测试只检查没有出现 `：「`，不能防止无 dialogue 场景的其它输出被误改。

## Findings

### 🟡 IMPORTANT — TEST — “无 dialogue 输出零变化”测试不是零变化断言

- 文件：`engine/tests/test_player.py:285`
- 代码：

```python
def test_adr040_absent_dialogue_output_unchanged(tmp_path):
    # legacy 场景（无 dialogue 字段）输出零变化：不出现对白体例
    scene_file = tmp_path / "scene_c.json"
    scene_file.write_text(json.dumps(_SCENE_C, ensure_ascii=False), encoding="utf-8")

    _, out = _run(scene_file, "1\n1\n")
    assert "：「" not in out
```

**问题**

测试名和注释说的是“输出零变化”，但实际只断言输出中没有 `：「`。这只能证明 legacy 场景没有新增 ADR-040 白体例，不能证明输出与改动前完全一致。

如果后续有人不小心改坏 legacy 输出，例如：

- header 多/少一个空行；
- narration 与 options 之间的间距改变；
- option 编号格式改变；
- end 节点输出顺序改变；
- speaker/location fallback 文案改变；

只要没有出现 `：「`，这条测试仍会通过。

这与本 PR 的重点之一“向后兼容（无 dialogue 场景输出零变化的测试是否真钉死）”不一致。

**建议修复**

把该测试改成真正的完整输出对比。可选做法：

1. 复用本文件已有 legacy 场景测试的 expected output，如果已有精确字符串；或
2. 在此测试中写出完整 expected `out` 字符串并 `assert out == expected`；或
3. 如果已有 golden/snapshot 机制，则对 `_SCENE_C` 的完整 stdout 做 golden 对比。

重点是断言完整 stdout，而不是只断言 absence of `：「`。

## 非 finding 核查记录

- `engine/player.py:96-101`：`dialogue = node.get("dialogue") or []` 对缺失字段与空数组均不输出，符合 optional `dialogue[]` 的向后兼容意图。
- `engine/player.py:98`：speaker 使用 `_resolve_display(entry["speaker_ref"], err)`，沿用既有本体显示名解析与 fallback 路径；未新增 generator/state/LLM 依赖。
- `engine/player.py:99`：输出格式为 `显示名：「裸正文」`，符合 ADR-040 决策四中“line 为裸正文，引号体例由呈现层施加”的方向。
- `engine/player.py`：本次仅增加少量渲染逻辑，未违反 engine ≤500 行、0 LLM、0 网络的约束。
- `engine/tests/test_player.py:258-279`：新增正向测试覆盖了多条 dialogue、narration 在 dialogue 前、`dialogue=[]` 不产生对白行。

## 严重度统计

- 总 findings：1
- 🔴 CRITICAL：0
- 🟡 IMPORTANT：1
- 🟢 NICE：0

## Top Priority

优先修复 `test_adr040_absent_dialogue_output_unchanged`：把“无 dialogue 场景输出零变化”改成完整 stdout 精确对比，确保 legacy 输出兼容性真的被钉死。


<!-- delivered via tools/cross_review.py (governance v0.6 §13); model=gpt-5.5; prompt_chars=13005; usage={"completion_tokens": 2970, "total_tokens": 9824, "prompt_tokens": 6854, "prompt_tokens_details": {"cached_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0}} -->
