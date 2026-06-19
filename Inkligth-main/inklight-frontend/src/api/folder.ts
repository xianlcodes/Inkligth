import apiClient from './client'

export interface FolderItem {
  id: string
  user_id: string
  name: string
  parent_id: string | null
  literature_count: number
  created_at: string
  updated_at: string
}

export interface FolderListResponse {
  items: FolderItem[]
}

export function getFolders() {
  return apiClient.get<FolderListResponse>('/folders')
}

export function createFolder(name: string) {
  return apiClient.post<FolderItem>('/folders', { name })
}

export function renameFolder(id: string, name: string) {
  return apiClient.patch<FolderItem>(`/folders/${id}`, { name })
}

export function deleteFolder(id: string) {
  return apiClient.delete(`/folders/${id}`)
}
