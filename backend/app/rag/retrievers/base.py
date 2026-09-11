"""检索器基类与统一结果结构。"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedChunk:
    """检索结果统一结构，key 为 ChromaDB 中的分片 ID。"""

    key: str
    content: str
    document_id: int
    filename: str
    section: str = ""
    chunk_index: int = 0
    score: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


class BaseRetriever:
    """检索器抽象：后续扩展 ES/全文检索等实现只需继承本类。"""

    name: str = "base"

    async def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        raise NotImplementedError
