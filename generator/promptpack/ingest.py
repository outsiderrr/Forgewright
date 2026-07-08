"""P-B 回流合并器（T-3P-2；ADR-039 决策二）：编剧回流文本 → scene.json 或整单退回.

解析编剧（BYOM）交回的轻量标签 markdown（格式契约单一真相源 =
generator/promptpack/format_spec.py），按 **node_id + 显式选项序号** 对齐锁定骨架，
全部对上才确定性合并成 dialogue_graph JSON；任何 E1-E8 → **不产 scene.json**，
console 摘要 + `<reply 去后缀>.reject.md` 整单退回。

与 assemble.py 的语义关系（ADR-039 后果 + 拆解 §3.2，**语义相反**，不可混用）：
  - assemble 消费同源可信数据（本仓库多 pass 产物），静默容错（截断对齐 /
    回退第一出边 / 缺数据照样产空节点）；
  - 本模块消费编剧手填文本，**硬报错**——收集全部 E1-E8 后一次退回，
    禁止任何截断对齐 / 回退默认 / 静默吞掉。
  - 机械合并半（引号归一 / 结构化对白 / 机械选项字段 / beats 入口映射）复用
    assemble 的**公开别名**（normalize_line / dialogue_entries / mk_option /
    entry_graph_node_id），不引下划线私有符号、不改其行为。

硬错误（E 类）只面向**编剧可改的问题**；design.json 侧的问题（缺 run_config、
拓扑走形等）是我们自己的产物坏了，一律 PromptpackInputError（CLI 退出码
EXIT_USAGE=2），不进退回单。锁定骨架**只准经 io.load_design_artifact 读**。

确定性：同 reply + 同 design.json（含 run_config）→ 逐字节相同 scene.json；
回流文本内节点块顺序不影响输出（合并按 topology 顺序遍历）。trace 只写
`generation_trace={"source": "human"}`（node + option 级），不写时间戳。

CLI（独立模块入口，T-3P-0 约定）：
    python -m generator.promptpack.ingest <design.json> <reply.md> [--out <scene.json>]
退出码三态：EXIT_OK=0 合并成功 / EXIT_REJECTED=1 回流拒收 / EXIT_USAGE=2 用法・输入错误。

0 LLM。本模块只做解析 + 对齐 + 合并 + 退回单；验收管线接线与 content/ 落地 = T-3P-3。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from generator.multipass.assemble import (
    dialogue_entries,
    entry_graph_node_id,
    mk_option,
    normalize_line,
)
from generator.promptpack.format_spec import (
    ERRORS,
    EXIT_OK,
    EXIT_REJECTED,
    EXIT_USAGE,
    KEY_CONTINUE,
    KEY_DIALOGUE,
    KEY_NARRATION,
    KEY_OPTIONS,
    NODE_CATEGORY_KEYS,
)
from generator.promptpack.io import PromptpackInputError, load_design_artifact

# ---------------------------------------------------------------------------
# 行级词法（严格按 format_spec §4.1；全角冒号变体单独识别 → E8 + 恢复解析防级联噪音）
# ---------------------------------------------------------------------------

# 节点块头 [node: <id>]；全角冒号捕出来单独报 E8（identified 后仍按块头恢复，
# 防止整块内容级联成一串无意义 E6/E8）
_NODE_HEADER_RE = re.compile(r"^\s*\[node\s*([:：])\s*([^\]\s][^\]]*?)\s*\]\s*$")

# key 行 = ASCII 标识符 + 冒号（值可跟可不跟）。**任何**匹配此形态的行都终止
# narration 多行值——未知标识符落 E6（unknown_key），否则 E6 永远探不到
# narration 之后的未知 key（会被多行值静默吞掉，违反硬报错语义）。
_KEY_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*([:：])\s?(.*)$")

# options 序号行 = 数字 + 冒号 + 玩家台词（单行值）
_OPTION_LINE_RE = re.compile(r"^\s*(\d+)\s*([:：])\s?(.*)$")

# dialogue 条目行 = 缩进可选 + "- "（连字符 + 空白）+ 裸正文。**严格要求空白**：
# 若容 `-` 后无空白，markdown 分隔线 `---` 会被读成对白行 "--" 静默入图
# （/review Angle A 实证的唯一静默腐蚀路径）。裸 `-`（后无内容）单独识别成
# 空条目 E7；`-xx` / `---` 等落 E8。
_DIALOGUE_ITEM_RE = re.compile(r"^\s*-[ \t](.*)$")
_DIALOGUE_BARE_DASH_RE = re.compile(r"^\s*-\s*$")

# 块头形状行（以 [node 开头）但没通过 _NODE_HEADER_RE 全匹配 = 坏块头（如漏右
# 方括号）。必须硬 E8——否则会被 narration 多行值吸收：块头文本混进上一节点旁白、
# 本块字段整体错挂，且若同名合法块另存在则 E1 不触发 → scene.json 照产（/review
# Angle B 实证的静默串块路径）。大小写不敏感，`[Node:` 之类也拦。
_HEADER_LIKE_RE = re.compile(r"^\s*\[\s*node\b", re.IGNORECASE)

_KNOWN_KEYS = (KEY_NARRATION, KEY_DIALOGUE, KEY_OPTIONS, KEY_CONTINUE)

_FULLWIDTH_COLON_GUIDE = "把全角冒号「：」改成半角冒号「:」（key 行 / 序号行必须用半角冒号）"


# ---------------------------------------------------------------------------
# 数据载体
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IngestError:
    """一条回流硬报错（E1-E8）；渲染进退回单 = 代码 / 节点 / 期望 vs 实际 / 修改指引。"""

    code: str  # E1..E8（format_spec.ERRORS 的 key）
    node_id: str | None  # None = 文件级（如文首游离行）
    line_no: int | None  # 回流文本 1-based 行号；对齐类错误可 None
    expected: str
    actual: str
    guidance: str  # 给编剧的一句话修改指引（编剧不是工程师，要能照着改）


@dataclass
class ParsedNode:
    """单个 [node: ...] 块的中间形态。

    fields 里 key 的**存在性 = 编剧交没交**（对齐层查 E5/E6 靠它）：
      - narration: str（多行已按行合并，段落空行保留为 \\n\\n）
      - dialogue: list[str]（原始行，未归一；0 行合法可选）
      - options: list[tuple[int, str]]（(序号, 台词) 按出现顺序；用 list 不用
        dict——dict 会静默塌掉重复序号（如 1:,1:,2:），E4 就探不到，违反硬报错语义。
        对齐通过后再转 {序号: 台词} 喂合并。）
      - continue: str（单行值）
    """

    node_id: str
    line_no: int  # 块头行号
    fields: dict[str, Any] = field(default_factory=dict)
    key_line_nos: dict[str, int] = field(default_factory=dict)


@dataclass
class IngestResult:
    """ingest_reply 的产出：errors 非空 ⇒ graph 必为 None（整单退回，不产 scene）。"""

    errors: list[IngestError]
    graph: dict[str, Any] | None
    parsed: dict[str, ParsedNode]

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------------------
# A. 解析器（收集全部错误，不 fail-fast；负责 E3 / E6(重复·未知 key) / E7 / E8）
# ---------------------------------------------------------------------------


class _Parser:
    """行级状态机。骨架无关——只按 format_spec 语法收块；对齐类判定在 align 层。"""

    def __init__(self) -> None:
        self.nodes: dict[str, ParsedNode] = {}
        self.errors: list[IngestError] = []
        self._cur: ParsedNode | None = None  # 当前块（重复节点块 = 影子块，不进 nodes）
        self._cur_is_shadow = False
        self._cur_key: str | None = None  # narration/dialogue/options 块上下文
        self._narration_buf: list[str] = []
        # options 块内**见过的序号行数**（含空正文行）——空块 E7 的判据是
        # "0 条序号行"，不是"0 条有效条目"（`3: ` 空正文行已单独报 E7，不再叠报空块）
        self._option_lines_seen = 0

    # -- 错误记录 ---------------------------------------------------------

    def _err(
        self,
        code: str,
        node_id: str | None,
        line_no: int | None,
        expected: str,
        actual: str,
        guidance: str,
    ) -> None:
        # 影子块（重复节点）内部不再逐条挑错：E3 的修复动作（删块）优先，
        # 重复块里的 E6/E7/E8 等删块即消，报出来反而让编剧困惑。
        if self._cur_is_shadow and code != "E3":
            return
        self.errors.append(IngestError(code, node_id, line_no, expected, actual, guidance))

    # -- 块收尾 -----------------------------------------------------------

    def _finalize_key(self) -> None:
        """当前 key 块收尾（narration 多行值合并 + options 空块判 E7）。"""
        cur = self._cur
        if cur is None or self._cur_key is None:
            return
        key = self._cur_key
        if key == KEY_NARRATION:
            lines = [ln.rstrip() for ln in self._narration_buf]
            while lines and not lines[0]:
                lines.pop(0)
            while lines and not lines[-1]:
                lines.pop()
            text = "\n".join(lines)
            cur.fields[KEY_NARRATION] = text
            if not text:
                self._err(
                    "E7",
                    cur.node_id,
                    cur.key_line_nos.get(KEY_NARRATION),
                    "narration: 后要有旁白正文（可多行）",
                    "narration: 行在，但正文为空",
                    "在 narration: 冒号后（或紧接的下一行起）写该节点的旁白。",
                )
            self._narration_buf = []
        elif key == KEY_OPTIONS:
            if self._option_lines_seen == 0:
                self._err(
                    "E7",
                    cur.node_id,
                    cur.key_line_nos.get(KEY_OPTIONS),
                    "options: 块内要有 1..N 的序号行（每行一条玩家台词）",
                    "options: 行在，但块内一条序号行都没有（空块）",
                    "在 options: 下一行起按「1: 台词」逐条写满锁定的选项数。",
                )
        self._cur_key = None

    def _finalize_node(self) -> None:
        self._finalize_key()
        cur = self._cur
        if cur is not None and not self._cur_is_shadow:
            self.nodes[cur.node_id] = cur
        self._cur = None
        self._cur_is_shadow = False

    # -- key 行 -----------------------------------------------------------

    def _open_key(self, key: str, colon: str, value: str, line_no: int) -> None:
        cur = self._cur
        assert cur is not None
        if colon == "：":
            self._err(
                "E8",
                cur.node_id,
                line_no,
                f"{key}: （半角冒号）",
                f"第 {line_no} 行用了全角冒号「：」",
                _FULLWIDTH_COLON_GUIDE,
            )
            # 记错后仍按 key 行恢复解析，防止块内后续行级联成 E8 噪音
        if key not in _KNOWN_KEYS:
            self._err(
                "E6",
                cur.node_id,
                line_no,
                f"key 只能是 {' / '.join(_KNOWN_KEYS)}",
                f"第 {line_no} 行出现未知 key「{key}:」",
                f"删掉「{key}:」这块（或改成正确的 key）；每个节点只交 "
                "narration / dialogue / options / continue。注意：这行下面的内容行"
                "本轮已一并跳过，修正后请确认它们各自的归属。",
            )
            self._cur_key = "_swallow"  # 未知 key 的块内容整体吞掉，只报一条 E6
            return
        if key in cur.fields:
            self._err(
                "E6",
                cur.node_id,
                line_no,
                f"每个节点块内 {key}: 只出现一次",
                f"第 {line_no} 行是本块第二个「{key}:」",
                f"删掉重复的「{key}:」块，把内容并进第一个（首个块已按正常内容读取；"
                "第二个块下面的内容行本轮已一并跳过）。",
            )
            self._cur_key = "_swallow"  # 重复 key 的第二块吞掉；首块归属不受影响
            return
        cur.key_line_nos[key] = line_no
        if key == KEY_NARRATION:
            self._narration_buf = [value]
            self._cur_key = KEY_NARRATION
        elif key == KEY_DIALOGUE:
            cur.fields[KEY_DIALOGUE] = []
            self._cur_key = KEY_DIALOGUE
            if value.strip():
                self._err(
                    "E8",
                    cur.node_id,
                    line_no,
                    "dialogue: 冒号后不带正文，对白逐行写在下面的「- 」行里",
                    f"第 {line_no} 行 dialogue: 冒号后直接跟了正文「{value.strip()[:20]}」",
                    "把这句挪到 dialogue: 的下一行，以「- 」开头。",
                )
        elif key == KEY_OPTIONS:
            cur.fields[KEY_OPTIONS] = []
            self._option_lines_seen = 0
            self._cur_key = KEY_OPTIONS
            if value.strip():
                self._err(
                    "E8",
                    cur.node_id,
                    line_no,
                    "options: 冒号后不带正文，选项逐行写在下面的「1: 台词」行里",
                    f"第 {line_no} 行 options: 冒号后直接跟了正文",
                    "把选项挪到 options: 的下一行起，每行「序号: 台词」。",
                )
        elif key == KEY_CONTINUE:
            text = value.strip()
            cur.fields[KEY_CONTINUE] = text
            if not text:
                self._err(
                    "E7",
                    cur.node_id,
                    line_no,
                    "continue: 后要有一句玩家接话",
                    "continue: 行在，但正文为空",
                    "在 continue: 冒号后同一行写一句短接话（≤20 字）。",
                )
            # continue 是单行值：其后的续行无法归属 → E8（_cur_key=None 自然落入）
            self._cur_key = None

    # -- 主循环 -----------------------------------------------------------

    def feed(self, text: str) -> None:
        # BOM（Windows 编辑器 UTF-8-with-BOM 存盘）不是内容：不剥掉会让首个块头
        # 匹配失败，产出编剧无法理解的 E8+E1 双报（/review Angle B）
        text = text.lstrip("\ufeff")
        for line_no, raw in enumerate(text.splitlines(), start=1):
            header = _NODE_HEADER_RE.match(raw)
            if header:
                self._on_header(header, line_no)
                continue
            if _HEADER_LIKE_RE.match(raw):
                self._on_malformed_header(raw, line_no)
                continue
            if self._cur is None:
                if raw.strip():
                    self.errors.append(
                        IngestError(
                            "E8",
                            None,
                            line_no,
                            "第一个 [node: ...] 块头之前不放正文",
                            f"第 {line_no} 行游离在任何节点块之外：「{raw.strip()[:30]}」",
                            "把这行挪进它所属节点的块内，或删掉。",
                        )
                    )
                continue
            key_m = _KEY_LINE_RE.match(raw)
            if key_m:
                self._finalize_key()
                self._open_key(key_m.group(1), key_m.group(2), key_m.group(3), line_no)
                continue
            self._on_content_line(raw, line_no)
        self._finalize_node()

    def _on_header(self, m: re.Match[str], line_no: int) -> None:
        self._finalize_node()
        colon, node_id = m.group(1), m.group(2)
        is_shadow = node_id in self.nodes
        self._cur = ParsedNode(node_id=node_id, line_no=line_no)
        self._cur_is_shadow = is_shadow
        self._cur_key = None
        if colon == "：":
            self._err(
                "E8",
                node_id,
                line_no,
                f"[node: {node_id}]（半角冒号）",
                f"第 {line_no} 行块头用了全角冒号「：」",
                _FULLWIDTH_COLON_GUIDE,
            )
        if is_shadow:
            spec = ERRORS["E3"]
            self.errors.append(
                IngestError(
                    "E3",
                    node_id,
                    line_no,
                    f"每个 node_id 只交一个块（{spec.meaning}）",
                    f"第 {line_no} 行是「[node: {node_id}]」的第二次出现",
                    # 指引必须指向"保留第一个"：影子块内部不逐条挑错（_err 过滤），
                    # 若编剧保留后交的块，其未检出的问题要多一轮退回才暴露
                    "删掉后交的重复块、保留第一个（第一个块已按正常内容读取，后交的块未逐条检查）。",
                )
            )

    def _on_malformed_header(self, raw: str, line_no: int) -> None:
        """块头形状行但格式坏掉（漏右方括号 / 大小写错等）→ 硬 E8 + 整块跳过。

        跳过（影子块吞行）而不是任其落进上一节点的 narration/字段：一条 E8 +
        （若无同名合法块）一条 E1，两条错误互相印证；比串块错挂后连环 E6 可读。
        """
        self._finalize_node()
        self.errors.append(
            IngestError(
                "E8",
                None,
                line_no,
                "[node: 节点id]（半角冒号 + 右方括号，一行写完）",
                f"第 {line_no} 行像是节点块头但格式不对：「{raw.strip()[:30]}」",
                "把块头改成「[node: 节点id]」——检查右方括号是否漏写、"
                "node 是否小写、冒号是否半角；该块内容本轮已整体跳过，修好块头后重交。",
            )
        )
        # 伪影子块：吞掉坏块头下的内容行、抑制块内二次报错（E8+E1 已足够指路）
        self._cur = ParsedNode(node_id="", line_no=line_no)
        self._cur_is_shadow = True
        self._cur_key = None

    def _on_content_line(self, raw: str, line_no: int) -> None:
        cur = self._cur
        assert cur is not None
        if self._cur_key == KEY_NARRATION:
            # narration 是唯一多行值（MULTILINE_VALUE_KEYS）：吃掉一切非块头/非 key 行
            self._narration_buf.append(raw)
            return
        if self._cur_key == "_swallow":
            return  # 未知/重复 key 的块内容：一条 E6 已报，整块吞掉不级联
        if not raw.strip():
            return  # 空行 = 无意义分隔
        if self._cur_key == KEY_DIALOGUE:
            item = _DIALOGUE_ITEM_RE.match(raw)
            if item:
                content = item.group(1).strip()
                if not content:
                    self._err(
                        "E7",
                        cur.node_id,
                        line_no,
                        "每条「- 」后要有一句对白裸正文",
                        f"第 {line_no} 行是空的「- 」条目",
                        "在「- 」后补上这句对白，或删掉这行。",
                    )
                elif not normalize_line(content):
                    self._err(
                        "E7",
                        cur.node_id,
                        line_no,
                        "对白行 = 裸正文（不带引号包裹），且不能只有引号",
                        f"第 {line_no} 行的「- 」条目去掉包裹引号后没有正文",
                        "把对白正文写进去；引号包裹（「」/\"\"）不要写，正文裸写即可。",
                    )
                else:
                    cur.fields[KEY_DIALOGUE].append(content)
                return
            if _DIALOGUE_BARE_DASH_RE.match(raw):
                self._err(
                    "E7",
                    cur.node_id,
                    line_no,
                    "每条「- 」后要有一句对白裸正文",
                    f"第 {line_no} 行是空的「- 」条目",
                    "在「- 」后补上这句对白，或删掉这行。",
                )
                return
            self._err(
                "E8",
                cur.node_id,
                line_no,
                "dialogue 块内每行以「- 」（连字符 + 空格）开头（单行值，无续行）",
                f"第 {line_no} 行在 dialogue 块内但不是「- 」行：「{raw.strip()[:30]}」",
                "以「- 」（连字符后带一个空格）开头把它写成一条对白；"
                "markdown 分隔线（---）之类的装饰行不要写。",
            )
            return
        if self._cur_key == KEY_OPTIONS:
            opt = _OPTION_LINE_RE.match(raw)
            if opt:
                self._option_lines_seen += 1
                idx, colon, text_val = int(opt.group(1)), opt.group(2), opt.group(3).strip()
                if colon == "：":
                    self._err(
                        "E8",
                        cur.node_id,
                        line_no,
                        f"{idx}: （半角冒号）",
                        f"第 {line_no} 行序号行用了全角冒号「：」",
                        _FULLWIDTH_COLON_GUIDE,
                    )
                if not text_val:
                    self._err(
                        "E7",
                        cur.node_id,
                        line_no,
                        "每条序号行要有玩家台词",
                        f"第 {line_no} 行「{idx}: 」后正文为空",
                        f"在「{idx}: 」后补上这条选项的玩家第一人称台词。",
                    )
                # 空正文行也保留序号给对齐层——序号集合本身是全的，只该报 E7，
                # 不该连带误报 E4 缺号（E7 存在 ⇒ 永不进 merge，空文本不会落图）
                cur.fields[KEY_OPTIONS].append((idx, text_val))
                return
            self._err(
                "E8",
                cur.node_id,
                line_no,
                "options 块内每行形如「1: 台词」（单行值，无续行）",
                f"第 {line_no} 行在 options 块内但不是序号行：「{raw.strip()[:30]}」",
                "把它并进所属序号行（一条选项一行写完），或按「序号: 台词」补上序号。",
            )
            return
        # 无任何 key 上下文（块头之后 / continue 之后）
        self._err(
            "E8",
            cur.node_id,
            line_no,
            "节点块内每行都要能归属某个 key（narration 之外都是单行值）",
            f"第 {line_no} 行无法归属任何 key：「{raw.strip()[:30]}」",
            "把这行并进它所属的 key（narration 可多行；continue/序号行/「- 」行"
            "都是一行写完），或删掉。",
        )


def parse_reply(text: str) -> tuple[dict[str, ParsedNode], list[IngestError]]:
    """回流 markdown → 中间形态 {node_id: ParsedNode}；收集全部解析层错误（不 fail-fast）。"""
    parser = _Parser()
    parser.feed(text)
    return parser.nodes, parser.errors


# ---------------------------------------------------------------------------
# B. 对齐（骨架 × 中间形态 全键精确对齐；负责 E1 / E2 / E4 / E5 / E6(错位块)）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ExpectedNode:
    node_id: str
    category: str  # NODE_CATEGORY_KEYS 的 key：choice / beat / end
    option_count: int | None = None  # 仅 choice：锁定选项数
    reveals: tuple[str, ...] = ()  # 仅 beat：本拍锁定线索（E1 指引用）


def _design_malformed(detail: str) -> PromptpackInputError:
    return PromptpackInputError(f"{detail}——design 产物走形，重跑 --structure-only（或人工修 design）")


def _topology_by_id(topology: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """topology 节点表。载体走形 = design 侧错误，硬拦成 PromptpackInputError。

    loader 只逐项校验 kind=beats/choice 子集；节点缺 node_id 会穿成裸 KeyError、
    重复 node_id 会被 dict 推导静默 last-wins（/review Angle C 实证），这里补拦。
    """
    by_id: dict[str, dict[str, Any]] = {}
    for i, n in enumerate(topology.get("nodes") or []):
        if not isinstance(n, dict) or not isinstance(n.get("node_id"), str) or not n["node_id"]:
            raise _design_malformed(f"design.topology nodes[{i}] 缺合法 node_id")
        if n["node_id"] in by_id:
            raise _design_malformed(f"design.topology 节点 id {n['node_id']!r} 重复出现")
        by_id[n["node_id"]] = n
    return by_id


def _expected_index(design: dict[str, Any]) -> dict[str, _ExpectedNode]:
    """锁定骨架 → 成品图节点期望表（插入序 = topology 序 = 报错顺序）。

    design 侧走形（loader 之外的缺口，如 beats 节点缺 next / 节点 id 与 beats
    拍 id 撞名）不是编剧的错，抛 PromptpackInputError（退出码 2），不进退回单。
    """
    topology = design["topology"]
    skeletons = design.get("skeletons") or {}
    beats_plan = design["beats_plan"]
    expected: dict[str, _ExpectedNode] = {}
    by_id = _topology_by_id(topology)

    def _add(exp: _ExpectedNode) -> None:
        # 成品图命名空间 = topology 节点 id ∪ beats 拍 id（{pid}_b{i}）。撞名会让
        # 期望表/合并静默互相覆盖，退回单还会把 design 侧撞名误怪到编剧头上
        # （合规回流反收 E3+E6；/review Angle C 实证）——design 侧硬拦
        if exp.node_id in expected:
            raise _design_malformed(
                f"design 成品图节点 id {exp.node_id!r} 撞名（topology 节点与 beats 拍 id 冲突）"
            )
        expected[exp.node_id] = exp

    for pid, node in by_id.items():
        kind = node.get("kind")
        if kind == "choice":
            routes = node.get("routes") or []
            if not routes:
                raise _design_malformed(f"design.topology choice 节点 {pid!r} 没有任何出边")
            for route in routes:
                if route.get("to") not in by_id:
                    raise _design_malformed(
                        f"design.topology choice 节点 {pid!r} 的出边 to={route.get('to')!r} "
                        "不在节点表内"
                    )
            # loader 保证每个 choice 都有骨架 dict；但 options 键缺失/空列表只在
            # "有出边"时才被覆盖复算拦住，0 选项会穿透成 KeyError 或产出违反
            # node.schema minItems:1 的节点（/review Angle A/C 实证）——这里硬拦
            options = (skeletons.get(pid) or {}).get("options") or []
            if not options:
                raise _design_malformed(f"design.skeletons[{pid!r}] 没有任何选项骨架")
            _add(_ExpectedNode(pid, "choice", option_count=len(options)))
        elif kind == "beats":
            nxt = node.get("next")
            if nxt not in by_id:
                raise _design_malformed(
                    f"design.topology beats 节点 {pid!r} 的 next={nxt!r} 不在节点表内"
                )
            for slot in beats_plan[pid]:
                _add(_ExpectedNode(slot["beat_id"], "beat", reveals=tuple(slot["reveals"])))
        elif kind == "end":
            _add(_ExpectedNode(pid, "end"))
        else:
            raise _design_malformed(
                f"design.topology 节点 {pid!r} 的 kind={kind!r} 不是 choice/beats/end"
            )
    if topology.get("entry_node_id") not in by_id:
        raise _design_malformed(
            f"design.topology entry_node_id={topology.get('entry_node_id')!r} 不在节点表内"
        )
    return expected


def _category_label(category: str) -> str:
    return {
        "choice": "choice 节点：narration + options（dialogue 可选）",
        "beat": "beats 拍：narration + continue（dialogue 可选）",
        "end": "end 节点：仅 narration（dialogue 可选）",
    }[category]


def align(
    design: dict[str, Any], parsed: dict[str, ParsedNode]
) -> tuple[dict[str, _ExpectedNode], list[IngestError]]:
    """全键精确对齐：节点集合相等（E1/E2）、类别 key 表（E5/E6）、选项序号 1..N（E4）。"""
    expected = _expected_index(design)
    errors: list[IngestError] = []

    for nid, exp in expected.items():  # E1：按骨架（topology）顺序报缺失
        if nid not in parsed:
            hint = (
                "（本拍锁定线索：" + "；".join(f"「{r}」" for r in exp.reveals) + "）"
                if exp.reveals
                else ""
            )
            errors.append(
                IngestError(
                    "E1",
                    nid,
                    None,
                    "锁定清单里的每个节点都要交一个 [node: ...] 块",
                    "回流文本里没有这个节点的块",
                    f"补交 [node: {nid}] 块（{_category_label(exp.category)}）{hint}。",
                )
            )
    for nid, pnode in parsed.items():  # E2：按回流出现顺序报多出
        if nid not in expected:
            errors.append(
                IngestError(
                    "E2",
                    nid,
                    pnode.line_no,
                    "只交锁定清单里有的节点（结构已锁定，不接受新增）",
                    f"第 {pnode.line_no} 行出现清单之外的 [node: {nid}]",
                    "对照随包的「锁定节点清单」核对 node_id 拼写；多余的块删掉。",
                )
            )

    for nid, exp in expected.items():
        pnode = parsed.get(nid)
        if pnode is None:
            continue
        keys = NODE_CATEGORY_KEYS[exp.category]
        allowed = keys["required"] + keys["optional"]
        for key in keys["required"]:  # E5：必填 key 缺失
            if key not in pnode.fields:
                errors.append(
                    IngestError(
                        "E5",
                        nid,
                        pnode.line_no,
                        f"{_category_label(exp.category)}——必交 {key}:",
                        f"块里没有 {key}:",
                        _missing_key_guidance(key, exp),
                    )
                )
        for key in pnode.fields:  # E6：错位块（已知 key 但该类别不该出现）
            if key not in allowed:
                errors.append(
                    IngestError(
                        "E6",
                        nid,
                        pnode.key_line_nos.get(key),
                        _category_label(exp.category),
                        f"块里带了 {key}:",
                        f"删掉该节点的 {key}: 块；{_misplaced_key_reason(key, exp.category)}",
                    )
                )
        if (
            exp.category == "choice"
            and KEY_OPTIONS in pnode.fields
            and pnode.fields[KEY_OPTIONS]  # 空块唯一归属 E7（解析层已报），E4 让出
        ):
            indexes = [i for i, _ in pnode.fields[KEY_OPTIONS]]
            n = exp.option_count or 0
            if sorted(indexes) != list(range(1, n + 1)):
                errors.append(
                    IngestError(
                        "E4",
                        nid,
                        pnode.key_line_nos.get(KEY_OPTIONS),
                        f"序号 1..{n} 连续完整（锁定选项数 = {n}）",
                        "交了 " + " / ".join(f"{i}:" for i in indexes),
                        f"把序号改成 1..{n} 连续完整、共 {n} 条，不得增删（结构已锁定）。",
                    )
                )
    return expected, errors


def _missing_key_guidance(key: str, exp: _ExpectedNode) -> str:
    if key == KEY_NARRATION:
        return "补一行 narration: 及该节点的旁白正文（可多行）。"
    if key == KEY_OPTIONS:
        return (
            f"补 options: 块，序号 1..{exp.option_count} 每行一条玩家第一人称台词"
            f"（锁定选项数 = {exp.option_count}，不得增删）。"
        )
    if key == KEY_CONTINUE:
        return "补一行 continue: 玩家把对话推进到下一拍的短接话（≤20 字，一行写完）。"
    return f"补上 {key}: 块。"  # pragma: no cover —— required 表当前只有上面三种


def _misplaced_key_reason(key: str, category: str) -> str:
    if category == "end":
        return "end 节点不带选项/接话，结局收束由结构锁定。"
    if category == "beat" and key == KEY_OPTIONS:
        return "beats 拍是单选项节点，接话写在 continue: 里，不用 options。"
    if category == "choice" and key == KEY_CONTINUE:
        return "choice 节点的玩家台词全部写在 options: 序号行里，不用 continue。"
    return "该类节点不该出现这个 key。"


# ---------------------------------------------------------------------------
# C. 确定性合并（对齐全过才进入；复用 assemble 公开别名的机械语义）
# ---------------------------------------------------------------------------

_HUMAN_TRACE = {"source": "human"}  # 正文来源审计（ADR-039；schema enum 现行合法）


def _mk_human_option(option_id: str, text: str, target: str) -> dict[str, Any]:
    option = mk_option(option_id, text, target)
    option["generation_trace"] = dict(_HUMAN_TRACE)
    return option


def _mk_node(
    nid: str,
    node_type: str,
    pnode: ParsedNode,
    options: list[dict[str, Any]],
    *,
    speaker_ref: str,
    scene_anchor: str,
) -> dict[str, Any]:
    """ADR-040 不变量在此落地：narration=纯旁白 / dialogue[] 结构化 / 节点 speaker_ref=None。"""
    return {
        "node_id": nid,
        "type": node_type,
        "narration": pnode.fields[KEY_NARRATION],
        "dialogue": dialogue_entries(speaker_ref, pnode.fields.get(KEY_DIALOGUE)),
        "speaker_ref": None,
        "location_ref": scene_anchor,
        "on_enter_effects": [],
        "options": options,
        "generation_trace": dict(_HUMAN_TRACE),
    }


def merge_scene(design: dict[str, Any], parsed: dict[str, ParsedNode]) -> dict[str, Any]:
    """对齐全过的中间形态 → dialogue_graph dict（schema_version "0.1.1"，不 bump）。

    只能在 align 零错误后调用；这里不做任何容错（对不上就该在对齐层退回）。
    遍历按 topology / beats_plan 顺序 → 同输入逐字节确定性输出，
    与回流文本的块顺序无关。
    """
    run_config = design["run_config"]
    topology = design["topology"]
    # .get：无 choice 节点的 design 可以合法地没有 skeletons 键（loader 只要求
    # beats_plan/run_config；choice 存在时 _expected_index 已保证骨架齐全）
    skeletons = design.get("skeletons") or {}
    beats_plan = design["beats_plan"]
    speaker_ref = run_config["speaker_ref"]
    scene_anchor = run_config["scene_anchor"]

    by_id = _topology_by_id(topology)
    target_map = {nid: entry_graph_node_id(n) for nid, n in by_id.items()}
    nodes: dict[str, dict[str, Any]] = {}

    for pid, pnode in by_id.items():
        kind = pnode.get("kind")
        if kind == "choice":
            reply = parsed[pid]
            text_by_index = dict(reply.fields[KEY_OPTIONS])  # 对齐后序号恰为 1..N 无重复
            options = [
                _mk_human_option(
                    f"opt_{pid}_{i + 1}",
                    text_by_index[i + 1],
                    target_map[skel_opt["route_to"]],
                )
                for i, skel_opt in enumerate(skeletons[pid]["options"])
            ]
            nodes[pid] = _mk_node(
                pid, "dialogue", reply, options,
                speaker_ref=speaker_ref, scene_anchor=scene_anchor,
            )
        elif kind == "beats":
            slots = beats_plan[pid]
            nxt = target_map[pnode["next"]]
            for i, slot in enumerate(slots, start=1):
                bid = slot["beat_id"]  # loader 已钉死 = {pid}_b{i} 连续
                reply = parsed[bid]
                target = f"{pid}_b{i + 1}" if i < len(slots) else nxt
                option = _mk_human_option(
                    f"opt_{bid}_continue", reply.fields[KEY_CONTINUE], target
                )
                nodes[bid] = _mk_node(
                    bid, "dialogue", reply, [option],
                    speaker_ref=speaker_ref, scene_anchor=scene_anchor,
                )
        elif kind == "end":
            nodes[pid] = _mk_node(
                pid, "end", parsed[pid], [],
                speaker_ref=speaker_ref, scene_anchor=scene_anchor,
            )

    return {
        "schema_version": "0.1.1",
        "graph_id": run_config["graph_id"],
        "entry_node_id": target_map[topology["entry_node_id"]],
        "scene_anchor": scene_anchor,
        "character_refs": list(run_config["character_refs"]),
        "nodes": nodes,
    }


# ---------------------------------------------------------------------------
# 装配入口 + 退回单
# ---------------------------------------------------------------------------


def ingest_reply(design: dict[str, Any], reply_text: str) -> IngestResult:
    """解析 + 对齐 + 合并一站式入口（design = load_design_artifact 返回的内层 dict）。

    任一 E1-E8 → graph=None（整单退回语义）；零错误 → graph=合并产物。
    """
    parsed, errors = parse_reply(reply_text)
    _, align_errors = align(design, parsed)
    errors = errors + align_errors
    errors = _sorted_errors(errors)
    if errors:
        return IngestResult(errors=errors, graph=None, parsed=parsed)
    return IngestResult(errors=[], graph=merge_scene(design, parsed), parsed=parsed)


def _sorted_errors(errors: list[IngestError]) -> list[IngestError]:
    """退回单顺序：按错误代码分组（E1→E8），组内保持收集顺序（稳定排序）。"""
    return sorted(errors, key=lambda e: int(e.code[1:]))


def render_reject_md(graph_id: str, errors: list[IngestError]) -> str:
    """退回单 markdown（形态对照 format_contract_sample.md 假想样张）。"""
    lines = [
        f"# 回流退回单：{graph_id}（{len(errors)} 处需修改）",
        "",
        "逐条修完后整份重交；node_id / 选项序号以随包的「锁定节点清单」为准。",
        "",
    ]
    for i, err in enumerate(errors, start=1):
        spec = ERRORS[err.code]
        where = f"节点 `{err.node_id}`" if err.node_id else "（文件级）"
        if err.line_no is not None:
            where += f"（第 {err.line_no} 行）"
        lines += [
            f"{i}. [{err.code} {spec.slug}] {where}",
            f"   期望：{err.expected}",
            f"   实际：{err.actual}",
            f"   修改指引：{err.guidance}",
            "",
        ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# D. CLI（独立模块入口；退出码三态按 format_spec）
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m generator.promptpack.ingest",
        description="P-B 回流合并器：编剧回流 markdown × 锁定骨架 design.json → scene.json；"
        "任一 E1-E8 整单退回（<reply 去后缀>.reject.md）",
    )
    parser.add_argument("design", type=Path, help="锁定骨架 design.json（--structure-only 产物，wrapper 形态）")
    parser.add_argument("reply", type=Path, help="编剧回流 markdown 文件")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="合并产物 scene.json 输出路径（默认 = <reply 去后缀>.scene.json）",
    )
    args = parser.parse_args(argv)

    try:
        design = load_design_artifact(args.design)
    except PromptpackInputError as e:
        print(f"[输入错误] {e}", file=sys.stderr)
        return EXIT_USAGE
    try:
        # utf-8-sig：兼容编剧 Windows 编辑器的 UTF-8-with-BOM 存盘（parse_reply
        # 内亦剥 BOM，双保险——BOM 是编码痕迹不是内容，剥掉不属于错误软化）
        reply_text = args.reply.read_text(encoding="utf-8-sig")
    except OSError as e:
        print(f"[输入错误] {args.reply}: 无法读取（{type(e).__name__}: {e}）", file=sys.stderr)
        return EXIT_USAGE
    except UnicodeDecodeError as e:
        print(f"[输入错误] {args.reply}: 不是 UTF-8 文本（{e}）", file=sys.stderr)
        return EXIT_USAGE

    try:
        result = ingest_reply(design, reply_text)
    except PromptpackInputError as e:  # design 侧走形（非编剧问题，不进退回单）
        print(f"[输入错误] {e}", file=sys.stderr)
        return EXIT_USAGE

    graph_id = design["run_config"]["graph_id"]
    reject_path = args.reply.with_suffix(".reject.md")
    out_path = args.out if args.out is not None else args.reply.with_suffix(".scene.json")
    if result.errors:
        reject_path.write_text(
            render_reject_md(graph_id, result.errors), encoding="utf-8"
        )
        print(f"[拒收] {graph_id}：{len(result.errors)} 处需修改，未产出 scene.json", file=sys.stderr)
        for err in result.errors:
            where = err.node_id or "（文件级）"
            print(f"  - [{err.code} {ERRORS[err.code].slug}] {where}：{err.actual}", file=sys.stderr)
        print(f"退回单已写入 {reject_path}", file=sys.stderr)
        if out_path.exists() and out_path != reject_path:
            # B 阶段 finding（2026-07-08_T-3P-2 review）：拒收若留下上一轮成功产的
            # 旧 scene.json，就在文件系统层面把「任一 E → 不产 scene.json」软化成
            # 「目录里仍有可用场景」——作者非程序员、下游只看文件是否存在会误吞过时图。
            # 对称成功分支删 stale reject 的逻辑：拒收删本轮 --out 的 stale scene。
            # out_path 是本 CLI 自己的产物路径（默认 <reply>.scene.json 或用户 --out），
            # 删它安全；路径相等守卫已在 if 条件里排除误删刚写的退回单。
            out_path.unlink()
            print(
                f"[清理] 上一轮合并产物已过时（本轮拒收），删除 {out_path}",
                file=sys.stderr,
            )
        return EXIT_REJECTED

    assert result.graph is not None  # ok ⇒ graph 非 None（IngestResult 不变量）
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result.graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[合并成功] {graph_id}：{len(result.graph['nodes'])} 节点 → {out_path}")
    if reject_path != out_path and reject_path.exists():
        # 上一轮拒收的退回单已过时——留着会误导编剧以为还要改，删除并告知。
        # 路径相等守卫：--out 恰好指到 <reply>.reject.md 时不许自删刚写的产物
        reject_path.unlink()
        print(f"[清理] 上一轮退回单已过时，删除 {reject_path}")
    return EXIT_OK


__all__ = [
    "IngestError",
    "IngestResult",
    "ParsedNode",
    "align",
    "ingest_reply",
    "main",
    "merge_scene",
    "parse_reply",
    "render_reject_md",
]


if __name__ == "__main__":
    sys.exit(main())
