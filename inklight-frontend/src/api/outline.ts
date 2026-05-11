import apiClient from './client'

export interface SlideData {
  title: string
  bullets: string[]
  notes?: string
}

export interface OutlineData {
  slides: SlideData[]
}

export function generateOutline(literatureId: string) {
  return apiClient.post<OutlineData>(`/literatures/${literatureId}/presentation-outline`)
}

export function downloadOutlinePptx(literatureId: string) {
  return apiClient.get(`/literatures/${literatureId}/presentation-outline/pptx`, {
    responseType: 'blob',
  })
}