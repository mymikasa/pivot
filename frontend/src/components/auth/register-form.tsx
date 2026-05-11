import { type FormEvent, useState } from "react"
import { isAxiosError } from "axios"
import { z } from "zod"

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

interface RegisterFormData {
  username: string
  email: string
  password: string
  confirm_password: string
}

type RegisterFormField = keyof RegisterFormData

type FieldErrors = Partial<Record<RegisterFormField, string>>

interface ApiErrorResponse {
  detail?: string | Array<{ msg?: string }>
}

function getApiErrorMessage(error: unknown): string {
  if (isAxiosError<ApiErrorResponse>(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") {
      return detail
    }
    if (Array.isArray(detail) && detail[0]?.msg) {
      return detail[0].msg
    }
  }
  return "注册失败，请稍后重试"
}

function getFieldErrors(data: RegisterFormData): FieldErrors {
  const result = registerSchema.safeParse(data)
  if (result.success) {
    return {}
  }

  return result.error.issues.reduce<FieldErrors>((errors, issue) => {
    const field = issue.path[0]
    if (
      typeof field === "string" &&
      field in data &&
      !errors[field as RegisterFormField]
    ) {
      errors[field as RegisterFormField] = issue.message
    }
    return errors
  }, {})
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

export function RegisterForm() {
  const [formData, setFormData] = useState<RegisterFormData>({
    username: "",
    email: "",
    password: "",
    confirm_password: "",
  })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [focusedField, setFocusedField] = useState<RegisterFormField | null>(
    null,
  )
  const registerMutation = useRegisterMutation()

  function updateField(field: RegisterFormField, value: string) {
    setFormData((current) => ({ ...current, [field]: value }))
    setFieldErrors((current) => ({ ...current, [field]: undefined }))
    setFormError("")
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setFormError("")

    const errors = getFieldErrors(formData)
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }

    try {
      await registerMutation.mutateAsync(formData)
    } catch (error) {
      setFormError(getApiErrorMessage(error))
    }
  }

  function renderTextField(
    field: Extract<RegisterFormField, "username" | "email">,
    label: string,
    type: "text" | "email",
    placeholder: string,
  ) {
    const hasError = Boolean(fieldErrors[field])
    const isFocused = focusedField === field

    return (
      <div className="space-y-1.5">
        <label
          htmlFor={field}
          className="block text-sm font-medium text-text-secondary transition-colors"
          style={{
            color: isFocused ? "var(--color-accent)" : undefined,
          }}
        >
          {label}
        </label>
        <div className="relative">
          <input
            id={field}
            data-testid={`${field}-input`}
            type={type}
            value={formData[field]}
            onChange={(event) => updateField(field, event.target.value)}
            onFocus={() => setFocusedField(field)}
            onBlur={() => setFocusedField(null)}
            placeholder={placeholder}
            className="w-full rounded-lg border bg-surface-2 px-3 py-2.5 text-sm text-text-primary placeholder-text-muted transition-all duration-200 focus:outline-none"
            style={getInputStyle(isFocused, hasError)}
            autoComplete={field}
          />
        </div>
        {hasError && (
          <p data-testid={`${field}-error`} className="text-xs text-danger">
            {fieldErrors[field]}
          </p>
        )}
      </div>
    )
  }

  function renderPasswordField(
    field: Extract<RegisterFormField, "password" | "confirm_password">,
    label: string,
    placeholder: string,
    isVisible: boolean,
    onToggleVisible: () => void,
  ) {
    const hasError = Boolean(fieldErrors[field])
    const isFocused = focusedField === field

    return (
      <div className="space-y-1.5">
        <label
          htmlFor={field}
          className="block text-sm font-medium text-text-secondary transition-colors"
          style={{
            color: isFocused ? "var(--color-accent)" : undefined,
          }}
        >
          {label}
        </label>
        <div className="relative">
          <input
            id={field}
            data-testid={
              field === "confirm_password"
                ? "confirm-password-input"
                : "password-input"
            }
            type={isVisible ? "text" : "password"}
            value={formData[field]}
            onChange={(event) => updateField(field, event.target.value)}
            onFocus={() => setFocusedField(field)}
            onBlur={() => setFocusedField(null)}
            placeholder={placeholder}
            className="w-full rounded-lg border bg-surface-2 px-3 py-2.5 pr-10 text-sm text-text-primary placeholder-text-muted transition-all duration-200 focus:outline-none"
            style={getInputStyle(isFocused, hasError)}
            autoComplete={field === "password" ? "new-password" : "new-password"}
          />
          <button
            type="button"
            data-testid={
              field === "confirm_password"
                ? "confirm-password-toggle-button"
                : "password-toggle-button"
            }
            onClick={onToggleVisible}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted transition-colors hover:text-text-secondary"
            aria-label={isVisible ? `隐藏${label}` : `显示${label}`}
          >
            {isVisible ? (
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
            )}
          </button>
        </div>
        {hasError && (
          <p
            data-testid={
              field === "confirm_password"
                ? "confirm-password-error"
                : "password-error"
            }
            className="text-xs text-danger"
          >
            {fieldErrors[field]}
          </p>
        )}
      </div>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="register-form"
      className="space-y-4"
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

      {renderTextField("username", "用户名", "text", "请输入用户名")}
      {renderTextField("email", "邮箱", "email", "请输入邮箱")}
      {renderPasswordField(
        "password",
        "密码",
        "至少 8 位，包含字母和数字",
        showPassword,
        () => setShowPassword((value) => !value),
      )}
      {renderPasswordField(
        "confirm_password",
        "确认密码",
        "请再次输入密码",
        showConfirmPassword,
        () => setShowConfirmPassword((value) => !value),
      )}

      <button
        data-testid="submit-button"
        type="submit"
        disabled={registerMutation.isPending}
        className="group relative w-full overflow-hidden rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-all duration-200 hover:bg-accent-hover hover:shadow-lg hover:shadow-accent/15 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span className="relative z-10 flex items-center justify-center gap-2">
          {registerMutation.isPending ? (
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
    </form>
  )
}
