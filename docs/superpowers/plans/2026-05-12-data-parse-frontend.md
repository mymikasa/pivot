# 数据解析前端实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在知识库详情页为已上传文档提供“解析”按钮、解析任务进度轮询、状态展示和失败提示。

**Architecture:** 前端继续使用 TanStack Query；Go 知识库接口提供文档列表，Python 解析服务提供任务创建和状态查询。新增 `parse.ts` 封装解析服务请求，文档表格行组件负责触发解析和按任务 ID 轮询。

**Tech Stack:** React 19, TypeScript, TanStack Query, TanStack Router, Vite, Axios, Tailwind CSS

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `frontend/vite.config.ts` | 将 `/api/v1/parse` 代理到 Python 解析服务 |
| `frontend/src/data/parse.ts` | 解析任务 API 封装与 Query/Mutation hooks |
| `frontend/src/data/kb.ts` | 扩展文档类型 re-export |
| `frontend/src/routes/_authenticated/kb/$kbId/index.tsx` | 文档列表增加解析按钮、进度和错误展示 |
| `frontend/e2e/kb.spec.ts` | 覆盖解析按钮和进度轮询 |

---

### Task 1: 解析服务 API 封装

**Files:**
- Create: `frontend/src/data/parse.ts`
- Test: `frontend/src/data/parse.test.ts`

- [ ] **Step 1: 写 API 封装测试**

创建 `frontend/src/data/parse.test.ts`：

```ts
import { describe, expect, it, vi } from "vitest"

import { createParseTask, getParseTask } from "./parse"
import { request } from "@/lib/request"

vi.mock("@/lib/request", () => ({
  request: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

describe("parse data api", () => {
  it("creates parse task with document metadata", async () => {
    vi.mocked(request.post).mockResolvedValueOnce({
      data: { task_id: 1, status: "pending" },
    })

    const result = await createParseTask({
      kbId: "7",
      documentId: "42",
      objectKey: "7/demo.txt",
      contentType: "text/plain",
    })

    expect(request.post).toHaveBeenCalledWith("/v1/parse/tasks", {
      kb_id: 7,
      document_id: 42,
      object_key: "7/demo.txt",
      content_type: "text/plain",
    })
    expect(result.taskId).toBe(1)
    expect(result.status).toBe("pending")
  })

  it("gets parse task status", async () => {
    vi.mocked(request.get).mockResolvedValueOnce({
      data: {
        task_id: 1,
        kb_id: 7,
        document_id: 42,
        status: "running",
        progress: 65,
        error_message: null,
        created_at: "2026-05-12T00:00:00",
        updated_at: "2026-05-12T00:00:01",
      },
    })

    const result = await getParseTask(1)

    expect(request.get).toHaveBeenCalledWith("/v1/parse/tasks/1")
    expect(result.progress).toBe(65)
    expect(result.errorMessage).toBeNull()
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm test -- parse.test.ts`

Expected: FAIL，提示 `./parse` 不存在。

- [ ] **Step 3: 实现 `frontend/src/data/parse.ts`**

```ts
import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query"
import { isAxiosError } from "axios"

import { request } from "@/lib/request"

interface CreateParseTaskInput {
  kbId: string
  documentId: string
  objectKey: string
  contentType: string
}

interface RawCreateParseTaskResponse {
  task_id: number
  status: string
}

interface RawParseTaskResponse {
  task_id: number
  kb_id: number
  document_id: number
  status: string
  progress: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface ParseTask {
  taskId: number
  kbId: number
  documentId: number
  status: string
  progress: number
  errorMessage: string | null
  createdAt: string
  updatedAt: string
}

function mapParseTask(raw: RawParseTaskResponse): ParseTask {
  return {
    taskId: raw.task_id,
    kbId: raw.kb_id,
    documentId: raw.document_id,
    status: raw.status,
    progress: raw.progress,
    errorMessage: raw.error_message,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  }
}

export function getParseApiErrorMessage(error: unknown): string {
  if (isAxiosError<{ detail?: string; message?: string }>(error)) {
    return (
      error.response?.data?.detail ??
      error.response?.data?.message ??
      "解析任务操作失败"
    )
  }
  return "解析任务操作失败"
}

export async function createParseTask(
  input: CreateParseTaskInput,
): Promise<{ taskId: number; status: string }> {
  const { data } = await request.post<RawCreateParseTaskResponse>(
    "/v1/parse/tasks",
    {
      kb_id: Number(input.kbId),
      document_id: Number(input.documentId),
      object_key: input.objectKey,
      content_type: input.contentType,
    },
  )
  return { taskId: data.task_id, status: data.status }
}

export async function getParseTask(taskId: number): Promise<ParseTask> {
  const { data } = await request.get<RawParseTaskResponse>(
    `/v1/parse/tasks/${taskId}`,
  )
  return mapParseTask(data)
}

export function parseTaskOptions(taskId: number | null) {
  return queryOptions({
    queryKey: ["parse", "tasks", taskId],
    enabled: taskId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === "pending" || status === "running" ? 2000 : false
    },
    queryFn: async () => {
      if (taskId === null) throw new Error("缺少解析任务 ID")
      return getParseTask(taskId)
    },
  })
}

export function useCreateParseTaskMutation(kbId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createParseTask,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["kb", kbId, "documents"],
      })
    },
  })
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npm test -- parse.test.ts`

