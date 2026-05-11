import apiClient from './client'

export interface TranslateRequest {
  text: string
  source_lang?: string
  target_lang?: string
}

export interface TranslateResponse {
  source_text: string
  translated_text: string
  source_lang: string
  target_lang: string
}

export interface FullTranslateResponse {
  task_id: string
  message: string
}

export interface TaskStatusResponse {
  task_id: string
  task_type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  total: number
  result: Record<string, unknown> | null
  error: string | null
}

export interface TranslatedParagraph {
  paragraph_index: number
  original: string
  translated: string
}

export function translateText(data: TranslateRequest) {
  return apiClient.post<TranslateResponse>('/translate/text', data)
}

export function startFullTranslate(literatureId: string) {
  return apiClient.post<FullTranslateResponse>(`/literatures/${literatureId}/translate/full`)
}

export function getTaskStatus(taskId: string) {
  return apiClient.get<TaskStatusResponse>(`/tasks/${taskId}`)
}
