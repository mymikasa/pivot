import { useState } from "react"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"

import { CreateKbDialog } from "@/components/kb/create-kb-dialog"
import { DeleteKbDialog } from "@/components/kb/delete-kb-dialog"
import { DocumentUploadDialog } from "@/components/kb/document-upload-dialog"
import {
  kbDetailOptions,
  documentListOptions,
  useDeleteDocumentMutation,
  useDeleteKBMutation,
} from "@/data/kb"

export const Route = createFileRoute("/_authenticated/kb/$kbId")({
  component: KbDetailPage,
})

function KbDetailPage() {
  const { kbId } = Route.useParams()
  const navigate = useNavigate()
  const { data: kb, isLoading: kbLoading } = useQuery(kbDetailOptions(kbId))
  const { data: docs, isLoading: docsLoading } = useQuery(
    documentListOptions(kbId),
  )
  const deleteKbMutation = useDeleteKBMutation()
  const deleteDocMutation = useDeleteDocumentMutation(kbId)

  const [editOpen, setEditOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [deleteKbTarget, setDeleteKbTarget] = useState(false)
  const [deleteDocTarget, setDeleteDocTarget] = useState<{
    id: string
    name: string
  } | null>(null)

  if (kbLoading) {
    return (
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
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl p-5 lg:p-8">
      <div className="mb-6">
        <Link
          to="/kb"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-text-muted transition-colors hover:text-accent"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          返回知识库列表
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold text-text-primary">
              {kb?.name ?? ""}
            </h1>
            <p className="mt-1 text-sm text-text-muted">
              {kb?.description || "暂无描述"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              data-testid="edit-kb-button"
              onClick={() => setEditOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-border-dim px-3 py-2 text-sm font-medium text-text-secondary transition-colors hover:bg-surface-2"
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
              编辑
            </button>
            <button
              data-testid="delete-kb-button"
              onClick={() => setDeleteKbTarget(true)}
              className="flex items-center gap-1.5 rounded-lg border border-danger/30 px-3 py-2 text-sm font-medium text-danger transition-colors hover:bg-danger-dim"
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
              删除
            </button>
          </div>
        </div>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-display text-lg font-semibold text-text-primary">
          文档列表
        </h2>
        <button
          data-testid="upload-document-button"
          onClick={() => setUploadOpen(true)}
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
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          上传文档
        </button>
      </div>

      {docsLoading && (
        <div className="py-10 text-center text-sm text-text-muted">
          加载中...
        </div>
      )}

      {!docsLoading && (!docs?.items || docs.items.length === 0) && (
        <div className="rounded-xl border border-border-dim bg-white py-16 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-surface-2">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--color-text-muted)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <p className="text-sm text-text-muted">
            还没有文档，点击上方按钮上传
          </p>
        </div>
      )}

      {!docsLoading && docs?.items && docs.items.length > 0 && (
        <div
          data-testid="document-table"
          className="overflow-hidden rounded-xl border border-border-dim bg-white"
        >
          <table className="w-full">
            <thead>
              <tr className="border-b border-border-dim bg-surface-1">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-text-muted">
                  文件名
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-text-muted">
                  大小
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-text-muted">
                  状态
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-text-muted">
                  上传时间
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-text-muted">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-dim">
              {docs.items.map((doc) => (
                <tr
                  key={doc.id}
                  className="transition-colors hover:bg-surface-1"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <FileIcon contentType={doc.content_type} />
                      <span className="text-sm font-medium text-text-primary">
                        {doc.filename}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-text-secondary">
                    {formatFileSize(doc.file_size)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-4 py-3 text-sm text-text-secondary">
                    {formatDate(doc.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      data-testid={`doc-delete-button-${doc.id}`}
                      onClick={() =>
                        setDeleteDocTarget({
                          id: doc.id,
                          name: doc.filename,
                        })
                      }
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Dialogs */}
      <CreateKbDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        editingKb={kb ?? null}
      />

      <DocumentUploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        kbId={kbId}
      />

      {deleteKbTarget && (
        <DeleteKbDialog
          open={deleteKbTarget}
          onOpenChange={(open) => {
            if (!open) setDeleteKbTarget(false)
          }}
          title={kb?.name ?? ""}
          description="删除后，知识库内的所有文档也将被删除，此操作不可撤销。"
          onConfirm={() => {
            deleteKbMutation.mutate(kbId, {
              onSuccess: () => {
                setDeleteKbTarget(false)
                void navigate({ to: "/kb" })
              },
            })
          }}
          isPending={deleteKbMutation.isPending}
        />
      )}

      {deleteDocTarget && (
        <DeleteKbDialog
          open={!!deleteDocTarget}
          onOpenChange={(open) => {
            if (!open) setDeleteDocTarget(null)
          }}
          title={deleteDocTarget.name}
          onConfirm={() => {
            deleteDocMutation.mutate(deleteDocTarget.id, {
              onSuccess: () => setDeleteDocTarget(null),
            })
          }}
          isPending={deleteDocMutation.isPending}
        />
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    uploading: "bg-amber-50 text-amber-600",
    ready: "bg-teal-50 text-teal-600",
    error: "bg-red-50 text-red-600",
  }
  const labels: Record<string, string> = {
    uploading: "上传中",
    ready: "就绪",
    error: "错误",
  }
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] ?? "bg-surface-2 text-text-muted"}`}
    >
      {labels[status] ?? status}
    </span>
  )
}

function FileIcon({ contentType }: { contentType: string }) {
  const color =
    contentType.includes("pdf")
      ? "text-red-500"
      : contentType.includes("word") || contentType.includes("document")
        ? "text-blue-500"
        : contentType.includes("sheet") || contentType.includes("excel")
          ? "text-green-500"
          : contentType.includes("presentation") || contentType.includes("powerpoint")
            ? "text-orange-500"
            : contentType.includes("json")
              ? "text-amber-600"
              : "text-text-muted"

  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={color}
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  )
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return ""
  }
}
