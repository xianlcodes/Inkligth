/**
 * 学术写作助手 API
 */

import apiClient from './client'

export interface WritingChatParams {
  message: string
  conversation_id?: string
  skill_names: string[]
  context_text?: string
}

export interface WritingChatResponse {
  reply: string
  conversation_id: string
  title: string
  skills_applied: string[]
}

export interface ConversationSummary {
  id: string
  title: string
  type: string
  created_at: string
  updated_at: string
}

export interface ConversationListResponse {
  total: number
  items: ConversationSummary[]
}

export interface ConversationMessageItem {
  id: number
  role: string
  content: string
  context_text: string | null
  created_at: string
}

export interface ConversationMessagesResponse {
  conversation_id: string
  title: string
  messages: ConversationMessageItem[]
}

export async function writingChat(params: WritingChatParams): Promise<WritingChatResponse> {
  const res = await apiClient.post('/writing/chat', params)
  return res.data
}

export async function getConversations(type?: string): Promise<ConversationListResponse> {
  const params = type ? { type } : {}
  const res = await apiClient.get('/writing/conversations', { params })
  return res.data
}

export async function getConversationMessages(id: string): Promise<ConversationMessagesResponse> {
  const res = await apiClient.get(`/writing/conversations/${id}/messages`)
  return res.data
}

export async function deleteConversation(id: string): Promise<void> {
  await apiClient.delete(`/writing/conversations/${id}`)
}
