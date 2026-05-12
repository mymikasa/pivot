import axios from "axios"

import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/stores/auth"

const apiClient = axios.create({
  timeout: 30000,
})

let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (token) {
      resolve(token)
    } else {
      reject(error)
    }
  })
  failedQueue = []
}

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    const shouldRefresh =
      error.response?.status === 401 ||
      (error.response?.status === 403 && !getAccessToken())

    if (shouldRefresh && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              originalRequest.headers.Authorization = `Bearer ${token}`
              resolve(apiClient(originalRequest))
            },
            reject,
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        clearTokens()
        window.location.href = "/auth/login"
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post("/api/v1/users/refresh", {
          refresh_token: refreshToken,
        })
        setTokens(data.access_token, refreshToken)
        processQueue(null, data.access_token)
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        clearTokens()
        processQueue(refreshError, null)
        window.location.href = "/auth/login"
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

export const createClientConfig = (config: Record<string, unknown>) => ({
  ...config,
  axios: apiClient,
})
