# Chunk Metadata 重新设计

## 背景

当前 chunk 存在以下问题：

1. **命名不一致** — Python 管道写的 collection 名叫 `llamacollection`（LlamaIndex 默认），Go 后端硬编码查 `default_vec`
2. **类型低效** — `kb_id`、`doc_document_id` 用 VARCHAR 存数值型 ID，查询需要字符串拼接
3. **字段冗余** — LlamaIndex 的 `doc_id` 和自定义的 `doc_document_id` 重复
4. **metadata 缺失** — 管道写入了 `object_key`、`content_type` 但未声明为 scalar field，查询时拿不到
5. **无结构化 metadata** — 缺少 source_page、section_title 等 RAG 检索所需的上下文信息

## 设计：Milvus + MySQL 双写

### 职责分离

- **Milvus**：只存向量检索和过滤必需的字段（embedding + 少量 scalar field）
- **MySQL**：存完整的 chunk metadata，支持复杂查询和列表展示

### Milvus schema（`pivot_chunks` collection）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INT64 PK 自增 | Milvus 自动生成 |
| `kb_id` | INT64 | 按知识库过滤 |
| `document_id` | INT64 | 按文档过滤 / 删除 |
| `chunk_index` | INT64 | 按 chunk 序号定位 / 删除 |
| `text` | VARCHAR | chunk 文本（检索用） |
| `embedding` | FLOAT_VECTOR(512) | 向量检索 |

### MySQL `document_chunks` 表

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BIGINT PK AUTO_INCREMENT | 主键 |
| `kb_id` | BIGINT NOT NULL | 知识库 ID |
| `document_id` | BIGINT NOT NULL | 文档 ID |
| `chunk_index` | INT NOT NULL | chunk 序号 |
| `content` | TEXT NOT NULL | chunk 文本内容 |
| `token_count` | INT NOT NULL DEFAULT 0 | token 数 |
| `source_page` | INT NULL | 来源页码（PDF 等） |
| `section_title` | VARCHAR(512) NULL | 章节标题 |
| `section_path` | VARCHAR(1024) NULL | 层级路径，如 "第1章 > 1.1 概述" |
| `filename` | VARCHAR(255) NOT NULL | 原始文件名 |
| `content_type` | VARCHAR(100) NOT NULL | 文件 MIME 类型 |
| `chunk_size` | INT NOT NULL DEFAULT 512 | 分块大小 |
| `chunk_overlap` | INT NOT NULL DEFAULT 50 | 分块重叠 |
| `version` | INT NOT NULL DEFAULT 1 | chunk 版本（重新解析时递增） |
| `user_id` | BIGINT NULL | 操作用户 ID |
| `milvus_id` | BIGINT NULL | Milvus 中对应行的 id |
| `created_at` | DATETIME DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

索引：`(kb_id, document_id)`、`milvus_id`

### 数据流

**写入（Python 管道 `ingest_bytes`）：**
1. 解析 → 清洗 → 分块
2. 写入 Milvus（拿到 milvus_id）
3. 写入 MySQL `document_chunks`（存 milvus_id 关联）

**查询（Go 后端）：**
- 列表查询：从 MySQL 读取，含完整 metadata
- 向量检索：Milvus 做语义搜索，返回 id 列表，再用 id 从 MySQL 取详情

**删除（Go 后端）：**
- 单个 chunk：同时删 Milvus（按 kb_id + document_id + chunk_index）和 MySQL
- 整个文档：同时删 Milvus（按 kb_id + document_id）和 MySQL

### Collection 名统一

Python 管道和 Go 后端统一使用 `pivot_chunks` 作为 collection 名。

### Python 管道改动

`_build_vector_store` 中：
- collection 名改为 `pivot_chunks`
- scalar field 改为 `kb_id`(INT64)、`document_id`(INT64)、`chunk_index`(INT64)
- 去掉 `doc_document_id`、`doc_id` 等冗余字段

`ingest_bytes` 中：
- 写入 Milvus 后，额外写 MySQL `document_chunks` 表
- metadata 中传入 source_page、section_title、section_path、filename、content_type、chunk_size、chunk_overlap、user_id

### Go 后端改动

- `ChunkRepository.FindChunksByDocument` 改为从 MySQL 读取（不再查 Milvus）
- `ChunkRepository.DeleteChunk` / `DeleteChunksByDocument` 同时操作 Milvus + MySQL
- proto `Chunk` message 增加新字段（source_page、section_title 等）
- collection 名改为 `pivot_chunks`

### 前端改动

- chunk 列表展示新增字段：来源页码、章节标题、层级路径
- 生成的 SDK 类型自动包含新字段

### 迁移策略

1. 创建 MySQL `document_chunks` 表
2. 更新 Python 管道代码，使用新 schema 写入
3. 更新 Go 后端，从 MySQL 读 chunks
4. 删除旧 `llamacollection` collection
5. 对已有文档重新解析，数据写入新 schema
