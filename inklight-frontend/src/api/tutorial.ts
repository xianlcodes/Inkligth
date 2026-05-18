import apiClient from './client'

export interface TutorialSummary {
  id: string
  title: string
  summary: string | null
  is_published: boolean
  published_at: string | null
  created_by: string
  created_at: string
  updated_at: string
  version_count: number
}

export interface TutorialDetail extends TutorialSummary {
  content: string
}

export interface TutorialListResponse {
  total: number
  items: TutorialSummary[]
}

export interface TutorialVersion {
  id: string
  tutorial_id: string
  version_number: number
  title: string
  content: string
  summary: string | null
  created_by: string
  created_at: string
}

export interface TutorialVersionListResponse {
  items: TutorialVersion[]
}

export interface ImageUploadResponse {
  code: number
  msg: string
  data: {
    url: string
    filename: string
  }
}

export function listTutorials(skip = 0, limit = 50) {
  return apiClient.get<TutorialListResponse>('/tutorials', { params: { skip, limit } })
}

export function getTutorial(id: string) {
  return apiClient.get<TutorialDetail>(`/tutorials/${id}`)
}

export function createTutorial(data: { title: string; content?: string; summary?: string }) {
  return apiClient.post<TutorialDetail>('/tutorials', data)
}

export function updateTutorial(id: string, data: Record<string, unknown>) {
  return apiClient.patch<TutorialDetail>(`/tutorials/${id}`, data)
}

export function deleteTutorial(id: string) {
  return apiClient.delete(`/tutorials/${id}`)
}

export function uploadTutorialImage(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post<ImageUploadResponse>('/tutorials/images/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listTutorialVersions(tutorialId: string) {
  return apiClient.get<TutorialVersionListResponse>(`/tutorials/${tutorialId}/versions`)
}

export function restoreTutorialVersion(tutorialId: string, versionId: string) {
  return apiClient.post<TutorialDetail>(`/tutorials/${tutorialId}/versions/${versionId}/restore`)
}

export function listPublishedTutorials(skip = 0, limit = 20) {
  return apiClient.get<TutorialListResponse>('/tutorials/published', { params: { skip, limit } })
}

export function getPublishedTutorial(id: string) {
  return apiClient.get<TutorialDetail>(`/tutorials/published/${id}`)
}