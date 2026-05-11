import { ReactNode } from "react"

import { useAuth } from "@/hooks/use-auth"

interface AdminRouteProps {
  children: ReactNode
}

export function AdminRoute({ children }: AdminRouteProps) {
  const { isAdmin, isLoading } = useAuth()

  if (isLoading) {
    return <div className="p-6 text-gray-500">加载中...</div>
  }

  if (!isAdmin) {
    return (
      <div className="p-6">
        <h2 className="text-xl font-semibold text-red-600">403</h2>
        <p className="mt-2 text-gray-500">权限不足</p>
      </div>
    )
  }

  return <>{children}</>
}
