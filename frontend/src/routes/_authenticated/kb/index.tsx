import { useState } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"

import { CreateKbDialog } from "@/components/kb/create-kb-dialog"
import { DeleteKbDialog } from "@/components/kb/delete-kb-dialog"
import { kbListOptions, useDeleteKBMutation } from "@/data/kb"

export const Route = createFileRoute("/_authenticated/kb/")({
  component: KbListPage,
})

function KbListPage() {
  const { data: kbs, isLoading } = useQuery(kbListOptions())
  const deleteMutation = useDeleteKBMutation()
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{
    id: string
    name: string
  } | null>(null)

  return (
    <div className="mx-auto max-w-6xl p-5 lg:p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">
            知识库
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            管理你的知识库和文档资源
          </p>
        </div>
        <button
          data-testid="create-kb-button"
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-all duration-200 hover:bg-accent-hover hover:shadow-lg hover:shadow-accent/15"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          创建知识库
        </button>
      </div>

      {isLoading && (
        <div data-testid="loading-spinner" className="py-20 text-center">
          <svg
            className="mx-auto h-8 w-8 animate-spin text-accent"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="3"
              className="opacity-25"
            />
            <path
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              fill="currentColor"
              className="opacity-75"
            />
          </svg>
          <p className="mt-3 text-sm text-text-muted">加载中...</p>
        </div>
      )}

      {!isLoading && (!kbs?.items || kbs.items.length === 0) && (
        <div className="py-20 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-accent-dim">
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--color-accent)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M3 5v14a9 3 0 0 0 18 0V5" />
              <path d="M3 12a9 3 0 0 0 18 0" />
            </svg>
          </div>
          <h3 className="font-display text-lg font-semibold text-text-primary">
            还没有知识库
          </h3>
          <p className="mt-1 text-sm text-text-muted">
            创建你的第一个知识库来组织文档资源
          </p>
          <button
            data-testid="create-kb-button-empty"
            onClick={() => setCreateOpen(true)}
            className="mt-4 rounded-lg bg-accent px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            创建知识库
          </button>
        </div>
      )}

      {!isLoading && kbs?.items && kbs.items.length > 0 && (
        <div
          data-testid="kb-list"
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {kbs.items.map((kb) => (
            <KbCard
              key={kb.id}
              kb={kb}
              onDelete={() => setDeleteTarget({ id: kb.id, name: kb.name })}
            />
          ))}
        </div>
      )}

      <CreateKbDialog open={createOpen} onOpenChange={setCreateOpen} />

      {deleteTarget && (
        <DeleteKbDialog
          open={!!deleteTarget}
          onOpenChange={(open) => {
            if (!open) setDeleteTarget(null)
          }}
          title={deleteTarget.name}
          description="删除后，知识库内的所有文档也将被删除，此操作不可撤销。"
          onConfirm={() => {
            deleteMutation.mutate(deleteTarget.id, {
              onSuccess: () => setDeleteTarget(null),
            })
          }}
          isPending={deleteMutation.isPending}
        />
      )}
    </div>
  )
}

function KbCard({
  kb,
  onDelete,
}: {
  kb: {
    id: string
    name: string
    description: string
    document_count: number
    updated_at: string
  }
  onDelete: () => void
}) {
  const deleteMutation = useDeleteKBMutation()

  return (
    <div className="group rounded-xl border border-border-dim bg-white p-5 transition-all duration-200 hover:border-accent/30 hover:shadow-sm">
      <div className="mb-3 flex items-start justify-between">
        <Link
          to="/kb/$kbId"
          params={{ kbId: kb.id }}
          className="flex-1 min-w-0"
        >
          <h3 className="truncate font-display font-semibold text-text-primary transition-colors group-hover:text-accent">
            {kb.name}
          </h3>
        </Link>
        <div className="flex shrink-0 items-center gap-1 ml-2">
          <Link
            to="/kb/$kbId"
            params={{ kbId: kb.id }}
            data-testid={`kb-edit-button-${kb.id}`}
            className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-surface-2 hover:text-text-secondary"
            title="查看详情"
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
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </Link>
          <button
            data-testid={`kb-delete-button-${kb.id}`}
            onClick={() => {
              onDelete()
            }}
            className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-danger-dim hover:text-danger"
            title="删除"
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
      </div>

      <p className="mb-4 line-clamp-2 text-sm leading-relaxed text-text-muted">
        {kb.description || "暂无描述"}
      </p>

      <div className="flex items-center justify-between text-xs text-text-muted">
        <span className="flex items-center gap-1.5">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          {kb.document_count} 篇文档
        </span>
        <span>{formatDate(kb.updated_at)}</span>
      </div>
    </div>
  )
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("zh-CN", {
      month: "short",
      day: "numeric",
    })
  } catch {
    return ""
  }
}
