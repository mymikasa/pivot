import { isAxiosError } from "axios"
import { useEffect, useRef, useState } from "react"

import { useUploadDocumentMutation } from "@/data/kb"

const MAX_FILE_SIZE = 100 * 1024 * 1024 // 100MB

const ALLOWED_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-powerpoint",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "text/plain",
  "text/markdown",
  "text/csv",
  "application/json",
]

const ALLOWED_EXTENSIONS = [
  ".pdf",
  ".doc",
  ".docx",
  ".xls",
  ".xlsx",
  ".ppt",
  ".pptx",
  ".txt",
  ".md",
  ".csv",
  ".json",
]

function isAllowedFile(file: File): boolean {
  if (ALLOWED_TYPES.includes(file.type)) return true
  const name = file.name.toLowerCase()
  return ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface DocumentUploadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  kbId: string
}

export function DocumentUploadDialog({
  open,
  onOpenChange,
  kbId,
}: DocumentUploadDialogProps) {
  const [error, setError] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const uploadMutation = useUploadDocumentMutation(kbId)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setSelectedFile(null)
      setError("")
      dialogRef.current?.showModal()
    } else {
      dialogRef.current?.close()
    }
  }, [open])

  function validateFile(file: File): boolean {
    if (!isAllowedFile(file)) {
      setError("不支持的文件类型。支持 PDF、Office、TXT、MD、CSV、JSON")
      return false
    }
    if (file.size > MAX_FILE_SIZE) {
      setError(`文件大小超过限制（最大 ${formatFileSize(MAX_FILE_SIZE)}）`)
      return false
    }
    return true
  }

  function handleFileSelect(file: File) {
    setError("")
    if (validateFile(file)) {
      setSelectedFile(file)
    } else {
      setSelectedFile(null)
    }
  }

  function handleSubmit() {
    if (!selectedFile) return
    setError("")
    uploadMutation.mutate(selectedFile, {
      onSuccess: () => {
        onOpenChange(false)
      },
      onError: (err) => {
        if (isAxiosError<{ message?: string }>(err)) {
          setError(err.response?.data?.message ?? "上传失败")
        } else {
          setError("上传失败")
        }
      },
    })
  }

  return (
    <dialog
      ref={dialogRef}
      data-testid="document-upload-dialog"
      className="backdrop:bg-black/40 backdrop:backdrop-blur-sm bg-transparent p-0 m-auto max-w-lg w-full"
      onClose={() => onOpenChange(false)}
      onClick={(e) => {
        if (e.target === dialogRef.current) onOpenChange(false)
      }}
    >
      <div className="rounded-xl border border-border-dim bg-surface-0 p-6 shadow-xl">
        <div className="mb-5">
          <h2 className="font-display text-lg font-semibold text-text-primary">
            上传文档
          </h2>
          <p className="mt-1 text-sm text-text-muted">
            支持 PDF、Office、TXT、MD、CSV、JSON，单文件最大 100MB
          </p>
        </div>

        {error && (
          <div
            data-testid="error-message"
            className="mb-4 flex items-center gap-2 rounded-lg border border-danger/20 bg-danger-dim px-4 py-3 text-sm text-danger"
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
              className="shrink-0"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            {error}
          </div>
        )}

        <div
          data-testid="drop-zone"
          className={`rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
            isDragOver
              ? "border-accent bg-accent-dim"
              : selectedFile
                ? "border-accent/40 bg-accent-dim/50"
                : "border-border-mid hover:border-accent/40"
          }`}
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragOver(true)
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setIsDragOver(false)
            const file = e.dataTransfer.files[0]
            if (file) handleFileSelect(file)
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ALLOWED_EXTENSIONS.join(",")}
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) handleFileSelect(file)
            }}
          />
          {selectedFile ? (
            <div className="flex items-center justify-center gap-3">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <div className="text-left">
                <p className="text-sm font-medium text-text-primary">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-text-muted">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            </div>
          ) : (
            <div>
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--color-text-muted)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="mx-auto mb-3"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <p className="text-sm text-text-muted">
                拖拽文件到此处，或{" "}
                <span className="font-medium text-accent">点击选择文件</span>
              </p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <button
            type="button"
            data-testid="cancel-button"
            onClick={() => onOpenChange(false)}
            className="rounded-lg border border-border-dim px-4 py-2 text-sm font-medium text-text-secondary transition-colors hover:bg-surface-2"
          >
            取消
          </button>
          <button
            type="button"
            data-testid="submit-button"
            disabled={!selectedFile || uploadMutation.isPending}
            onClick={handleSubmit}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-all duration-200 hover:bg-accent-hover hover:shadow-lg hover:shadow-accent/15 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploadMutation.isPending ? "上传中..." : "上传"}
          </button>
        </div>
      </div>
    </dialog>
  )
}
