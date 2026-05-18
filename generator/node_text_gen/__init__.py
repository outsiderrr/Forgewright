"""Node text generation（节点级文本生成）入口 — T-3Y-1 子 goal 2.

把 Forward Planner 输出 + 节点骨架 + 项目配置 → 通过 LLMProvider 调用 → 解析输出。

模块：
  - mock_provider.py  MockLLMProvider：单元测试用，返回预设字符串
  - render.py         render_node_prompt：把节点骨架 + Forward Planner 输出渲染成
                      {system, user} 两段 prompt
  - run.py            run_node_generation：端到端 = render → provider.generate → json.loads

注意 ADR-011：业务代码严禁直接 import google.genai / openai；必须经 LLMProvider 接口。
T-3Y-1 mini prototype 阶段只用 MockLLMProvider（单元测试）；真实 LLM 调用在 goal 3 dry-run
经现有 generator/providers/poloai.py 走 GPT-5.5-pro。
"""
__all__ = ["mock_provider", "render", "run"]
