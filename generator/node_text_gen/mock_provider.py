"""Mock LLM provider（mock LLM 提供者）— T-3Y-1 子 goal 2 单元测试用.

返回预设字符串，记录所有调用；不依赖任何真实 LLM SDK。

与 generator.llm_provider.LLMProvider Protocol 不完全对齐——本 mock 仅暴露
T-3Y-1 节点生成需要的最小接口（generate(system, user) -> str）。生产路径下
goal 3 dry-run 走 generator.providers.poloai 适配 GPT-5.5-pro。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MockLLMProvider:
    """单元测试 mock：固定字符串响应 + 调用记录器.

    Attributes:
        response: 每次 generate() 返回的字符串（默认 '{}'，valid JSON 空对象）
        calls:    每次 generate() 调用的 {system, user} 记录列表
    """
    response: str = "{}"
    calls: list[dict[str, str]] = field(default_factory=list)

    def generate(self, *, system: str, user: str) -> str:
        """T-3Y-1 mini prototype 的 generate 接口（最小契约）.

        Args:
            system: system prompt 全文
            user:   user message 全文

        Returns:
            预设的 self.response 字符串
        """
        self.calls.append({"system": system, "user": user})
        return self.response

    def set_response(self, response: str) -> None:
        """方便单元测试改 mock 响应."""
        self.response = response

    def reset(self) -> None:
        """清空调用记录."""
        self.calls.clear()


def make_mock_node_response(
    *,
    node_id: str = "node_3_info_offer",
    narration: str = "测试旁白：露西降下警惕，开始按双重支配信任度暴露浅层信息。",
    option_texts: list[str] | None = None,
) -> str:
    """生成一份合 schema 的 mock node response JSON 字符串（便于测试 e2e 流水线）.

    Returns:
        JSON 字符串（valid Node 形态）
    """
    import json
    if option_texts is None:
        option_texts = [
            "[step 4 fill - 浅层追问] 莱特那时和谁有过节？",
            "[step 4 fill - 警告] 维克的人很危险，离他远点。",
        ]
    payload = {
        "node_id": node_id,
        "type": "dialogue",
        "narration": narration,
        "speaker_ref": "char_lucy",
        "location_ref": "scene_inn",
        "on_enter_effects": [],
        "options": [
            {
                "option_id": f"opt_mock_{i}",
                "text": txt,
                "target_node_id": "node_end",
                "condition": None,
                "effects": [],
                "unavailable_behavior": "hide",
            }
            for i, txt in enumerate(option_texts)
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


__all__ = ["MockLLMProvider", "make_mock_node_response"]
