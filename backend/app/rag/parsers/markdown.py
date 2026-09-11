"""Markdown / 纯文本解析：解码规范化后原样返回。"""


def parse_markdown(content: bytes) -> str:
    return _decode(content)


def _decode(content: bytes) -> str:
    text = content.decode("utf-8", errors="ignore")
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    return text


# txt 复用同一实现
parse_txt = _decode
