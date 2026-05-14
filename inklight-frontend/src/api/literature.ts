import apiClient from './client'

export interface Literature {
  id: string
  user_id: string
  title: string | null
  authors: string | null
  abstract: string | null
  year: string | null
  journal: string | null
  doi: string | null
  file_path: string
  raw_text: string | null
  translated_text: string | null
  translated_at: string | null
  status: 'unread' | 'reading' | 'read'
  folder_id: string | null
  created_at: string
  updated_at: string
}

export interface LiteratureListResponse {
  total: number
  items: Literature[]
}

export interface LiteratureQuery {
  skip?: number
  limit?: number
  title?: string
  status?: string
  sort_by_year?: string
  folder_id?: string
}

export function uploadLiterature(file: File, folderId?: string) {
  const formData = new FormData()
  formData.append('file', file)
  const params: Record<string, string> = {}
  if (folderId) params.folder_id = folderId
  return apiClient.post<Literature>('/literatures', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    params,
  })
}

export function getLiteratures(params?: LiteratureQuery) {
  return apiClient.get<LiteratureListResponse>('/literatures', { params })
}

export function getLiterature(id: string) {
  return apiClient.get<Literature>(`/literatures/${id}`)
}

export function updateLiteratureStatus(id: string, status: string) {
  return apiClient.patch<Literature>(`/literatures/${id}`, { status })
}

export function updateLiterature(id: string, data: Partial<Literature>) {
  return apiClient.patch<Literature>(`/literatures/${id}`, data)
}

export function updateLiteratureFolder(id: string, folderId: string | null) {
  return apiClient.patch<Literature>(`/literatures/${id}`, { folder_id: folderId })
}

export function getLiteratureFileBlob(id: string) {
  return apiClient.get(`/literatures/${id}/file`, { responseType: 'blob' })
}

export function deleteLiterature(id: string) {
  return apiClient.delete(`/literatures/${id}`)
}
