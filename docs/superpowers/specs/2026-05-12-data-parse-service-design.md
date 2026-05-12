# 数据解析服务设计文档

## 背景

RAG 系统中，文档已通过知识库功能上传到 MinIO。数据解析服务是"数据源管理"的下层，负责将原始文档经过 解析 → 清洗 → 切分 → Embedding → 存储 的完整管道，最终输出可检索的向量数据。

## 架构概述

```
前端 → FastAPI API → MySQL (parse_tasks) → Background Worker
                                                    │
                                         ┌──────────┴──────────┐
                                         │ Pipeline Executor    │
                                         │                      │
                                         │ 1. 从 MinIO 下载文件  │
                                         │ 2. 解析 (Parser)      │
                                         │ 3. 清洗/脱敏          │
                                         │ 4. Chunk 切分         │
                                         │ 5. Embedding          │
                                         │ 6. 存储 (Milvus+MySQL)│
                                         └──────────────────────┘
```

Python FastAPI 独立暴露 API，前端直接调用，不走 Go gRPC 转发。JWT 鉴权复用 Go 服务的 secret。

## 触发方式

用户在知识库详情页选中文档，手动点击"解析"按钮触发。

## 任务队列：MySQL 自建任务表

在 `pivot` 数据库中新建 `parse_tasks` 表，FastAPI 启动时拉起后台 worker 线程轮询待执行任务。

选择理由：零外部依赖，任务状态持久化，单 worker 够用，重启不丢任务。

## 数据库模型

### `parse_tasks` — 解析任务表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT AUTO_INCREMENT | 主键 |
| kb_id | BIGINT NOT NULL | 知识库 ID |
| document_id | BIGINT NOT NULL | 文档 ID |
| object_key | VARCHAR(512) | MinIO 对象 Key |
| content_type | VARCHAR(128) | 文件 MIME 类型 |
| status | VARCHAR(32) | pending / running / completed / failed |
| progress | TINYINT DEFAULT 0 | 进度百分比 0-100 |
| error_message | TEXT | 失败原因 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### `document_chunks` — Chunk 元数据表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT AUTO_INCREMENT | 主键 |
| kb_id | BIGINT NOT NULL | 知识库 ID |
| document_id | BIGINT NOT NULL | 文档 ID |
| chunk_index | INT NOT NULL | chunk 序号 |
| content | TEXT NOT NULL | chunk 文本内容 |
| token_count | INT | token 数量 |
| milvus_id | BIGINT | Milvus 向量 ID |
| created_at | DATETIME | 创建时间 |

### Milvus Collection: `document_vectors`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT64 | 主键 |
| kb_id | INT64 | 知识库 ID（分区键） |
| document_id | INT64 | 文档 ID |
| chunk_index | INT32 | chunk 序号 |
| embedding | FLOAT_VECTOR | 向量数据 |
| content | VARCHAR | chunk 文本（冗余存储便于检索返回） |

## 可编排解析管道

### 核心抽象

管道由多个 Step 串联，每个 Step 接收 `PipelineContext`，处理后传递给下一个 Step。

```python
class PipelineStep(ABC):
    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> PipelineContext: ...

class PipelineContext:
    raw_binary: bytes              # 原始文件内容
    content_type: str              # 文件类型
    sections: list[Section]        # 解析后段落
    chunks: list[Chunk]            # 切分后 chunk
    embeddings: list[list[float]]  # 向量数据
    metadata: dict                 # 管道元数据
```

### Pipeline 配置（JSON）

```json
{
    "name": "default",
    "steps": [
        {"type": "parse", "parser": "auto", "params": {}},
        {"type": "clean", "params": {"remove_html_tags": true, "normalize_whitespace": true}},
        {"type": "chunk", "strategy": "naive", "params": {"chunk_token_num": 512, "overlap": 50}},
        {"type": "embed", "model": "text-embedding-3-small", "params": {}},
        {"type": "store", "params": {}}
    ]
}
```

现阶段只有一个 `DefaultPipeline`。后续前端用 xyflow 拖拽编排 pipeline，后端保存 JSON 配置，worker 按配置执行。

