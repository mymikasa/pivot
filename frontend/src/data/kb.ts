import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query"
import { isAxiosError } from "axios"

import {
  knowledgeBaseServiceCreateKnowledgeBase,
  knowledgeBaseServiceDeleteDocument,
  knowledgeBaseServiceDeleteKnowledgeBase,
  knowledgeBaseServiceGetKnowledgeBase,
  knowledgeBaseServiceListDocuments,
  knowledgeBaseServiceListKnowledgeBases,
  knowledgeBaseServiceUpdateKnowledgeBase,
  knowledgeBaseServiceUploadDocumentSimple,
} from "@/lib/api-generated/sdk.gen"

import type {
  V1KnowledgeBase,
  V1Document,
  V1ListKnowledgeBasesResponse,
  V1GetKnowledgeBaseResponse,
  V1ListDocumentsResponse,
  V1CreateKnowledgeBaseResponse,
  V1UpdateKnowledgeBaseResponse,
  V1UploadDocumentResponse,
  RpcStatus,
} from "@/lib/api-generated/types.gen"

// Re-export generated types for consumers
export type { V1KnowledgeBase as KnowledgeBase, V1Document as Document }

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
      return unwrap<V1ListDocumentsResponse>(
        await knowledgeBaseServiceListDocuments({ path: { kbId } }),
      )
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
      const base64Data = await fileToBase64(file)
      const data = unwrap<V1UploadDocumentResponse>(
        await knowledgeBaseServiceUploadDocumentSimple({
          path: { kbId },
          body: {
            filename: file.name,
            contentType: file.type || "application/octet-stream",
            data: base64Data,
          },
        }),
      )
      return data.document
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

// --- Helpers ---

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      const base64 = result.split(",")[1] ?? ""
      resolve(base64)
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}
