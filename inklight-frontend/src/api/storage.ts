import apiClient from './client'

export interface StorageInfo {
  total_space: number
  used_space: number
  remaining_space: number
  base_space: number
  check_in_bonus: number
  invitation_bonus: number
}

export async function getStorage(): Promise<StorageInfo> {
  const res = await apiClient.get('/storage')
  return res.data
}