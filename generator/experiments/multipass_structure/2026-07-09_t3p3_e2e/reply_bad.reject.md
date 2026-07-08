# 回流退回单：lucy_roadhouse_multipass（4 处需修改）

逐条修完后整份重交；node_id / 选项序号以随包的「锁定节点清单」为准。

1. [E1 missing_node] 节点 `pressure_line_b4`
   期望：锁定清单里的每个节点都要交一个 [node: ...] 块
   实际：回流文本里没有这个节点的块
   修改指引：补交 [node: pressure_line_b4] 块（beats 拍：narration + continue（dialogue 可选））（本拍锁定线索：「高压让露西更害怕角落男人听见，她不会给钥匙位置、楼下传闻或空间异常细节。」）。

2. [E4 option_count_mismatch] 节点 `opening`（第 7 行）
   期望：序号 1..4 连续完整（锁定选项数 = 4）
   实际：交了 1: / 2: / 3: / 5:
   修改指引：把序号改成 1..4 连续完整、共 4 条，不得增删（结构已锁定）。

3. [E6 unknown_key] 节点 `end_soft_leave`（第 71 行）
   期望：end 节点：仅 narration（dialogue 可选）
   实际：块里带了 options:
   修改指引：删掉该节点的 options: 块；end 节点不带选项/接话，结局收束由结构锁定。

4. [E8 parse_error] 节点 `opening`（第 12 行）
   期望：options 块内每行形如「1: 台词」（单行值，无续行）
   实际：第 12 行在 options 块内但不是序号行：「（这是一行游离备注，既不是选项也不是对白，无法归属任何 ke」
   修改指引：把它并进所属序号行（一条选项一行写完），或按「序号: 台词」补上序号。
