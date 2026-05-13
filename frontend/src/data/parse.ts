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
