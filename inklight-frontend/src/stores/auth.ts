import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient, { setApiToken, setRefreshToken, getApiToken, clearAuth } from '@/api/client'
import { cancelAllUserTasks } from '@/api/translate'

interface User {
  id: string
  email: string
  username: string | null
  is_admin: boolean
  avatar_style: string | null
  theme_color: string | null
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

  async function register(email: string, password: string, captchaId: string, captchaAnswer: string, emailVerificationCode: string, username?: string, agreedToTerms?: boolean, inviteCode?: string) {
    const res = await apiClient.post('/auth/register', {
      email,
      password,
      username: username || null,
      captcha_id: captchaId,
      captcha_answer: captchaAnswer,
      email_verification_code: emailVerificationCode,
      agreed_to_terms: agreedToTerms === true,
      invite_code: inviteCode || null,
    })
    return res.data
  }

  async function sendVerificationCode(email: string): Promise<string> {
    const res = await apiClient.post('/auth/send-verification-code', { email })
    return res.data.message
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
    try {
      await cancelAllUserTasks()
    } catch {
      // 取消失败不阻塞登出流程
    }
    token.value = null
    user.value = null
    clearAuth()
  }

  async function updateProfile(data: { username?: string; avatar_style?: string; theme_color?: string }) {
    const res = await apiClient.patch('/users/me', data)
    user.value = res.data
    return res.data
  }

  const avatarUrl = computed(() => {
    const style = user.value?.avatar_style || 'initials'
    const seed = user.value?.username || user.value?.email || 'user'
    return `https://api.dicebear.com/9.x/${style}/svg?seed=${encodeURIComponent(seed)}`
  })

  return {
    token,
    user,
    isLoggedIn,
    avatarUrl,
    setToken,
    login,
    register,
    fetchUser,
    fetchCaptcha,
    sendVerificationCode,
    updateProfile,
    logout,
  }
})
