"""解析器工厂：按文件类型分发。"""
from app.rag.parsers import docx as docx_parser
from app.rag.parsers import html as html_parser
from app.rag.parsers import markdown as md_parser
from app.rag.parsers import pdf as pdf_parser

SUPPORTED_TYPES = {
    "pdf": ("pdf",),
    "docx": ("docx",),
    "markdown": ("md", "markdown"),
    "txt": ("txt",),
    "html": ("html", "htm"),
}

_EXT_ALIASES = {
    "pdf": "pdf",
    "docx": "docx",
    "md": "markdown",
    "markdown": "markdown",
    "txt": "txt",
    "html": "html",
    "htm": "html",
}


class UnsupportedFileTypeError(Exception):
    pass


def detect_file_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _EXT_ALIASES:
        raise UnsupportedFileTypeError(
            f"不支持的文件类型: .{ext}，支持: {sorted(set(_EXT_ALIASES))}"
        )
    return _EXT_ALIASES[ext]


def parse_document(file_type: str, content: bytes) -> str:
    """文件字节 -> 带结构标记的纯文本。"""
    if file_type == "pdf":
        return pdf_parser.parse_pdf(content)
    if file_type == "docx":
        return docx_parser.parse_docx(content)
    if file_type == "markdown":
        return md_parser.parse_markdown(content)
    if file_type == "txt":
        return md_parser.parse_txt(content)
    if file_type == "html":
        return html_parser.parse_html(content)
    raise UnsupportedFileTypeError(f"未知文件类型: {file_type}")
