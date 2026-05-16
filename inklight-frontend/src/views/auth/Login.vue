<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <el-icon :size="28"><Reading /></el-icon>
        </div>
        <h1 class="login-title">ScholarFocus</h1>
        <p class="login-subtitle">研墨文献 · 智能研读平台</p>
      </div>

      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" :rules="rules" ref="loginFormRef" label-position="top">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="loginForm.email" placeholder="请输入邮箱" size="large" class="login-input" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" show-password size="large" class="login-input" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleLogin" :loading="loading" class="login-btn">
                登录
              </el-button>
            </el-form-item>
            <div class="forgot-link-row">
              <router-link to="/forgot-password" class="forgot-link">忘记密码？</router-link>
            </div>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef" label-position="top">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="registerForm.email" placeholder="请输入邮箱" size="large" class="login-input" />
            </el-form-item>
            <el-form-item label="用户名" prop="username">
              <el-input v-model="registerForm.username" placeholder="请输入用户名" size="large" class="login-input" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" show-password size="large" class="login-input" />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input v-model="registerForm.confirmPassword" type="password" placeholder="请再次输入密码" show-password size="large" class="login-input" />
            </el-form-item>
            <el-form-item label="邀请码（选填）" prop="inviteCode">
              <el-input v-model="registerForm.inviteCode" placeholder="请输入邀请码（选填）" size="large" class="login-input" />
            </el-form-item>
            <el-form-item label="邮箱验证码" prop="emailVerifyCode">
              <div class="captcha-row">
                <el-input v-model="registerForm.emailVerifyCode" placeholder="请输入邮箱验证码" size="large" class="captcha-input" />
                <el-button
                  size="small"
                  :loading="emailCodeSending"
                  :disabled="emailCodeCooldown > 0 || !registerForm.email"
                  class="captcha-refresh-btn"
                  @click="handleSendEmailCode"
                >
                  {{ emailCodeCooldown > 0 ? `${emailCodeCooldown}s` : '发送验证码' }}
                </el-button>
              </div>
            </el-form-item>
            <el-form-item label="图形验证码" prop="captchaAnswer">
              <div class="captcha-row">
                <el-input v-model="registerForm.captchaAnswer" placeholder="请输入验证码" size="large" class="captcha-input" />
                <img
                  v-if="captchaImageBase64"
                  :src="'data:image/png;base64,' + captchaImageBase64"
                  class="captcha-image"
                  alt="验证码"
                  title="点击刷新验证码"
                  @click="refreshCaptcha"
                />
                <el-button text size="small" :loading="captchaLoading" class="captcha-refresh-btn" @click="refreshCaptcha">
                  换一张
                </el-button>
              </div>
            </el-form-item>
            <el-form-item>
              <div class="agreement-section">
                <el-checkbox v-model="registerForm.agreedToTerms">
                  <span>
                    我已阅读并同意
                    <router-link to="/terms-of-service" target="_blank">《用户服务协议》</router-link>
                    和
                    <router-link to="/privacy-policy" target="_blank">《隐私政策》</router-link>
                  </span>
                </el-checkbox>
              </div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleRegister" :loading="loading" class="login-btn">
                注册
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Reading } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import bgImage from '@/assets/bg_image.jpg'
import { tr } from 'element-plus/es/locale/index.mjs'

const bgUrl = `url(${bgImage})`

const router = useRouter()
const authStore = useAuthStore()
const activeTab = ref('login')
const loading = ref(false)
const loginFormRef = ref()
const registerFormRef = ref()
const captchaLoading = ref(false)
const captchaId = ref('')
const captchaImageBase64 = ref('')
const emailCodeSending = ref(false)
const emailCodeCooldown = ref(0)
let emailCooldownTimer: ReturnType<typeof setInterval> | null = null

const loginForm = reactive({
  email: '',
  password: ''
})

