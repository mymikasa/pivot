# 数据解析 Python 后端实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现独立 FastAPI 数据解析服务，提供解析任务 API、JWT 鉴权、MySQL 任务表、后台 Worker 和默认 parse -> clean -> chunk -> embed -> store 管道。

**Architecture:** FastAPI 挂载 `/api/v1/parse/tasks`，API 只负责创建、查询、取消任务；后台 Worker 轮询 `parse_tasks` 并执行 Pipeline。Pipeline 的每个 Step 只读写 `PipelineContext`，外部依赖通过构造参数注入，便于单元测试。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic Settings, PyJWT, Alembic, pytest

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/config.yaml` | 解析服务默认配置 |
| `src/core/config.py` | 读取 `.env`、`config.yaml` 和 `PIVOT_PARSE_` 环境变量 |
| `src/core/security.py` | 校验 Go 服务签发的 JWT |
| `src/core/database.py` | SQLAlchemy engine、SessionLocal、Base、get_db |
| `src/models/parse_task.py` | `parse_tasks` SQLAlchemy 模型 |
| `src/models/document_chunk.py` | `document_chunks` SQLAlchemy 模型 |
| `src/schemas/parse_task.py` | 解析任务请求和响应模型 |
| `src/pipeline/context.py` | `PipelineContext`、`Section`、`Chunk` 数据结构 |
| `src/pipeline/base.py` | `PipelineStep` 抽象基类 |
| `src/pipeline/steps/parser_step.py` | 按 content type 解析原始文件 |
| `src/pipeline/steps/clean_step.py` | 规范化空白、去重段落 |
| `src/pipeline/steps/chunk_step.py` | 按 token 近似长度切分文本 |
| `src/pipeline/steps/embed_step.py` | 生成 embedding；无 API key 时生成确定性测试向量 |
| `src/pipeline/steps/store_step.py` | 写入 `document_chunks`；Milvus 缺省为可替换适配器 |
| `src/pipeline/default_pipeline.py` | 默认 Step 编排 |
| `src/pipeline/executor.py` | 执行 Pipeline 并上报进度 |
| `src/worker/task_manager.py` | 任务 CRUD 与状态流转 |
| `src/worker/task_runner.py` | 后台轮询 Worker |
| `src/api/deps.py` | FastAPI 依赖注入 |
| `src/api/parse_task.py` | 解析任务 API |
| `src/api/router.py` | API 路由注册 |
| `src/main.py` | FastAPI app、lifespan、CORS、路由挂载 |
| `migrations/versions/001_create_parse_tables.py` | 创建解析表迁移 |
| `tests/test_parse_task_api.py` | API 行为测试 |
| `tests/test_pipeline_steps.py` | Pipeline Step 单元测试 |
| `tests/test_task_manager.py` | 任务状态流转测试 |

---

### Task 1: 配置与数据库基础

**Files:**
- Modify: `src/core/config.py`
- Modify: `src/core/database.py`
- Create: `src/config.yaml`
- Test: `tests/test_config.py`

- [ ] **Step 1: 写配置测试**

在 `tests/test_config.py` 追加：

```python
from src.core.config import Settings


