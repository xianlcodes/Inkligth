import apiClient from './client'

export interface ChatRequest {
  message: string
  context_text: string
  conversation_id?: string | null
}

export interface ChatResponse {
  reply: string
  conversation_id: string
}

export function chatWithPaper(literatureId: string, data: ChatRequest) {
  return apiClient.post<ChatResponse>(`/papers/${literatureId}/chat`, data)
}
