# Pivot

知识库管理与文档解析平台，支持多格式文档上传、解析、分块、向量化，并提供 RAG 检索能力。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 19 + TypeScript + TanStack (Router/Query/Form) + Tailwind v4 + Vite |
| Go 后端 | gRPC + grpc-gateway + Wire + GORM + Viper |
| Python 后端 | FastAPI + LlamaIndex + HuggingFace/OpenAI Embedding |
| 数据库 | MySQL 8.0 |
| 向量数据库 | Milvus Standalone |
| 对象存储 | MinIO |
| Web UI (Milvus) | Attu |

## 架构概览

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  前端     │────▶│  Go gRPC GW  │────▶│   MySQL      │
│  React   │     │  (:8082)     │     │   (:13306)   │
└──────────┘     └──────┬───────┘     └──────────────┘
     │                  │
     │                  ▼
     │           ┌──────────────┐
     │           │  Milvus      │
     │           │  (:19530)    │
     │           └──────────────┘
     │
     ▼
┌──────────────┐     ┌──────────────┐
│  Python API  │────▶│   MinIO      │
│  (:8000)     │     │   (:19000)   │
└──────────────┘     └──────────────┘
```

- **Go 后端**：知识库/文档 CRUD、用户鉴权、chunks 查询
- **Python 后端**：文档解析（PDF/Word/Excel 等）、分块、向量化、写入 Milvus + MySQL

## 快速启动

```bash
# 启动基础设施
docker compose up -d

# 启动 Go 后端
cd backend/app/kb && go run cmd/main.go

# 启动 Python 解析服务
cd src && python -m uvicorn api.main:app --reload --port 8000

# 启动前端
cd frontend && npm run dev
```

### 服务端口

| 服务 | 端口 | 说明 |
|---|---|---|
| 前端 | 5174 | Vite dev server |
| Go gRPC Gateway | 8082 | REST API |
| Python API | 8000 | 解析任务 API |
| MySQL | 13306 | 结构化数据 |
| MinIO | 19000 / 19001 | 对象存储 / Console |
| Milvus | 19530 | 向量数据库 |
| Attu | 19080 | Milvus Web UI |

## Chunk Metadata 设计

文档解析后按 chunk 存储，采用 **Milvus + MySQL 双写** 策略。

### Milvus（`pivot_chunks` collection）

只存向量检索和过滤必需的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INT64 PK | Milvus 自增 |
| `kb_id` | INT64 | 按知识库过滤 |
| `document_id` | INT64 | 按文档过滤/删除 |
| `chunk_index` | INT64 | 按 chunk 序号定位 |
| `text` | VARCHAR | chunk 文本（检索用） |
| `embedding` | FLOAT_VECTOR(512) | 向量 |

### MySQL（`document_chunks` 表）

存完整 metadata，支持复杂查询和列表展示：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BIGINT PK | 主键 |
| `kb_id` | BIGINT | 知识库 ID |
| `document_id` | BIGINT | 文档 ID |
| `chunk_index` | INT | chunk 序号 |
| `content` | TEXT | chunk 文本 |
| `token_count` | INT | token 数 |
| `source_page` | INT nullable | 来源页码 |
| `section_title` | VARCHAR(512) nullable | 章节标题 |
| `section_path` | VARCHAR(1024) nullable | 层级路径，如 "第1章 > 1.1 概述" |
| `filename` | VARCHAR(255) | 原始文件名 |
| `content_type` | VARCHAR(100) | 文件 MIME 类型 |
| `chunk_size` | INT | 分块大小 |
| `chunk_overlap` | INT | 分块重叠 |
| `version` | INT | chunk 版本 |
| `user_id` | BIGINT nullable | 操作用户 |
| `milvus_id` | BIGINT nullable | Milvus 对应 id |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

索引：`(kb_id, document_id)`、`milvus_id`

### 数据流

```
文档上传 → Python 管道解析/分块/向量化
                │
                ├─▶ Milvus（embedding + 过滤字段）
                │
                └─▶ MySQL document_chunks（完整 metadata）

查询 chunks ──▶ Go 后端 ──▶ MySQL（列表查询）
向量检索     ──▶ Go 后端 ──▶ Milvus（语义搜索）──▶ MySQL（取详情）

删除文档     ──▶ Go 后端 ──▶ Milvus + MySQL 同时删除
```

详细设计文档：`docs/superpowers/specs/2026-05-14-chunk-metadata-redesign.md`
