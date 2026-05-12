import type { AxiosResponse } from "axios"

export async function handleApiResponse<T>(
  response: AxiosResponse<T> | { data: T },
): Promise<T> {
  return response.data
}
