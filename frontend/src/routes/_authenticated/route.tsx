import { useState } from "react"
import {
  createFileRoute,
  Link,
  Outlet,
  redirect,
  useRouterState,
} from "@tanstack/react-router"

import { useAuth } from "@/hooks/use-auth"
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
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, isAdmin } = useAuth()
  const logoutMutation = useLogoutMutation()

  function handleLogout() {
    logoutMutation.mutate(undefined, {
      onSuccess: () => {
        window.location.href = "/auth/login"
      },
    })
  }

  return (
    <div className="flex h-screen bg-surface-1">
      <aside className="hidden lg:flex lg:w-60 lg:flex-col lg:fixed lg:inset-y-0 bg-sidebar">
        <SidebarContent
          user={user}
          isAdmin={isAdmin}
          onLogout={handleLogout}
        />
      </aside>

      <div
        className={`fixed inset-0 z-40 bg-black/40 transition-opacity duration-300 lg:hidden ${mobileOpen ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={() => setMobileOpen(false)}
      />
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-60 -translate-x-full bg-sidebar transition-transform duration-300 lg:hidden ${mobileOpen ? "translate-x-0" : ""}`}
      >
        <SidebarContent
          user={user}
          isAdmin={isAdmin}
          onLogout={handleLogout}
        />
      </aside>

      <div className="flex flex-1 flex-col lg:pl-60">
        <header className="flex items-center gap-3 border-b border-border-dim bg-white px-4 py-3 lg:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-md p-1.5 text-text-secondary hover:bg-surface-2"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </button>
          <span className="font-display text-base font-semibold text-text-primary">
            Pivot
          </span>
        </header>

        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function SidebarContent({
  user,
  isAdmin,
  onLogout,
}: {
  user: {
    username?: string
    email?: string
  } | null
  | undefined
  isAdmin: boolean
  onLogout: () => void
}) {
  const pathname = useRouterState({
    select: (s) => s.location.pathname,
  })

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center px-5">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent">
            <span className="text-sm font-bold text-white">P</span>
          </div>
          <span className="font-display text-lg font-semibold tracking-tight text-white">
            Pivot
          </span>
        </Link>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-2">
        <NavButton
          to="/"
          active={pathname === "/"}
          icon={
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
          }
        >
          概览
        </NavButton>

        <NavDisabled
          icon={
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M3 5v14a9 3 0 0 0 18 0V5" />
              <path d="M3 12a9 3 0 0 0 18 0" />
            </svg>
          }
        >
          知识库
        </NavDisabled>

        <NavDisabled
          icon={
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
            </svg>
          }
        >
          对话
        </NavDisabled>

        <NavDisabled
          icon={
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="4" y="4" width="16" height="16" rx="2" />
              <rect x="9" y="9" width="6" height="6" />
              <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3" />
            </svg>
          }
        >
          模型管理
        </NavDisabled>

        {isAdmin && (
          <>
            <div className="my-2 border-t border-sidebar-border" />
            <NavButton
              to="/manage/users"
              active={pathname.startsWith("/manage")}
              icon={
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              }
            >
              用户管理
            </NavButton>
          </>
        )}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/20 text-xs font-semibold text-accent">
            {user?.username?.[0]?.toUpperCase() ?? "?"}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-sidebar-text-active">
              {user?.username}
            </p>
            <p className="truncate text-xs text-sidebar-text">
              {user?.email}
            </p>
          </div>
          <button
            data-testid="logout-button"
            onClick={onLogout}
            className="rounded-md p-1.5 text-sidebar-text transition-colors hover:bg-sidebar-hover hover:text-sidebar-text-active"
            title="登出"
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
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

function NavButton({
  to,
  active,
  icon,
  children,
}: {
  to: string
  active: boolean
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <Link
      to={to}
      className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
        active
          ? "bg-sidebar-active text-sidebar-text-active [&_svg]:text-accent"
          : "text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active"
      }`}
    >
      {icon}
      {children}
    </Link>
  )
}

function NavDisabled({
  icon,
  children,
}: {
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-sidebar-text/40">
      {icon}
      <span className="flex-1">{children}</span>
      <span className="rounded bg-sidebar-text/10 px-1.5 py-0.5 text-[10px] font-medium leading-none">
        即将推出
      </span>
    </div>
  )
}
