# MinIO 对象存储集成

## 概述

Pivot 使用 MinIO 作为文件存储后端，通过 Presigned URL 机制实现文件直传直下，文件内容不经过应用层（gRPC/HTTP），大小只受 MinIO 限制。

## 架构

```
                        ┌──────────┐
                        │  MinIO   │
                        │ :9000    │
                        └────┬─────┘
                  PUT(直传) │  │ GET(直下)
                ┌──────────┘  └──────────┐
                │                         │
┌───────┐  Prepare  ┌──────────┐  DownloadURL  ┌───────┐
│ 前端  │ ────────→ │ KB 后端  │ ←────────── │ 前端  │
│ :5174 │  Confirm  │ :8082    │               │ :5174 │
└───────┘ ────────→ └──────────┘               └───────┘
```

文件上传下载直接在浏览器和 MinIO 之间进行，后端只负责生成 Presigned URL 和管理元数据。

## 配置

### config.yaml

```yaml
minio:
  endpoint: "localhost:9000"
  bucket: "pivot"
  region: "us-east-1"
  access_key: "minioadmin"      # 生产环境走环境变量
  secret_key: "minioadmin"      # 生产环境走环境变量
```

### 环境变量

| 变量 | 说明 | 优先级 |
|------|------|--------|
| `PIVOT_KB_MINIO_ACCESS_KEY` | Access Key | 覆盖 config.yaml |
| `PIVOT_KB_MINIO_SECRET_KEY` | Secret Key | 覆盖 config.yaml |

### Docker Compose

```yaml
minio:
  image: pgsty/minio:RELEASE.2026-03-25T00-00-00Z
  ports:
    - "9000:9000"   # S3 API
    - "9001:9001"   # 管理控制台
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
```

### CORS

前端直传 MinIO 需要配置 CORS：

```bash
mc alias set local http://localhost:9000 minioadmin minioadmin
mc admin config set local api cors_allow_origin="http://localhost:5174"
mc admin service restart local
```

## Object Key 设计

```
格式: {kbId}/{uuid}{ext}
示例: 7/a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf

kbId  — 知识库 ID，按知识库逻辑隔离
uuid  — 防止同名文件冲突
ext   — 保留原始扩展名，MinIO 据此推断 Content-Type
```

DB 层 `documents.object_key` 有唯一索引，同一 key 不会产生重复记录。

## 存储层 API

`backend/pkg/storage/minio.go` 提供以下方法：

| 方法 | 用途 |
|------|------|
| `EnsureBucket(ctx)` | 启动时确保 bucket 存在 |
| `Upload(ctx, key, reader, size, contentType)` | 直接上传（旧流程用） |
| `Download(ctx, key)` | 直接下载（旧流程用） |
| `Delete(ctx, key)` | 删除对象 |
| `PresignedPutObject(ctx, key, expires)` | 生成上传用 Presigned URL |
| `PresignedGetObject(ctx, key, expires)` | 生成下载用 Presigned URL |
| `ObjectExists(ctx, key)` | 检查对象是否存在 |

## 上传流程

### 三步上传

```
Step 1: PrepareDocumentUpload
  前端 → 后端: {kbId, filename, contentType, fileSize}
  后端 → 前端: {objectKey, uploadUrl}
  后端行为: 校验文件类型/大小，生成 object_key + presigned PUT URL（15 分钟有效）
  注意: 不写数据库

Step 2: PUT 直传 MinIO
  前端 → MinIO: PUT uploadUrl, body=文件, Content-Type=contentType
  前端行为: 直接上传，不经过后端

Step 3: ConfirmDocumentUpload
  前端 → 后端: {kbId, objectKey, filename, contentType, fileSize}
  后端行为: 验证 MinIO 对象存在 → 创建 DB 记录(status=ready)
  后端 → 前端: {document}
```

### 为什么 Prepare 阶段不写 DB

如果在 Prepare 时就创建 `status=uploading` 记录，用户取消/刷新/崩溃后会留下脏数据。改为 Confirm 时才创建记录，直接 `status=ready`，不会产生脏数据。

### Presigned URL 有效期

| URL 类型 | 有效期 | 常量 |
|----------|--------|------|
| 上传 (PUT) | 15 分钟 | `presignedPutTTL` |
| 下载 (GET) | 1 小时 | `presignedGetTTL` |

上传 URL 过期后用户无法继续上传，因此不会产生需要清理的中间状态。

## 下载/预览流程

```
前端调用 GetDocumentDownloadURL(kbId, docId)
  → 后端验证文档 status=ready
  → 生成 presigned GET URL（1 小时有效）
  → 返回 {downloadUrl, filename, contentType}

前端根据 contentType 渲染:
  文本 (text/*, application/json) → fetch(url).text() → <pre>
  PDF  (application/pdf)          → <iframe src={url}>
  图片 (image/*)                  → <img src={url}>
  其他                            → <a href={url} download>
```

## 文件校验

| 规则 | 值 |
|------|-----|
| 最大文件大小 | 100MB |
| 允许的扩展名 | .pdf .doc .docx .xls .xlsx .ppt .pptx .txt .md .csv .json |

前后端都做校验。后端只校验扩展名和大小，不校验实际内容（文件直传 MinIO，后端不碰文件内容）。

## Proto API

```protobuf
// 准备上传（不写 DB）
rpc PrepareDocumentUpload(PrepareDocumentUploadRequest) returns (PrepareDocumentUploadResponse) {
  post: "/api/v1/kb/{kb_id}/documents/prepare-upload"
}

// 确认上传（创建 DB 记录）
rpc ConfirmDocumentUpload(ConfirmDocumentUploadRequest) returns (ConfirmDocumentUploadResponse) {
  post: "/api/v1/kb/{kb_id}/documents/confirm-upload"
}

// 获取下载 URL
rpc GetDocumentDownloadURL(GetDocumentDownloadURLRequest) returns (GetDocumentDownloadURLResponse) {
  get: "/api/v1/kb/{kb_id}/documents/{doc_id}/download-url"
}
```

## 关键文件索引

| 文件 | 职责 |
|------|------|
| `backend/pkg/storage/minio.go` | MinIO 客户端封装 |
| `backend/app/kb/service/kb.go` | 上传/下载业务逻辑 |
| `backend/app/kb/grpc/kb.go` | gRPC handler |
| `backend/app/kb/domain/document.go` | 文档领域模型 |
| `backend/app/kb/repository/dao/document.go` | DB 模型（含 object_key 唯一索引） |
| `backend/app/kb/ioc/config.go` | 配置加载 |
| `backend/app/kb/config.yaml` | 配置文件 |
| `frontend/src/data/kb.ts` | 上传 mutation + 预览 query |
| `frontend/src/routes/_authenticated/kb/$kbId/$docId.tsx` | 预览页面 |
