import { useState } from "react"
import { z } from "zod"

import {
  getFieldErrorMessage,
  useAppForm,
} from "@/components/ui/tanstack-form"
import { useLoginMutation } from "@/data/auth"

const loginSchema = z.object({
  username: z.string().min(1, "请输入用户名"),
  password: z.string().min(1, "请输入密码"),
})

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

export function LoginForm() {
  const [showPassword, setShowPassword] = useState(false)
  const [formError, setFormError] = useState("")
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const loginMutation = useLoginMutation()

  const form = useAppForm({
    schema: loginSchema,
    defaultValues: { username: "", password: "" },
    onSubmit: async ({ value }) => {
      setFormError("")
      try {
        await loginMutation.mutateAsync(value)
        window.location.href = "/"
      } catch {
        setFormError("用户名或密码错误")
      }
    },
  })

  return (
    <form
      data-testid="login-form"
      className="space-y-5"
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
        {(field) => {
          const error = getFieldErrorMessage(field)
          const isFocused = focusedField === "username"
          return (
            <div className="space-y-1.5">
              <label
                htmlFor="username"
                className="block text-sm font-medium text-text-secondary transition-colors"
                style={{
                  color: isFocused ? "var(--color-accent)" : undefined,
                }}
              >
                用户名
              </label>
              <div className="relative">
                <div
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted transition-colors"
                  style={{
                    color: isFocused ? "var(--color-accent)" : undefined,
                  }}
                >
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
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
                <input
                  id="username"
                  data-testid="username-input"
                  type="text"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onFocus={() => setFocusedField("username")}
                  onBlur={() => {
                    field.handleBlur()
                    setFocusedField(null)
                  }}
                  placeholder="请输入用户名"
                  className="w-full rounded-lg border bg-surface-2 px-3 py-2.5 pl-10 text-sm text-text-primary placeholder-text-muted transition-all duration-200 focus:outline-none"
                  style={getInputStyle(isFocused, Boolean(error))}
                  autoComplete="username"
                />
              </div>
              {error && (
                <p
                  data-testid="username-error"
                  className="text-xs text-danger"
                >
                  {error}
                </p>
              )}
            </div>
          )
        }}
      </form.Field>

      <form.Field name="password">
        {(field) => {
          const error = getFieldErrorMessage(field)
          const isFocused = focusedField === "password"
          return (
            <div className="space-y-1.5">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-text-secondary transition-colors"
                style={{
                  color: isFocused ? "var(--color-accent)" : undefined,
                }}
              >
                密码
              </label>
              <div className="relative">
                <div
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted transition-colors"
                  style={{
                    color: isFocused ? "var(--color-accent)" : undefined,
                  }}
                >
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
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <input
                  id="password"
                  data-testid="password-input"
                  type={showPassword ? "text" : "password"}
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onFocus={() => setFocusedField("password")}
                  onBlur={() => {
                    field.handleBlur()
                    setFocusedField(null)
                  }}
                  placeholder="请输入密码"
                  className="w-full rounded-lg border bg-surface-2 px-3 py-2.5 pl-10 pr-10 text-sm text-text-primary placeholder-text-muted transition-all duration-200 focus:outline-none"
                  style={getInputStyle(isFocused, Boolean(error))}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  data-testid="password-toggle-button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted transition-colors hover:text-text-secondary"
                  tabIndex={-1}
                  aria-label={showPassword ? "隐藏密码" : "显示密码"}
                >
                  {showPassword ? (
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
              {error && (
                <p
                  data-testid="password-error"
                  className="text-xs text-danger"
                >
                  {error}
                </p>
              )}
            </div>
          )
        }}
      </form.Field>

      <form.Subscribe selector={(state) => state.isSubmitting}>
        {(isSubmitting) => (
          <button
            data-testid="submit-button"
            type="submit"
            disabled={isSubmitting || loginMutation.isPending}
            className="group relative w-full overflow-hidden rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-all duration-200 hover:bg-accent-hover hover:shadow-lg hover:shadow-accent/15 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="relative z-10 flex items-center justify-center gap-2">
              {isSubmitting || loginMutation.isPending ? (
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
                  正在验证...
                </>
              ) : (
                "登 录"
              )}
            </span>
          </button>
        )}
      </form.Subscribe>
    </form>
  )
}
