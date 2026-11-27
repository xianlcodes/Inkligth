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
  tutorial_completed: boolean
  created_at: string
  updated_at: string
  // 平台免费额度（/users/me 实时返回）
  has_ai_engine: boolean      // 是否已配置自己的 AI 引擎（自配 Key 无限量）
  free_translations: number   // 平台免费额度剩余（篇）
  free_translations_used: number
  prefer_free_quota: boolean  // 翻译通道偏好：优先使用免费额度
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getApiToken())
  const user = ref<User | null>(null)
  const isLoggedIn = computed(() => !!token.value)
  /** 用户详情是否已加载：登录/会话恢复后置位，守卫据此跳过重复的 /users/me */
  const userLoaded = ref(false)

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
      tutorial_completed: false,
      created_at: '',
      updated_at: '',
      has_ai_engine: false,
      free_translations: 0,
      free_translations_used: 0,
      prefer_free_quota: false,
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
    // 用户详情已就绪：登录后的路由守卫不必重复请求 /users/me
    userLoaded.value = true
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
    userLoaded.value = false
    clearAuth()
  }

  /** 切换翻译通道偏好：优先免费额度 / 优先自有 Key（返回更新后的用户信息） */
  async function setQuotaPreference(preferFree: boolean) {
    const res = await apiClient.patch<User>('/users/me/quota-preference', { prefer_free: preferFree })
    user.value = res.data
    return res.data
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
    userLoaded,
    isLoggedIn,
    setQuotaPreference,
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
