"""LLM-as-judge（文风评审层）—— 同维 taxonomy 打分 + AP 执行层检出.

边界铁律（ADR-008 / handoff §4）：judge 调 LLM，所以落 /generator；
/validator 保持确定性（AP-7/8/10 程序化检测不动）。judge 只执行作者已批准的标准
（taxonomy 14 维 + AP-1~6/9），不为个案立新标准。
"""
from generator.judge.style_judge import judge_scene, render_judge_md, write_judge_artifacts
from generator.judge.taxonomy import GATE_DIM_IDS, GATE_THRESHOLD, TAXONOMY

__all__ = [
    "TAXONOMY",
    "GATE_DIM_IDS",
    "GATE_THRESHOLD",
    "judge_scene",
    "render_judge_md",
    "write_judge_artifacts",
]
