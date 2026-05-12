# 知识库功能设计文档（修订版）

## 概述

为 Pivot 平台新增「知识库」功能，支持知识库 CRUD 和文档上传管理。后端使用 Go gRPC 独立服务实现，文件存储使用 MinIO。

### MVP 范围

- 知识库元数据管理（创建、查看、编辑、删除）
- 文档上传到知识库（存储到 MinIO）
- 文档列表查看、下载、删除

### 不在范围内

- 文档解析与分块
- 向量化与存储
- 检索与 RAG 对话

## 需求总结

| 项目 | 决策 |
|---|---|
| 后端实现 | Go gRPC 独立服务（`backend/app/kb/`） |
| 文件存储 | MinIO（S3 兼容），docker-compose 新增服务 |
| 支持文件类型 | Office/PDF、纯文本（TXT/MD）、结构化数据（CSV/JSON） |
| 单文件大小限制 | 10MB |
| 权限模型 | 用户私有 + 管理员全局（普通用户管理自己的，管理员管理所有） |
| 知识库名称 | 全局唯一 |
| 前端方案 | 沿用原设计，React + Radix UI + Tailwind CSS |

## 架构

| 层 | 方案 |
|---|---|
| 后端 | `backend/app/kb/` — 独立 Go 服务，gRPC + grpc-gateway |
| 存储 | MinIO，Go SDK `minio/minio-go/v7` |
| 前端 | React，新增 `/kb` 和 `/kb/$kbId` 路由 |
| 数据库 | MySQL，新增 `knowledge_bases` + `documents` 表 |
| 鉴权 | 复用 `pkg/jwt`，interceptor + 白名单 |

## 数据模型

### `knowledge_bases` 表

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGINT UNSIGNED | PK, 自增 | 主键 |
| `name` | VARCHAR(128) | NOT NULL, UNIQUE | 知识库名称（全局唯一） |
| `description` | TEXT | nullable | 知识库描述 |
| `owner_id` | BIGINT UNSIGNED | NOT NULL, FK → users.id | 创建者 |
| `created_at` | DATETIME | NOT NULL | 创建时间 |
| `updated_at` | DATETIME | NOT NULL, 自动更新 | 更新时间 |

### `documents` 表

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGINT UNSIGNED | PK, 自增 | 主键 |
| `kb_id` | BIGINT UNSIGNED | FK → knowledge_bases.id, ON DELETE CASCADE | 所属知识库 |
| `filename` | VARCHAR(255) | NOT NULL | 原始文件名 |
| `object_key` | VARCHAR(512) | NOT NULL, UNIQUE | MinIO 中的对象键 |
| `content_type` | VARCHAR(128) | NOT NULL | MIME 类型 |
| `file_size` | INT UNSIGNED | NOT NULL | 文件大小（字节） |
| `status` | ENUM('uploading','ready','error') | NOT NULL, 默认 'uploading' | 文档状态 |
| `created_at` | DATETIME | NOT NULL | 上传时间 |

### 对象键格式

```
{kb_id}/{uuid}.{ext}
```

使用 UUID 避免文件名冲突。

## Proto 定义

文件位置：`backend/api/proto/kb/v1/kb.proto`

