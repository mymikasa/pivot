# MinIO 对象存储开发规范

本规范定义项目中 MinIO 集成的架构约束、接口约定和开发规则。涉及文件上传/下载的后端开发都遵循它。

## 何时适用

- 新增/修改 `pkg/storage/` 下的 MinIO 客户端方法
- 新增使用文件存储的业务功能（上传、下载、预览、清理）
- 修改 Presigned URL 生成逻辑或 TTL
- 修改 Object Key 格式或文件校验规则
- 配置 MinIO 连接（config.yaml、环境变量、Docker Compose）

任务若完全不涉及以上场景，不要套用本规范。

## 架构约束

### 文件不经过应用层

文件内容通过 Presigned URL 在浏览器和 MinIO 之间直传直下，后端只负责：

- 生成 Presigned URL（带签名 + 过期时间）
- 管理 DB 元数据（文件名、object_key、content_type、status）
- 文件校验（类型、大小）

**禁止**在后端代码中读取文件内容到内存再转发。旧的 `Upload`/`Download` 方法仅为兼容保留，新功能一律使用 Presigned URL。

### 单 Bucket + Key 前缀隔离

项目使用单一 Bucket `pivot`，通过 Object Key 前缀实现逻辑隔离：

```
格式: {业务前缀}/{uuid}{ext}
当前: {kbId}/{uuid}{ext}     — 知识库文档
示例: 7/a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf
```

新增业务时，定义自己的前缀规则，不要跟知识库混用。

### Object Key 约束

- UUID 防止同名冲突，**不要**用原始文件名作为 key
- 保留原始扩展名，MinIO 据此推断 Content-Type
- DB 层 `object_key` 必须有唯一索引
- key 生成规则集中在 service 层，dao/grpc 层不生成 key

## 存储层接口

`pkg/storage/minio.go` 是 MinIO 的唯一封装层，业务代码通过它访问 MinIO，不直接使用 `minio-go` SDK。

### 现有方法

| 方法 | 签名 | 用途 |
|------|------|------|
| `NewMinIO` | `(Config) (*MinIO, error)` | 构造客户端 |
| `EnsureBucket` | `(ctx) error` | 启动时确保 bucket 存在 |
| `Upload` | `(ctx, key, reader, size, contentType) error` | 直接上传（旧流程） |
| `Download` | `(ctx, key) (io.ReadCloser, error)` | 直接下载（旧流程） |
| `Delete` | `(ctx, key) error` | 删除对象 |
| `PresignedPutObject` | `(ctx, key, expires) (string, error)` | 生成上传 URL |
| `PresignedGetObject` | `(ctx, key, expires) (string, error)` | 生成下载 URL |
| `ObjectExists` | `(ctx, key) (bool, error)` | 检查对象是否存在 |

### 新增方法规则

- 方法签名第一个参数必须是 `ctx context.Context`
- 返回错误时用 `fmt.Errorf("操作名: %w", err)` 包装，不泄漏 minio-go 错误类型
- `*minio.Client` 不暴露出包外
- 方法内不做业务逻辑判断（文件类型校验等在 service 层）

## 上传流程（Presigned URL 三步）

```
Step 1: PrepareDocumentUpload
  service 生成 object_key + presigned PUT URL
  不写 DB，不接触文件内容
  返回 (objectKey, uploadURL)

Step 2: 前端 PUT 直传 MinIO
  后端不参与

Step 3: ConfirmDocumentUpload
  service 验证 MinIO 对象存在
  创建 DB 记录，status 直接设为 "ready"
  返回 document
```

### 为什么 Prepare 不写 DB

Prepare 时写 DB 会产生 `status=uploading` 记录。用户取消/刷新/崩溃后这条记录永远不会变成 ready，变成脏数据。改为 Confirm 时才创建记录（直接 ready），不会产生脏数据。

### Presigned URL TTL

| 类型 | TTL | 说明 |
|------|-----|------|
| PUT（上传） | 15 分钟 | 超时后 URL 失效，上传不可能继续 |
| GET（下载） | 1 小时 | 前端用 TanStack Query 自动刷新 |

TTL 定义为 service 层常量，不在 grpc/repository 层硬编码。

## 下载/预览流程

```
GetDocumentDownloadURL(kbId, docId)
  验证 status == "ready"
  生成 presigned GET URL
  返回 (url, document)
```

前端拿到 URL 后根据 Content-Type 选择渲染方式（iframe/img/fetch text），不需要后端参与渲染。

## 文件校验

### 校验位置

| 层 | 校验内容 |
|----|----------|
| 前端 | 文件类型（MIME + 扩展名）、文件大小 |
| service | 文件扩展名、文件大小 |
| storage | 不校验，只执行操作 |

### 当前规则

- 最大 100MB（`maxFileSize`）
- 允许扩展名：`.pdf .doc .docx .xls .xlsx .ppt .pptx .txt .md .csv .json`
- 新增文件类型时，前后端允许列表同步更新

## 配置

### config.yaml 字段

```yaml
minio:
  endpoint: "localhost:9000"   # 必填
  bucket: "pivot"              # 必填
  region: "us-east-1"
  access_key: "minioadmin"     # 生产走环境变量
  secret_key: "minioadmin"     # 生产走环境变量
```

### 环境变量覆盖

| 变量 | 覆盖字段 |
|------|----------|
| `PIVOT_KB_MINIO_ACCESS_KEY` | `minio.access_key` |
| `PIVOT_KB_MINIO_SECRET_KEY` | `minio.secret_key` |

环境变量前缀格式：`PIVOT_{SERVICE}_MINIO_{FIELD}`。新增微服务时遵循此命名。

### 配置加载

`ioc/config.go` 中用 viper 的 `BindEnv` 绑定敏感字段，`config.yaml` 放开发默认值，生产用环境变量覆盖。新增 MinIO 配置项必须同时在 Config struct、config.yaml 和 BindEnv 列表中添加。

## 反模式（明确禁止）

- ❌ 在 service 层读取文件内容到 `[]byte` 再传给 storage（使用 Presigned URL）
- ❌ 在 grpc 层生成 object_key（key 生成规则集中在 service 层）
- ❌ 使用原始文件名作为 object_key（用 UUID 防冲突）
- ❌ 在 storage 层做文件类型校验（校验在 service 层）
- ❌ 直接 import `github.com/minio/minio-go/v7`（通过 `pkg/storage` 封装层访问）
- ❌ 新增业务混用知识库的 key 前缀（定义自己的前缀规则）
- ❌ 创建 `status=uploading` 的 DB 记录（Confirm 时直接创建 ready 记录）

## 关键文件

| 文件 | 职责 |
|------|------|
| `backend/pkg/storage/minio.go` | MinIO 客户端封装（唯一访问入口） |
| `backend/app/kb/service/kb.go` | 上传/下载业务逻辑、校验规则、TTL 常量 |
| `backend/app/kb/domain/document.go` | 文档领域模型（含 ObjectKey 字段） |
| `backend/app/kb/repository/dao/document.go` | DB 模型（object_key 唯一索引） |
| `backend/app/kb/ioc/config.go` | 配置加载（含 MinIO 环境变量绑定） |
| `backend/app/kb/config.yaml` | 配置默认值 |
