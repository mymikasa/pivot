import { useQuery } from "@tanstack/react-query"

import { currentUserOptions } from "@/data/auth"
import { getRefreshToken } from "@/stores/auth"

export function useAuth() {
  const hasToken = !!getRefreshToken()
  const { data: user, isLoading } = useQuery({
    ...currentUserOptions(),
    enabled: hasToken,
  })

  return {
    user,
    isLoading: hasToken && isLoading,
    isAuthenticated: !!user,
    isAdmin: user?.role === "admin",
  }
}
