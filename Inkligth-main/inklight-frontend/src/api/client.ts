import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type Router from 'vue-router'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 60000
})

let _memoryToken: string | null = null
let _memoryRefreshToken: string | null = null

let _isRefreshing = false
let _pendingRequests: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

let _router: Router | null = null

let _onUnauthorized: (() => void) | null = null

export function setRouter(router: Router) {
  _router = router
}

/**
 * 注入「清除认证状态」回调，用于清空 Pinia auth store。
 * 避免 401 重定向时路由守卫因 store.token 未清而循环调用 fetchUser()。
 */
export function setOnUnauthorized(callback: () => void) {
  _onUnauthorized = callback
}

export function setApiToken(token: string | null) {
  _memoryToken = token
  try {
    if (token) {
      localStorage.setItem('token', token)
    } else {
      localStorage.removeItem('token')
    }
  } catch {
    // localStorage 不可用时静默跳过
  }
}

export function getApiToken(): string | null {
  try {
    const lsToken = localStorage.getItem('token')
    if (lsToken) return lsToken
  } catch {
    // localStorage 不可用
  }
  return _memoryToken
}

export function setRefreshToken(token: string | null) {
  _memoryRefreshToken = token
  try {
    if (token) {
      localStorage.setItem('refresh_token', token)
    } else {
      localStorage.removeItem('refresh_token')
    }
  } catch {
    // localStorage 不可用时静默跳过
  }
}

export function getRefreshToken(): string | null {
  try {
    const lsToken = localStorage.getItem('refresh_token')
    if (lsToken) return lsToken
  } catch {
    // localStorage 不可用
  }
  return _memoryRefreshToken
}

export function clearAuth() {
  _memoryToken = null
  _memoryRefreshToken = null
  try {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
  } catch {
    // localStorage 不可用时静默跳过
  }
}

function redirectToLogin() {
  _onUnauthorized?.()
  if (_router) {
    _router.push('/login')
  }
}

apiClient.interceptors.request.use((config) => {
  const token = getApiToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (!originalRequest) return Promise.reject(error)

    // 非 401 错误不处理
    if (error.response?.status !== 401) {
      return Promise.reject(error)
    }

    // 已经重试过一次仍然 401 → token 彻底失效，强制登录
    if (originalRequest._retry) {
      clearAuth()
      redirectToLogin()
      return Promise.reject(error)
    }

    // 尝试用 refresh token 续期
    const refreshToken = getRefreshToken()
    if (!refreshToken) {
      clearAuth()
      redirectToLogin()
      return Promise.reject(error)
    }

    // 已有其他请求在刷新中，排队等待
    if (_isRefreshing) {
      return new Promise((resolve, reject) => {
        _pendingRequests.push({ resolve, reject })
      }).then((newToken) => {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return apiClient(originalRequest)
      })
    }

    _isRefreshing = true
    originalRequest._retry = true

    try {
      const res = await axios.post('/api/v1/auth/refresh', {
        refresh_token: refreshToken,
      })

      const { access_token, refresh_token: newRefreshToken } = res.data
      setApiToken(access_token)
      setRefreshToken(newRefreshToken)

      _pendingRequests.forEach(({ resolve }) => resolve(access_token))
      _pendingRequests = []

      originalRequest.headers.Authorization = `Bearer ${access_token}`
      return apiClient(originalRequest)
    } catch (refreshError) {
      _pendingRequests.forEach(({ reject }) => reject(refreshError))
      _pendingRequests = []

      clearAuth()
      redirectToLogin()
      return Promise.reject(refreshError)
    } finally {
      _isRefreshing = false
    }
  }
)

export default apiClient
