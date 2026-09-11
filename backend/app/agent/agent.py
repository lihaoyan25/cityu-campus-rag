"""Agent 流式循环：function-calling + 多轮工具迭代。

产出统一事件流，由 chat_service 转换为 SSE。
"""
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.agent import tools
from app.llm import deepseek

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3


def _merge_usage(acc: dict[str, int] | None, usage: dict[str, int] | None) -> dict[str, int] | None:
    """多轮工具调用时累计 token usage。"""
    if not usage:
        return acc
    if acc is None:
        return dict(usage)
    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
        acc[k] = acc.get(k, 0) + usage.get(k, 0)
    return acc


async def run_agent_stream(
    messages: list[dict[str, Any]],
    thinking: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """运行 Agent 流式循环。

    入参 messages 为已组装好的完整消息列表（system + 历史 + 当前问题）。
    yield 事件:
      {"type": "thinking", "content"}          -- 深度思考增量
      {"type": "tool", "name", "arguments"}    -- 开始调用工具
      {"type": "tool_result", "name", "brief"} -- 工具执行完成
      {"type": "delta", "content"}             -- 正文增量
      {"type": "finish", "content", "reasoning", "usage"} -- 最终回复(usage为多轮累计)
      {"type": "error", "message"}
    """
    work_messages = list(messages)
    total_usage: dict[str, int] | None = None

    for _ in range(MAX_TOOL_ROUNDS + 1):
        collected_content: list[str] = []
        collected_reasoning: list[str] = []
        pending_tool_calls: list[dict] | None = None
        try:
            stream = deepseek.chat_stream(work_messages, tools=tools.openai_schemas(), thinking=thinking)
            async for event in stream:
                if event["type"] == "delta":
                    collected_content.append(event["content"])
                    yield event
                elif event["type"] == "thinking":
                    collected_reasoning.append(event["content"])
                    yield event
                elif event["type"] == "tool_calls":
                    pending_tool_calls = event["tool_calls"]
                elif event["type"] == "finish":
                    total_usage = _merge_usage(total_usage, event.get("usage"))
                    pending_tool_calls = pending_tool_calls or event.get("tool_calls")
        except Exception as e:
            logger.exception("Agent 流式调用失败")
            yield {"type": "error", "message": f"模型调用失败: {e}"}
            return

        if not pending_tool_calls:
            yield {
                "type": "finish",
                "content": "".join(collected_content),
                "reasoning": "".join(collected_reasoning),
                "usage": total_usage,
            }
            return

        # 记录 assistant 的工具调用请求，再执行并回填结果
        work_messages.append(
            {
                "role": "assistant",
                "content": "".join(collected_content) or None,
                "tool_calls": pending_tool_calls,
            }
        )
        for tc in pending_tool_calls:
            fn_name = tc["function"]["name"]
            try:
                arguments = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                arguments = {}
            yield {"type": "tool", "name": fn_name, "arguments": arguments}
            result = await tools.execute_tool(fn_name, arguments)
            if fn_name == "kb_search":
                all_sources = arguments.get("query", "")
                logger.info("Agent 调用 kb_search: %s", all_sources)
            yield {"type": "tool_result", "name": fn_name, "brief": result[:120]}
            work_messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": result}
            )

    yield {"type": "error", "message": f"工具调用轮次超过上限({MAX_TOOL_ROUNDS})，已中止"}
