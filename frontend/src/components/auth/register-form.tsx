import type { AnyFieldApi } from "@tanstack/react-form"
import { isAxiosError } from "axios"
import { useState } from "react"
import { z } from "zod"

import {
  getFieldErrorMessage,
  useAppForm,
} from "@/components/ui/tanstack-form"
import { useRegisterMutation } from "@/data/auth"

const registerSchema = z
  .object({
    username: z
      .string()
      .min(3, "用户名至少 3 个字符")
      .max(64, "用户名最多 64 个字符"),
    email: z.email("请输入有效邮箱"),
    password: z
      .string()
      .min(8, "密码至少 8 位，需包含字母和数字")
      .regex(/[A-Za-z]/, "密码至少 8 位，需包含字母和数字")
      .regex(/[0-9]/, "密码至少 8 位，需包含字母和数字"),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "两次密码不一致",
    path: ["confirm_password"],
  })

interface ApiErrorResponse {
  message?: string // grpc-gateway 标准
  detail?: string | Array<{ msg?: string }> // 兼容 Python 残留
}

function getApiErrorMessage(error: unknown): string {
  if (isAxiosError<ApiErrorResponse>(error)) {
    const data = error.response?.data
    if (data?.message) return data.message
    const detail = data?.detail
    if (typeof detail === "string") return detail
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  }
  return "注册失败，请稍后重试"
}

