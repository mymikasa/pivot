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

interface UserInfo {
  id: string
  username: string
  email: string
  role: string
  is_active: boolean
}

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: UserInfo
}

interface CurrentUserResponse {
  user: UserInfo
}

export function useLoginMutation() {
  return useMutation({
    mutationFn: async (body: LoginRequest) => {
      return handleApiResponse(
        await request.post<LoginResponse>("/v1/users/login", body),
      )
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
      // 后端不消费 confirm_password，前端表单层已做一致性校验
      const { username, email, password } = body
      return handleApiResponse(
        await request.post<MessageResponse>("/v1/users/register", {
          username,
          email,
          password,
        }),
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
      return handleApiResponse(await request.post("/v1/users/logout"))
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
      const data = await handleApiResponse(
        await request.get<CurrentUserResponse>("/v1/users/me"),
      )
      return data.user
    },
    retry: false,
  })
}
