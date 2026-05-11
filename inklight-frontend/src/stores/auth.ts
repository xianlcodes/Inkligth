import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api/client'

interface User {
  id: string
  email: string
  username: string | null
  created_at: string
  updated_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)
  const isLoggedIn = computed(() => !!token.value)

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function clearAuth() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  async function login(email: string, password: string) {
    const params = new URLSearchParams()
    params.append('username', email)
    params.append('password', password)
    const res = await apiClient.post('/auth/token', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    setToken(res.data.access_token)
    await fetchUser()
    return res.data
  }

  async function register(email: string, password: string, username?: string) {
    const res = await apiClient.post('/auth/register', {
      email,
      password,
      username: username || null
    })
    return res.data
  }

  async function fetchUser() {
    if (!token.value) return
    const res = await apiClient.get('/users/me')
    user.value = res.data
  }

  function logout() {
    clearAuth()
  }

  return {
    token,
    user,
    isLoggedIn,
    setToken,
    clearAuth,
    login,
    register,
    fetchUser,
    logout
  }
})
