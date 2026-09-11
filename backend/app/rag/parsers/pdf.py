"""PDF 解析：pymupdf4llm 提取为 Markdown，保留标题/表格/阅读顺序。"""
import logging
import tempfile
from pathlib import Path

import pymupdf
import pymupdf4llm

logger = logging.getLogger(__name__)


def parse_pdf(content: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        md_text = pymupdf4llm.to_markdown(tmp_path, show_progress=False)
        return md_text
    except Exception:
        # 4llm 失败时退化为纯文本逐页提取，保证入库不中断
        logger.warning("pymupdf4llm 解析失败，退化为逐页纯文本提取", exc_info=True)
        with pymupdf.open(tmp_path) as doc:
            return "\n\n".join(page.get_text("text") for page in doc)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
