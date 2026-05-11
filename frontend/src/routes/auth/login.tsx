import { createFileRoute, redirect } from "@tanstack/react-router"

import { LoginForm } from "@/components/auth/login-form"
import { getRefreshToken } from "@/stores/auth"

export const Route = createFileRoute("/auth/login")({
  beforeLoad: () => {
    if (getRefreshToken()) {
      throw redirect({ to: "/" })
    }
  },
  component: LoginPage,
})

function LoginPage() {
  return (
    <div className="flex min-h-screen">
      <div className="flex flex-1 items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600 p-10 text-white">
        <div className="text-center">
          <h2 className="mb-3 text-3xl font-bold text-white">Pivot</h2>
          <p className="text-sm opacity-80">智能数据管理平台</p>
        </div>
      </div>
      <div className="flex flex-1 items-center justify-center bg-white p-10">
        <div className="w-full max-w-sm">
          <LoginForm />
        </div>
      </div>
    </div>
  )
}
