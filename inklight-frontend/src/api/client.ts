import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 60000
})

let _memoryToken: string | null = null

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
  (error) => {
    if (error.response?.status === 401) {
      console.error('[API 401] Token present:', !!getApiToken(), 'URL:', error.config?.url)
    }
    return Promise.reject(error)
  }
)

export default apiClient
