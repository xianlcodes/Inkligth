import apiClient from './client'
import type { OutlineData } from './outline'

export interface PresentationItem {
  id: string
  literature_id: string | null
  literature_title: string | null
  slides: OutlineData['slides']
  slide_count: string | null
  created_at: string
  updated_at: string
}

export interface PresentationListData {
  total: number
  items: PresentationItem[]
}

export function getPresentations(limit = 50, offset = 0) {
  return apiClient.get<PresentationListData>('/presentations', {
    params: { limit, offset },
  })
}

export function getPresentation(id: string) {
  return apiClient.get<PresentationItem>(`/presentations/${id}`)
}

export function deletePresentation(id: string) {
  return apiClient.delete(`/presentations/${id}`)
}
