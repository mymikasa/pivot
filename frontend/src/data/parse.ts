import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { isAxiosError } from "axios"

import {
  createParseTaskApiV1ParseTasksPost,
  getParseTaskApiV1ParseTasksTaskIdGet,
  listParseTasksApiV1ParseTasksGet,
} from "@/lib/parse-api-generated/sdk.gen"

import type {
  CreateParseTaskResponse,
  ParseTaskResponse,
} from "@/lib/parse-api-generated/types.gen"

function unwrap<T>(response: unknown): T {
  if (isAxiosError(response)) throw response
  return (response as { data: T }).data
}

export type { ParseTaskResponse as ParseTask }

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
      return unwrap<ParseTaskResponse>(
        await getParseTaskApiV1ParseTasksTaskIdGet({
          path: { task_id: taskId },
        }),
      )
    },
  })
}

export function useParseTask(taskId: number | null) {
  return useQuery(parseTaskOptions(taskId))
}

export function parseTaskListOptions(kbId?: number, documentId?: number) {
  return queryOptions({
    queryKey: ["parse", "tasks", { kbId, documentId }],
    refetchInterval: (query) => {
      const tasks = query.state.data?.tasks ?? []
      const hasActive = tasks.some(
        (t) => t.status === "pending" || t.status === "running",
      )
      return hasActive ? 60000 : false
    },
    queryFn: async () => {
      return unwrap<{ tasks: ParseTaskResponse[] }>(
        await listParseTasksApiV1ParseTasksGet({
          query: { kb_id: kbId, document_id: documentId },
        }),
      )
    },
  })
}

export function useCreateParseTaskMutation(kbId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: {
      documentId: string
      objectKey: string
      contentType: string
      filename: string
    }) => {
      return unwrap<CreateParseTaskResponse>(
        await createParseTaskApiV1ParseTasksPost({
          body: {
            kb_id: Number(kbId),
            document_id: Number(input.documentId),
            object_key: input.objectKey,
            content_type: input.contentType,
            filename: input.filename,
          },
        }),
      )
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["kb", kbId, "documents"],
      })
      void queryClient.invalidateQueries({
        queryKey: ["parse", "tasks"],
      })
    },
  })
}
