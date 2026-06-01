<template>
  <div class="forgot-page">
    <div class="forgot-card">
      <div class="forgot-header">
        <div class="forgot-logo">
          <el-icon :size="28"><Reading /></el-icon>
        </div>
        <h1 class="forgot-title">ScholarFocus</h1>
        <p class="forgot-subtitle">重置密码</p>
      </div>

      <template v-if="step === 1">
        <el-form :model="emailForm" :rules="emailRules" ref="emailFormRef" label-position="top">
          <el-form-item label="邮箱" prop="email">
            <el-input
              v-model="emailForm.email"
              placeholder="请输入注册邮箱"
              size="large"
              class="forgot-input"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSendCode" :loading="sending" class="forgot-btn">
              发送验证码
            </el-button>
          </el-form-item>
        </el-form>
      </template>

      <template v-if="step === 2">
        <div class="success-banner">
          <el-icon class="success-icon"><SuccessFilled /></el-icon>
          <div class="success-text">
            <strong>验证码已发送</strong>
            <span>一封包含6位验证码的邮件已发送至 {{ emailForm.email }}，有效期15分钟</span>
          </div>
        </div>
        <el-form :model="codeForm" :rules="codeRules" ref="codeFormRef" label-position="top" class="code-form">
          <el-form-item label="验证码" prop="code">
            <el-input
              v-model="codeForm.code"
              placeholder="请输入6位验证码"
              size="large"
              maxlength="6"
              class="forgot-input code-input"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleVerifyCode" :loading="verifying" class="forgot-btn">
              验证
            </el-button>
          </el-form-item>
        </el-form>
        <div class="step-links">
          <el-button text type="primary" size="small" :disabled="resendCooldown > 0" @click="handleResend">
            {{ resendCooldown > 0 ? `${resendCooldown}秒后重新发送` : '重新发送验证码' }}
          </el-button>
          <el-button text size="small" @click="step = 1">更换邮箱</el-button>
        </div>
      </template>

      <template v-if="step === 3">
        <div class="success-banner">
          <el-icon class="success-icon"><SuccessFilled /></el-icon>
          <div class="success-text">
            <strong>验证通过</strong>
            <span>请设置您的新密码</span>
          </div>
        </div>
        <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-position="top" class="code-form">
          <el-form-item label="新密码" prop="password">
            <el-input
              v-model="passwordForm.password"
              type="password"
              placeholder="至少8位，含大小写字母和数字"
              show-password
              size="large"
              class="forgot-input"
            />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="passwordForm.confirmPassword"
              type="password"
              placeholder="再次输入新密码"
              show-password
              size="large"
              class="forgot-input"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleResetPassword" :loading="resetting" class="forgot-btn">
              重置密码
            </el-button>
          </el-form-item>
        </el-form>
      </template>

      <div class="forgot-footer">
        <router-link to="/login" class="back-link">
          <el-icon><ArrowLeft /></el-icon>
          返回登录
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Reading, ArrowLeft, SuccessFilled } from '@element-plus/icons-vue'
import apiClient from '@/api/client'
import bgImage from '@/assets/bg_image.jpg'

const bgUrl = `url(${bgImage})`

const router = useRouter()
const step = ref(1)
const sending = ref(false)
const verifying = ref(false)
const resetting = ref(false)
const verificationId = ref('')
const resendCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

const emailFormRef = ref()
const codeFormRef = ref()
const passwordFormRef = ref()

const emailForm = reactive({ email: '' })
const codeForm = reactive({ code: '' })
const passwordForm = reactive({ password: '', confirmPassword: '' })

const emailRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
}

const codeRules = {
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' },
  ],
}

const passwordRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: Function) => {
        if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(value)) {
          callback(new Error('密码需包含大小写字母和数字'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: Function) => {
        if (value !== passwordForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function startCooldown() {
  resendCooldown.value = 60
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    resendCooldown.value--
    if (resendCooldown.value <= 0) {
      if (cooldownTimer) clearInterval(cooldownTimer)
    }
  }, 1000)
}

async function handleSendCode() {
  const valid = await emailFormRef.value?.validate().catch(() => false)
  if (!valid) return
  sending.value = true
  try {
    const resp = await apiClient.post('/auth/forgot-password', { email: emailForm.email })
    ElMessage.success(resp.data.message || '验证码已发送')
    step.value = 2
    startCooldown()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    sending.value = false
  }
}

async function handleResend() {
  if (resendCooldown.value > 0) return
  sending.value = true
  try {
    const resp = await apiClient.post('/auth/forgot-password', { email: emailForm.email })
    ElMessage.success(resp.data.message || '验证码已发送')
    startCooldown()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    sending.value = false
  }
}

async function handleVerifyCode() {
  const valid = await codeFormRef.value?.validate().catch(() => false)
  if (!valid) return
  verifying.value = true
  try {
    const resp = await apiClient.post('/auth/verify-reset-code', {
      email: emailForm.email,
      code: codeForm.code,
    })
    verificationId.value = resp.data.verification_id
    ElMessage.success('验证通过')
    step.value = 3
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '验证码错误')
  } finally {
    verifying.value = false
  }
}

async function handleResetPassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  resetting.value = true
  try {
    await apiClient.post('/auth/reset-password', {
      email: emailForm.email,
      verification_id: verificationId.value,
      new_password: passwordForm.password,
    })
    ElMessage.success('密码重置成功，请使用新密码登录')
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.forgot-page {
  position: relative;
  box-sizing: border-box;
  height: 100vh;
  height: 100dvh;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: v-bind(bgUrl) no-repeat center center;
  background-size: cover;
  padding: 20px;
}

.forgot-card {
  width: 420px;
  max-width: 100%;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-3xl);
  padding: 40px 36px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.forgot-header {
  text-align: center;
  margin-bottom: 28px;
}

.forgot-logo {
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

.forgot-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 6px;
  letter-spacing: -0.5px;
}

.forgot-subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.forgot-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  box-shadow: none !important;
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.5);
  transition: background 0.2s ease, border-color 0.2s ease;
}

.forgot-input :deep(.el-input__wrapper:hover) {
  border-color: var(--teal-300);
  background: rgba(255, 255, 255, 0.7);
  box-shadow: none !important;
}

.forgot-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: none !important;
  background: rgba(255, 255, 255, 0.85);
}

.forgot-input :deep(.el-input__wrapper:-webkit-autofill),
.forgot-input :deep(.el-input__wrapper:autofill) {
  box-shadow: none !important;
}

.code-input :deep(input) {
  font-size: 24px;
  letter-spacing: 8px;
  text-align: center;
}

.forgot-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  border-radius: var(--radius-lg);
  margin-top: 4px;
}

.success-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
}

.success-icon {
  font-size: 22px;
  color: #16a34a;
  flex-shrink: 0;
  margin-top: 1px;
}

.success-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.success-text strong {
  font-size: 14px;
  color: #166534;
}

.success-text span {
  font-size: 13px;
  color: #15803d;
  line-height: 1.5;
}

.code-form {
  margin-top: 4px;
}

.step-links {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
}

.forgot-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--accent-primary);
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

/* === Mobile Responsive === */
@media (max-width: 640px) {
  .forgot-page {
    padding: 0;
    align-items: flex-start;
    justify-content: flex-start;
  }

  .forgot-card {
    width: 100%;
    border-radius: 0;
    padding: 40px 20px;
    min-height: 100vh;
    min-height: 100dvh;
    box-shadow: none;
    border: none;
    background: rgba(255, 255, 255, 0.88);
  }

  .forgot-header {
    margin-bottom: 20px;
  }

  .forgot-logo {
    width: 44px;
    height: 44px;
    margin-bottom: 10px;
  }

  .forgot-title {
    font-size: 20px;
  }

  .forgot-subtitle {
    font-size: 13px;
  }

  .forgot-btn {
    height: 42px;
    font-size: 15px;
  }

  .success-banner {
    padding: 12px;
  }

  .success-text strong {
    font-size: 13px;
  }

  .success-text span {
    font-size: 12px;
  }

  .step-links {
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .forgot-footer {
    margin-top: 20px;
    padding-top: 16px;
  }
}

/* Very small screens */
@media (max-width: 360px) {
  .forgot-card {
    padding: 24px 14px;
  }

  .forgot-title {
    font-size: 18px;
  }
}
</style>
