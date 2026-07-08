"""回流格式契约 v1 —— 单一真相源（T-3P-0；ADR-039 路线 A）.

编剧（BYOM）拿到的整场写作提示词包里，"输出格式"段按本模块常量声明；
回流解析器（T-3P-2）按本模块常量解析与报错。拆解文档 §4 是草案，
**文字与代码不一致时以本模块 + 其测试为准**（格式变化需回样张同步）。

本模块**只定义契约，不写解析器**（解析器 = T-3P-2）。

回流文本形态（§4.1 轻量标签 markdown，作者 2026-06-29 拍板单一格式）：

    [node: <node_id>]          ← node_id = 成品图节点 id；beats 拍 = {pid}_b{i} 锁定微节点 id
    narration: <旁白正文>       ← 必填；值 = 冒号后至下一个 key 行 / 下一个 [node:] 之间全部文本
    dialogue:                  ← 可选；0 行合法
      - <NPC 的一句话，裸正文不带引号包裹>
    options:                   ← 仅 choice 节点；序号必须 1..N 连续完整，N = 锁定选项数
      1: <玩家第一人称台词>
    continue: <接话>            ← 仅 beats 拍（单选项）；end 节点无 options / continue

编剧不得增删节点、不得改 node_id、不得增删选项序号（结构已由我们锁定）。
dialogue 行说话人归属：v1 = 图级单说话人（run_config.speaker_ref），编剧不写说话人名。
多行值范围：**只有 narration 是多行值**（MULTILINE_VALUE_KEYS）；continue 的值、
options 每条序号行、dialogue 每条 `- ` 行都是单行值，其后的续行落 E8（parse_error）。
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# §4.1 标签语法常量
# ---------------------------------------------------------------------------

# 节点块头（node_id 与锁定骨架逐字一致；beats 拍 = beat_split 的 {pid}_b{i}）
NODE_HEADER_TEMPLATE = "[node: {node_id}]"

# 四个字段 key（key 行形态 = "<key>:"，冒号后跟值或换行接块内容）
KEY_NARRATION = "narration"
KEY_DIALOGUE = "dialogue"
KEY_OPTIONS = "options"
KEY_CONTINUE = "continue"

# dialogue 块内每行 = 缩进可选 + "- " + 裸正文（不带引号包裹；说话人归属图级单说话人）
DIALOGUE_ITEM_PREFIX = "- "

# options 块内每行 = 序号 + ": " + 玩家第一人称台词；序号必须 1..N 连续完整
OPTION_LINE_TEMPLATE = "{index}: {text}"

# 多行值白名单：值可以吃后续行（直到下一个 key 行 / 节点头）的 key **只有 narration**。
# continue 的值 / options 序号行 / dialogue `- ` 行都是单行值——其后的续行不属于
# 任何多行值，按 E8（parse_error）归类。用 list 不用 tuple：同 NODE_CATEGORY_KEYS
# 的 JSON round-trip 理由。
MULTILINE_VALUE_KEYS: list[str] = [KEY_NARRATION]

# 节点类别 → 必交 / 可选 key 表（结构锁定后编剧唯一要填的三类正文槽位）
#   choice = 多选项决策点；beat = beats 链单选项拍（锁定微节点）；end = 收束节点
# 值用 list 不用 tuple：契约数据要能无损过 JSON round-trip（架构共识 1 JSON-native；
# tuple 经 json dumps/loads 变 list，== 比较会永假）
NODE_CATEGORY_KEYS: dict[str, dict[str, list[str]]] = {
    "choice": {"required": [KEY_NARRATION, KEY_OPTIONS], "optional": [KEY_DIALOGUE]},
    "beat": {"required": [KEY_NARRATION, KEY_CONTINUE], "optional": [KEY_DIALOGUE]},
    "end": {"required": [KEY_NARRATION], "optional": [KEY_DIALOGUE]},
}


# ---------------------------------------------------------------------------
# §4.2 硬报错分类 E1-E8（收集全清单后一次退回，不 fail-fast）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ErrorSpec:
    """一类回流硬报错的契约定义（T-3P-2 解析器按此分类；退回单逐条引用）。"""

    code: str  # E1..E8
    slug: str  # 机器可读短名
    meaning: str  # 含义（给编剧的退回单用语基准）
    boundary: str  # 边界判定（逐 case 定死；样张覆盖）


ERRORS: dict[str, ErrorSpec] = {
    e.code: e
    for e in (
        ErrorSpec(
            "E1",
            "missing_node",
            "锁定骨架有、回流缺的节点",
            "以锁定骨架节点清单为基准逐一核对；整块 [node: X] 不在回流文本里即 E1",
        ),
        ErrorSpec(
            "E2",
            "unknown_node",
            "回流有、锁定骨架没有的节点（结构已锁定，不接受新增）",
            "回流文本出现骨架清单之外的 [node: X] 即 E2；改 node_id 拼写同样落此类",
        ),
        ErrorSpec(
            "E3",
            "duplicate_node",
            "同一 node_id 出现两个块",
            "第二次出现即记 E3；两个块内容是否一致不影响判定",
        ),
        ErrorSpec(
            "E4",
            "option_count_mismatch",
            "选项序号缺号 / 多号 / 不连续 / 与锁定数不符",
            "options: 块存在且**至少有 1 条序号行**、但序号缺号、多号、不连续或总数 ≠ "
            "锁定选项数时为 E4；块整体缺失不落此类（那是 E5）；块在但一条序号行都没有"
            "（0 条）也不落此类（唯一归属 E7 空块——E4 只管序号行存在但对不上）",
        ),
        ErrorSpec(
            "E5",
            "missing_field",
            "必填 key 缺失（narration / continue / options 块整体缺失）",
            "按 NODE_CATEGORY_KEYS 的 required 表核对；options: 块**整体缺失** = E5"
            "（必填块缺失），与 E4（块在但序号不对）互斥",
        ),
        ErrorSpec(
            "E6",
            "unknown_key",
            "不认识或不该出现的字段 key（含错位块与重复出现的已知 key）",
            "不在 NODE_CATEGORY_KEYS required+optional 之内的 key 即 E6；"
            "错位块同类处理（如 end 带 options、choice 带 continue）；"
            "同一节点块内**已知 key 第二次出现**（如两个 narration: 行、两个 options: 块）"
            "同样落 E6，从第二次出现处记（首次出现的块正常归属，不受影响）",
        ),
        ErrorSpec(
            "E7",
            "empty_text",
            "key 行或序号行存在但正文为空",
            "key 行存在但冒号后（及其块内）无任何非空白正文即 E7；逐 case："
            "options 序号行有序号无正文（如 `3: ` 后为空）= E7；"
            "dialogue 块内空 `- ` 条目（连字符后无正文）= E7；"
            "options: key 行在但块内 0 条序号行 = E7（空块唯一归属此类，不落 E4）；"
            "dialogue: 块 0 行是合法可选，不落此类",
        ),
        ErrorSpec(
            "E8",
            "parse_error",
            "无法归属任何 key 的行",
            "不构成节点头、key 行、dialogue 行、options 序号行且不属于任何多行值的"
            "游离行即 E8；多行值只有 narration（MULTILINE_VALUE_KEYS）——continue 的值、"
            "options 序号行、dialogue 行都是单行值，其后的续行落 E8",
        ),
    )
}


# ---------------------------------------------------------------------------
# CLI 约定（v1 各工具独立模块入口；不建共享 __main__.py——见包 docstring）
# ---------------------------------------------------------------------------

# 退出码三态（P-A / P-B CLI 统一遵守）
EXIT_OK = 0  # 成功
EXIT_REJECTED = 1  # 回流拒收（格式 E 类或验收 fail）
EXIT_USAGE = 2  # 用法・输入错误


__all__ = [
    "NODE_HEADER_TEMPLATE",
    "KEY_NARRATION",
    "KEY_DIALOGUE",
    "KEY_OPTIONS",
    "KEY_CONTINUE",
    "DIALOGUE_ITEM_PREFIX",
    "OPTION_LINE_TEMPLATE",
    "MULTILINE_VALUE_KEYS",
    "NODE_CATEGORY_KEYS",
    "ErrorSpec",
    "ERRORS",
    "EXIT_OK",
    "EXIT_REJECTED",
    "EXIT_USAGE",
]