Expected: PASS。

---

### Task 2: Vite 代理 Python 解析服务

**Files:**
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: 增加代理配置**

在 `frontend/vite.config.ts` 的 `server.proxy` 中，把 `/api/v1/parse` 放在 `/api` 前面：

```ts
"/api/v1/parse": {
  target: "http://localhost:8000",
  changeOrigin: true,
},
```

完整 proxy 顺序为：

```ts
proxy: {
  "/api/v1/parse": {
    target: "http://localhost:8000",
    changeOrigin: true,
  },
  "/api/v1/kb": {
    target: "http://localhost:8082",
    changeOrigin: true,
  },
  "/api": {
    target: "http://localhost:8081",
    changeOrigin: true,
  },
},
```

- [ ] **Step 2: 运行类型检查**

Run: `cd frontend && npm run type-check`

Expected: PASS。

---

### Task 3: 文档类型扩展

**Files:**
- Modify: `frontend/src/data/kb.ts`

- [ ] **Step 1: 定义前端文档扩展类型**

在 `frontend/src/data/kb.ts` 的 type 区域增加：

```ts
export interface KbDocument extends V1Document {
  object_key?: string
  objectKey?: string
  parse_status?: string
  parseStatus?: string
  parse_task_id?: number
  parseTaskId?: number
  parse_progress?: number
  parseProgress?: number
  parse_error?: string
  parseError?: string
}
```

并把 re-export 改为：

```ts
export type { V1KnowledgeBase as KnowledgeBase }
```

- [ ] **Step 2: 让 `documentListOptions` 返回扩展类型**

更新 `documentListOptions` 的返回：

```ts
const data = unwrap<V1ListDocumentsResponse>(
  await knowledgeBaseServiceListDocuments({ path: { kbId } }),
)
return {
  ...data,
  items: (data.items ?? []) as KbDocument[],
}
```

- [ ] **Step 3: 运行类型检查**

Run: `cd frontend && npm run type-check`

Expected: 如果页面还未使用新字段，应 PASS。

---

### Task 4: 文档行解析按钮与进度展示

**Files:**
- Modify: `frontend/src/routes/_authenticated/kb/$kbId/index.tsx`

- [ ] **Step 1: 拆出 DocumentRow 组件**

在 `frontend/src/routes/_authenticated/kb/$kbId/index.tsx` 中导入：

```ts
import {
  getParseApiErrorMessage,
  parseTaskOptions,
  useCreateParseTaskMutation,
} from "@/data/parse"
import type { KbDocument } from "@/data/kb"
```

把 `docs.items.map((doc) => (...))` 替换为：

```tsx
{docs.items.map((doc) => (
  <DocumentRow
    key={doc.id}
    kbId={kbId}
    doc={doc}
    onDelete={() =>
      setDeleteDocTarget({
        id: doc.id,
        name: doc.filename,
      })
    }
  />
))}
```

- [ ] **Step 2: 新增字段读取 helper**

在页面底部增加：

```ts
function getObjectKey(doc: KbDocument): string {
  return doc.objectKey ?? doc.object_key ?? ""
}

function getParseStatus(doc: KbDocument): string {
  return doc.parseStatus ?? doc.parse_status ?? "not_parsed"
}

function getParseTaskId(doc: KbDocument): number | null {
  return doc.parseTaskId ?? doc.parse_task_id ?? null
}

function getParseProgress(doc: KbDocument): number {
  return doc.parseProgress ?? doc.parse_progress ?? 0
}

function getParseError(doc: KbDocument): string {
  return doc.parseError ?? doc.parse_error ?? ""
}
```

- [ ] **Step 3: 新增 DocumentRow 组件**

在 `StatusBadge` 前新增：