function getInputStyle(isFocused: boolean, hasError: boolean) {
  if (hasError) {
    return {
      borderColor: "var(--color-danger)",
      boxShadow: "0 0 0 3px var(--color-danger-dim)",
    }
  }
  if (isFocused) {
    return {
      borderColor: "var(--color-accent)",
      boxShadow: "0 0 0 3px var(--color-accent-dim)",
    }
  }
  return {
    borderColor: "var(--color-border-dim)",
    boxShadow: "none",
  }
}

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  ) : (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

interface TextFieldProps {
  field: AnyFieldApi
  htmlFor: string
  label: string
  type: "text" | "email"
  placeholder: string
  autoComplete: string
  testid: string
  errorTestid: string
  isFocused: boolean
  onFocus: () => void
  onBlur: () => void
}

function TextField(props: TextFieldProps) {
  const error = getFieldErrorMessage(props.field)
  return (
    <div className="space-y-1.5">
      <label
        htmlFor={props.htmlFor}
        className="block text-sm font-medium text-text-secondary transition-colors"
        style={{
          color: props.isFocused ? "var(--color-accent)" : undefined,
        }}
      >
        {props.label}
      </label>
      <div className="relative">
        <input
          id={props.htmlFor}
          data-testid={props.testid}
          type={props.type}
          value={props.field.state.value}
          onChange={(e) => props.field.handleChange(e.target.value)}
          onFocus={props.onFocus}
          onBlur={() => {
            props.field.handleBlur()
            props.onBlur()
          }}
          placeholder={props.placeholder}
          className="w-full rounded-lg border bg-surface-2 px-3 py-2.5 text-sm text-text-primary placeholder-text-muted transition-all duration-200 focus:outline-none"
          style={getInputStyle(props.isFocused, Boolean(error))}
          autoComplete={props.autoComplete}
        />
      </div>
      {error && (
        <p data-testid={props.errorTestid} className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  )
}

interface PasswordFieldProps {
  field: AnyFieldApi
  htmlFor: string
  label: string
  placeholder: string
  autoComplete: string
  testid: string
  errorTestid: string
  toggleTestid: string
  isVisible: boolean
  onToggleVisible: () => void
  isFocused: boolean
  onFocus: () => void
  onBlur: () => void
}

function PasswordField(props: PasswordFieldProps) {
  const error = getFieldErrorMessage(props.field)
  return (
    <div className="space-y-1.5">
      <label
        htmlFor={props.htmlFor}
        className="block text-sm font-medium text-text-secondary transition-colors"
        style={{
          color: props.isFocused ? "var(--color-accent)" : undefined,
        }}
      >
        {props.label}
      </label>
      <div className="relative">
        <input
          id={props.htmlFor}
          data-testid={props.testid}
          type={props.isVisible ? "text" : "password"}
          value={props.field.state.value}
          onChange={(e) => props.field.handleChange(e.target.value)}
          onFocus={props.onFocus}
          onBlur={() => {
            props.field.handleBlur()
            props.onBlur()
          }}
          placeholder={props.placeholder}
          className="w-full rounded-lg border bg-surface-2 px-3 py-2.5 pr-10 text-sm text-text-primary placeholder-text-muted transition-all duration-200 focus:outline-none"
          style={getInputStyle(props.isFocused, Boolean(error))}
          autoComplete={props.autoComplete}
        />
        <button
          type="button"
          data-testid={props.toggleTestid}
          onClick={props.onToggleVisible}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted transition-colors hover:text-text-secondary"
          aria-label={
            props.isVisible ? `隐藏${props.label}` : `显示${props.label}`
          }
        >
          <EyeIcon open={props.isVisible} />
        </button>
      </div>
      {error && (
        <p data-testid={props.errorTestid} className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  )
}

export function RegisterForm() {
  const [formError, setFormError] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const registerMutation = useRegisterMutation()

  const form = useAppForm({
    schema: registerSchema,
    defaultValues: {
      username: "",
      email: "",
      password: "",
      confirm_password: "",
    },
    onSubmit: async ({ value }) => {
      setFormError("")
      try {
        await registerMutation.mutateAsync(value)
      } catch (error) {
        setFormError(getApiErrorMessage(error))
      }
    },
  })

  return (
    <form
      data-testid="register-form"
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault()
        void form.handleSubmit()
      }}
    >
      {formError && (
        <div
          data-testid="error-message"
          className="animate-slide-in flex items-center gap-2 rounded-lg border border-danger/20 bg-danger-dim px-4 py-3 text-sm text-danger"
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

      <form.Field name="username">
        {(field) => (
          <TextField
            field={field}
            htmlFor="username"
            label="用户名"
            type="text"
            placeholder="请输入用户名"
            autoComplete="username"
            testid="username-input"
            errorTestid="username-error"
            isFocused={focusedField === "username"}
            onFocus={() => setFocusedField("username")}
            onBlur={() => setFocusedField(null)}
          />
        )}
      </form.Field>

      <form.Field name="email">
        {(field) => (
          <TextField
            field={field}
            htmlFor="email"
            label="邮箱"
            type="email"
            placeholder="请输入邮箱"
            autoComplete="email"
            testid="email-input"
            errorTestid="email-error"
            isFocused={focusedField === "email"}
            onFocus={() => setFocusedField("email")}
            onBlur={() => setFocusedField(null)}
          />
        )}
      </form.Field>

      <form.Field name="password">
        {(field) => (
          <PasswordField
            field={field}
            htmlFor="password"
            label="密码"
            placeholder="至少 8 位，包含字母和数字"
            autoComplete="new-password"
            testid="password-input"
            errorTestid="password-error"
            toggleTestid="password-toggle-button"
            isVisible={showPassword}
            onToggleVisible={() => setShowPassword((v) => !v)}
            isFocused={focusedField === "password"}
            onFocus={() => setFocusedField("password")}
            onBlur={() => setFocusedField(null)}
          />
        )}
      </form.Field>

      <form.Field name="confirm_password">
        {(field) => (
          <PasswordField
            field={field}
            htmlFor="confirm_password"
            label="确认密码"
            placeholder="请再次输入密码"
            autoComplete="new-password"
            testid="confirm-password-input"
            errorTestid="confirm-password-error"
            toggleTestid="confirm-password-toggle-button"
            isVisible={showConfirmPassword}
            onToggleVisible={() => setShowConfirmPassword((v) => !v)}
            isFocused={focusedField === "confirm_password"}
            onFocus={() => setFocusedField("confirm_password")}
            onBlur={() => setFocusedField(null)}
          />
        )}
      </form.Field>

      <form.Subscribe selector={(state) => state.isSubmitting}>
        {(isSubmitting) => (
          <button
            data-testid="submit-button"
            type="submit"
            disabled={isSubmitting || registerMutation.isPending}
            className="group relative w-full overflow-hidden rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-all duration-200 hover:bg-accent-hover hover:shadow-lg hover:shadow-accent/15 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="relative z-10 flex items-center justify-center gap-2">
              {isSubmitting || registerMutation.isPending ? (
                <>
                  <svg
                    className="h-4 w-4 animate-spin"
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
                  正在注册...
                </>
              ) : (
                "注 册"
              )}
            </span>
          </button>
        )}
      </form.Subscribe>
    </form>
  )
}
