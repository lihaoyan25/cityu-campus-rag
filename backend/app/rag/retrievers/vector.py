"""向量检索器：GLM embedding + ChromaDB。"""
from app.llm import glm_embedding
from app.rag import vector_store
from app.rag.retrievers.base import BaseRetriever, RetrievedChunk


class VectorRetriever(BaseRetriever):
    name = "vector"

    async def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        embedding = await glm_embedding.embed_query(query)
        hits = vector_store.query(embedding, top_k)
        results: list[RetrievedChunk] = []
        for rank, hit in enumerate(hits):
            meta = hit["metadata"] or {}
            results.append(
                RetrievedChunk(
                    key=hit["id"],
                    content=hit["document"],
                    document_id=int(meta.get("document_id", 0)),
                    filename=str(meta.get("filename", "")),
                    section=str(meta.get("section", "")),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    # 距离转相似度，便于展示
                    score=round(1 - hit["distance"], 4) if hit["distance"] is not None else 0.0,
                    extra={"rank": rank},
                )
            )
        return results
