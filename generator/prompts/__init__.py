"""Prompt assets for the generator.

Templates and few-shot loaders live here. Keep them dumb (no I/O beyond
reading bundled scene files, no LLM calls); composition happens in
`generate_node`.
"""
from generator.prompts.few_shot import (
    FewShotPair,
    load_composite_condition_few_shot,
    load_iron_oath_few_shot,
    render_few_shot_block,
)
from generator.prompts.system import SYSTEM_PROMPT

__all__ = [
    "SYSTEM_PROMPT",
    "FewShotPair",
    "load_composite_condition_few_shot",
    "load_iron_oath_few_shot",
    "render_few_shot_block",
]
