import type { AxiosResponse } from "axios"

export async function handleApiResponse<T>(response: AxiosResponse<T>): Promise<T> {
  return response.data
}
