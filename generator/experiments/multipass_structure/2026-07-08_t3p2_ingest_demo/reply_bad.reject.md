# 回流退回单：lucy_roadhouse_multipass（5 处需修改）

逐条修完后整份重交；node_id / 选项序号以随包的「锁定节点清单」为准。

1. [E1 missing_node] 节点 `soft_private_line_b3`
   期望：锁定清单里的每个节点都要交一个 [node: ...] 块
   实际：回流文本里没有这个节点的块
   修改指引：补交 [node: soft_private_line_b3] 块（beats 拍：narration + continue（dialogue 可选））（本拍锁定线索：「路标是第七码碑和一根断了半截的电线杆。」）。

2. [E4 option_count_mismatch] 节点 `opening`（第 7 行）
   期望：序号 1..4 连续完整（锁定选项数 = 4）
   实际：交了 1: / 2: / 3: / 5:
   修改指引：把序号改成 1..4 连续完整、共 4 条，不得增删（结构已锁定）。

3. [E6 unknown_key] 节点 `end_soft_leave`（第 65 行）
   期望：end 节点：仅 narration（dialogue 可选）
   实际：块里带了 options:
   修改指引：删掉该节点的 options: 块；end 节点不带选项/接话，结局收束由结构锁定。

4. [E7 empty_text] 节点 `money_line_b2`（第 76 行）
   期望：narration: 后要有旁白正文（可多行）
   实际：narration: 行在，但正文为空
   修改指引：在 narration: 冒号后（或紧接的下一行起）写该节点的旁白。

5. [E8 parse_error] 节点 `soft_private_line_b7`（第 51 行）
   期望：节点块内每行都要能归属某个 key（narration 之外都是单行值）
   实际：第 51 行无法归属任何 key：「（这里是我想留给下一拍的备注）」
   修改指引：把这行并进它所属的 key（narration 可多行；continue/序号行/「- 」行都是一行写完），或删掉。
