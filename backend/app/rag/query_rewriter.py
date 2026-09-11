"""查询改写：结合对话历史把追问改写为独立问题（DeepSeek）。"""
import logging

from app.llm import deepseek, prompts

logger = logging.getLogger(__name__)

# 参与改写的历史条数
MAX_HISTORY_MESSAGES = 6


async def rewrite_query(question: str, history: list[dict]) -> str:
    """history: [{"role", "content"}]，按时间正序。失败时返回原问题。"""
    if not history:
        return question
    history_text = "\n".join(
        f"{'用户' if m['role'] == 'user' else '助手'}: {str(m.get('content') or '')[:500]}"
        for m in history[-MAX_HISTORY_MESSAGES:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    )
    if not history_text:
        return question
    try:
        user_msg = prompts.QUERY_REWRITE_USER_TEMPLATE.format(
            history=history_text, question=question
        )
        result = await deepseek.chat(
            [
                {"role": "system", "content": prompts.QUERY_REWRITE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=256,
        )
        rewritten = (result.get("content") or "").strip().strip('"')
        return rewritten or question
    except Exception:
        logger.exception("查询改写失败，使用原问题")
        return question
