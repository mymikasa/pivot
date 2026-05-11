import { Link, createFileRoute, redirect } from "@tanstack/react-router"

import { RegisterForm } from "@/components/auth/register-form"
import { getRefreshToken } from "@/stores/auth"

export const Route = createFileRoute("/auth/register")({
  beforeLoad: () => {
    if (getRefreshToken()) {
      throw redirect({ to: "/" })
    }
  },
  component: RegisterPage,
})

function RegisterPage() {
  return (
    <div className="relative flex min-h-screen overflow-hidden bg-surface-0 font-[var(--font-display)]">
      <div
        className="pointer-events-none absolute -left-32 -top-32 h-[600px] w-[600px] rounded-full blur-[120px]"
        style={{ background: "rgba(13, 148, 136, 0.07)" }}
      />
      <div
        className="pointer-events-none absolute -bottom-48 -right-48 h-[700px] w-[700px] rounded-full blur-[140px]"
        style={{ background: "rgba(94, 234, 212, 0.06)" }}
      />
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[400px] w-[400px] -translate-x-1/2 -translate-y-1/2 rounded-full blur-[100px]"
        style={{ background: "rgba(13, 148, 136, 0.03)" }}
      />

      <div className="relative z-10 hidden flex-col justify-between p-12 lg:flex lg:w-[55%]">
        <div>
          <div className="animate-fade-up flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-light">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <span className="text-lg font-semibold tracking-tight text-accent">
              Pivot
            </span>
          </div>
        </div>

        <div className="max-w-lg" style={{ animationDelay: "0.15s" }}>
          <h1
            className="animate-fade-up text-5xl font-bold leading-[1.1] tracking-tight text-text-primary"
            style={{ animationDelay: "0.2s" }}
          >
            从第一位用户开始
            <br />
            <span className="bg-gradient-to-r from-accent to-teal-400 bg-clip-text text-transparent">
              搭建业务知识中枢
            </span>
          </h1>
          <p
            className="animate-fade-up mt-6 text-lg leading-relaxed text-text-secondary"
            style={{ animationDelay: "0.35s" }}
          >
            创建账号后即可进入 Pivot，
            <br />
            将团队知识整理成可检索、可推理的 AI 工作流。
          </p>

          <div
            className="animate-fade-up mt-10 flex gap-8"
            style={{ animationDelay: "0.5s" }}
          >
            {[
              { value: "账号", label: "自助创建" },
              { value: "User", label: "默认角色" },
              { value: "安全", label: "密码加密" },
            ].map((stat) => (
              <div key={stat.label} className="group">
                <div className="font-mono text-2xl font-semibold text-accent transition-colors group-hover:text-accent-hover">
                  {stat.value}
                </div>
                <div className="mt-1 text-sm text-text-muted">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div
          className="animate-fade-up text-sm text-text-muted"
          style={{ animationDelay: "0.65s" }}
        >
          &copy; {new Date().getFullYear()} Pivot. 安全、可靠、高效。
        </div>
      </div>

      <div className="relative z-10 flex flex-1 items-center justify-center p-6 sm:p-10 lg:p-12">
        <div
          className="w-full max-w-[440px] animate-fade-up rounded-2xl border border-border-dim bg-white/80 p-8 shadow-xl shadow-black/[0.03] backdrop-blur-xl sm:p-10"
          style={{ animationDelay: "0.1s" }}
        >
          <div className="mb-8 lg:hidden">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-light">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--color-accent)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <span className="text-base font-semibold tracking-tight text-accent">
                Pivot
              </span>
            </div>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-semibold tracking-tight text-text-primary">
              创建账号
            </h2>
            <p className="mt-2 text-sm text-text-secondary">
              填写信息注册新账号
            </p>
          </div>

          <RegisterForm />

          <div className="mt-6 text-center text-sm text-text-secondary">
            已有账号？
            <Link
              to="/auth/login"
              data-testid="nav-login"
              className="font-semibold text-accent transition-colors hover:text-accent-hover"
            >
              去登录
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
