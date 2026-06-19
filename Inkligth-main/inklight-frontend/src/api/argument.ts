/**
 * Argument Companion API client
 *
 * 论文评审系统 API 封装，包括：
 * - 承诺台账 (Ledger) — 构建、查询、更新
 * - 多角度评审 (Review) — 运行、查询、答辩
 */

import apiClient from './client'

// ── Types ──

export interface PromiseResponse {
  id: string
  claim_text: string
  claim_anchor?: string
  claim_section?: string
  status: string
  severity: string
  discharge_text?: string
  discharge_anchor?: string
  user_overridden: boolean
  user_status?: string
  created_at: string
}

export interface LedgerResponse {
  id: string
  literature_id: string
  title?: string
  status: string
  checksum?: string
  promises: PromiseResponse[]
  created_at: string
  updated_at: string
}

export interface ReviewPointResponse {
  id: string
  category: string
  severity: string
  title: string
  description: string
  suggestion?: string
  anchor_ref?: string
  rebuttal?: string
  rebuttal_status?: string
  reviewer_response?: string
  created_at: string
}

export interface ReviewSessionResponse {
  id: string
  literature_id: string
  mode: string
  status: string
  overall_assessment?: string
  strengths?: string
  top_issues?: string
  points: ReviewPointResponse[]
  created_at: string
  updated_at: string
}

export interface HistoryResponse {
  ledgers: Array<{
    id: string
    literature_id: string
    title?: string
    status: string
    created_at: string
    updated_at: string
  }>
  review_sessions: Array<{
    id: string
    literature_id: string
    mode: string
    status: string
    overall_assessment?: string
    created_at: string
    updated_at: string
  }>
}

// ── Ledger API ──

/**
 * 构建承诺台账（SSE 流式）
 * 返回 EventSource URL，前端用 EventSource 消费
 */
export function buildLedger(literatureId: string, mode: 'full' | 'incremental' = 'full'): string {
  const baseUrl = apiClient.defaults.baseURL || ''
  const token = localStorage.getItem('token')
  const params = new URLSearchParams({ literature_id: literatureId, mode })
  return `${baseUrl}/argument/ledger/build?${params}&token=${token}`
}

/**
 * 获取台账详情
 */
export async function getLedger(ledgerId: string): Promise<LedgerResponse> {
  const { data } = await apiClient.get(`/argument/ledger/${ledgerId}`)
  return data
}

/**
 * 按论文 ID 获取台账
 */
export async function getLedgerByLiterature(literatureId: string): Promise<LedgerResponse | null> {
  const { data } = await apiClient.get(`/argument/ledger/by-lit/${literatureId}`)
  return data
}

/**
 * 更新承诺状态（用户手动覆盖）
 */
export async function updatePromise(
  promiseId: string,
  userStatus: 'paid' | 'partial' | 'unpaid' | 'mismatch',
): Promise<void> {
  await apiClient.put(`/argument/ledger/promise/${promiseId}`, {
    user_status: userStatus,
    user_overridden: true,
  })
}

// ── Review API ──

/**
 * 运行论文评审（SSE 流式）
 */
export function runReview(
  literatureId: string,
  perspectives: string[] = ['methodology', 'experiment', 'writing', 'devils_advocate'],
  mode: 'serial' | 'parallel' = 'parallel',
): string {
  const baseUrl = apiClient.defaults.baseURL || ''
  const token = localStorage.getItem('token')
  const params = new URLSearchParams({
    literature_id: literatureId,
    mode,
    perspectives: perspectives.join(','),
  })
  return `${baseUrl}/argument/review/run?${params}&token=${token}`
}

/**
 * 获取评审详情
 */
export async function getReview(sessionId: string): Promise<ReviewSessionResponse> {
  const { data } = await apiClient.get(`/argument/review/${sessionId}`)
  return data
}

/**
 * 按论文 ID 获取最新评审
 */
export async function getReviewByLiterature(literatureId: string): Promise<ReviewSessionResponse | null> {
  const { data } = await apiClient.get(`/argument/review/by-lit/${literatureId}`)
  return data
}

// ── Rebuttal API ──

/**
 * 作者提交答辩
 */
export async function submitRebuttal(
  sessionId: string,
  pointId: string,
  message: string,
): Promise<{ point_id: string; session_id: string; rebuttal_status: string; reviewer_response: string | null }> {
  const { data } = await apiClient.post('/argument/review/rebuttal', {
    session_id: sessionId,
    point_id: pointId,
    message,
  })
  return data
}

