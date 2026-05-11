import { queryOptions, useMutation } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import { handleApiResponse } from "@/lib/api-utils"
import { request } from "@/lib/request"
import { clearTokens, setTokens } from "@/stores/auth"

interface LoginRequest {
  username: string
  password: string
}

interface RegisterRequest {
  username: string
  email: string
  password: string
  confirm_password: string
}

interface MessageResponse {
  message: string
}

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: {
    id: number
    username: string
    email: string
    role: string
    is_active: boolean
  }
}

interface UserInfo {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
}

export function useLoginMutation() {
  return useMutation({
    mutationFn: async (body: LoginRequest) => {
      return handleApiResponse(await request.post<LoginResponse>("/auth/login", body))
    },
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token)
    },
  })
}

export function useRegisterMutation() {
  const navigate = useNavigate()

  return useMutation({
    mutationFn: async (body: RegisterRequest) => {
      return handleApiResponse(
        await request.post<MessageResponse>("/auth/register", body),
      )
    },
    onSuccess: () => {
      void navigate({ to: "/auth/login" })
    },
  })
}

export function useLogoutMutation() {
  return useMutation({
    mutationFn: async () => {
      return handleApiResponse(await request.post("/auth/logout"))
    },
    onSuccess: () => {
      clearTokens()
    },
  })
}

export function currentUserOptions() {
  return queryOptions({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      return handleApiResponse(await request.get<UserInfo>("/users/me"))
    },
    retry: false,
  })
}
