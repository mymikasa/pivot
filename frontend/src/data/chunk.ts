import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query"
import { isAxiosError } from "axios"

import {
  knowledgeBaseServiceDeleteChunk,
  knowledgeBaseServiceListChunks,
} from "@/lib/api-generated/sdk.gen"

import type { V1Chunk } from "@/lib/api-generated/types.gen"

export type { V1Chunk as Chunk }

function unwrap<T>(response: unknown): T {
  if (isAxiosError(response)) throw response
  return (response as { data: T }).data
}

interface RawChunk {
  id?: string
  kbId?: string
  kb_id?: string
  documentId?: string
  document_id?: string
  chunkIndex?: number
  chunk_index?: number
  content?: string
  tokenCount?: number
  token_count?: number
  sourcePage?: number
  source_page?: number
  sectionTitle?: string
  section_title?: string
  sectionPath?: string
  section_path?: string
  filename?: string
  contentType?: string
  content_type?: string
  chunkSize?: number
  chunk_size?: number
  chunkOverlap?: number
  chunk_overlap?: number
  version?: number
  userId?: string
  user_id?: string
  milvusId?: string
  milvus_id?: string
  createdAt?: string
  created_at?: string
  updatedAt?: string
  updated_at?: string
}

function normalize(raw: RawChunk): V1Chunk {
  return {
    id: raw.id,
    kbId: raw.kbId ?? raw.kb_id,
    documentId: raw.documentId ?? raw.document_id,
    chunkIndex: raw.chunkIndex ?? raw.chunk_index,
    content: raw.content,
    tokenCount: raw.tokenCount ?? raw.token_count,
    sourcePage: raw.sourcePage ?? raw.source_page,
    sectionTitle: raw.sectionTitle ?? raw.section_title,
    sectionPath: raw.sectionPath ?? raw.section_path,
    filename: raw.filename,
    contentType: raw.contentType ?? raw.content_type,
    chunkSize: raw.chunkSize ?? raw.chunk_size,
    chunkOverlap: raw.chunkOverlap ?? raw.chunk_overlap,
    version: raw.version,
    userId: raw.userId ?? raw.user_id,
    milvusId: raw.milvusId ?? raw.milvus_id,
    createdAt: raw.createdAt ?? raw.created_at,
    updatedAt: raw.updatedAt ?? raw.updated_at,
  }
}

export function chunkListOptions(kbId: string, docId: string) {
  return queryOptions({
    queryKey: ["kb", kbId, "documents", docId, "chunks"],
    queryFn: async () => {
      const data = unwrap<{ items?: RawChunk[] }>(
        await knowledgeBaseServiceListChunks({
          path: { kbId, docId },
        }),
      )
      const items = (data.items ?? []).map(normalize)
      items.sort((a, b) => (a.chunkIndex ?? 0) - (b.chunkIndex ?? 0))
      return items
    },
    enabled: !!kbId && !!docId,
  })
}

export function useDeleteChunkMutation(kbId: string, docId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (chunkIndex: number) => {
      unwrap<unknown>(
        await knowledgeBaseServiceDeleteChunk({
          path: { kbId, docId, chunkIndex },
        }),
      )
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["kb", kbId, "documents", docId, "chunks"],
      })
    },
  })
}
