# Parsers 策略模式重构设计

## 目标

将 `src/rag/parsers/` 从函数字典模式重构为策略模式，支持：
- 每种文档格式一个独立类/文件，职责单一
- 统一 `ParseResult` 返回值，携带解析 metadata
- `config` + `variant` 双机制支持定制化需求
- 清理 `src/pipeline/` 中废弃的解析代码

## 当前问题

1. `registry.py` 247 行，混合了 6 个解析函数 + 3 个工具函数 + 2 个处理函数
2. `markdown.py` 中的 `RAGFlowMarkdownParser` 和 `MarkdownElementExtractor` 未接入主注册表
3. `src/pipeline/steps/parser_step.py` 和 `src/pipeline/default_pipeline.py` 仍使用旧解析逻辑
4. 所有 parser 返回 `list[TextNode]`，无法携带额外信息（图片、表格、页数等）

## 重构后文件结构

```
src/rag/parsers/
├── __init__.py          # 导出 registry 实例 + ParseResult + clean_nodes/chunk_nodes
├── base.py              # BaseParser + ParseResult + ParserConfig
├── registry.py          # ParserRegistry 类，content_type → BaseParser 映射 + variant 查找
├── text.py              # TextParser
├── json_parser.py       # JsonParser
├── html.py              # HtmlParser
├── markdown.py          # MarkdownParser（整合 RAGFlowMarkdownParser、MarkdownElementExtractor）
├── pdf.py               # PdfParser
├── docx.py              # DocxParser
└── utils.py             # extract_image_urls_with_lines, md_to_html, load_images_from_urls, _parse_with_reader
```

## 核心接口

### ParseResult

```python
@dataclass
class ParseResult:
    nodes: list[TextNode]
    metadata: dict[str, Any] = field(default_factory=dict)
    # metadata 示例字段：
    #   page_count: int          # PDF 页数
    #   images: list[dict]        # 提取的图片 [{url, line}]
    #   tables: list[str]         # 提取的表格原始文本
    #   element_count: int        # 结构化元素数量
```

### BaseParser

```python
class BaseParser(ABC):
    content_type: str           # 主 content-type，如 "application/pdf"
    variants: list[str] = []    # 变体后缀，如 ["+invoice"]

    @abstractmethod
    def parse(self, raw: bytes, config: dict[str, Any] | None = None) -> ParseResult:
        ...
```

### ParserRegistry

```python
class ParserRegistry:
    def register(self, parser: BaseParser) -> None:
        """注册 parser 到其 content_type 和所有 variants"""
        ...

    def get(self, content_type: str) -> BaseParser:
        """查找 parser，支持 variant 精确匹配 + 基础类型 fallback"""
        # 1. 精确匹配 content_type（含 variant）
        # 2. 取 content_type 的基础部分（去掉 +xxx）再匹配
        # 3. 抛出 UnsupportedContentTypeError
        ...

    @property
    def supported_types(self) -> list[str]:
        """返回所有已注册的 content_type"""
        ...
```

## 各 Parser 实现

### TextParser (`text.py`)

```python
class TextParser(BaseParser):
    content_type = "text/plain"

    def parse(self, raw, config=None) -> ParseResult:
        text = raw.decode("utf-8", errors="ignore")
        return ParseResult(nodes=[TextNode(text=text)])
```

### JsonParser (`json_parser.py`)

```python
class JsonParser(BaseParser):
    content_type = "application/json"

    def parse(self, raw, config=None) -> ParseResult:
        data = json.loads(raw.decode("utf-8"))
        return ParseResult(nodes=[TextNode(text=json.dumps(data, ensure_ascii=False, indent=2))])
```

### HtmlParser (`html.py`)

```python
class HtmlParser(BaseParser):
    content_type = "text/html"

    def parse(self, raw, config=None) -> ParseResult:
        # 使用 html.parser.HTMLParser 提取文本（复用现有逻辑）
        ...
        return ParseResult(nodes=[TextNode(text="\n".join(parts))])
```

### MarkdownParser (`markdown.py`)

整合现有的 `RAGFlowMarkdownParser` 和 `MarkdownElementExtractor`：

