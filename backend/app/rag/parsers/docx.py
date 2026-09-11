"""Word(docx) 解析：按文档 body 顺序遍历段落与表格，输出 Markdown 风格文本。"""
import io

from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


def parse_docx(content: bytes) -> str:
    doc = DocxDocument(io.BytesIO(content))
    lines: list[str] = []
    for block in _iter_blocks(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            lines.append(_heading_mark(block) + text)
        elif isinstance(block, Table):
            lines.extend(_table_to_markdown(block))
    return "\n\n".join(lines)


def _iter_blocks(doc: DocxDocument):
    """按 body 实际顺序产出段落/表格（doc.paragraphs 会丢失顺序）。"""
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def _heading_mark(para: Paragraph) -> str:
    style = (para.style.name or "") if para.style is not None else ""
    if style.lower().startswith("heading"):
        try:
            level = int(style.split()[-1])
            return "#" * min(max(level, 1), 6) + " "
        except ValueError:
            return "## "
    return ""


def _table_to_markdown(table: Table) -> list[str]:
    rows = [
        [cell.text.strip().replace("\n", " ").replace("|", "\\|") for cell in row.cells]
        for row in table.rows
    ]
    if not rows:
        return []
    out = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * len(rows[0])) + " |"]
    for row in rows[1:]:
        out.append("| " + " | ".join(row) + " |")
    return out
