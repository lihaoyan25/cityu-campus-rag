"""文本清洗工具：适配 MySQL 5.1 utf8(3字节) 字符集。"""
import re

# 4字节字符（emoji、生僻CJK扩展等），utf8mb3 无法存储
_NON_BMP_RE = re.compile(r"[\U00010000-\U0010FFFF]")


def strip_4byte(text: str | None) -> str | None:
    """过滤超出 UTF-8 3字节的字符，避免写入 MySQL utf8 时报错。"""
    if text is None:
        return None
    return _NON_BMP_RE.sub("", text)
