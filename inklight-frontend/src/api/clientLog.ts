/**
 * 前端错误上报：把浏览器端 JS 错误送到后端日志（POST /api/v1/client-logs）。
 *
 * 设计约束：
 * - 用原生 fetch 而非 axios：不经过 client.ts 拦截器，杜绝「上报失败再上报」死循环；
 * - 全程静默：上报本身绝不能抛错影响页面；
 * - 同一错误 10 秒内只报一次，防止渲染循环类错误刷爆后端；
 * - 只上报诊断信息（message/stack/url），不含业务数据。
 */

const ENDPOINT = '/api/v1/client-logs'
const DEDUP_WINDOW_MS = 10_000

export interface ClientErrorInput {
  level?: 'error' | 'warning'
  message: string
  stack?: string | null
  /** 出错 API 请求的 X-Request-ID（用于串联后端日志） */
  requestId?: string | null
}

const _recentMessages = new Map<string, number>()

function isDuplicate(key: string): boolean {
  const now = Date.now()
  const last = _recentMessages.get(key)
  _recentMessages.set(key, now)
  if (_recentMessages.size > 50) {
    // 只保留最近的记录，防止 Map 无限增长
    const oldestKey = _recentMessages.keys().next().value
    if (oldestKey !== undefined && _recentMessages.size > 50) {
      _recentMessages.delete(oldestKey)
    }
  }
  return last !== undefined && now - last < DEDUP_WINDOW_MS
}

export function reportClientError(input: ClientErrorInput): void {
  try {
    const message = String(input.message || '')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 480)
    if (!message || isDuplicate(message)) return

    const stack = String(input.stack || '')
      .slice(0, 3900)

    // fire-and-forget：任何失败都静默吞掉
    void fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        level: input.level || 'error',
        message,
        stack: stack || null,
        url: location.href.slice(0, 490),
        request_id: input.requestId || null,
      }),
      keepalive: true,
    }).catch(() => {})
  } catch {
    // 上报逻辑自身的异常一律吞掉
  }
}
