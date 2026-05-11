import { createFileRoute } from "@tanstack/react-router"

import { AdminRoute } from "@/components/auth/admin-route"

export const Route = createFileRoute("/_authenticated/manage/users")({
  component: UsersPage,
})

function UsersPage() {
  return (
    <AdminRoute>
      <div>
        <h2 className="mb-4 text-xl font-semibold">用户管理</h2>
        <p className="text-gray-500">用户管理页面（待实现）</p>
      </div>
    </AdminRoute>
  )
}