```tsx
function DocumentRow({
  kbId,
  doc,
  onDelete,
}: {
  kbId: string
  doc: KbDocument
  onDelete: () => void
}) {
  const [localTaskId, setLocalTaskId] = useState<number | null>(
    getParseTaskId(doc),
  )
  const createParseTaskMutation = useCreateParseTaskMutation(kbId)
  const parseTaskQuery = useQuery(parseTaskOptions(localTaskId))
  const parseTask = parseTaskQuery.data
  const parseStatus = parseTask?.status ?? getParseStatus(doc)
  const parseProgress = parseTask?.progress ?? getParseProgress(doc)
  const parseError = parseTask?.errorMessage ?? getParseError(doc)
  const objectKey = getObjectKey(doc)
  const isParsing = parseStatus === "pending" || parseStatus === "running"
  const canParse = doc.status === "ready" && objectKey && !isParsing

  function handleParse() {
    createParseTaskMutation.mutate(
      {
        kbId,
        documentId: doc.id,
        objectKey,
        contentType: doc.content_type,
      },
      {
        onSuccess: (task) => setLocalTaskId(task.taskId),
      },
    )
  }

  return (
    <tr className="transition-colors hover:bg-surface-1">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2.5">
          <FileIcon contentType={doc.content_type} />
          <Link
            to="/kb/$kbId/$docId"
            params={{ kbId, docId: doc.id }}
            className="text-sm font-medium text-text-primary transition-colors hover:text-accent"
          >
            {doc.filename}
          </Link>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-text-secondary">
        {formatFileSize(doc.file_size)}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-col gap-1">
          <StatusBadge status={doc.status} />
          <ParseStatusBadge status={parseStatus} />
          {isParsing && (
            <div className="h-1.5 w-28 overflow-hidden rounded-full bg-surface-2">
              <div
                className="h-full rounded-full bg-accent transition-all"
                style={{ width: `${parseProgress}%` }}
              />
            </div>
          )}
          {parseStatus === "failed" && parseError && (
            <span className="max-w-48 truncate text-xs text-danger">
              {parseError}
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-text-secondary">
        {formatDate(doc.created_at)}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-1">
          <button
            data-testid={`doc-parse-button-${doc.id}`}
            onClick={handleParse}
            disabled={!canParse || createParseTaskMutation.isPending}
            className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-accent-dim hover:text-accent disabled:cursor-not-allowed disabled:opacity-40"
            title={
              isParsing
                ? "解析中"
                : objectKey
                  ? "解析文档"
                  : "缺少对象 Key，无法解析"
            }
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2v6" />
              <path d="M12 16v6" />
              <path d="m4.93 4.93 4.24 4.24" />
              <path d="m14.83 14.83 4.24 4.24" />
              <path d="M2 12h6" />
              <path d="M16 12h6" />
              <path d="m4.93 19.07 4.24-4.24" />
              <path d="m14.83 9.17 4.24-4.24" />
            </svg>
          </button>
          <button
            data-testid={`doc-delete-button-${doc.id}`}
            onClick={onDelete}
            className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-danger-dim hover:text-danger"
            title="删除文档"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </button>
        </div>
        {createParseTaskMutation.isError && (
          <p className="mt-1 text-xs text-danger">
            {getParseApiErrorMessage(createParseTaskMutation.error)}
          </p>
        )}
      </td>
    </tr>
  )
}
```

- [ ] **Step 4: 新增 ParseStatusBadge**

在 `StatusBadge` 后增加：

```tsx
function ParseStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    not_parsed: "bg-surface-2 text-text-muted",
    pending: "bg-amber-50 text-amber-600",
    running: "bg-blue-50 text-blue-600",
    completed: "bg-teal-50 text-teal-600",
    failed: "bg-red-50 text-red-600",
    cancelled: "bg-surface-2 text-text-muted",
  }
  const labels: Record<string, string> = {
    not_parsed: "未解析",
    pending: "等待解析",
    running: "解析中",
    completed: "已解析",
    failed: "解析失败",
    cancelled: "已取消",
  }
  return (
    <span
      className={`inline-flex w-fit rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] ?? "bg-surface-2 text-text-muted"}`}
    >
      {labels[status] ?? status}
    </span>
  )
}
```

- [ ] **Step 5: 运行类型检查**

Run: `cd frontend && npm run type-check`

Expected: PASS。

---

### Task 5: E2E 覆盖解析按钮

**Files:**
- Modify: `frontend/e2e/kb.spec.ts`

- [ ] **Step 1: 新增 MSW 或路由 mock**

在现有知识库 e2e 测试中，为 Python 解析服务增加路由拦截：

```ts
await page.route("**/api/v1/parse/tasks", async (route) => {
  if (route.request().method() === "POST") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ task_id: 101, status: "pending" }),
    })
    return
  }
  await route.continue()
})

await page.route("**/api/v1/parse/tasks/101", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      task_id: 101,
      kb_id: 1,
      document_id: 2,
      status: "running",
      progress: 65,
      error_message: null,
      created_at: "2026-05-12T00:00:00",
      updated_at: "2026-05-12T00:00:01",
    }),
  })
})
```

- [ ] **Step 2: 新增断言**

在文档列表测试中加入：

```ts
await page.getByTestId("doc-parse-button-2").click()
await expect(page.getByText("解析中")).toBeVisible()
await expect(page.locator('[style*="width: 65%"]')).toBeVisible()
```

- [ ] **Step 3: 运行 E2E**

Run: `cd frontend && npx playwright test e2e/kb.spec.ts`

Expected: PASS。

---

### Task 6: 前端验证

**Files:**
- Modify only if verification reveals failures in files touched by this plan.

- [ ] **Step 1: 类型检查**

Run: `cd frontend && npm run type-check`

Expected: PASS。

- [ ] **Step 2: Lint**

Run: `cd frontend && npm run lint`

Expected: PASS。

- [ ] **Step 3: 构建**

Run: `cd frontend && npm run build`

Expected: PASS。

- [ ] **Step 4: 检查 Git diff**

Run: `git diff -- frontend`

Expected: 只包含解析服务 API 封装、知识库文档页、代理配置和相关测试。

