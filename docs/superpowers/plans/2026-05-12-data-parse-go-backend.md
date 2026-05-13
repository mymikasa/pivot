# 数据解析 Go 后端协作实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Go 知识库服务为解析服务提供稳定的文档元数据边界：文档列表显示解析状态，确认上传后保留 `object_key`，并允许前端用现有 JWT 直接调用 Python 解析服务。

**Architecture:** Go 服务仍负责知识库、文档记录和 MinIO 预签名 URL；Python 服务直接消费 `document_id`、`kb_id`、`object_key` 和 `content_type`。Go 侧新增文档状态字段约定和测试，避免解析服务需要反查 Go 内部接口。

**Tech Stack:** Go, gRPC-Gateway, GORM, MySQL, MinIO, protobuf, Playwright e2e where applicable

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `backend/migrations/0004_add_document_parse_status.sql` | 给 `documents` 增加解析状态字段 |
| `backend/app/kb/domain/document.go` | 扩展文档领域模型 |
| `backend/app/kb/repository/dao/document.go` | 映射解析状态字段，新增更新方法 |
| `backend/app/kb/repository/types.go` | Repository 接口补充解析状态更新 |
| `backend/app/kb/repository/document.go` | Repository 方法转发 |
| `backend/api/proto/kb/v1/kb.proto` | `Document` message 输出解析状态 |
| `backend/app/kb/grpc/kb.go` | gRPC response 映射解析状态 |
| `backend/app/kb/service/kb.go` | 上传确认后初始化解析状态 |
| `backend/app/kb/e2e_test.go` | 覆盖文档解析状态字段 |

---

### Task 1: 数据库迁移与 DAO 字段

**Files:**
- Create: `backend/migrations/0004_add_document_parse_status.sql`
- Modify: `backend/app/kb/domain/document.go`
- Modify: `backend/app/kb/repository/dao/document.go`
- Test: `backend/app/kb/e2e_test.go`

- [ ] **Step 1: 写 e2e 断言**

在 `backend/app/kb/e2e_test.go` 的文档上传确认测试中，对返回的 `Document` 增加断言：

```go
require.Equal(t, "not_parsed", confirmed.Document.ParseStatus)
require.Equal(t, int32(0), confirmed.Document.ParseProgress)
```

如果当前测试尚未覆盖 confirm upload，新增一个测试用例，流程为创建知识库、prepare upload、PUT 到 MinIO、confirm upload、list documents。

- [ ] **Step 2: 运行测试确认失败**

Run: `go test ./app/kb/...`

Expected: FAIL，提示 `ParseStatus` 或 `ParseProgress` 字段不存在。

- [ ] **Step 3: 新增 SQL 迁移**

创建 `backend/migrations/0004_add_document_parse_status.sql`：

```sql
ALTER TABLE documents
    ADD COLUMN parse_status VARCHAR(32) NOT NULL DEFAULT 'not_parsed',
    ADD COLUMN parse_task_id BIGINT NULL,
    ADD COLUMN parse_progress TINYINT UNSIGNED NOT NULL DEFAULT 0,
    ADD COLUMN parse_error TEXT NULL,
    ADD COLUMN parsed_at DATETIME NULL,
    ADD INDEX idx_documents_parse_status (parse_status),
    ADD INDEX idx_documents_parse_task_id (parse_task_id);
```

- [ ] **Step 4: 扩展领域模型**

更新 `backend/app/kb/domain/document.go`：

```go
package domain

import "time"

const (
	DocumentParseStatusNotParsed = "not_parsed"
	DocumentParseStatusPending   = "pending"
	DocumentParseStatusRunning   = "running"
	DocumentParseStatusCompleted = "completed"
	DocumentParseStatusFailed    = "failed"
)

type Document struct {
	ID            int64
	KBID          int64
	Filename      string
	ObjectKey     string
	ContentType   string
	FileSize      int32
	Status        string
	ParseStatus   string
	ParseTaskID   *int64
	ParseProgress int32
	ParseError    string
	ParsedAt      *time.Time
	CreatedAt     time.Time
}

type NewDocumentInput struct {
	KBID        int64
	Filename    string
	ObjectKey   string
	ContentType string
	FileSize    int32
}
```

