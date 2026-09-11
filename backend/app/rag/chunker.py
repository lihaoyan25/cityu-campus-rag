"""结构感知分块：按 Markdown 标题切节，节内按段落聚合成 chunk，带重叠。"""
import re
from dataclasses import dataclass, field

from app.core.config import settings

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@dataclass
class Chunk:
    content: str
    index: int
    meta: dict = field(default_factory=dict)


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """返回内容互有重叠、带章节路径的文本块列表。"""
    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap or settings.chunk_overlap
    sections = _split_sections(text)

    raw_chunks: list[tuple[str, str]] = []  # (content, title_path)
    for title_path, body in sections:
        for piece in _pack_paragraphs(body, size, overlap):
            raw_chunks.append((piece, title_path))

    # 过滤过小片段并合并到前一块
    merged: list[tuple[str, str]] = []
    for piece, title_path in raw_chunks:
        if merged and len(piece) < 50:
            prev_content, prev_title = merged[-1]
            merged[-1] = (prev_content + "\n\n" + piece, prev_title)
        else:
            merged.append((piece, title_path))

    chunks = []
    for i, (content, title_path) in enumerate(merged):
        meta = {"section": title_path} if title_path else {}
        chunks.append(Chunk(content=content, index=i, meta=meta))
    return chunks


def _split_sections(text: str) -> list[tuple[str, str]]:
    """按标题层级切分，返回 (章节路径, 正文)。无标题的文本整体为一节。"""
    sections: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []  # (level, title)
    current: list[str] = []

    def title_path() -> str:
        return " / ".join(t for _, t in stack)

    def flush() -> None:
        body = "\n\n".join(current).strip()
        if body:
            sections.append((title_path(), body))

    for line in text.split("\n"):
        m = _HEADING_RE.match(line.strip())
        if m:
            flush()
            current = []
            level, title = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        else:
            current.append(line)
    flush()
    if not sections:
        body = text.strip()
        if body:
            sections.append(("", body))
    return sections


def _pack_paragraphs(body: str, size: int, overlap: int) -> list[str]:
    """段落聚合：不足 size 拼接，超出则成块；末尾保留 overlap 重叠。"""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    pieces: list[str] = []
    buf: list[str] = []
    buf_len = 0

    def buf_text() -> str:
        return "\n\n".join(buf)

    for para in paragraphs:
        if len(para) > size:
            if buf:
                pieces.append(buf_text())
                buf, buf_len = [], 0
            pieces.extend(_hard_split(para, size, overlap))
            continue
        if buf_len + len(para) + 2 > size and buf:
            pieces.append(buf_text())
            # 保留尾部重叠
            tail = buf_text()[-overlap:] if overlap > 0 else ""
            buf, buf_len = ([tail], len(tail)) if tail else ([], 0)
        buf.append(para)
        buf_len += len(para) + 2
    if buf:
        pieces.append(buf_text())
    return pieces


def _hard_split(text: str, size: int, overlap: int) -> list[str]:
    step = max(size - overlap, 1)
    return [text[i : i + size] for i in range(0, len(text), step)]
