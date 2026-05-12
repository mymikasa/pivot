import { useForm } from "@tanstack/react-form"
import type { z } from "zod"

/**
 * 项目统一表单入口：强制 Zod schema + 标准 onSubmit 回调。
 * 与裸 useForm 的区别：
 * - 必须传 schema，验证规则集中在一处
 * - onSubmit 收到的 value 类型 = z.infer<schema>，无需手动断言
 */
export function useAppForm<TSchema extends z.ZodType>(opts: {
  schema: TSchema
  defaultValues: z.infer<TSchema>
  onSubmit: (args: { value: z.infer<TSchema> }) => Promise<void> | void
}) {
  return useForm({
    defaultValues: opts.defaultValues,
    validators: {
      onChange: opts.schema,
    },
    onSubmit: opts.onSubmit,
  })
}
