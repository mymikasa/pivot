from __future__ import annotations

import logging
import re
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image


def _parse_with_reader(
    raw: bytes, reader_cls: type, param_name: str, suffix: str
) -> list:
    from llama_index.core.schema import TextNode

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        docs = reader_cls().load_data(**{param_name: Path(tmp_path)})
        return [TextNode(text=doc.text) for doc in docs if doc.text.strip()]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def extract_image_urls_with_lines(text: str) -> list[dict[str, Any]]:
    md_img_re = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
    html_img_re = re.compile(r'src=["\\\']([^"\\\'>\\s]+)', re.IGNORECASE)
    urls: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
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

    return urls


def md_to_html(sections):
    import markdown as md_lib
    from bs4 import BeautifulSoup

    if not sections:
        return []
    if isinstance(sections, str):
        text = sections
    elif isinstance(sections, list) and isinstance(sections[0], str):
        text = sections[0]
    else:
        return []
    html_content = md_lib.markdown(text)
    soup = BeautifulSoup(html_content, "html.parser")
    return soup


def load_images_from_urls(urls: list[str], cache: dict | None = None) -> tuple[list, dict]:
    import requests

    cache = cache or {}
    images: list[Image.Image] = []
    for url in urls:
        if url in cache:
            if cache[url]:
                images.append(cache[url])
            continue
        img_obj = None
        try:
            if url.startswith(("http://", "https://")):
                response = requests.get(url, stream=True, timeout=30)
                if response.status_code == 200 and response.headers.get(
                    "Content-Type", ""
                ).startswith("image/"):
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