```protobuf
syntax = "proto3";
package pivot.kb.v1;

import "google/api/annotations.proto";
import "google/protobuf/empty.proto";
import "google/protobuf/timestamp.proto";

message KnowledgeBase {
  int64 id = 1;
  string name = 2;
  string description = 3;
  int64 owner_id = 4;
  int32 document_count = 5;
  google.protobuf.Timestamp created_at = 6;
  google.protobuf.Timestamp updated_at = 7;
}

message Document {
  int64 id = 1;
  int64 kb_id = 2;
  string filename = 3;
  string content_type = 4;
  int32 file_size = 5;
  string status = 6;
  google.protobuf.Timestamp created_at = 7;
}

// --- 知识库管理 ---

message CreateKBRequest {
  string name = 1;
  string description = 2;
}

message ListKBRequest {}
message ListKBResponse { repeated KnowledgeBase items = 1; }

message GetKBRequest { int64 id = 1; }
message KBResponse { KnowledgeBase kb = 1; }

message UpdateKBRequest {
  int64 id = 1;
  string name = 2;
  string description = 3;
}

message DeleteKBRequest { int64 id = 1; }

// --- 文档管理 ---

message UploadDocumentRequest {
  int64 kb_id = 1;
  string filename = 2;
  string content_type = 3;
  bytes data = 4;
}

message DocumentResponse { Document document = 1; }

message ListDocumentsRequest { int64 kb_id = 1; }
message ListDocumentsResponse { repeated Document items = 1; }

message DeleteDocumentRequest {
  int64 kb_id = 1;
  int64 doc_id = 2;
}

message DownloadDocumentRequest {
  int64 kb_id = 1;
  int64 doc_id = 2;
}

message DownloadDocumentResponse {
  string filename = 1;
  string content_type = 2;
  bytes data = 3;
}

service KnowledgeBaseService {
  // 知识库 CRUD
  rpc CreateKnowledgeBase(CreateKBRequest) returns (KBResponse) {
    option (google.api.http) = { post: "/api/v1/kb" };
  }
  rpc ListKnowledgeBases(ListKBRequest) returns (ListKBResponse) {
    option (google.api.http) = { get: "/api/v1/kb" };
  }
  rpc GetKnowledgeBase(GetKBRequest) returns (KBResponse) {
    option (google.api.http) = { get: "/api/v1/kb/{id}" };
  }
  rpc UpdateKnowledgeBase(UpdateKBRequest) returns (KBResponse) {
    option (google.api.http) = { post: "/api/v1/kb/{id}/update" };
  }
  rpc DeleteKnowledgeBase(DeleteKBRequest) returns (google.protobuf.Empty) {
    option (google.api.http) = { post: "/api/v1/kb/{id}/delete" };
  }

  // 文档管理
  rpc UploadDocument(stream UploadDocumentRequest) returns (DocumentResponse);
  rpc ListDocuments(ListDocumentsRequest) returns (ListDocumentsResponse) {
    option (google.api.http) = { get: "/api/v1/kb/{kb_id}/documents" };
  }
  rpc DeleteDocument(DeleteDocumentRequest) returns (google.protobuf.Empty) {
    option (google.api.http) = { post: "/api/v1/kb/{kb_id}/documents/{doc_id}/delete" };
  }
  rpc DownloadDocument(DownloadDocumentRequest) returns (stream DownloadDocumentResponse);
}
```

> 文件上传/下载走 gRPC streaming。grpc-gateway 不直接支持 streaming，前端可通过 gRPC-web 客户端调用，或额外暴露一个 HTTP multipart 上传端点。

## Go 服务结构

```
backend/app/kb/
├── cmd/
│   ├── main.go              # 启动 gRPC + HTTP gateway
│   ├── wire.go              # Wire 注入定义
│   └── wire_gen.go          # Wire 生成
├── domain/
│   ├── knowledge_base.go    # KnowledgeBase 实体
│   ├── document.go          # Document 实体
│   └── errors.go            # 领域错误
├── service/
│   ├── kb.go                # KBService
│   ├── document.go          # DocumentService
│   └── types.go             # Service 接口
├── repository/
│   ├── kb.go                # KBRepository
│   ├── document.go          # DocumentRepository
│   ├── types.go             # Repository 接口
│   └── dao/
│       ├── kb.go            # KnowledgeBaseDAO（GORM）
│       ├── document.go      # DocumentDAO（GORM）
│       └── types.go         # DAO 接口
├── grpc/
│   ├── kb.go                # KnowledgeBaseServer
│   └── errors.go            # domain error → gRPC status 映射
├── ioc/
│   ├── app.go               # App struct
│   ├── config.go            # Config + Viper
│   ├── db.go                # GORM MySQL
│   ├── grpc.go              # gRPC Server + JWT 拦截器
│   ├── gateway.go           # grpc-gateway HTTP 代理
│   ├── jwt.go               # JWT Verifier 初始化
│   ├── minio.go             # MinIO 客户端初始化
│   ├── logger.go            # slog JSON logger
│   └── providers.go         # Wire ProviderSet
├── config.yaml
└── Makefile
```

