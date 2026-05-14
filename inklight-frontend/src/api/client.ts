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

export function setRouter(router: Router) {
  _router = router
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
    if (!originalRequest) {
      return Promise.reject(error)
    }

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    const refreshToken = getRefreshToken()
    if (!refreshToken) {
      clearAuth()
      redirectToLogin()
      return Promise.reject(error)
    }

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
