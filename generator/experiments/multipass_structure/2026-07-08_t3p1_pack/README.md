# T-3P-1 作者验收物：lucy 整场写作提示词包（P-A 渲染器真渲染）

- `lucy_roadhouse_multipass.pack.md` —— 编剧（BYOM）实际会拿到的**整场唯一交付物**
  （35 个节点块：2 choice + 28 beats 拍 + 5 end）。请按"一个编剧拿到这个能不能直接开写、
  会不会写崩结构、格式说明看不看得懂"判效果；参照物 = 转向提案附录 A（单节点样例，
  `docs/reviews/master_plan/2026-06-21_pivot_to_writer_prompt_pack.md`）。
- 输入 = T-3P-0 共用 fixture（`../2026-06-29_t3p_fixture/lucy/design.json`，
  beats_plan 按作者 2026-07-08 拍板的每拍 1 条线索）+ `../specs/lucy.json`；无前情摘要
  （lucy 是首场用例，pack 内"故事至此"段显式写明）。
- 复现命令（0 LLM，确定性——同输入逐字节相同；golden 测试
  `generator/promptpack/tests/test_render_pack.py` 引用本文件为基准）：

```bash
python -m generator.promptpack.render_pack \
  --design generator/experiments/multipass_structure/2026-06-29_t3p_fixture/lucy/design.json \
  --spec generator/experiments/multipass_structure/specs/lucy.json \
  --out generator/experiments/multipass_structure/2026-07-08_t3p1_pack/lucy_roadhouse_multipass.pack.md
```