### Content-Type → Parser 映射

| Content-Type | Parser |
|---|---|
| application/pdf | PdfParser |
| application/vnd.openxmlformats-officedocument.wordprocessingml.document | DocxParser |
| application/vnd.openxmlformats-officedocument.spreadsheetml.sheet | ExcelParser |
| application/vnd.openxmlformats-officedocument.presentationml.presentation | PptParser |
| text/markdown | MarkdownParser |
| text/html | HtmlParser |
| application/json | JsonParser |
| text/plain | TxtParser |

`parser: "auto"` 根据 content_type 自动选择。

### 管道步骤

1. **Parse**: 从 MinIO 下载文件 → 调用 ragflow parser → 输出 `sections`
2. **Clean**: 去除无效字符、规范化空白、去重段落
3. **Chunk**: 按 token 数量切分（默认 512 tokens, overlap 50）
4. **Embed**: 调用 LLM Embedding API → 输出向量
5. **Store**: 写入 Milvus（向量）+ MySQL（元数据）

## API 接口

### 创建解析任务

```
POST /api/v1/parse/tasks
Authorization: Bearer <jwt_token>
Body: { "kb_id": 7, "document_id": 42 }
Response: { "task_id": 1, "status": "pending" }
```

### 查询任务状态

```
GET /api/v1/parse/tasks/{task_id}
Authorization: Bearer <jwt_token>
Response: {
    "task_id": 1,
    "status": "running",
    "progress": 65,
    "error_message": null,
    "created_at": "...",
    "updated_at": "..."
}
```

### 查询知识库下任务列表

```
GET /api/v1/parse/tasks?kb_id=7&document_id=42
Authorization: Bearer <jwt_token>
Response: { "tasks": [...] }
```

### 取消任务

```
DELETE /api/v1/parse/tasks/{task_id}
Authorization: Bearer <jwt_token>
Response: { "message": "task cancelled" }
```

## 鉴权

复用 Go 服务的 JWT secret。FastAPI 中间件从 `Authorization: Bearer <token>` 提取 token，校验签名和过期时间，从 claims 中提取 user_id。

配置项：`PIVOT_JWT_SECRET` 环境变量，与 Go 服务共享。

## Worker 机制

- FastAPI 启动时（`lifespan` event）拉起后台 worker 线程
- Worker 每 2 秒轮询 `parse_tasks` 表中 `status = pending` 的任务
- 取到任务后：更新 status = running → 执行 pipeline → 更新 status = completed/failed
- 任何步骤失败：记录 error_message，status = failed

## 目录结构

```
src/
├── main.py                          # FastAPI 入口（已有，扩展）
├── config.yaml                      # 配置文件（新增）
├── core/
│   ├── config.py                    # 配置加载（重写：yaml + env 覆盖）
│   ├── security.py                  # JWT 校验（新增）
│   └── database.py                  # SQLAlchemy 配置（已有）
├── pipeline/
│   ├── __init__.py
│   ├── context.py                   # PipelineContext 定义
│   ├── base.py                      # PipelineStep 抽象基类
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── parser_step.py           # 文件解析（调度 ragflow parsers）
│   │   ├── clean_step.py            # 清洗/脱敏
│   │   ├── chunk_step.py            # Chunk 切分
│   │   ├── embed_step.py            # Embedding（调用 LLM API）
│   │   └── store_step.py            # 写入 Milvus + MySQL
│   ├── default_pipeline.py          # 默认管道编排
│   └── executor.py                  # 管道执行器
├── worker/
│   ├── __init__.py
│   ├── task_runner.py               # 后台 Worker 线程
│   └── task_manager.py              # 任务 CRUD
├── api/
│   ├── __init__.py
│   ├── router.py                    # 路由注册
│   ├── parse_task.py                # /api/v1/parse/tasks 端点
│   └── deps.py                      # 依赖注入
├── models/
│   ├── __init__.py
│   ├── parse_task.py                # ParseTask SQLAlchemy 模型
│   └── document_chunk.py            # DocumentChunk SQLAlchemy 模型
├── schemas/
│   ├── __init__.py
│   └── parse_task.py                # Pydantic 请求/响应模型
└── migrations/
    └── versions/
        └── 001_create_parse_tables.py
```