const registerForm = reactive({
  email: '',
  username: '',
  password: '',
  confirmPassword: '',
  captchaAnswer: '',
  emailVerifyCode: '',
  agreedToTerms: false,
  inviteCode: '',
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

const registerRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少3个字符', trigger: 'blur' },
    { max: 20, message: '用户名最多20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: Function) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  captchaAnswer: [
    { required: true, message: '请输入图形验证码', trigger: 'blur' },
    { min: 4, message: '验证码长度不正确', trigger: 'blur' },
  ],
  emailVerifyCode: [
    { required: true, message: '请输入邮箱验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' },
  ],
}

async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authStore.login(loginForm.email, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!registerForm.agreedToTerms) {
    ElMessage.warning('请先阅读并同意用户服务协议和隐私政策')
    return
  }
  loading.value = true
  try {
    await authStore.register(
      registerForm.email,
      registerForm.password,
      captchaId.value,
      registerForm.captchaAnswer,
      registerForm.emailVerifyCode,
      registerForm.username || undefined,
      registerForm.agreedToTerms,
      registerForm.inviteCode || undefined,
    )
    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
    registerForm.email = ''
    registerForm.username = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
    registerForm.captchaAnswer = ''
    registerForm.emailVerifyCode = ''
  } catch (e: any) {
    const detail = e.response?.data?.detail || '注册失败'
    ElMessage.error(detail)
    if (detail.includes('验证码')) {
      refreshCaptcha()
    }
  } finally {
    loading.value = false
  }
}

async function handleSendEmailCode() {
  if (!registerForm.email) { ElMessage.warning('请先输入邮箱'); return }
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRe.test(registerForm.email)) { ElMessage.warning('邮箱格式不正确'); return }

  emailCodeSending.value = true
  try {
    const msg = await authStore.sendVerificationCode(registerForm.email)
    ElMessage.success(msg)
    emailCodeCooldown.value = 60
    if (emailCooldownTimer) clearInterval(emailCooldownTimer)
    emailCooldownTimer = setInterval(() => {
      emailCodeCooldown.value--
      if (emailCodeCooldown.value <= 0) {
        if (emailCooldownTimer) clearInterval(emailCooldownTimer)
      }
    }, 1000)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    emailCodeSending.value = false
  }
}

async function refreshCaptcha() {
  captchaLoading.value = true
  try {
    const data = await authStore.fetchCaptcha()
    captchaId.value = data.captcha_id
    captchaImageBase64.value = data.image_base64
  } catch {
    ElMessage.error('获取验证码失败，请稍后重试')
  } finally {
    captchaLoading.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'register') {
    refreshCaptcha()
  }
})

onMounted(() => {
  if (activeTab.value === 'register') {
    refreshCaptcha()
  }
})
</script>

<style scoped>
.login-page {
  box-sizing: border-box;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: v-bind(bgUrl) no-repeat center center;
  background-size: cover;
  padding: 20px;
  overflow: hidden;
}

.login-card {
  width: 440px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-3xl);
  padding: 40px 36px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.login-logo {
  width: 52px;
  height: 52px;
  background: var(--accent-primary);
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 14px;
  box-shadow: 0 8px 16px -4px rgba(13, 148, 136, 0.3);
  color: #ffffff;
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 6px;
  letter-spacing: -0.5px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.login-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--accent-primary);
}

.login-tabs :deep(.el-tabs__item.is-active) {
  color: var(--accent-primary);
  font-weight: 600;
}

.login-tabs :deep(.el-tabs__item:hover) {
  color: var(--accent-primary);
}

.login-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  box-shadow: none !important;
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.5);
  transition: background 0.2s ease, border-color 0.2s ease;
}

.login-input :deep(.el-input__wrapper:hover) {
  border-color: var(--teal-300);
  background: rgba(255, 255, 255, 0.7);
  box-shadow: none !important;
}

.login-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: none !important;
  background: rgba(255, 255, 255, 0.85);
}

.login-input :deep(.el-input__wrapper:-webkit-autofill),
.login-input :deep(.el-input__wrapper:autofill) {
  box-shadow: none !important;
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  border-radius: var(--radius-lg);
  margin-top: 4px;
}

.forgot-link-row {
  text-align: right;
  margin-top: -8px;
}

.forgot-link {
  font-size: 13px;
  color: var(--accent-primary);
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.captcha-input {
  flex: 1;
  min-width: 120px;
}

.captcha-image {
  height: 42px;
  width: 130px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  flex-shrink: 0;
  object-fit: contain;
  background: var(--bg-primary);
}

.captcha-image:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.15);
}

.captcha-refresh-btn {
  flex-shrink: 0;
  white-space: nowrap;
}

.agreement-section {
  margin-top: -8px;
  margin-bottom: 4px;
}

.agreement-section :deep(.el-checkbox__label) {
  font-size: 13px;
  color: var(--text-secondary, #666);
  line-height: 1.5;
}

.agreement-section a {
  color: var(--accent-primary);
  text-decoration: none;
}

.agreement-section a:hover {
  text-decoration: underline;
}
</style>
