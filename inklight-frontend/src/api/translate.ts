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

export function deleteFullTranslation(literatureId: string) {
  return apiClient.delete<{ message: string }>(`/literatures/${literatureId}/translate/full`)
}

export function getTaskStatus(taskId: string) {
  return apiClient.get<TaskStatusResponse>(`/tasks/${taskId}`)
}

export function cancelTask(taskId: string) {
  return apiClient.post<{ code: number; msg: string; data: Record<string, unknown> }>(`/tasks/${taskId}/cancel`)
}

export function cleanupExpiredTranslations() {
  return apiClient.post<{ code: number; msg: string; data: { deleted: number; cutoff: string; ttl_days: number } }>('/tasks/translations/cleanup')
}

export async function translateTextStream(
  data: TranslateRequest,
  onChunk: (chunk: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
): Promise<void> {
  const token = localStorage.getItem('token')
  let response: Response
  try {
    response = await fetch('/api/v1/translate/text/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
    })
  } catch (err: any) {
    onError(err?.message || '网络请求失败')
    return
  }

  if (!response.ok) {
    let errorText = ''
    try {
      errorText = await response.text()
    } catch {
      // ignore
    }
    onError(errorText || `翻译请求失败 (${response.status})`)
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    onError('无法读取响应流')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  function processLines(lines: string[]): boolean {
    for (const line of lines) {
      if (line === '' || line === '\r') continue
      const trimmed = line.trim()
      if (!trimmed) continue
      if (trimmed.startsWith('data:')) {
        const data = trimmed.slice(5).trim()
        if (data === '[DONE]') {
          onDone()
          return true
        }
        if (data.startsWith('[ERROR]')) {
          onError(data.slice(7).trim())
          return true
        }
        onChunk(data)
      }
    }
    return false
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      if (processLines(lines)) return
    }

    const finalChunk = decoder.decode()
    if (finalChunk) {
      buffer += finalChunk
    }
    if (buffer.trim()) {
      const remaining = buffer.split('\n')
      if (processLines(remaining)) return
    }
  } catch (err: any) {
    onError(err?.message || '流读取失败')
    return
  }

  onDone()
}