## 配置

与 Go 后端保持一致：`config.yaml` 配置文件 + `PIVOT_PARSE_` 前缀环境变量覆盖。优先级：环境变量 > 配置文件 > 默认值。

### config.yaml

```yaml
server:
  host: "0.0.0.0"
  port: 8000

db:
  url: "mysql+pymysql://pivot:pivot_pass_2026@localhost:3306/pivot"

log:
  level: "INFO"

jwt:
  secret: "pivot-dev-jwt-secret-2026-change-in-prod"

minio:
  endpoint: "localhost:9000"
  bucket: "pivot"
  access_key: "minioadmin"
  secret_key: "minioadmin"

milvus:
  uri: "./milvus.db"

embedding:
  model: "text-embedding-3-small"
  api_key: ""
  api_base: "https://api.openai.com/v1"
  dim: 1536
```

### 环境变量覆盖

配置文件路径通过 `PIVOT_PARSE_CONFIG` 环境变量指定，默认 `./config.yaml`。

| 环境变量 | 对应配置项 | 说明 |
|---|---|---|
| PIVOT_PARSE_CONFIG | - | 配置文件路径 |
| PIVOT_PARSE_SERVER_HOST | server.host | 服务地址 |
| PIVOT_PARSE_SERVER_PORT | server.port | 服务端口 |
| PIVOT_PARSE_DB_URL | db.url | 数据库连接串 |
| PIVOT_PARSE_JWT_SECRET | jwt.secret | JWT 密钥（与 Go 服务共享） |
| PIVOT_PARSE_MINIO_ENDPOINT | minio.endpoint | MinIO 地址 |
| PIVOT_PARSE_MINIO_ACCESS_KEY | minio.access_key | MinIO Access Key |
| PIVOT_PARSE_MINIO_SECRET_KEY | minio.secret_key | MinIO Secret Key |
| PIVOT_PARSE_MINIO_BUCKET | minio.bucket | MinIO Bucket |
| PIVOT_PARSE_MILVUS_URI | milvus.uri | Milvus Lite URI |
| PIVOT_PARSE_EMBEDDING_MODEL | embedding.model | Embedding 模型名 |
| PIVOT_PARSE_EMBEDDING_API_KEY | embedding.api_key | Embedding API Key |
| PIVOT_PARSE_EMBEDDING_API_BASE | embedding.api_base | Embedding API Base URL |
| PIVOT_PARSE_EMBEDDING_DIM | embedding.dim | Embedding 维度 |

### 实现方式

使用 `pydantic-settings` 的 YAML 支持加载 `config.yaml`，同时保留环境变量覆盖能力：

```python
class Settings(BaseSettings):
    server: ServerConfig
    db: DBConfig
    jwt: JWTConfig
    minio: MinIOConfig
    milvus: MilvusConfig
    embedding: EmbeddingConfig

    model_config = SettingsConfigDict(
        yaml_file=os.getenv("PIVOT_PARSE_CONFIG", "config.yaml"),
        env_prefix="PIVOT_PARSE_",
        env_nested_delimiter="__",
    )
```

敏感配置（jwt.secret、minio.access_key、minio.secret_key、embedding.api_key）优先从环境变量读取，配置文件中可留空。

## 实现阶段

### Phase 1（本次）：基础管道

- 任务表 + Worker 线程
- 默认 pipeline：parse → clean → chunk → embed → store
- ragflow 通用 Parser（auto detect by content_type）
- Milvus Lite 向量存储
- JWT 鉴权
- 前端：解析按钮 + 进度轮询

### Phase 2（后续）：自定义 Parser

- 支持用户自定义 Parser 配置
- Pipeline JSON 配置存数据库
- 前端 xyflow 工作流编排

### Phase 3（后续）：高级能力

- 重新解析（更新已有 chunk）
- 批量解析
- 解析结果预览
- 更多 Embedding 模型支持
