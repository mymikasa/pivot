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
