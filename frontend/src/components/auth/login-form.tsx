import { useState } from "react"

import { useLoginMutation } from "@/data/auth"

export function LoginForm() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const loginMutation = useLoginMutation()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    try {
      await loginMutation.mutateAsync({ username, password })
      window.location.href = "/"
    } catch {
      setError("用户名或密码错误")
    }
  }

  return (
    <form onSubmit={handleSubmit} data-testid="login-form">
      <h3 className="mb-2 text-xl font-semibold">欢迎回来</h3>
      <p className="mb-6 text-sm text-gray-500">请登录你的账号</p>

      {error && (
        <div data-testid="error-message" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="mb-4">
        <label className="mb-1 block text-sm text-gray-600">用户名</label>
        <input
          data-testid="username-input"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="请输入用户名"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          required
        />
      </div>

      <div className="mb-6">
        <label className="mb-1 block text-sm text-gray-600">密码</label>
        <input
          data-testid="password-input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="请输入密码"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          required
        />
      </div>

      <button
        data-testid="submit-button"
        type="submit"
        disabled={loginMutation.isPending}
        className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {loginMutation.isPending ? "登录中..." : "登 录"}
      </button>
    </form>
  )
}
