import { isAxiosError } from "axios"
import { useEffect, useRef, useState } from "react"
import { z } from "zod"

import {
  getFieldErrorMessage,
  useAppForm,
} from "@/components/ui/tanstack-form"
import {
  useCreateKBMutation,
  useUpdateKBMutation,
} from "@/data/kb"

import type { KnowledgeBase } from "@/data/kb"

const kbSchema = z.object({
  name: z
    .string()
    .min(1, "请输入知识库名称")
    .max(128, "名称最多 128 个字符"),
  description: z.string().max(2000, "描述最多 2000 个字符"),
})

interface CreateKbDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  editingKb?: KnowledgeBase | null
}

export function CreateKbDialog({
  open,
  onOpenChange,
  editingKb,
}: CreateKbDialogProps) {
  const [formError, setFormError] = useState("")
  const createMutation = useCreateKBMutation()
  const updateMutation = useUpdateKBMutation()
  const isEditing = !!editingKb
  const dialogRef = useRef<HTMLDialogElement>(null)

  const form = useAppForm({
    schema: kbSchema,
    defaultValues: {
      name: editingKb?.name ?? "",
      description: editingKb?.description ?? "",
    },
    onSubmit: async ({ value }) => {
      setFormError("")
      try {
        if (isEditing && editingKb) {
          await updateMutation.mutateAsync({ id: editingKb.id, ...value })
        } else {
          await createMutation.mutateAsync(value)
        }
        onOpenChange(false)
      } catch (error) {
        setFormError(getErrorMessage(error))
      }
    },
  })

  useEffect(() => {
    if (open) {
      dialogRef.current?.showModal()
    } else {
      dialogRef.current?.close()
    }
  }, [open])

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <dialog
      ref={dialogRef}
      data-testid="kb-form-dialog"
      className="backdrop:bg-black/40 backdrop:backdrop-blur-sm bg-transparent p-0 m-auto max-w-lg w-full"
      onClose={() => onOpenChange(false)}
      onClick={(e) => {
        if (e.target === dialogRef.current) onOpenChange(false)
      }}
    >
      <div className="rounded-xl border border-border-dim bg-surface-0 p-6 shadow-xl">
        <div className="mb-5">
          <h2 className="font-display text-lg font-semibold text-text-primary">
            {isEditing ? "编辑知识库" : "创建知识库"}
          </h2>
          <p className="mt-1 text-sm text-text-muted">
            {isEditing ? "修改知识库的名称和描述" : "创建一个新的知识库来组织文档"}
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            void form.handleSubmit()
          }}
          className="space-y-4"
        >
          {formError && (
            <div
              data-testid="error-message"
              className="flex items-center gap-2 rounded-lg border border-danger/20 bg-danger-dim px-4 py-3 text-sm text-danger"
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
              {formError}
            </div>
          )}

          <form.Field name="name">
            {(field) => {
              const error = getFieldErrorMessage(field)
              return (
                <div className="space-y-1.5">
                  <label
                    htmlFor="kb-name"
                    className="block text-sm font-medium text-text-secondary"
                  >
                    名称 <span className="text-danger">*</span>
                  </label>
                  <input
                    id="kb-name"
                    data-testid="kb-name-input"
                    type="text"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={() => field.handleBlur()}
                    placeholder="输入知识库名称"
                    className="w-full rounded-lg border border-border-dim bg-surface-2 px-3 py-2.5 text-sm text-text-primary placeholder-text-muted transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--color-accent-dim)] focus:outline-none"
                  />
                  {error && (
                    <p
                      data-testid="kb-name-error"
                      className="text-xs text-danger"
                    >
                      {error}
                    </p>
                  )}
                </div>
              )
            }}
          </form.Field>

          <form.Field name="description">
            {(field) => {
              const error = getFieldErrorMessage(field)
              return (
                <div className="space-y-1.5">
                  <label
                    htmlFor="kb-description"
                    className="block text-sm font-medium text-text-secondary"
                  >
                    描述
                  </label>
                  <textarea
                    id="kb-description"
                    data-testid="kb-description-input"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={() => field.handleBlur()}
                    placeholder="描述知识库的用途（可选）"
                    rows={3}
                    className="w-full resize-none rounded-lg border border-border-dim bg-surface-2 px-3 py-2.5 text-sm text-text-primary placeholder-text-muted transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--color-accent-dim)] focus:outline-none"
                  />
                  {error && (
                    <p
                      data-testid="kb-description-error"
                      className="text-xs text-danger"
                    >
                      {error}
                    </p>
                  )}
                </div>
              )
            }}
          </form.Field>

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
              type="submit"
              data-testid="submit-button"
              disabled={isPending}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-all duration-200 hover:bg-accent-hover hover:shadow-lg hover:shadow-accent/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isPending
                ? (isEditing ? "保存中..." : "创建中...")
                : (isEditing ? "保存" : "创建")}
            </button>
          </div>
        </form>
      </div>
    </dialog>
  )
}

function getErrorMessage(error: unknown): string {
  if (isAxiosError<{ message?: string }>(error)) {
    return error.response?.data?.message ?? "操作失败"
  }
  return "操作失败"
}
