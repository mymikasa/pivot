import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"

import { useLogoutMutation } from "@/data/auth"
import { getRefreshToken } from "@/stores/auth"

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: () => {
    if (!getRefreshToken()) {
      throw redirect({ to: "/auth/login" })
    }
  },
  component: AuthenticatedLayout,
})

function AuthenticatedLayout() {
  const logoutMutation = useLogoutMutation()

  function handleLogout() {
    logoutMutation.mutate(undefined, {
      onSuccess: () => {
        window.location.href = "/auth/login"
      },
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="flex items-center justify-between border-b bg-white px-6 py-3">
        <span className="text-lg font-semibold">Pivot</span>
        <button
          data-testid="logout-button"
          onClick={handleLogout}
          className="rounded-md px-3 py-1 text-sm text-gray-600 hover:bg-gray-100"
        >
          登出
        </button>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  )
}
