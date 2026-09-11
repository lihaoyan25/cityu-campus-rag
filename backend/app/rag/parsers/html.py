"""HTML 解析：BeautifulSoup 提取正文，保留标题/列表/表格的 Markdown 结构。"""
import io

from bs4 import BeautifulSoup


def parse_html(content: bytes) -> str:
    soup = BeautifulSoup(content, "lxml")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    body = soup.body or soup
    lines: list[str] = []
    _render(body, lines)
    return "\n\n".join(chunk for chunk in (ln.strip() for ln in lines) if chunk)


def _render(node, lines: list[str]) -> None:
    if node.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(node.name[1])
        text = node.get_text(" ", strip=True)
        if text:
            lines.append("#" * level + " " + text)
        return
    if node.name in ("p", "blockquote"):
        text = node.get_text(" ", strip=True)
        if text:
            lines.append(text)
        return
    if node.name in ("ul", "ol"):
        for i, li in enumerate(node.find_all("li", recursive=False), start=1):
            text = li.get_text(" ", strip=True)
            if text:
                lines.append(f"{i}. {text}" if node.name == "ol" else f"- {text}")
        return
    if node.name == "table":
        _render_table(node, lines)
        return
    for child in node.children:
        if getattr(child, "name", None):
            _render(child, lines)
        elif str(child).strip():
            lines.append(str(child).strip())


def _render_table(table, lines: list[str]) -> None:
    rows = table.find_all("tr")
    if not rows:
        return
    cells = [[c.get_text(" ", strip=True).replace("|", "\\|") for c in tr.find_all(["td", "th"])] for tr in rows]
    width = max(len(r) for r in cells)
    for r in cells:
        r += [""] * (width - len(r))
    lines.append("| " + " | ".join(cells[0]) + " |")
    lines.append("| " + " | ".join(["---"] * width) + " |")
    for row in cells[1:]:
        lines.append("| " + " | ".join(row) + " |")
