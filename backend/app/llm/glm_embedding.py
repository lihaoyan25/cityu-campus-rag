"""GLM embedding-3 客户端：批量向量化，httpx 直连 + tenacity 重试。"""
import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """向量化失败。"""


class _TransientStatus(Exception):
    """可重试的 HTTP 状态码。"""

    def __init__(self, status_code: int, body: str):
        super().__init__(f"HTTP {status_code}: {body}")


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError, _TransientStatus)),
)
async def _embed_batch(texts: list[str]) -> tuple[list[list[float]], dict[str, int]]:
    """单批向量化，返回 (与输入顺序一致的向量列表, usage)。"""
    payload = {
        "model": settings.glm_model,
        "input": texts,
        "dimensions": settings.glm_embedding_dimensions,
    }
    headers = {"Authorization": f"Bearer {settings.glm_api_key}"}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(settings.glm_base_url, json=payload, headers=headers)
    if resp.status_code in (429, 500, 502, 503, 504):
        raise _TransientStatus(resp.status_code, resp.text[:200])
    if resp.status_code != 200:
        raise EmbeddingError(f"GLM embedding API 错误 {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    data = body.get("data", [])
    if len(data) != len(texts):
        raise EmbeddingError(f"GLM embedding 返回数量不符: 期望 {len(texts)} 实际 {len(data)}")
    # 按 index 对齐输入顺序
    data.sort(key=lambda item: item.get("index", 0))
    usage_raw = body.get("usage") or {}
    usage = {
        "prompt_tokens": usage_raw.get("prompt_tokens", 0) or 0,
        "total_tokens": usage_raw.get("total_tokens", 0) or 0,
    }
    return [item["embedding"] for item in data], usage


async def embed_texts(texts: list[str], usage_out: dict[str, int] | None = None) -> list[list[float]]:
    """批量向量化：自动按配置批次切分，结果顺序与输入一致。

    usage_out 不为 None 时，将本批次的 token 消耗累加进去（键: prompt_tokens/total_tokens）。
    """
    if not texts:
        return []
    batch_size = max(1, settings.glm_embedding_batch_size)
    results: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        vectors, usage = await _embed_batch(batch)
        results.extend(vectors)
        if usage_out is not None:
            usage_out["prompt_tokens"] = usage_out.get("prompt_tokens", 0) + usage["prompt_tokens"]
            usage_out["total_tokens"] = usage_out.get("total_tokens", 0) + usage["total_tokens"]
        logger.info("GLM embedding 批次完成: %d/%d", min(i + batch_size, len(texts)), len(texts))
    return results


async def embed_query(text: str) -> list[float]:
    """单条查询向量化。"""
    vectors = await embed_texts([text])
    return vectors[0]
