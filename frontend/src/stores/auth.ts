const REFRESH_TOKEN_KEY = "pivot_refresh_token"

let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens(access: string, refresh: string): void {
  accessToken = access
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
}

export function clearTokens(): void {
  accessToken = null
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function initAuth(): void {
  const refresh = getRefreshToken()
  if (refresh) {
    accessToken = null
  }
}
