"""知识库检索工具：Agent 可反复调用的检索入口。"""
from app.agent.tools import register_tool
from app.rag.retrievers import get_retriever

_TOOL_TOP_K = 5


@register_tool(
    name="kb_search",
    description=(
        "在澳门城市大学校园知识库中检索资料。回答学校规章制度、院系介绍、"
        "办事流程、校园活动等校园相关问题时，应优先调用本工具。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "检索查询语句，建议使用具体的关键词或完整问题",
            }
        },
        "required": ["query"],
    },
)
async def kb_search(query: str) -> str:
    results = await get_retriever().retrieve(query, top_k=_TOOL_TOP_K)
    if not results:
        return "知识库中未检索到相关资料。"
    blocks = []
    for i, item in enumerate(results, start=1):
        source = f"{item.filename}" + (f" - {item.section}" if item.section else "")
        blocks.append(f"[编号 {i}] 来源: {source}\n{item.content}")
    return "\n\n".join(blocks)
