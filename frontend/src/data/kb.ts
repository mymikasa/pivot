import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query"
import { isAxiosError } from "axios"

import {
  knowledgeBaseServiceConfirmDocumentUpload,
  knowledgeBaseServiceCreateKnowledgeBase,
  knowledgeBaseServiceDeleteDocument,
  knowledgeBaseServiceDeleteKnowledgeBase,
  knowledgeBaseServiceGetDocumentDownloadUrl,
  knowledgeBaseServiceGetKnowledgeBase,
  knowledgeBaseServiceListDocuments,
  knowledgeBaseServiceListKnowledgeBases,
  knowledgeBaseServicePrepareDocumentUpload,
  knowledgeBaseServiceUpdateKnowledgeBase,
} from "@/lib/api-generated/sdk.gen"

import type {
  V1KnowledgeBase,
  V1Document,
  V1ListKnowledgeBasesResponse,
  V1GetKnowledgeBaseResponse,
  V1ListDocumentsResponse,
  V1CreateKnowledgeBaseResponse,
  V1UpdateKnowledgeBaseResponse,
  V1PrepareDocumentUploadResponse,
  V1ConfirmDocumentUploadResponse,
  V1GetDocumentDownloadUrlResponse,
  RpcStatus,
} from "@/lib/api-generated/types.gen"

// Re-export generated types for consumers
export type { V1KnowledgeBase as KnowledgeBase }

export interface KbDocument extends V1Document {
  content_type?: string
  file_size?: number
  created_at?: string
  object_key?: string
  objectKey?: string
  parse_status?: string
  parseStatus?: string
  parse_task_id?: number | string
  parseTaskId?: number | string
  parse_progress?: number
  parseProgress?: number
  parse_error?: string
  parseError?: string
}

// --- Error helpers ---

interface ApiErrorResponse {
  message?: string
}

export function getKbApiErrorMessage(error: unknown): string {
  if (isAxiosError<ApiErrorResponse>(error)) {
    return error.response?.data?.message ?? "操作失败，请稍后重试"
  }
  return "操作失败，请稍后重试"
}

// Generated SDK returns AxiosError on failure instead of throwing.
// unwrap detects that case and re-throws so TanStack Query handles it.
function unwrap<T>(response: unknown): T {
  if (isAxiosError<RpcStatus>(response)) throw response
  return (response as { data: T }).data
}

// --- Query Options ---

export function kbListOptions() {
  return queryOptions({
    queryKey: ["kb", "list"],
    queryFn: async () => {
      return unwrap<V1ListKnowledgeBasesResponse>(
        await knowledgeBaseServiceListKnowledgeBases(),
      )
    },
  })
}

export function kbDetailOptions(id: string) {
  return queryOptions({
    queryKey: ["kb", "detail", id],
    queryFn: async () => {
      const data = unwrap<V1GetKnowledgeBaseResponse>(
        await knowledgeBaseServiceGetKnowledgeBase({ path: { id } }),
      )
      return data.kb
    },
  })
}

export function documentListOptions(kbId: string) {
  return queryOptions({
    queryKey: ["kb", kbId, "documents"],
    queryFn: async () => {
      const data = unwrap<V1ListDocumentsResponse>(
        await knowledgeBaseServiceListDocuments({ path: { kbId } }),
      )
      return {
        ...data,
        items: (data.items ?? []) as KbDocument[],
      }
    },
  })
}

export function documentPreviewOptions(kbId: string, docId: string) {
  return queryOptions({
    queryKey: ["kb", kbId, "documents", docId, "download-url"],
    queryFn: async () => {
      const raw = unwrap<
        V1GetDocumentDownloadUrlResponse & {
          download_url?: string
          content_type?: string
        }
      >(
        await knowledgeBaseServiceGetDocumentDownloadUrl({
          path: { kbId, docId },
        }),
      )
      return {
        downloadUrl: raw.downloadUrl ?? raw.download_url ?? "",
        filename: raw.filename ?? "",
        contentType: raw.contentType ?? raw.content_type ?? "",
      }
    },
  })
}

// --- Mutations ---

export function useCreateKBMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: { name: string; description: string }) => {
      const data = unwrap<V1CreateKnowledgeBaseResponse>(
        await knowledgeBaseServiceCreateKnowledgeBase({ body }),
      )
      return data.kb
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["kb", "list"] })
    },
  })
}

export function useUpdateKBMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: {
      id: string
      name: string
      description: string
    }) => {
      const data = unwrap<V1UpdateKnowledgeBaseResponse>(
        await knowledgeBaseServiceUpdateKnowledgeBase({
          path: { id },
          body,
        }),
      )
      return data.kb
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["kb", "list"] })
      void queryClient.invalidateQueries({
        queryKey: ["kb", "detail", variables.id],
      })
    },
  })
}

export function useDeleteKBMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      unwrap(await knowledgeBaseServiceDeleteKnowledgeBase({ path: { id } }))
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["kb", "list"] })
    },
  })
}

export function useUploadDocumentMutation(kbId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      // Step 1: Prepare — get presigned upload URL + object key
      const rawPrepare = unwrap<
        V1PrepareDocumentUploadResponse & {
          object_key?: string
          upload_url?: string
        }
      >(
        await knowledgeBaseServicePrepareDocumentUpload({
          path: { kbId },
          body: {
            filename: file.name,
            contentType: file.type || "application/octet-stream",
            fileSize: String(file.size),
          },
        }),
      )
      const objectKey =
        rawPrepare.objectKey ?? rawPrepare.object_key ?? ""
      const uploadUrl = rawPrepare.uploadUrl ?? rawPrepare.upload_url ?? ""

      // Step 2: PUT file directly to MinIO
      const putResp = await fetch(uploadUrl, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type || "application/octet-stream" },
      })
      if (!putResp.ok) throw new Error("Upload to storage failed")

      // Step 3: Confirm — create DB record (ready)
      const confirm = unwrap<V1ConfirmDocumentUploadResponse>(
        await knowledgeBaseServiceConfirmDocumentUpload({
          path: { kbId },
          body: {
            objectKey,
            filename: file.name,
            contentType: file.type || "application/octet-stream",
            fileSize: String(file.size),
          },
        }),
      )
      return confirm.document
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["kb", kbId, "documents"],
      })
      void queryClient.invalidateQueries({ queryKey: ["kb", "list"] })
      void queryClient.invalidateQueries({
        queryKey: ["kb", "detail", kbId],
      })
    },
  })
}

export function useDeleteDocumentMutation(kbId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (docId: string) => {
      unwrap(
        await knowledgeBaseServiceDeleteDocument({
          path: { kbId, docId },
        }),
      )
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["kb", kbId, "documents"],
      })
      void queryClient.invalidateQueries({ queryKey: ["kb", "list"] })
      void queryClient.invalidateQueries({
        queryKey: ["kb", "detail", kbId],
      })
    },
  })
}
