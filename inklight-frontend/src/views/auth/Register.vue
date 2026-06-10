<template>
  <div class="register-page">
    <div class="register-card">
      <div class="register-header">
        <div class="register-logo">
          <el-icon :size="28"><Reading /></el-icon>
        </div>
        <h1 class="register-title">InkLight</h1>
        <p class="register-subtitle">创建新账号</p>
      </div>

      <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef" label-position="top">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="registerForm.email" placeholder="请输入邮箱" size="large" class="register-input" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="registerForm.username" placeholder="请输入用户名" size="large" class="register-input" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" show-password size="large" class="register-input" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="registerForm.confirmPassword" type="password" placeholder="请再次输入密码" show-password size="large" class="register-input" />
        </el-form-item>
        <el-form-item label="邀请码（选填）" prop="inviteCode">
          <el-input v-model="registerForm.inviteCode" placeholder="请输入邀请码（选填）" size="large" class="register-input" />
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
          <el-button type="primary" @click="handleRegister" :loading="loading" class="register-btn">
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-link-row">
        <span>已有账号？</span>
        <router-link to="/login" class="login-link">去登录</router-link>
      </div>
    </div>

    <div class="icp-footer">
      <a href="http://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">渝ICP备2026008976号</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Reading } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import bgImage from '@/assets/bg_image.jpg'

const bgUrl = `url(${bgImage})`

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const registerFormRef = ref()
const captchaLoading = ref(false)
const captchaId = ref('')
const captchaImageBase64 = ref('')
const emailCodeSending = ref(false)
const emailCodeCooldown = ref(0)
let emailCooldownTimer: ReturnType<typeof setInterval> | null = null

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
    router.push('/login')
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

onMounted(() => {
  refreshCaptcha()
})
</script>

<style scoped>
.register-page {
  position: relative;
  box-sizing: border-box;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: v-bind(bgUrl) no-repeat center center;
  background-size: cover;
  padding: 40px 20px;
}

.register-card {
  width: 440px;
  max-width: 100%;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-3xl);
  padding: 40px 36px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.08);
  margin-top: 20px;
}

.register-header {
  text-align: center;
  margin-bottom: 24px;
}

.register-logo {
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

.register-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 6px;
  letter-spacing: -0.5px;
}

.register-subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.register-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  box-shadow: none !important;
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.5);
  transition: background 0.2s ease, border-color 0.2s ease;
}

.register-input :deep(.el-input__wrapper:hover) {
  border-color: var(--sky-300);
  background: rgba(255, 255, 255, 0.7);
  box-shadow: none !important;
}

.register-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: none !important;
  background: rgba(255, 255, 255, 0.85);
}

.register-input :deep(.el-input__wrapper:-webkit-autofill),
.register-input :deep(.el-input__wrapper:autofill) {
  box-shadow: none !important;
}

.register-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  border-radius: var(--radius-lg);
  margin-top: 4px;
}

.login-link-row {
  text-align: center;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
  font-size: 14px;
  color: var(--text-secondary);
}

.login-link {
  color: var(--accent-primary);
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
}

.login-link:hover {
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
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
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

.icp-footer {
  margin-top: auto;
  padding: 16px 0 12px;
  text-align: center;
  white-space: nowrap;
}

.icp-footer a {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
  text-decoration: none;
  transition: color 0.2s ease;
}

.icp-footer a:hover {
  color: rgba(255, 255, 255, 0.9);
  text-decoration: underline;
}

/* === Mobile Responsive === */
@media (max-width: 640px) {
  .register-page {
    padding: 20px 12px;
  }

  .register-card {
    width: 100%;
    padding: 28px 18px;
    border-radius: var(--radius-2xl);
  }

  .register-header {
    margin-bottom: 18px;
  }

  .register-logo {
    width: 44px;
    height: 44px;
    margin-bottom: 10px;
  }

  .register-logo :deep(.el-icon) {
    font-size: 22px !important;
  }

  .register-title {
    font-size: 20px;
    margin-bottom: 4px;
  }

  .register-subtitle {
    font-size: 13px;
  }

  .register-btn {
    height: 42px;
    font-size: 15px;
  }

  .captcha-row {
    flex-wrap: wrap;
    gap: 8px;
  }

  .captcha-input {
    min-width: 100px;
  }

  .captcha-image {
    width: 90px;
    height: 36px;
  }

  .captcha-refresh-btn {
    font-size: 12px;
    padding: 0 8px;
  }

  .agreement-section {
    margin-top: -4px;
  }

  .agreement-section :deep(.el-checkbox__label) {
    font-size: 12px;
  }

  .icp-footer a {
    font-size: 11px;
  }

  :deep(.el-form-item) {
    margin-bottom: 18px;
  }

  :deep(.el-form-item__label) {
    padding-bottom: 4px;
    font-size: 13px;
  }
}

/* Very small screens */
@media (max-width: 360px) {
  .register-card {
    padding: 20px 14px;
  }

  .register-title {
    font-size: 18px;
  }

  .captcha-row {
    flex-direction: column;
    align-items: stretch;
  }

  .captcha-image {
    width: 100%;
    height: 40px;
  }

  .register-btn {
    height: 40px;
    font-size: 14px;
  }
}
</style>
