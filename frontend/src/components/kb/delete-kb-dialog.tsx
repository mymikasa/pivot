import { useEffect, useRef } from "react"

interface DeleteKbDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  onConfirm: () => void
  isPending?: boolean
}

export function DeleteKbDialog({
  open,
  onOpenChange,
  title,
  description,
  onConfirm,
  isPending,
}: DeleteKbDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    if (open) {
      dialogRef.current?.showModal()
    } else {
      dialogRef.current?.close()
    }
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      data-testid="delete-confirm-dialog"
      className="backdrop:bg-black/40 backdrop:backdrop-blur-sm bg-transparent p-0 m-auto max-w-md w-full"
      onClose={() => onOpenChange(false)}
      onClick={(e) => {
        if (e.target === dialogRef.current) onOpenChange(false)
      }}
    >
      <div className="rounded-xl border border-border-dim bg-surface-0 p-6 shadow-xl">
        <div className="mb-4 flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-danger-dim">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--color-danger)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              <line x1="10" y1="11" x2="10" y2="17" />
              <line x1="14" y1="11" x2="14" y2="17" />
            </svg>
          </div>
          <div>
            <h2 className="font-display text-lg font-semibold text-text-primary">
              确认删除
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              确定要删除「{title}」吗？
              {description && (
                <span className="block mt-1">{description}</span>
              )}
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
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
            data-testid="confirm-delete-button"
            disabled={isPending}
            onClick={onConfirm}
            className="rounded-lg bg-danger px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isPending ? "删除中..." : "确认删除"}
          </button>
        </div>
      </div>
    </dialog>
  )
}