/**
 * 审稿人回复
 */
export async function reviewerRespond(
  sessionId: string,
  pointId: string,
  message: string,
): Promise<{ point_id: string; session_id: string; rebuttal_status: string; reviewer_response: string }> {
  const { data } = await apiClient.post('/argument/review/respond', {
    session_id: sessionId,
    point_id: pointId,
    message,
  })
  return data
}

// ── History ──

/**
 * 获取用户的历史记录
 */
export async function getArgumentHistory(
  skip = 0,
  limit = 20,
): Promise<HistoryResponse> {
  const { data } = await apiClient.get('/argument/history', {
    params: { skip, limit },
  })
  return data
}

// ── SSE Helpers ──

interface SSEHandlers {
  onProgress?: (data: Record<string, unknown>) => void
  onReviewPoint?: (data: Record<string, unknown>) => void
  onPromiseExtracted?: (data: Record<string, unknown>) => void
  onPromiseChecked?: (data: Record<string, unknown>) => void
  onAnchored?: (data: Record<string, unknown>) => void
  onSynthesizing?: (data: Record<string, unknown>) => void
  onAssessment?: (data: Record<string, unknown>) => void
  onComplete?: (data: Record<string, unknown>) => void
  onError?: (message: string) => void
}

/**
 * 通过 POST 建立 SSE 连接（用于需要发送 request body 的端点）
 *
 * 用法:
 * ```ts
 * const abort = connectSSEPost('/api/v1/argument/ledger/build', body, handlers)
 * // abort() 来取消
 * ```
 */
export function connectSSEPost(
  url: string,
  body: Record<string, unknown>,
  handlers: SSEHandlers,
): AbortController {
  const controller = new AbortController()

  const eventMap: Record<string, (data: Record<string, unknown>) => void> = {
    progress: handlers.onProgress || (() => {}),
    review_point: handlers.onReviewPoint || (() => {}),
    promise_extracted: handlers.onPromiseExtracted || (() => {}),
    promise_checked: handlers.onPromiseChecked || (() => {}),
    anchored: handlers.onAnchored || (() => {}),
    synthesizing: handlers.onSynthesizing || (() => {}),
    assessment: handlers.onAssessment || (() => {}),
    complete: handlers.onComplete || (() => {}),
  }

  const token = localStorage.getItem('token')

  ;(async () => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (!response.ok) {
        const errText = await response.text().catch(() => 'Unknown error')
        if (handlers.onError) handlers.onError(`HTTP ${response.status}: ${errText}`)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        if (handlers.onError) handlers.onError('Response body is not readable')
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      let currentEvent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || trimmed.startsWith(':')) continue

          if (trimmed.startsWith('event: ')) {
            currentEvent = trimmed.slice(7).trim()
          } else if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.slice(6)
            try {
              const parsed = JSON.parse(dataStr)
              const handler = eventMap[currentEvent]
              if (handler) {
                handler(parsed)
              }
            } catch {
              // ignore parse errors for individual events
            }
            currentEvent = ''
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return
      if (handlers.onError) handlers.onError(err.message || 'SSE connection failed')
    }
  })()

  return controller
}

/**
 * 构建承诺台账（POST SSE 流式）
 * 返回 AbortController，调用 abort() 取消
 */
export function buildLedgerSSE(
  literatureId: string,
  handlers: SSEHandlers,
  mode: 'full' | 'incremental' = 'full',
): AbortController {
  const baseUrl = apiClient.defaults.baseURL || ''
  return connectSSEPost(
    `${baseUrl}/argument/ledger/build`,
    { literature_id: literatureId, mode },
    handlers,
  )
}

/**
 * 运行论文评审（POST SSE 流式）
 * 返回 AbortController，调用 abort() 取消
 */
export function runReviewSSE(
  literatureId: string,
  handlers: SSEHandlers,
  perspectives: string[] = ['methodology', 'experiment', 'writing', 'devils_advocate'],
  mode: 'serial' | 'parallel' = 'parallel',
): AbortController {
  const baseUrl = apiClient.defaults.baseURL || ''
  return connectSSEPost(
    `${baseUrl}/argument/review/run`,
    { literature_id: literatureId, perspectives, mode },
    handlers,
  )
}
