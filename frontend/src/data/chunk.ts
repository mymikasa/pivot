import { queryOptions } from "@tanstack/react-query"
import { isAxiosError } from "axios"

import { knowledgeBaseServiceListChunks } from "@/lib/api-generated/sdk.gen"

import type { V1Chunk, V1ListChunksResponse } from "@/lib/api-generated/types.gen"

export type { V1Chunk as Chunk }

function unwrap<T>(response: unknown): T {
  if (isAxiosError(response)) throw response
  return (response as { data: T }).data
}

interface RawChunk {
  id?: string
  kb_id?: string
  document_id?: string
  chunk_index?: number
  content?: string
  token_count?: number
}

function normalize(raw: RawChunk): V1Chunk {
  return {
    id: raw.id,
    kbId: raw.kb_id,
    documentId: raw.document_id,
    chunkIndex: raw.chunk_index,
    content: raw.content,
    tokenCount: raw.token_count,
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
