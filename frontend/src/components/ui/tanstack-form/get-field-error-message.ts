import type { AnyFieldApi } from "@tanstack/react-form"

/**
 * 取字段第一条错误用于展示。规则：
 * - 字段未 touched 不展示（避免初次渲染就铺一片错误）
 * - 提交时 tanstack-form 会把所有字段标 touched，因此 submit 失败后会立刻展示
 * - errors 兼容字符串和 Zod issue 对象
 */
export function getFieldErrorMessage(field: AnyFieldApi): string | undefined {
  if (!field.state.meta.isTouched) return undefined
  const first = field.state.meta.errors[0]
  if (!first) return undefined
  if (typeof first === "string") return first
  return (first as { message?: string }).message
}
