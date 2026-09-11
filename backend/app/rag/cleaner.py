"""LLM 预处理编排：将解析出的原始文本清洗为高质量入库文本。

策略：
- 开关关闭或文本过短时直接跳过；
- 长文本按段落边界切段，逐段清洗，单段失败保留原文（不中断入库）。
"""
import logging

from app.core.config import settings
from app.llm import deepseek, prompts

logger = logging.getLogger(__name__)

# 超过该长度才启用 LLM 清洗（短文本清洗收益低）
MIN_CLEAN_CHARS = 300
# 每段送 LLM 的最大字符数
SEGMENT_CHARS = 6000


async def clean_text(raw_text: str, filename: str) -> str:
    if not settings.doc_clean_enabled or len(raw_text) < MIN_CLEAN_CHARS:
        return raw_text

    segments = _split_segments(raw_text, SEGMENT_CHARS)
    cleaned_parts: list[str] = []
    for i, seg in enumerate(segments):
        try:
            user_msg = prompts.DOC_CLEAN_USER_TEMPLATE.format(filename=filename, raw_text=seg)
            result = await deepseek.chat(
                [
                    {"role": "system", "content": prompts.DOC_CLEAN_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
            )
            content = (result.get("content") or "").strip()
            if content:
                cleaned_parts.append(content)
            else:
                logger.warning("文档清洗第 %d/%d 段返回为空，保留原文", i + 1, len(segments))
                cleaned_parts.append(seg)
        except Exception:
            logger.exception("文档清洗第 %d/%d 段失败，保留原文", i + 1, len(segments))
            cleaned_parts.append(seg)
    return "\n\n".join(cleaned_parts)


def _split_segments(text: str, max_chars: int) -> list[str]:
    """按段落边界切分，段内超长则硬切。"""
    segments: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for para in text.split("\n\n"):
        if len(para) > max_chars:
            if buf:
                segments.append("\n\n".join(buf))
                buf, buf_len = [], 0
            for i in range(0, len(para), max_chars):
                segments.append(para[i : i + max_chars])
            continue
        if buf_len + len(para) > max_chars and buf:
            segments.append("\n\n".join(buf))
            buf, buf_len = [], 0
        buf.append(para)
        buf_len += len(para) + 2
    if buf:
        segments.append("\n\n".join(buf))
    return segments
