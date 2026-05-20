# RAG 模块整合设计

## 背景

当前 RAG 相关代码散落在 `src/pipeline/` 和 `src/api/` 中，缺乏统一的业务入口层。`src/rag/` 目录已存在但为空。需要将检索、生成等业务逻辑整合到 `src/rag/` 下，形成清晰的分层架构。

## 目标

将 `src/rag/` 建设为 RAG 生命周期的统一门面（ingest → retrieve → generate），`src/pipeline/` 降级为底层执行引擎，`src/api/` 瘦身为纯 HTTP 薄层。

## 目标结构

```
src/rag/
├── __init__.py           # 对外暴露的公共 API
├── ingest.py             # Ingest 门面：编排 pipeline 处理文档
├── retrieval.py          # 检索：向量搜索 + 可选 rerank
├── generation.py         # RAG 生成：chat with tools
├── rerank.py             # Reranker 抽象与实现
├── schemas.py            # 统一数据模型
├── dependencies.py       # 共享基础设施：embedding / vector store 构建
└── errors.py             # RAG 层错误定义
```

## 分层职责

| 层 | 职责 |
|---|------|
| `src/rag/` | RAG 生命周期门面：ingest → retrieve → generate |
| `src/pipeline/` | 底层执行引擎：parsers, steps, executor（保持不动） |
| `src/api/` | 薄 HTTP 层：只做请求/响应转换 + 鉴权 |

## 数据流

```
HTTP Request
    ↓
src/api/ (验证、鉴权、序列化)
    ↓
src/rag/ (业务编排)
    ├── ingest.py → 调用 pipeline executor
    ├── retrieval.py → 调用 dependencies 构建 vector store
    └── generation.py → 调用 retrieval + LLM
    ↓
src/pipeline/ (底层执行)
    └── parsers / steps / executor
```

## 迁移清单

### 1. `rag/schemas.py` — 数据模型

从 `pipeline/search.py` 提取：

- `SearchResult` dataclass

新增：

- `ChatMessage`, `ChatSource`, `ChatRequest`, `ChatResponse` 从 `api/chat.py` 提取
- `RerankerConfig` 用于 reranker 构建参数

### 2. `rag/errors.py` — 错误定义

从 `pipeline/search.py` 提取：

- `RerankerUnavailableError`

从 `pipeline/ingest.py` 提取：

- `UnsupportedContentTypeError`

### 3. `rag/dependencies.py` — 共享基础设施

从 `pipeline/ingest.py` 提取：

- `_build_embedding()` → `build_embedding()`
- `_build_vector_store()` → `build_vector_store()`
- `PivotMilvusVectorStore` 类

这些函数同时被 `rag/ingest.py` 和 `rag/retrieval.py` 使用。

### 4. `rag/rerank.py` — Reranker

从 `pipeline/search.py` 提取：

- `Reranker` Protocol
- `HuggingFaceReranker` 类
- `build_reranker()` 工厂函数
- `_resolve_retrieval_top_k()` 辅助函数
- 相关常量 `DEFAULT_RERANK_CANDIDATE_MULTIPLIER`, `DEFAULT_RERANK_CANDIDATE_LIMIT`

### 5. `rag/retrieval.py` — 检索

从 `pipeline/search.py` 迁移核心检索逻辑：

- `search_chunks()` 函数

依赖：

- `rag/dependencies.py` 的 `build_embedding()`, `build_vector_store()`
- `rag/rerank.py` 的 `build_reranker()`
- `rag/schemas.py` 的 `SearchResult`

### 6. `rag/ingest.py` — 文档入库

从 `pipeline/ingest.py` 迁移上层入口：

- `ingest_bytes()` 函数
- `_persist_nodes()` 辅助函数

依赖：

- `rag/dependencies.py` 的 `build_embedding()`, `build_vector_store()`, `PivotMilvusVectorStore`
- `src/pipeline/parsers` 的 `PARSERS`, `clean_nodes`, `chunk_nodes`
- `src/models/document_chunk` 的 `DocumentChunk`

### 7. `rag/generation.py` — RAG 生成

从 `api/chat.py` 迁移核心生成逻辑：

- `chat_with_tools()` 函数
- `_execute_tool()` 辅助函数
- `SYSTEM_PROMPT_TEMPLATE`, `TOOLS` 常量

依赖：

- `rag/retrieval.py` 的 `search_chunks()`
- `rag/schemas.py` 的数据模型

### 8. `rag/__init__.py` — 公共 API

对外暴露：

- `ingest_bytes`
- `search_chunks`
- `chat_with_tools`
- 关键 schema 类

## 对现有模块的影响

### `src/pipeline/search.py`

- 整个文件废弃，逻辑已迁移到 `rag/retrieval.py` + `rag/rerank.py` + `rag/schemas.py` + `rag/errors.py`
- 可保留为 re-export 壳以保持向后兼容，后续移除

### `src/pipeline/ingest.py`

- `ingest_bytes`, `_persist_nodes`, `PivotMilvusVectorStore`, `_build_embedding`, `_build_vector_store` 迁移到 `rag/`
- 保留解析器注册相关代码（`clean_nodes`, `chunk_nodes` 已在 `parsers/registry.py` 中）
- 文件改为从 `rag/ingest.py` re-export 以保持向后兼容

### `src/api/chat.py`

- `chat_with_tools`, `_execute_tool`, `ChatMessage`, `ChatSource`, `SYSTEM_PROMPT_TEMPLATE`, `TOOLS` 迁移到 `rag/generation.py`
- `ChatRequest`, `ChatResponse` 迁移到 `rag/schemas.py`
- API 路由保留，改为调用 `rag/generation.py`

### `src/api/search.py`

- 改为调用 `rag/retrieval.search_chunks()` 而非 `pipeline/search.search_chunks()`
- `SearchHit`, `SearchRequest`, `SearchResponse` 保留在 `schemas/search.py`（API 层 schema）

### 测试

- 现有测试如果引用 `pipeline.search` 或 `pipeline.ingest`，需更新 import 路径
- 新增 `tests/rag/` 测试目录，与 `src/rag/` 结构对应

## 关键原则

1. **不改变底层实现**：pipeline/ 的 parsers、steps、executor 原样保留
2. **抽取共享依赖**：embedding 和 vector store 构建逻辑移到 `rag/dependencies.py`
3. **API 层瘦身**：api/chat.py 只保留路由 + 请求模型
4. **向后兼容过渡**：pipeline/search.py 和 pipeline/ingest.py 保留 re-export 壳
