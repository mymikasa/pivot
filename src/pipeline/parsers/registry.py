import logging
import json
import re
import tempfile
from io import BytesIO

from html.parser import HTMLParser
from pathlib import Path
from PIL import Image

import markdown
from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SimpleFileNodeParser
from llama_index.core.schema import TextNode
from llama_index.readers.file import DocxReader, PyMuPDFReader

from src.pipeline.parsers.markdown import RAGFlowMarkdownParser


def parse_text(raw: bytes) -> list[TextNode]:
    return [TextNode(text=raw.decode("utf-8", errors="ignore"))]


def parse_json(raw: bytes) -> list[TextNode]:
    data = json.loads(raw.decode("utf-8"))
    return [TextNode(text=json.dumps(data, ensure_ascii=False, indent=2))]


def parse_html(raw: bytes) -> list[TextNode]:
    class _TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts: list[str] = []
        def handle_data(self, data):
            if data.strip():
                self.parts.append(data.strip())

    p = _TextExtractor()
    p.feed(raw.decode("utf-8", errors="ignore"))
    return [TextNode(text="\n".join(p.parts))]


def _parse_with_reader(raw: bytes, reader_cls, param_name: str, suffix: str) -> list[TextNode]:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        docs = reader_cls().load_data(**{param_name: Path(tmp_path)})
        return [TextNode(text=doc.text) for doc in docs if doc.text.strip()]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def parse_pdf(raw: bytes) -> list[TextNode]:
    return _parse_with_reader(raw, PyMuPDFReader, "file_path", ".pdf")


def parse_docx(raw: bytes) -> list[TextNode]:
    return _parse_with_reader(raw, DocxReader, "file", ".docx")


def parse_markdown(raw: bytes) -> list[TextNode]:
    text = raw.decode("utf-8", errors="ignore")

    nodes: list[TextNode] = []

    # 用 LlamaIndex MarkdownNodeParser 做语义拆分
    parser = MarkdownNodeParser()
    doc = Document(text=text)
    parsed_nodes = parser.get_nodes_from_documents([doc])

    for node in parsed_nodes:
        content = node.text.strip()
        if not content:
            continue

        header_path = node.metadata.get("header_path", "")
        parts = [p for p in header_path.strip("/").split("/") if p]
        section_title = parts[-1] if parts else ""

        nodes.append(TextNode(
            text=content,
            metadata={
                "section_title": section_title,
                "section_path": header_path,
            },
        ))

    return nodes


# content_type → 解析函数
PARSERS = {
    "text/plain": parse_text,
    "application/json": parse_json,
    "text/html": parse_html,
    "text/markdown": parse_markdown,
    "text/x-markdown": parse_markdown,
    "application/pdf": parse_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
}


def clean_nodes(nodes: list[TextNode]) -> list[TextNode]:
    seen: set[str] = set()
    cleaned: list[TextNode] = []
    for node in nodes:
        text = re.sub(r"\s+", " ", node.text).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(TextNode(text=text, metadata=node.metadata))
    return cleaned


def chunk_nodes(nodes: list[TextNode], chunk_size: int = 512, overlap: int = 50) -> list[TextNode]:
    result: list[TextNode] = []
    for node in nodes:
        text = node.text
        tokens = text.split()
        token_count = len(tokens)

        if token_count <= chunk_size:
            result.append(node)
            continue

        # 超长 node：按段落边界切分
        paragraphs = re.split(r"\n\n+", text)
        current_parts: list[str] = []
        current_len = 0

        for para in paragraphs:
            para_tokens = len(para.split())
            if current_len + para_tokens > chunk_size and current_parts:
                result.append(TextNode(
                    text="\n\n".join(current_parts),
                    metadata={**node.metadata, "token_count": current_len},
                ))
                current_parts = [para]
                current_len = para_tokens
            else:
                current_parts.append(para)
                current_len += para_tokens

        if current_parts:
            result.append(TextNode(
                text="\n\n".join(current_parts),
                metadata={**node.metadata, "token_count": current_len},
            ))

    return result


def md_to_html(sections):
    if not sections:
        return []
    if isinstance(sections, type("")):
        text = sections
    elif isinstance(sections[0], type("")):
        text = sections[0]
    else:
        return []

    from bs4 import BeautifulSoup

    html_content = markdown(text)
    soup = BeautifulSoup(html_content, "html.parser")
    return soup


def extract_image_urls_with_lines(text):
    md_img_re = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
    html_img_re = re.compile(r'src=["\\\']([^"\\\'>\\s]+)', re.IGNORECASE)
    urls = []
    seen = set()
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        for url in md_img_re.findall(line):
            if (url, idx) not in seen:
                urls.append({"url": url, "line": idx})
                seen.add((url, idx))
        for url in html_img_re.findall(line):
            if (url, idx) not in seen:
                urls.append({"url": url, "line": idx})
                seen.add((url, idx))

    # cross-line
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "html.parser")
        newline_offsets = [m.start() for m in re.finditer(r"\n", text)] + [len(text)]
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src")
            if not src:
                continue

            tag_str = str(img_tag)
            pos = text.find(tag_str)
            if pos == -1:
                # fallback
                pos = max(text.find(src), 0)
            line_no = 0
            for i, off in enumerate(newline_offsets):
                if pos <= off:
                    line_no = i
                    break
            if (src, line_no) not in seen:
                urls.append({"url": src, "line": line_no})
                seen.add((src, line_no))
    except Exception as e:
        logging.error("Failed to extract image urls: {}".format(e))
        pass

    return urls


def load_images_from_urls(urls, cache=None):
    import requests
    from pathlib import Path

    cache = cache or {}
    images = []
    for url in urls:
        if url in cache:
            if cache[url]:
                images.append(cache[url])
            continue
        img_obj = None
        try:
            if url.startswith(("http://", "https://")):
                response = requests.get(url, stream=True, timeout=30)
                if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
                    img_obj = Image.open(BytesIO(response.content)).convert("RGB")
            else:
                local_path = Path(url)
                if local_path.exists():
                    img_obj = Image.open(url).convert("RGB")
                else:
                    logging.warning(f"Local image file not found: {url}")
        except Exception as e:
            logging.error(f"Failed to download/open image from {url}: {e}")
        cache[url] = img_obj
        if img_obj:
            images.append(img_obj)
    return images, cache
