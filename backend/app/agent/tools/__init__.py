"""工具注册表：新工具只需用 @register_tool 装饰并实现 execute。"""
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema
    execute: Callable[..., Awaitable[str]]


_TOOLS: dict[str, Tool] = {}


def register_tool(
    name: str, description: str, parameters: dict
) -> Callable[[Callable[..., Awaitable[str]]], Callable[..., Awaitable[str]]]:
    def decorator(fn: Callable[..., Awaitable[str]]) -> Callable[..., Awaitable[str]]:
        _TOOLS[name] = Tool(name=name, description=description, parameters=parameters, execute=fn)
        return fn

    return decorator


def get_tools() -> dict[str, Tool]:
    return _TOOLS


def openai_schemas() -> list[dict[str, Any]]:
    """导出为 OpenAI function-calling tools 协议格式。"""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in _TOOLS.values()
    ]


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    tool = _TOOLS.get(name)
    if tool is None:
        return f"错误: 未知工具 {name}"
    try:
        return await tool.execute(**arguments)
    except Exception as e:
        logger.exception("工具 %s 执行失败", name)
        return f"工具执行失败: {e}"


# 导入触发注册
from app.agent.tools import current_time, kb_search  # noqa: E402,F401