### 共享包

`backend/pkg/storage/` — MinIO 存储封装，跨服务可复用：

| 方法 | 说明 |
|---|---|
| `Upload(bucket, key, reader, size, contentType)` | 上传文件 |
| `Download(bucket, key)` | 下载文件，返回 io.ReadCloser |
| `Delete(bucket, key)` | 删除单个对象 |
| `DeletePrefix(bucket, prefix)` | 按前缀批量删除 |
| `EnsureBucket(bucket)` | 确保 Bucket 存在 |

## 权限

- JWT interceptor 复用 `pkg/jwt`
- 所有 RPC（除白名单外）需要 Bearer token
- 普通用户只能操作 `owner_id == user_id` 的知识库
- 管理员可操作全部知识库
- 权限校验在 service 层执行，repository 层可传 `owner_id` 过滤

## MinIO 集成

### docker-compose.yml 新增

```yaml
minio:
  image: minio/minio:latest
  ports:
    - "9000:9000"
    - "9001:9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  volumes:
    - minio_data:/data
  command: server /data --console-address ":9001"
```

### 配置项

`config.yaml` 新增 `minio` 块：

| 配置项 | 环境变量 | 默认值 |
|---|---|---|
| `endpoint` | `PIVOT_KB_MINIO_ENDPOINT` | `localhost:9000` |
| `access_key` | `PIVOT_KB_MINIO_ACCESS_KEY` | `minioadmin` |
| `secret_key` | `PIVOT_KB_MINIO_SECRET_KEY` | `minioadmin` |
| `bucket` | `PIVOT_KB_MINIO_BUCKET` | `pivot` |
| `region` | `PIVOT_KB_MINIO_REGION` | `us-east-1` |

密钥走环境变量，不进 yaml。

### 新增 Go 依赖

- `github.com/minio/minio-go/v7`

## 前端

沿用原设计，新增路由和组件：

### 路由

| 路由 | 页面文件 | 说明 |
|---|---|---|
| `/kb` | `_authenticated/kb/index.tsx` | 知识库列表页 |
| `/kb/$kbId` | `_authenticated/kb/$kbId.tsx` | 知识库详情页（文档管理） |

### 新增文件

```
src/data/kb.ts                           — React Query 查询和变更
src/components/kb/
  create-kb-dialog.tsx                   — 创建/编辑知识库弹窗
  delete-kb-dialog.tsx                   — 删除确认弹窗
  document-upload-dialog.tsx             — 文档上传弹窗
```

### 侧边栏

将「知识库」从禁用状态改为激活，链接到 `/kb`。

## 错误处理

| 场景 | gRPC Code | 处理 |
|---|---|---|
| 知识库名称已存在 | AlreadyExists | 返回重复名称错误 |
| 知识库不存在 | NotFound | 返回资源不存在错误 |
| 无权限操作 | PermissionDenied | 返回权限不足错误 |
| 文件类型不支持 | InvalidArgument | 返回不支持的文件类型错误 |
| 文件超过 10MB | InvalidArgument | 返回文件过大错误 |
| MinIO 上传失败 | Internal | 记录日志，返回上传失败错误 |
| 未认证 | Unauthenticated | JWT interceptor 统一处理 |

## 服务端口

| 服务 | gRPC 端口 | HTTP 端口 |
|---|---|---|
| user | 9090 | 8081 |
| kb | 9091 | 8082 |

## 数据库迁移

`backend/migrations/` 新增：

- `0002_create_knowledge_bases.sql`
- `0003_create_documents.sql`
