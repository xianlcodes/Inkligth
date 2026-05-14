import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient, { setApiToken, setRefreshToken, getApiToken, clearAuth } from '@/api/client'

interface User {
  id: string
  email: string
  username: string | null
  is_admin: boolean
  created_at: string
  updated_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getApiToken())
  const user = ref<User | null>(null)
  const isLoggedIn = computed(() => !!token.value)

  function setToken(newToken: string) {
    token.value = newToken
    setApiToken(newToken)
  }

  async function login(email: string, password: string) {
    const params = new URLSearchParams()
    params.append('username', email)
    params.append('password', password)
    const res = await apiClient.post('/auth/token', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    const { access_token, refresh_token, is_admin } = res.data
    setToken(access_token)
    setRefreshToken(refresh_token)
    user.value = {
      id: '',
      email,
      username: null,
      is_admin: is_admin === true,
      created_at: '',
      updated_at: '',
    }
    try {
      await fetchUser()
    } catch {
      // fetchUser 失败不影响已登录状态
    }
    return res.data
  }

  async function register(email: string, password: string, captchaId: string, captchaAnswer: string, username?: string) {
    const res = await apiClient.post('/auth/register', {
      email,
      password,
      username: username || null,
      captcha_id: captchaId,
      captcha_answer: captchaAnswer,
    })
    return res.data
  }

  async function fetchUser() {
    if (!token.value) return
    const res = await apiClient.get('/users/me')
    user.value = res.data
  }

  async function fetchCaptcha(): Promise<{ captcha_id: string; image_base64: string }> {
    const res = await apiClient.get('/auth/captcha')
    return res.data
  }

  async function logout() {
    try {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        await apiClient.post('/auth/logout', { refresh_token: refreshToken })
      }
    } catch {
      // logout 失败不阻塞本地清理
    }
    token.value = null
    user.value = null
    clearAuth()
  }

  return {
    token,
    user,
    isLoggedIn,
    setToken,
    login,
    register,
    fetchUser,
    fetchCaptcha,
    logout,
  }
})
