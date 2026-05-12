import axios from "axios"

import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/stores/auth"

const request = axios.create({
  baseURL: "/api",
  timeout: 10000,
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

request.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
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
              resolve(request(originalRequest))
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
        // m-jwt skill 默认 refresh 不 rotate，后端仅返回新 access；本地 refresh 沿用旧值
        setTokens(data.access_token, refreshToken)
        processQueue(null, data.access_token)
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        return request(originalRequest)
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

export { request }