- [ ] **Step 5: 扩展 DAO 模型**

在 `backend/app/kb/repository/dao/document.go` 的 `Document` struct 中加入：

```go
ParseStatus   string     `gorm:"size:32;not null;default:not_parsed"`
ParseTaskID   *int64     `gorm:"index"`
ParseProgress int32      `gorm:"not null;default:0"`
ParseError    string     `gorm:"type:text"`
ParsedAt      *time.Time
```

- [ ] **Step 6: 运行测试确认仍失败但编译前进**

Run: `go test ./app/kb/...`

Expected: FAIL，提示 proto 生成类型还没有 parse 字段。

---

### Task 2: Proto 输出解析状态

**Files:**
- Modify: `backend/api/proto/kb/v1/kb.proto`
- Generated: `backend/api/gen/kb/v1/kb.pb.go`
- Generated: `backend/api/gen/kb/v1/kb.pb.gw.go`
- Generated: `backend/api/gen/kb/v1/kb_grpc.pb.go`
- Generated: `backend/api/gen/openapi/pivot-v1.swagger.json`
- Modify: `frontend/openapi.json` in frontend plan only, not here

- [ ] **Step 1: 修改 `Document` message**

在 `backend/api/proto/kb/v1/kb.proto` 中更新 `Document`：

```proto
message Document {
  int64 id = 1;
  int64 kb_id = 2;
  string filename = 3;
  string content_type = 4;
  int32 file_size = 5;
  string status = 6;
  google.protobuf.Timestamp created_at = 7;
  string parse_status = 8;
  int64 parse_task_id = 9;
  int32 parse_progress = 10;
  string parse_error = 11;
  google.protobuf.Timestamp parsed_at = 12;
  string object_key = 13;
}
```

- [ ] **Step 2: 生成 proto 代码**

Run: `make proto-gen`

Expected: `backend/api/gen/kb/v1/*` 和 `backend/api/gen/openapi/pivot-v1.swagger.json` 更新。

- [ ] **Step 3: 运行 Go 测试确认映射仍失败**

Run: `go test ./app/kb/...`

Expected: FAIL，提示 gRPC 映射没有填充新增字段。

---

### Task 3: Repository 与 gRPC 映射

**Files:**
- Modify: `backend/app/kb/repository/types.go`
- Modify: `backend/app/kb/repository/document.go`
- Modify: `backend/app/kb/repository/dao/document.go`
- Modify: `backend/app/kb/grpc/kb.go`

- [ ] **Step 1: 扩展 Repository 接口**

在 `backend/app/kb/repository/types.go` 中加入：

```go
UpdateDocumentParseState(ctx context.Context, docID int64, status string, taskID *int64, progress int32, parseErr string) error
```

- [ ] **Step 2: 实现 DAO 更新方法**

在 `backend/app/kb/repository/dao/document.go` 中加入：

```go
func (d *KbDAO) UpdateDocumentParseState(ctx context.Context, docID int64, status string, taskID *int64, progress int32, parseErr string) error {
	updates := map[string]any{
		"parse_status":   status,
		"parse_task_id":  taskID,
		"parse_progress": progress,
		"parse_error":    parseErr,
	}
	if status == domain.DocumentParseStatusCompleted {
		updates["parsed_at"] = time.Now()
	}
	return d.db.WithContext(ctx).Model(&Document{}).
		Where("id = ?", docID).
		Updates(updates).Error
}
```

- [ ] **Step 3: Repository 转发**

在 `backend/app/kb/repository/document.go` 中加入：

