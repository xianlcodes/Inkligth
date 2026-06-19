import apiClient from './client'

export interface AIEngine {
  id: string
  user_id: string
  provider: string
  api_base: string
  api_key_mask: string
  default_model: string
  fallback_models: string | null
  is_default: boolean
  proxy_enabled: boolean
  created_at: string
  updated_at: string
}

export interface AIEngineListResponse {
  total: number
  items: AIEngine[]
}

export interface AIEngineCreatePayload {
  provider: string
  api_base: string
  api_key: string
  default_model: string
  fallback_models?: string
  is_default?: boolean
  proxy_enabled?: boolean
}

export interface AIEngineUpdatePayload {
  provider?: string
  api_base?: string
  api_key?: string
  default_model?: string
  fallback_models?: string
  is_default?: boolean
  proxy_enabled?: boolean
}

export interface AIEngineTestResult {
  success: boolean
  message: string
  models: string[]
}

export async function fetchEngines(): Promise<AIEngineListResponse> {
  const res = await apiClient.get<AIEngineListResponse>('/ai-engines')
  return res.data
}

export async function fetchEngine(engineId: string): Promise<AIEngine> {
  const res = await apiClient.get<AIEngine>(`/ai-engines/${engineId}`)
  return res.data
}

export async function createEngine(payload: AIEngineCreatePayload): Promise<AIEngine> {
  const res = await apiClient.post<AIEngine>('/ai-engines', payload)
  return res.data
}

export async function updateEngine(engineId: string, payload: AIEngineUpdatePayload): Promise<AIEngine> {
  const res = await apiClient.patch<AIEngine>(`/ai-engines/${engineId}`, payload)
  return res.data
}

export async function deleteEngine(engineId: string): Promise<void> {
  await apiClient.delete(`/ai-engines/${engineId}`)
}

export async function testEngine(engineId: string): Promise<AIEngineTestResult> {
  const res = await apiClient.post<AIEngineTestResult>(`/ai-engines/${engineId}/test`)
  return res.data
}

export async function setDefaultEngine(engineId: string): Promise<void> {
  await apiClient.post(`/ai-engines/${engineId}/set-default`)
}
