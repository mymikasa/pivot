import { useEffect, useState } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"

import { documentPreviewOptions } from "@/data/kb"
import { chunkListOptions } from "@/data/chunk"

export const Route = createFileRoute(
  "/_authenticated/kb/$kbId/$docId",
)({
  component: DocumentDetailPage,
})

function DocumentDetailPage() {
  const { kbId, docId } = Route.useParams()
  const { data, isLoading, isError } = useQuery(
    documentPreviewOptions(kbId, docId),
  )
  const {
    data: chunks,
    isLoading: chunksLoading,
    isError: chunksError,
  } = useQuery(chunkListOptions(kbId, docId))

  if (isLoading) {
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

  if (isError) {
    return (
      <div className="mx-auto max-w-6xl p-5 lg:p-8">
        <Link
          to="/kb/$kbId"
          params={{ kbId }}
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
          返回文档列表
        </Link>
        <div className="rounded-xl border border-danger/30 bg-danger-dim p-8 text-center">
          <p className="text-sm font-medium text-danger">
            文档加载失败，请稍后重试
          </p>
        </div>
      </div>
    )
  }

  const contentType = data?.contentType ?? ""
  const filename = data?.filename ?? "未知文件"
  const downloadUrl = data?.downloadUrl ?? ""

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-border-dim bg-surface-0 px-5 py-3 lg:px-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              to="/kb/$kbId"
              params={{ kbId }}
              className="inline-flex items-center gap-1.5 text-sm text-text-muted transition-colors hover:text-accent"
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
              返回
            </Link>
            <span className="text-border-dim">|</span>
            <h1
              data-testid="preview-filename"
              className="font-display text-lg font-semibold text-text-primary"
            >
              {filename}
            </h1>
          </div>
          <a
            href={downloadUrl}
            download={filename}
            data-testid="preview-download-button"
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
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            下载
          </a>
        </div>
      </div>

      {/* Main content: left preview + right chunks */}
      <div className="flex min-h-0 flex-1">
        {/* Left: Document Preview */}
        <div className="flex-1 overflow-auto p-5 lg:p-6">
          <PreviewContent
            contentType={contentType}
            downloadUrl={downloadUrl}
            filename={filename}
          />
        </div>

        {/* Right: Chunks Panel */}
        <div className="flex w-[420px] shrink-0 flex-col border-l border-border-dim bg-surface-0">
          <div className="shrink-0 border-b border-border-dim px-4 py-3">
            <h2 className="text-sm font-semibold text-text-primary">
              Chunks
              {!chunksLoading && chunks && (
                <span className="ml-1.5 text-xs font-normal text-text-muted">
                  ({chunks.length})
                </span>
              )}
            </h2>
          </div>
          <div className="flex-1 overflow-auto p-4">
            {chunksLoading && (
              <div className="py-10 text-center text-sm text-text-muted">
                加载中...
              </div>
            )}
            {chunksError && (
              <div className="rounded-lg border border-danger/30 bg-danger-dim p-4 text-center">
                <p className="text-xs text-danger">Chunks 加载失败</p>
              </div>
            )}
            {chunks && chunks.length === 0 && (
              <div className="py-10 text-center">
                <p className="text-sm text-text-muted">
                  暂无 Chunks，请先解析文档
                </p>
              </div>
            )}
            {chunks &&
              chunks.length > 0 &&
              chunks.map((chunk) => (
                <div
                  key={chunk.id}
                  className="mb-3 rounded-lg border border-border-dim bg-white p-3"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="rounded bg-surface-2 px-1.5 py-0.5 text-xs font-medium text-text-muted">
                      #{chunk.chunk_index}
                    </span>
                    <span className="text-xs text-text-muted">
                      {chunk.token_count} tokens
                    </span>
                  </div>
                  <p className="line-clamp-6 text-xs leading-relaxed text-text-secondary">
                    {chunk.content}
                  </p>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function PreviewContent({
  contentType,
  downloadUrl,
  filename,
}: {
  contentType: string
  downloadUrl: string
  filename: string
}) {
  if (isTextType(contentType)) {
    return <TextPreview downloadUrl={downloadUrl} />
  }

  if (contentType === "application/pdf") {
    return (
      <div
        data-testid="preview-pdf"
        className="overflow-hidden rounded-xl border border-border-dim"
      >
        <iframe
          src={downloadUrl}
          title={filename}
          className="h-[75vh] w-full"
        />
      </div>
    )
  }

  if (contentType.startsWith("image/")) {
    return (
      <div
        data-testid="preview-image"
        className="flex justify-center rounded-xl border border-border-dim bg-white p-4"
      >
        <img
          src={downloadUrl}
          alt={filename}
          className="max-h-[75vh] max-w-full object-contain"
        />
      </div>
    )
  }

  return (
    <div
      data-testid="preview-unsupported"
      className="rounded-xl border border-border-dim bg-white py-16 text-center"
    >
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
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <p className="text-sm text-text-muted">暂不支持该文件类型预览</p>
      <a
        href={downloadUrl}
        download={filename}
        className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-accent transition-colors hover:text-accent-hover"
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
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        下载文件查看
      </a>
    </div>
  )
}

function TextPreview({ downloadUrl }: { downloadUrl: string }) {
  const [text, setText] = useState<string | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetch(downloadUrl)
      .then((r) => r.text())
      .then(setText)
      .catch(() => setError(true))
  }, [downloadUrl])

  if (error) {
    return (
      <div className="rounded-xl border border-danger/30 bg-danger-dim p-8 text-center">
        <p className="text-sm font-medium text-danger">
          文本内容加载失败
        </p>
      </div>
    )
  }
  if (text === null) {
    return (
      <div className="py-10 text-center text-sm text-text-muted">
        加载中...
      </div>
    )
  }

  return (
    <div
      data-testid="preview-text"
      className="overflow-auto rounded-xl border border-border-dim bg-white"
    >
      <pre className="p-4 text-sm leading-relaxed text-text-primary whitespace-pre-wrap break-words">
        {text}
      </pre>
    </div>
  )
}

function isTextType(contentType: string): boolean {
  return (
    contentType.startsWith("text/") ||
    contentType === "application/json" ||
    contentType === "application/xml" ||
    contentType === "application/javascript"
  )
}
