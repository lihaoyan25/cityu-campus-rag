"""DeepSeek 客户端：基于 openai SDK（OpenAI 兼容协议）。

统一输出 dict 结构的消息，便于 Agent 循环与 MySQL 持久化。
支持深度思考模式（thinking 参数）：开启后流式产出 reasoning_content。
"""
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


def _default_params(temperature: float | None, max_tokens: int | None) -> dict[str, Any]:
    return {
        "model": settings.deepseek_model,
        "temperature": settings.deepseek_temperature if temperature is None else temperature,
        "max_tokens": settings.deepseek_max_tokens if max_tokens is None else max_tokens,
        "top_p": settings.deepseek_top_p,
    }


def _usage_to_dict(usage: Any) -> dict[str, int] | None:
    if usage is None:
        return None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
    }


def _get_reasoning(delta: Any) -> str | None:
    """从流式 delta 中提取思考内容（reasoning_content / reasoning 兼容）。"""
    value = getattr(delta, "reasoning_content", None)
    if not value:
        value = getattr(delta, "reasoning", None)
    if not value and getattr(delta, "model_extra", None):
        value = delta.model_extra.get("reasoning_content")
    return value


def _thinking_body(thinking: bool) -> dict[str, Any]:
    """deepseek-flash 默认开启思考，必须显式 disabled 才能关闭（平台实测）。"""
    return {"extra_body": {"thinking": {"type": "enabled" if thinking else "disabled"}}}


async def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    thinking: bool = False,
) -> dict[str, Any]:
    """非流式对话，返回 assistant 消息 dict：{role, content, tool_calls?, usage}。"""
    kwargs: dict[str, Any] = _default_params(temperature, max_tokens)
    kwargs["messages"] = messages
    if tools:
        kwargs["tools"] = tools
    kwargs.update(_thinking_body(thinking))
    resp = await get_client().chat.completions.create(**kwargs)
    msg = resp.choices[0].message
    out = _message_to_dict(msg)
    out["usage"] = _usage_to_dict(resp.usage)
    return out


async def chat_stream(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    thinking: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """流式对话。

    依次 yield:
      {"type": "thinking", "content": "..."}                  -- 深度思考增量
      {"type": "delta", "content": "..."}                     -- 正文增量
      {"type": "tool_calls", "tool_calls": [...]}             -- 模型请求工具调用
      {"type": "finish", content/tool_calls/reasoning/usage}  -- 结束(含完整聚合)
    """
    kwargs: dict[str, Any] = _default_params(temperature, max_tokens)
    kwargs["messages"] = messages
    kwargs["stream"] = True
    kwargs["stream_options"] = {"include_usage": True}
    if tools:
        kwargs["tools"] = tools
    kwargs.update(_thinking_body(thinking))

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    # tool call 增量片段按 index 聚合
    tc_buf: dict[int, dict[str, Any]] = {}
    usage: dict[str, int] | None = None

    stream = await get_client().chat.completions.create(**kwargs)
    async for chunk in stream:
        if getattr(chunk, "usage", None) is not None:
            usage = _usage_to_dict(chunk.usage)
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta is None:
            continue
        reasoning = _get_reasoning(delta)
        if reasoning:
            reasoning_parts.append(reasoning)
            yield {"type": "thinking", "content": reasoning}
        if delta.content:
            content_parts.append(delta.content)
            yield {"type": "delta", "content": delta.content}
        if delta.tool_calls:
            for frag in delta.tool_calls:
                buf = tc_buf.setdefault(
                    frag.index,
                    {"id": "", "name": "", "arguments": ""},
                )
                if frag.id:
                    buf["id"] = frag.id
                if frag.function:
                    if frag.function.name:
                        buf["name"] = frag.function.name
                    if frag.function.arguments:
                        buf["arguments"] += frag.function.arguments

    full_content = "".join(content_parts)
    tool_calls = None
    if tc_buf:
        tool_calls = [
            {
                "id": buf["id"] or f"call_{idx}",
                "type": "function",
                "function": {"name": buf["name"], "arguments": buf["arguments"]},
            }
            for idx, buf in sorted(tc_buf.items())
        ]
        yield {"type": "tool_calls", "tool_calls": tool_calls}

    yield {
        "type": "finish",
        "content": full_content,
        "tool_calls": tool_calls,
        "reasoning": "".join(reasoning_parts),
        "usage": usage,
    }


def _message_to_dict(msg: Any) -> dict[str, Any]:
    """openai SDK 消息对象 -> 可 JSON 持久化的 dict。"""
    out: dict[str, Any] = {"role": msg.role, "content": msg.content}
    if getattr(msg, "tool_calls", None):
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
    return out