def test_settings_accepts_parse_service_values():
    settings = Settings(
        database_url="sqlite:///:memory:",
        server_port=8080,
        cors_origins=["http://localhost:5174"],
        jwt_secret_key="test-secret",
        minio_endpoint="localhost:9000",
        minio_bucket="pivot",
        embedding_dim=8,
    )

    assert settings.database_url == "sqlite:///:memory:"
    assert settings.jwt_secret_key == "test-secret"
    assert settings.minio_bucket == "pivot"
    assert settings.embedding_dim == 8
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_config.py -v`

Expected: FAIL，提示 `jwt_secret_key` 或 `minio_endpoint` 不是 `Settings` 字段。

- [ ] **Step 3: 扩展配置模块**

把 `src/core/config.py` 更新为包含这些字段：

```python
import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://pivot:pivot_pass_2026@localhost:3306/pivot"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: list[str] = Field(default_factory=list)
    log_level: str = "INFO"
    debug: bool = False

    jwt_secret_key: str = "pivot-dev-jwt-secret-2026-change-in-prod"
    jwt_algorithm: str = "HS256"

    minio_endpoint: str = "localhost:9000"
    minio_bucket: str = "pivot"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    milvus_uri: str = "./milvus.db"

    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_api_base: str = "https://api.openai.com/v1"
    embedding_dim: int = 1536

    worker_poll_interval_seconds: float = 2.0

    model_config = SettingsConfigDict(
        env_file=os.getenv("PIVOT_ENV_FILE", ".env.dev"),
        env_prefix="PIVOT_",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        allowed_prefixes = ("mysql+pymysql://", "sqlite:///")
        if not value.startswith(allowed_prefixes):
            raise ValueError("database_url 必须以 mysql+pymysql:// 或 sqlite:/// 开头")
        return value

    @field_validator("server_port")
    @classmethod
    def validate_server_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("server_port 必须在 1-65535 范围内")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized_value = value.upper()
        if normalized_value not in VALID_LOG_LEVELS:
            raise ValueError("log_level 必须是 DEBUG、INFO、WARNING、ERROR 或 CRITICAL")
        return normalized_value

    @field_validator("embedding_dim")
    @classmethod
    def validate_embedding_dim(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("embedding_dim 必须大于 0")
        return value


settings = Settings()
```

- [ ] **Step 4: 新增默认 YAML 示例**

创建 `src/config.yaml`：

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

- [ ] **Step 5: 运行测试确认通过**

Run: `uv run pytest tests/test_config.py -v`

Expected: PASS。

---

### Task 2: SQLAlchemy 模型与迁移

**Files:**
- Create: `src/models/parse_task.py`
- Create: `src/models/document_chunk.py`
- Modify: `src/models/__init__.py`
- Create: `migrations/versions/001_create_parse_tables.py`
- Test: `tests/test_parse_models.py`

- [ ] **Step 1: 写模型测试**

创建 `tests/test_parse_models.py`：

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.database import Base
from src.models.document_chunk import DocumentChunk
from src.models.parse_task import ParseTask, ParseTaskStatus


def test_parse_task_and_chunk_models_can_persist():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    task = ParseTask(
        kb_id=7,
        document_id=42,
        object_key="7/demo.txt",
        content_type="text/plain",
        status=ParseTaskStatus.PENDING.value,
    )
    session.add(task)
    session.commit()

    chunk = DocumentChunk(
        kb_id=7,
        document_id=42,
        chunk_index=0,
        content="hello pivot",
        token_count=2,
        milvus_id=1001,
    )
    session.add(chunk)
    session.commit()

    assert task.id is not None
    assert chunk.id is not None
    assert session.query(ParseTask).count() == 1
    assert session.query(DocumentChunk).count() == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_parse_models.py -v`

Expected: FAIL，提示模型模块不存在。

- [ ] **Step 3: 新增 `ParseTask` 模型**

创建 `src/models/parse_task.py`：

```python
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ParseTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ParseTask(Base):
    __tablename__ = "parse_tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 4: 新增 `DocumentChunk` 模型**

创建 `src/models/document_chunk.py`：

```python
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    milvus_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
```

- [ ] **Step 5: 导出模型**

更新 `src/models/__init__.py`：

```python
from src.models.document_chunk import DocumentChunk
from src.models.parse_task import ParseTask, ParseTaskStatus

__all__ = ["DocumentChunk", "ParseTask", "ParseTaskStatus"]
```

- [ ] **Step 6: 新增 Alembic 迁移**

创建 `migrations/versions/001_create_parse_tables.py`：

```python
"""create parse tables

Revision ID: 001_create_parse_tables
Revises: 8c72d27bacbf
Create Date: 2026-05-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001_create_parse_tables"
down_revision: Union[str, Sequence[str], None] = "8c72d27bacbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parse_tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kb_id", sa.BigInteger(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parse_tasks_status", "parse_tasks", ["status"])
    op.create_index("ix_parse_tasks_kb_id", "parse_tasks", ["kb_id"])
    op.create_index("ix_parse_tasks_document_id", "parse_tasks", ["document_id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kb_id", sa.BigInteger(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("milvus_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_chunks_kb_id", "document_chunks", ["kb_id"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_kb_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_parse_tasks_document_id", table_name="parse_tasks")
    op.drop_index("ix_parse_tasks_kb_id", table_name="parse_tasks")
    op.drop_index("ix_parse_tasks_status", table_name="parse_tasks")
    op.drop_table("parse_tasks")
```

- [ ] **Step 7: 运行测试确认通过**

Run: `uv run pytest tests/test_parse_models.py -v`

Expected: PASS。

---

### Task 3: JWT 鉴权

**Files:**
- Create: `src/core/security.py`
- Create: `src/api/deps.py`
- Test: `tests/test_parse_security.py`

- [ ] **Step 1: 写鉴权测试**

创建 `tests/test_parse_security.py`：

```python
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from src.core.security import AuthenticatedUser, decode_access_token


def test_decode_access_token_returns_user():
    token = jwt.encode(
        {
            "sub": "123",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "test-secret",
        algorithm="HS256",
    )

    user = decode_access_token(token, secret="test-secret", algorithm="HS256")

    assert user == AuthenticatedUser(user_id=123, role="admin")


def test_decode_access_token_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc:
        decode_access_token("bad.token", secret="test-secret", algorithm="HS256")

    assert exc.value.status_code == 401
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_parse_security.py -v`

Expected: FAIL，提示 `src.core.security` 不存在。

- [ ] **Step 3: 实现 `src/core/security.py`**

```python
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, status


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    role: str


def decode_access_token(
    token: str,
    *,
    secret: str,
    algorithm: str,
) -> AuthenticatedUser:
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        subject = payload.get("sub")
        if subject is None:
            raise ValueError("missing sub")
        return AuthenticatedUser(
            user_id=int(subject),
            role=str(payload.get("role", "user")),
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的访问令牌",
        ) from exc
```

- [ ] **Step 4: 实现依赖注入**

创建 `src/api/deps.py`：

```python
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import settings
from src.core.database import get_db
from src.core.security import AuthenticatedUser, decode_access_token


bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> AuthenticatedUser:
    return decode_access_token(
        credentials.credentials,
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


__all__ = ["get_current_user", "get_db"]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `uv run pytest tests/test_parse_security.py -v`

Expected: PASS。

---

### Task 4: Pipeline Context 与基础 Step

**Files:**
- Create: `src/pipeline/__init__.py`
- Create: `src/pipeline/context.py`
- Create: `src/pipeline/base.py`
- Create: `src/pipeline/steps/__init__.py`
- Create: `src/pipeline/steps/clean_step.py`
- Create: `src/pipeline/steps/chunk_step.py`
- Test: `tests/test_pipeline_steps.py`

- [ ] **Step 1: 写 Step 测试**

创建 `tests/test_pipeline_steps.py`：

```python
import pytest

from src.pipeline.context import PipelineContext, Section
from src.pipeline.steps.chunk_step import ChunkStep
from src.pipeline.steps.clean_step import CleanStep


@pytest.mark.asyncio
async def test_clean_step_normalizes_and_deduplicates_sections():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        sections=[
            Section(text=" hello   world "),
            Section(text="hello world"),
            Section(text="second\n\nparagraph"),
        ],
    )

    result = await CleanStep().execute(ctx)

    assert [section.text for section in result.sections] == [
        "hello world",
        "second paragraph",
    ]


@pytest.mark.asyncio
async def test_chunk_step_splits_text_with_overlap():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        sections=[Section(text="one two three four five six")],
    )

    result = await ChunkStep(chunk_token_num=3, overlap=1).execute(ctx)

    assert [chunk.content for chunk in result.chunks] == [
        "one two three",
        "three four five",
        "five six",
    ]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_pipeline_steps.py -v`

Expected: FAIL，提示 pipeline 模块不存在。

- [ ] **Step 3: 新增 Context**

创建 `src/pipeline/context.py`：

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Section:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    index: int
    content: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineContext:
    kb_id: int
    document_id: int
    object_key: str
    content_type: str
    raw_binary: bytes
    sections: list[Section] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: 新增 Step 抽象**

创建 `src/pipeline/base.py`：

```python
from abc import ABC, abstractmethod

from src.pipeline.context import PipelineContext


class PipelineStep(ABC):
    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        raise NotImplementedError
```

- [ ] **Step 5: 实现 CleanStep**

创建 `src/pipeline/steps/clean_step.py`：

```python
import re

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext, Section


class CleanStep(PipelineStep):
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        seen: set[str] = set()
        cleaned_sections: list[Section] = []

        for section in ctx.sections:
            text = re.sub(r"\s+", " ", section.text).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned_sections.append(Section(text=text, metadata=section.metadata))

        ctx.sections = cleaned_sections
        return ctx
```

- [ ] **Step 6: 实现 ChunkStep**

创建 `src/pipeline/steps/chunk_step.py`：

```python
from src.pipeline.base import PipelineStep
from src.pipeline.context import Chunk, PipelineContext


class ChunkStep(PipelineStep):
    def __init__(self, chunk_token_num: int = 512, overlap: int = 50) -> None:
        if chunk_token_num <= 0:
            raise ValueError("chunk_token_num 必须大于 0")
        if overlap < 0 or overlap >= chunk_token_num:
            raise ValueError("overlap 必须大于等于 0 且小于 chunk_token_num")
        self.chunk_token_num = chunk_token_num
        self.overlap = overlap

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        chunks: list[Chunk] = []
        step_size = self.chunk_token_num - self.overlap

        for section in ctx.sections:
            tokens = section.text.split()
            for start in range(0, len(tokens), step_size):
                window = tokens[start : start + self.chunk_token_num]
                if not window:
                    continue
                chunks.append(
                    Chunk(
                        index=len(chunks),
                        content=" ".join(window),
                        token_count=len(window),
                        metadata=section.metadata,
                    )
                )

        ctx.chunks = chunks
        return ctx
```

- [ ] **Step 7: 创建包标记文件**

创建空文件：

```text
src/pipeline/__init__.py
src/pipeline/steps/__init__.py
```

- [ ] **Step 8: 运行测试确认通过**

Run: `uv run pytest tests/test_pipeline_steps.py -v`

Expected: PASS。

---

### Task 5: Parser、Embedding 与 Store Step

**Files:**
- Create: `src/pipeline/steps/parser_step.py`
- Create: `src/pipeline/steps/embed_step.py`
- Create: `src/pipeline/steps/store_step.py`
- Test: `tests/test_pipeline_io_steps.py`

- [ ] **Step 1: 写 IO Step 测试**

创建 `tests/test_pipeline_io_steps.py`：

```python
import pytest

from src.pipeline.context import Chunk, PipelineContext
from src.pipeline.steps.embed_step import EmbedStep
from src.pipeline.steps.parser_step import ParserStep
from src.pipeline.steps.store_step import StoreStep


@pytest.mark.asyncio
async def test_parser_step_parses_plain_text():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary="第一段\n\n第二段".encode(),
    )

    result = await ParserStep().execute(ctx)

    assert [section.text for section in result.sections] == ["第一段", "第二段"]


@pytest.mark.asyncio
async def test_embed_step_generates_deterministic_vectors():
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        chunks=[Chunk(index=0, content="hello", token_count=1)],
    )

    result = await EmbedStep(api_key="", dim=4).execute(ctx)

    assert len(result.embeddings) == 1
    assert len(result.embeddings[0]) == 4
    assert result.embeddings[0] == await EmbedStep(api_key="", dim=4).embed_text("hello")


@pytest.mark.asyncio
async def test_store_step_persists_chunks(db):
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
        chunks=[Chunk(index=0, content="hello", token_count=1)],
        embeddings=[[0.1, 0.2, 0.3, 0.4]],
    )

    result = await StoreStep(db).execute(ctx)

    assert result.metadata["stored_chunks"] == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_pipeline_io_steps.py -v`

Expected: FAIL，提示 Step 模块不存在。

- [ ] **Step 3: 实现 ParserStep**

创建 `src/pipeline/steps/parser_step.py`：

```python
import json
from html.parser import HTMLParser
from typing import Any

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext, Section


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


class ParserStep(PipelineStep):
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        text = self._to_text(ctx.raw_binary, ctx.content_type)
        ctx.sections = [
            Section(text=part.strip())
            for part in text.splitlines()
            if part.strip()
        ]
        return ctx

    def _to_text(self, raw_binary: bytes, content_type: str) -> str:
        if content_type == "application/json":
            data: Any = json.loads(raw_binary.decode("utf-8"))
            return json.dumps(data, ensure_ascii=False, indent=2)
        if content_type == "text/html":
            parser = _TextExtractor()
            parser.feed(raw_binary.decode("utf-8", errors="ignore"))
            return "\n".join(parser.parts)
        return raw_binary.decode("utf-8", errors="ignore")
```

- [ ] **Step 4: 实现 EmbedStep**

创建 `src/pipeline/steps/embed_step.py`：

```python
import hashlib
import random

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext


class EmbedStep(PipelineStep):
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        api_base: str = "https://api.openai.com/v1",
        dim: int = 1536,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.dim = dim

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        ctx.embeddings = [await self.embed_text(chunk.content) for chunk in ctx.chunks]
        return ctx

    async def embed_text(self, text: str) -> list[float]:
        if not self.api_key:
            seed = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
            rng = random.Random(seed)
            return [rng.uniform(-1.0, 1.0) for _ in range(self.dim)]
        raise RuntimeError("远程 embedding 调用将在接入 OpenAI SDK 后启用")
```

- [ ] **Step 5: 实现 StoreStep**

创建 `src/pipeline/steps/store_step.py`：

```python
from sqlalchemy.orm import Session

from src.models.document_chunk import DocumentChunk
from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext


class StoreStep(PipelineStep):
    def __init__(self, db: Session) -> None:
        self.db = db

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        self.db.query(DocumentChunk).filter(
            DocumentChunk.kb_id == ctx.kb_id,
            DocumentChunk.document_id == ctx.document_id,
        ).delete()

        for chunk in ctx.chunks:
            self.db.add(
                DocumentChunk(
                    kb_id=ctx.kb_id,
                    document_id=ctx.document_id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    milvus_id=None,
                )
            )
        self.db.commit()
        ctx.metadata["stored_chunks"] = len(ctx.chunks)
        return ctx
```

- [ ] **Step 6: 运行测试确认通过**

Run: `uv run pytest tests/test_pipeline_io_steps.py -v`

Expected: PASS。

---

### Task 6: Pipeline Executor 与默认编排

**Files:**
- Create: `src/pipeline/default_pipeline.py`
- Create: `src/pipeline/executor.py`
- Test: `tests/test_pipeline_executor.py`

- [ ] **Step 1: 写 Executor 测试**

创建 `tests/test_pipeline_executor.py`：

```python
import pytest

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext, Section
from src.pipeline.executor import PipelineExecutor


class AppendStep(PipelineStep):
    def __init__(self, text: str) -> None:
        self.text = text

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        ctx.sections.append(Section(text=self.text))
        return ctx


@pytest.mark.asyncio
async def test_executor_runs_steps_and_reports_progress():
    progress: list[int] = []
    ctx = PipelineContext(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
        raw_binary=b"",
    )
    executor = PipelineExecutor([AppendStep("a"), AppendStep("b")])

    result = await executor.execute(ctx, on_progress=progress.append)

    assert [section.text for section in result.sections] == ["a", "b"]
    assert progress == [50, 100]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_pipeline_executor.py -v`

Expected: FAIL，提示 `PipelineExecutor` 不存在。

- [ ] **Step 3: 实现 Executor**

创建 `src/pipeline/executor.py`：

```python
from collections.abc import Callable

from src.pipeline.base import PipelineStep
from src.pipeline.context import PipelineContext


class PipelineExecutor:
    def __init__(self, steps: list[PipelineStep]) -> None:
        self.steps = steps

    async def execute(
        self,
        ctx: PipelineContext,
        on_progress: Callable[[int], None] | None = None,
    ) -> PipelineContext:
        total = len(self.steps)
        for index, step in enumerate(self.steps, start=1):
            ctx = await step.execute(ctx)
            if on_progress is not None:
                on_progress(int(index / total * 100))
        return ctx
```

- [ ] **Step 4: 实现默认 Pipeline 工厂**

创建 `src/pipeline/default_pipeline.py`：

```python
from sqlalchemy.orm import Session

from src.core.config import settings
from src.pipeline.executor import PipelineExecutor
from src.pipeline.steps.chunk_step import ChunkStep
from src.pipeline.steps.clean_step import CleanStep
from src.pipeline.steps.embed_step import EmbedStep
from src.pipeline.steps.parser_step import ParserStep
from src.pipeline.steps.store_step import StoreStep


def build_default_pipeline(db: Session) -> PipelineExecutor:
    return PipelineExecutor(
        [
            ParserStep(),
            CleanStep(),
            ChunkStep(chunk_token_num=512, overlap=50),
            EmbedStep(
                api_key=settings.embedding_api_key,
                model=settings.embedding_model,
                api_base=settings.embedding_api_base,
                dim=settings.embedding_dim,
            ),
            StoreStep(db),
        ]
    )
```

- [ ] **Step 5: 运行测试确认通过**

Run: `uv run pytest tests/test_pipeline_executor.py -v`

Expected: PASS。

---

### Task 7: Task Manager

**Files:**
- Create: `src/worker/__init__.py`
- Create: `src/worker/task_manager.py`
- Test: `tests/test_task_manager.py`

- [ ] **Step 1: 写任务管理测试**

创建 `tests/test_task_manager.py`：

```python
from src.models.parse_task import ParseTaskStatus
from src.worker.task_manager import TaskManager


def test_task_manager_creates_and_lists_tasks(db):
    manager = TaskManager(db)

    task = manager.create_task(
        kb_id=7,
        document_id=42,
        object_key="7/demo.txt",
        content_type="text/plain",
    )

    assert task.id is not None
    assert task.status == ParseTaskStatus.PENDING.value
    assert manager.list_tasks(kb_id=7, document_id=42)[0].id == task.id


def test_task_manager_claims_next_pending_task(db):
    manager = TaskManager(db)
    created = manager.create_task(
        kb_id=7,
        document_id=42,
        object_key="7/demo.txt",
        content_type="text/plain",
    )

    claimed = manager.claim_next_pending_task()

    assert claimed is not None
    assert claimed.id == created.id
    assert claimed.status == ParseTaskStatus.RUNNING.value
    assert claimed.progress == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_task_manager.py -v`

Expected: FAIL，提示 `TaskManager` 不存在。

- [ ] **Step 3: 实现 TaskManager**

创建 `src/worker/task_manager.py`：

```python
from sqlalchemy.orm import Session

from src.models.parse_task import ParseTask, ParseTaskStatus


class TaskManager:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_task(
        self,
        *,
        kb_id: int,
        document_id: int,
        object_key: str,
        content_type: str,
    ) -> ParseTask:
        task = ParseTask(
            kb_id=kb_id,
            document_id=document_id,
            object_key=object_key,
            content_type=content_type,
            status=ParseTaskStatus.PENDING.value,
            progress=0,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, task_id: int) -> ParseTask | None:
        return self.db.get(ParseTask, task_id)

    def list_tasks(
        self,
        *,
        kb_id: int | None = None,
        document_id: int | None = None,
    ) -> list[ParseTask]:
        query = self.db.query(ParseTask)
        if kb_id is not None:
            query = query.filter(ParseTask.kb_id == kb_id)
        if document_id is not None:
            query = query.filter(ParseTask.document_id == document_id)
        return query.order_by(ParseTask.id.desc()).all()

    def claim_next_pending_task(self) -> ParseTask | None:
        task = (
            self.db.query(ParseTask)
            .filter(ParseTask.status == ParseTaskStatus.PENDING.value)
            .order_by(ParseTask.id.asc())
            .first()
        )
        if task is None:
            return None
        task.status = ParseTaskStatus.RUNNING.value
        task.progress = 0
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_progress(self, task_id: int, progress: int) -> None:
        task = self.db.get(ParseTask, task_id)
        if task is None:
            return
        task.progress = max(0, min(100, progress))
        self.db.commit()

    def complete_task(self, task_id: int) -> None:
        task = self.db.get(ParseTask, task_id)
        if task is None:
            return
        task.status = ParseTaskStatus.COMPLETED.value
        task.progress = 100
        self.db.commit()

    def fail_task(self, task_id: int, message: str) -> None:
        task = self.db.get(ParseTask, task_id)
        if task is None:
            return
        task.status = ParseTaskStatus.FAILED.value
        task.error_message = message
        self.db.commit()

    def cancel_task(self, task_id: int) -> bool:
        task = self.db.get(ParseTask, task_id)
        if task is None or task.status == ParseTaskStatus.RUNNING.value:
            return False
        task.status = ParseTaskStatus.CANCELLED.value
        self.db.commit()
        return True
```

- [ ] **Step 4: 创建包标记文件**

创建空文件：

```text
src/worker/__init__.py
```

- [ ] **Step 5: 运行测试确认通过**

Run: `uv run pytest tests/test_task_manager.py -v`

Expected: PASS。

---

### Task 8: Worker Runner

**Files:**
- Create: `src/worker/task_runner.py`
- Test: `tests/test_task_runner.py`

- [ ] **Step 1: 写 Worker 测试**

创建 `tests/test_task_runner.py`：

```python
from src.models.parse_task import ParseTaskStatus
from src.worker.task_manager import TaskManager
from src.worker.task_runner import run_one_task


def test_run_one_task_completes_pending_task(db):
    manager = TaskManager(db)
    task = manager.create_task(
        kb_id=1,
        document_id=2,
        object_key="1/a.txt",
        content_type="text/plain",
    )

    def download(_object_key: str) -> bytes:
        return b"hello pivot"

    ran = run_one_task(db, download_file=download)

    refreshed = manager.get_task(task.id)
    assert ran is True
    assert refreshed is not None
    assert refreshed.status == ParseTaskStatus.COMPLETED.value
    assert refreshed.progress == 100
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_task_runner.py -v`

Expected: FAIL，提示 `run_one_task` 不存在。

- [ ] **Step 3: 实现 Worker 单次执行与循环**

创建 `src/worker/task_runner.py`：

```python
import asyncio
import logging
import threading
import time
from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings
from src.pipeline.context import PipelineContext
from src.pipeline.default_pipeline import build_default_pipeline
from src.worker.task_manager import TaskManager

logger = logging.getLogger(__name__)


def default_download_file(object_key: str) -> bytes:
    raise RuntimeError(f"尚未配置 MinIO 下载客户端，无法下载 {object_key}")


def run_one_task(
    db: Session,
    *,
    download_file: Callable[[str], bytes] = default_download_file,
) -> bool:
    manager = TaskManager(db)
    task = manager.claim_next_pending_task()
    if task is None:
        return False

    try:
        raw_binary = download_file(task.object_key)
        ctx = PipelineContext(
            kb_id=task.kb_id,
            document_id=task.document_id,
            object_key=task.object_key,
            content_type=task.content_type,
            raw_binary=raw_binary,
        )
        pipeline = build_default_pipeline(db)
        asyncio.run(
            pipeline.execute(
                ctx,
                on_progress=lambda progress: manager.update_progress(task.id, progress),
            )
        )
        manager.complete_task(task.id)
        return True
    except Exception as exc:
        logger.exception("解析任务执行失败", extra={"task_id": task.id})
        manager.fail_task(task.id, str(exc))
        return True


class ParseTaskWorker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        poll_interval_seconds: float = settings.worker_poll_interval_seconds,
    ) -> None:
        self.session_factory = session_factory
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            with self.session_factory() as db:
                did_work = run_one_task(db)
            if not did_work:
                time.sleep(self.poll_interval_seconds)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_task_runner.py -v`

Expected: PASS。

---

### Task 9: 解析任务 API

**Files:**
- Create: `src/schemas/parse_task.py`
- Create: `src/api/__init__.py`
- Create: `src/api/parse_task.py`
- Create: `src/api/router.py`
- Modify: `src/main.py`
- Test: `tests/test_parse_task_api.py`

- [ ] **Step 1: 写 API 测试**

创建 `tests/test_parse_task_api.py`：

```python
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from src.core.config import settings
from src.core.database import Base, get_db
from src.main import app
from tests.conftest import TestingSessionLocal, engine


def auth_headers() -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": "1",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_and_get_parse_task():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.post(
        "/api/v1/parse/tasks",
        json={
            "kb_id": 7,
            "document_id": 42,
            "object_key": "7/demo.txt",
            "content_type": "text/plain",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"

    detail = client.get(
        f"/api/v1/parse/tasks/{data['task_id']}",
        headers=auth_headers(),
    )
    assert detail.status_code == 200
    assert detail.json()["task_id"] == data["task_id"]

    app.dependency_overrides.clear()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_parse_task_api.py -v`

Expected: FAIL，提示路由不存在或 schema 不存在。

- [ ] **Step 3: 创建 Schema**

创建 `src/schemas/parse_task.py`：

```python
from datetime import datetime

from pydantic import BaseModel, Field


class CreateParseTaskRequest(BaseModel):
    kb_id: int = Field(gt=0)
    document_id: int = Field(gt=0)
    object_key: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=128)


class CreateParseTaskResponse(BaseModel):
    task_id: int
    status: str


class ParseTaskResponse(BaseModel):
    task_id: int
    kb_id: int
    document_id: int
    status: str
    progress: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ListParseTasksResponse(BaseModel):
    tasks: list[ParseTaskResponse]
```

- [ ] **Step 4: 创建 API 路由**

创建 `src/api/parse_task.py`：

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.core.security import AuthenticatedUser
from src.models.parse_task import ParseTask
from src.schemas.parse_task import (
    CreateParseTaskRequest,
    CreateParseTaskResponse,
    ListParseTasksResponse,
    ParseTaskResponse,
)
from src.worker.task_manager import TaskManager

router = APIRouter(prefix="/parse/tasks", tags=["parse"])


def to_response(task: ParseTask) -> ParseTaskResponse:
    return ParseTaskResponse(
        task_id=task.id,
        kb_id=task.kb_id,
        document_id=task.document_id,
        status=task.status,
        progress=task.progress,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post("", response_model=CreateParseTaskResponse)
def create_parse_task(
    body: CreateParseTaskRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CreateParseTaskResponse:
    task = TaskManager(db).create_task(
        kb_id=body.kb_id,
        document_id=body.document_id,
        object_key=body.object_key,
        content_type=body.content_type,
    )
    return CreateParseTaskResponse(task_id=task.id, status=task.status)


@router.get("", response_model=ListParseTasksResponse)
def list_parse_tasks(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    kb_id: Annotated[int | None, Query(gt=0)] = None,
    document_id: Annotated[int | None, Query(gt=0)] = None,
) -> ListParseTasksResponse:
    tasks = TaskManager(db).list_tasks(kb_id=kb_id, document_id=document_id)
    return ListParseTasksResponse(tasks=[to_response(task) for task in tasks])


@router.get("/{task_id}", response_model=ParseTaskResponse)
def get_parse_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ParseTaskResponse:
    task = TaskManager(db).get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return to_response(task)


@router.delete("/{task_id}")
def cancel_parse_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict[str, str]:
    if not TaskManager(db).cancel_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="任务不存在或正在运行，无法取消",
        )
    return {"message": "task cancelled"}
```

- [ ] **Step 5: 注册 API Router**

创建 `src/api/router.py`：

```python
from fastapi import APIRouter

from src.api.parse_task import router as parse_task_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(parse_task_router)
```

创建空文件：

```text
src/api/__init__.py
```

- [ ] **Step 6: 挂载到 app**

更新 `src/main.py`：

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.core.config import settings
from src.core.database import SessionLocal
from src.worker.task_runner import ParseTaskWorker

logging.basicConfig(level=settings.log_level)

worker = ParseTaskWorker(SessionLocal)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.debug:
        worker.start()
    yield
    worker.stop()


app = FastAPI(title="Pivot Parse Service", version="0.1.0", debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
```

- [ ] **Step 7: 运行 API 测试确认通过**

Run: `uv run pytest tests/test_parse_task_api.py -v`

Expected: PASS。

---

### Task 10: 全量后端验证

**Files:**
- Modify only if verification reveals failures in files touched by this plan.

- [ ] **Step 1: 运行 Python 测试**

Run: `uv run pytest -v`

Expected: 所有 Python 测试通过。

- [ ] **Step 2: 运行格式检查**

Run: `uv run python -m compileall src tests`

Expected: exit 0。

- [ ] **Step 3: 检查 Git diff**

Run: `git diff -- src tests migrations`

Expected: 只包含本计划涉及的 Python 解析服务、测试和迁移改动。

