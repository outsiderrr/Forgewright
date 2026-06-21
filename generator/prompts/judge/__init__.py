"""judge 提示词模板（文风评审）."""
from generator.prompts.judge.style_judge_prompt import (
    STYLE_JUDGE_SYSTEM,
    build_judge_schema,
    build_judge_user_prompt,
)

__all__ = ["STYLE_JUDGE_SYSTEM", "build_judge_schema", "build_judge_user_prompt"]
