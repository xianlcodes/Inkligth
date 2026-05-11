import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 60000
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  console.log('[API Request]', config.method?.toUpperCase(), config.url, 'HasToken:', !!token)
  return config
}, (error) => {
  return Promise.reject(error)
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const token = localStorage.getItem('token')
      console.error('[API 401] Token present:', !!token, 'Length:', token?.length, 'URL:', error.config?.url)
    }
    return Promise.reject(error)
  }
)

export default apiClient
