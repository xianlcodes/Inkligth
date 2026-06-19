import apiClient from './client'

export interface FeedbackSubmit {
  content: string
  page_url?: string
  browser_info?: string
}

export interface FeedbackItem {
  id: string
  user_id: string
  user_email: string | null
  user_name: string | null
  content: string
  page_url: string | null
  browser_info: string | null
  is_resolved: boolean
  created_at: string
}

export interface FeedbackList {
  total: number
  items: FeedbackItem[]
}

export function submitFeedback(data: FeedbackSubmit) {
  return apiClient.post<FeedbackItem>('/feedback', data)
}

export function listFeedback(params: { skip?: number; limit?: number; resolved?: boolean }) {
  return apiClient.get<FeedbackList>('/feedback', { params })
}

export function resolveFeedback(id: string) {
  return apiClient.post<FeedbackItem>(`/feedback/${id}/resolve`)
}