```python
class MarkdownParser(BaseParser):
    content_type = "text/markdown"
    variants = ["text/x-markdown"]

    def parse(self, raw, config=None) -> ParseResult:
        text = raw.decode("utf-8", errors="ignore")
        # 使用 LlamaIndex MarkdownNodeParser 做语义拆分
        # 保留 section_title / section_path metadata
        ...
        return ParseResult(
            nodes=nodes,
            metadata={"element_count": len(elements)},
        )
```

`RAGFlowMarkdownParser` 和 `MarkdownElementExtractor` 保留在同文件中作为内部工具类。

### PdfParser (`pdf.py`)

```python
class PdfParser(BaseParser):
    content_type = "application/pdf"

    def parse(self, raw, config=None) -> ParseResult:
        # config 可传入 strip_header_lines 等选项
        nodes = _parse_with_reader(raw, PyMuPDFReader, "file_path", ".pdf")
        return ParseResult(nodes=nodes, metadata={"page_count": len(nodes)})
```

### DocxParser (`docx.py`)

```python
class DocxParser(BaseParser):
    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def parse(self, raw, config=None) -> ParseResult:
        nodes = _parse_with_reader(raw, DocxReader, "file", ".docx")
        return ParseResult(nodes=nodes)
```

## 自动注册机制

各 parser 文件在模块级别自注册：

```python
# pdf.py 底部
registry.register(PdfParser())
```

`__init__.py` 通过 import 所有 parser 模块触发注册：

```python
# __init__.py
from src.rag.parsers.registry import registry, ParserRegistry
from src.rag.parsers.base import BaseParser, ParseResult

# 触发自注册
from src.rag.parsers import text, json_parser, html, markdown, pdf, docx

# 向后兼容
PARSERS = registry  # 旧代码可能用到 PARSERS dict 接口

__all__ = ["registry", "BaseParser", "ParseResult", "PARSERS"]
```

## 定制化支持

### 轻量场景：config 选项

```python
parser = registry.get("application/pdf")
result = parser.parse(raw, config={"strip_header_lines": 3})
```

Parser 在内部读取 config，不需要新建类。

### 重量场景：variant 注册

```python
# custom_invoice_parser.py
class InvoicePdfParser(BaseParser):
    content_type = "application/pdf"
    variants = ["+invoice"]

    def parse(self, raw, config=None) -> ParseResult:
        # 完全不同的解析逻辑
        ...

registry.register(InvoicePdfParser())

# 使用
parser = registry.get("application/pdf+invoice")
```

Registry 查找优先级：精确匹配（含 variant） > 基础类型匹配。

## clean_nodes / chunk_nodes 处理

这两个函数不属于 parser 策略模式，而是后处理步骤。保留在 `registry.py` 中作为独立函数，由 `__init__.py` 导出。`ingest.py` 中的 `parse_bytes()` 改为调用 `registry.get(content_type).parse(raw)`，返回值从 `list[TextNode]` 变为 `ParseResult`。

## 旧代码清理

| 文件 | 操作 |
|---|---|
| `src/pipeline/__init__.py` | 保留但更新 import 指向新接口 |
| `src/pipeline/ingest.py` | 保留废弃 re-export，更新指向 |
| `src/pipeline/steps/parser_step.py` | 删除 |
| `src/pipeline/default_pipeline.py` | 更新为使用新 registry 或标记废弃 |
| `src/pipeline/parsers/` | 已不存在，无需操作 |
| `src/rag/parsers/models.py` | 删除（只有注释） |

## ingest.py 适配

```python
# src/rag/ingest.py — parse_bytes 函数改为：
def parse_bytes(raw: bytes, content_type: str, config: dict | None = None) -> ParseResult:
    parser = registry.get(content_type)
    return parser.parse(raw, config=config)
```

`IngestPipeline.run()` 相应适配，从 `ParseResult` 中取 `nodes`。

## 不在范围内

- 不改变 `clean_nodes` / `chunk_nodes` 的算法逻辑
- 不改变 `embed_and_store` / `persist_chunks` 的接口
- 不引入插件自动发现机制（entry_points / 动态导入），按需手动 import 即可
- 不改变 `RAGFlowMarkdownParser` 和 `MarkdownElementExtractor` 的内部实现
