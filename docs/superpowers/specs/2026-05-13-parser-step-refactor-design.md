# ParserStep 重构设计

## 背景

当前 `ParserStep` 存在两个问题：
1. 文本提取后按 `\n` 拆成多个 section，但拆分应交给 `ChunkStep`
2. 不同 content_type 的解析逻辑用 if-else 写在同一个方法里，扩展性差

## 目标

- ParserStep 只负责文本提取，输出整个文档作为单个 `Section`
- 用 Registry + 策略模式组织不同文件类型的解析逻辑
- 后续新增格式（PDF、Markdown）只需添加 parser 类并注册

## 设计

### DocumentParser 策略接口

```python
# src/pipeline/parsers/base.py
class DocumentParser(ABC):
    @abstractmethod
    def parse(self, raw: bytes) -> str: ...
```

### 内置 Parser

| 类 | 文件 | content_type |
|---|---|---|
| `TextParser` | `text_parser.py` | `text/plain` 及默认 fallback |
| `JsonParser` | `json_parser.py` | `application/json` |
| `HtmlParser` | `html_parser.py` | `text/html` |

每个 parser 实现 `parse(raw: bytes) -> str`，只做 bytes → text 转换。

### ParserRegistry

```python
# src/pipeline/parsers/registry.py
class ParserRegistry:
    def __init__(self) -> None: ...
    def register(self, content_type: str, parser: DocumentParser) -> None: ...
    def get(self, content_type: str) -> DocumentParser: ...  # fallback to TextParser
```

### ParserStep 改造

```python
class ParserStep(PipelineStep):
    def __init__(self, registry: ParserRegistry) -> None: ...

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        parser = self.registry.get(ctx.content_type)
        text = parser.parse(ctx.raw_binary)
        ctx.sections = [Section(text=text)]
        return ctx
```

### 对下游的影响

- **CleanStep**：逻辑不变（去重、空白处理），输入从多个 section 变为单个 section
- **ChunkStep**：逻辑不变（滑窗分块），完全接管分块职责
- **EmbedStep / StoreStep**：无影响

## 文件变更

| 操作 | 文件 |
|---|---|
| 新增 | `src/pipeline/parsers/__init__.py` |
| 新增 | `src/pipeline/parsers/base.py` |
| 新增 | `src/pipeline/parsers/text_parser.py` |
| 新增 | `src/pipeline/parsers/json_parser.py` |
| 新增 | `src/pipeline/parsers/html_parser.py` |
| 新增 | `src/pipeline/parsers/registry.py` |
| 修改 | `src/pipeline/steps/parser_step.py` — 改为从 registry 查找 parser，输出单 section |
| 修改 | `src/pipeline/default_pipeline.py` — 构建 registry 并注入 ParserStep |
| 修改 | `tests/test_pipeline.py` — 适配新行为 |
| 删除 | `src/pipeline/steps/parser_step.py` 中的 `_TextExtractor` 和 `_to_text` |
