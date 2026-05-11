import { createFileRoute } from "@tanstack/react-router"

import { useAuth } from "@/hooks/use-auth"

export const Route = createFileRoute("/_authenticated/")({
  component: HomePage,
})

function HomePage() {
  const { user } = useAuth()

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold">
        你好，{user?.username}
      </h2>
      <p className="text-gray-500">欢迎回到 Pivot 管理平台</p>
    </div>
  )
}