```go
func (r *KbRepository) UpdateDocumentParseState(ctx context.Context, docID int64, status string, taskID *int64, progress int32, parseErr string) error {
	return r.dao.UpdateDocumentParseState(ctx, docID, status, taskID, progress, parseErr)
}
```

- [ ] **Step 4: 映射 DAO 到 domain**

在 `backend/app/kb/repository/document.go` 的 document 转换函数中填充：

```go
ParseStatus:   row.ParseStatus,
ParseTaskID:   row.ParseTaskID,
ParseProgress: row.ParseProgress,
ParseError:    row.ParseError,
ParsedAt:      row.ParsedAt,
```

- [ ] **Step 5: 映射 domain 到 proto**

在 `backend/app/kb/grpc/kb.go` 的文档转换函数中填充：

```go
ParseStatus:   doc.ParseStatus,
ParseProgress: doc.ParseProgress,
ParseError:    doc.ParseError,
ObjectKey:     doc.ObjectKey,
```

并处理可空字段：

```go
if doc.ParseTaskID != nil {
	pb.ParseTaskId = *doc.ParseTaskID
}
if doc.ParsedAt != nil {
	pb.ParsedAt = timestamppb.New(*doc.ParsedAt)
}
```

- [ ] **Step 6: 运行测试确认通过**

Run: `go test ./app/kb/...`

Expected: PASS。

---

### Task 4: 上传确认初始化解析状态

**Files:**
- Modify: `backend/app/kb/service/kb.go`
- Test: `backend/app/kb/e2e_test.go`

- [ ] **Step 1: 写初始化状态测试**

在 confirm upload 的 e2e 测试中增加：

```go
docs, err := client.ListDocuments(ctx, &kbv1.ListDocumentsRequest{KbId: kb.Id})
require.NoError(t, err)
require.Len(t, docs.Items, 1)
require.Equal(t, "not_parsed", docs.Items[0].ParseStatus)
require.Zero(t, docs.Items[0].ParseTaskId)
require.Zero(t, docs.Items[0].ParseProgress)
require.Empty(t, docs.Items[0].ParseError)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `go test ./app/kb/...`

Expected: FAIL，如果默认值未返回或字段未映射。

- [ ] **Step 3: 创建文档时保持默认解析状态**

确认 `backend/app/kb/service/kb.go` 的 `ConfirmDocumentUpload` 只传入 `NewDocumentInput`，由 DB 默认值写入 `not_parsed`。如果测试环境未执行迁移，测试 fixture 中的 `AutoMigrate` 或建表 SQL 要包含 `parse_status` 默认值。

- [ ] **Step 4: 运行测试确认通过**

Run: `go test ./app/kb/...`

Expected: PASS。

---

### Task 5: 前端 OpenAPI 生成输入

**Files:**
- Generated: `backend/api/gen/openapi/pivot-v1.swagger.json`
- Consumed by frontend plan: `frontend/openapi.json`

- [ ] **Step 1: 检查 Swagger 包含字段**

Run: `rg "parse_status|parse_progress|object_key" backend/api/gen/openapi/pivot-v1.swagger.json`

Expected: 能看到 `parse_status`、`parse_progress`、`object_key`。

- [ ] **Step 2: 不在 Go 计划中更新前端生成物**

前端生成物由 `2026-05-12-data-parse-frontend.md` 负责，避免两个计划同时写 `frontend/src/lib/api-generated/*`。

---

### Task 6: Go 后端验证

**Files:**
- Modify only if verification reveals failures in files touched by this plan.

- [ ] **Step 1: 格式化 Go 代码**

Run: `gofmt -w backend/app/kb backend/api/proto`

Expected: Go 文件格式化完成。

- [ ] **Step 2: 运行 Go 测试**

Run: `go test ./...`

Expected: PASS。

- [ ] **Step 3: 检查 Git diff**

Run: `git diff -- backend`

Expected: 只包含文档解析状态、proto 生成物和迁移相关改动。

