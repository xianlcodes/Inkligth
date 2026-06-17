<template>
  <div class="register-page">
    <!-- 左侧：品牌视觉 -->
    <div class="left-panel">
      <div class="left-top">
        <div class="brand-mark">
          <img :src="quillLogo" alt="InkLight" class="brand-img" />
        </div>
        <span class="brand-name">InkLight</span>
      </div>

      <div class="left-center">
        <div class="value-props">
          <div class="value-item">
            <div class="value-icon" style="background:rgba(56,189,248,0.15)">
              <span class="value-dot" style="background:#38bdf8" />
            </div>
            <div class="value-text">
              <span class="value-title">文献管理</span>
              <span class="value-desc">智能分类、全文检索、引用导出</span>
            </div>
          </div>
          <div class="value-item">
            <div class="value-icon" style="background:rgba(52,211,153,0.15)">
              <span class="value-dot" style="background:#34d399" />
            </div>
            <div class="value-text">
              <span class="value-title">AI 辅助</span>
              <span class="value-desc">智能翻译、学术写作、论文评审</span>
            </div>
          </div>
          <div class="value-item">
            <div class="value-icon" style="background:rgba(251,191,36,0.15)">
              <span class="value-dot" style="background:#fbbf24" />
            </div>
            <div class="value-text">
              <span class="value-title">协作分享</span>
              <span class="value-desc">组会汇报、笔记共享、团队协作</span>
            </div>
          </div>
        </div>
      </div>

      <div class="typewriter-wrapper">
        <TypewriterHeader />
      </div>

      <div class="decor-blur-1" />
      <div class="decor-blur-2" />
      <div class="decor-grid" />
    </div>

    <!-- 右侧：注册表单 -->
    <div class="right-panel">
      <div class="right-decor-blur-1" />
      <div class="right-decor-blur-2" />
      <div class="right-decor-blur-3" />
      <div class="right-decor-grid" />

      <div class="form-wrapper">
        <div class="mobile-logo">
          <div class="mobile-logo-icon">
            <el-icon color="var(--accent-primary)" :size="18"><Reading /></el-icon>
          </div>
          <span>InkLight 研墨</span>
        </div>

        <div class="form-card">
          <div class="form-header">
            <div class="form-greeting">欢迎加入</div>
            <h1 class="form-title">创建新账号</h1>
            <p class="form-subtitle">研墨文献 · 智能研读 · 高效写作</p>
          </div>

          <el-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            label-position="top"
            class="register-form"
            hide-required-asterisk
          >
            <div class="form-row">
              <div class="form-col">
                <div class="field-label">邮箱 <span class="field-required">*</span></div>
                <el-form-item prop="email">
                  <el-input
                    v-model="registerForm.email"
                    placeholder="输入您的邮箱"
                    size="large"
                    class="reg-input"
                    :prefix-icon="Message"
                  />
                </el-form-item>
              </div>
              <div class="form-col">
                <div class="field-label">用户名 <span class="field-required">*</span></div>
                <el-form-item prop="username">
                  <el-input
                    v-model="registerForm.username"
                    placeholder="给自己取个名字"
                    size="large"
                    class="reg-input"
                  />
                </el-form-item>
              </div>
            </div>

            <div class="form-row">
              <div class="form-col">
                <div class="field-label">密码 <span class="field-required">*</span></div>
                <el-form-item prop="password">
                  <el-input
                    v-model="registerForm.password"
                    type="password"
                    placeholder="至少6位密码"
                    show-password
                    size="large"
                    class="reg-input"
                  />
                </el-form-item>
              </div>
              <div class="form-col">
                <div class="field-label">确认密码 <span class="field-required">*</span></div>
                <el-form-item prop="confirmPassword">
                  <el-input
                    v-model="registerForm.confirmPassword"
                    type="password"
                    placeholder="再次输入密码"
                    show-password
                    size="large"
                    class="reg-input"
                  />
                </el-form-item>
              </div>
            </div>

            <div class="form-section-divider">
              <span class="section-divider-line" />
              <span class="section-divider-label">安全验证</span>
              <span class="section-divider-line" />
            </div>

            <div class="field-label">邮箱验证码 <span class="field-required">*</span></div>
            <el-form-item prop="emailVerifyCode">
              <div class="code-input-row">
                <el-input
                  v-model="registerForm.emailVerifyCode"
                  placeholder="6位验证码"
                  size="large"
                  class="code-input"
                />
                <el-button
                  :loading="emailCodeSending"
                  :disabled="emailCodeCooldown > 0 || !registerForm.email"
                  class="code-btn"
                  @click="handleSendEmailCode"
                >
                  {{ emailCodeCooldown > 0 ? `${emailCodeCooldown}s` : '发送验证码' }}
                </el-button>
              </div>
            </el-form-item>

            <div class="field-label">图形验证码 <span class="field-required">*</span></div>
            <el-form-item prop="captchaAnswer">
              <div class="code-input-row captcha-input-row">
                <el-input
                  v-model="registerForm.captchaAnswer"
                  placeholder="输入验证码"
                  size="large"
                  class="code-input"
                />
                <img
                  v-if="captchaImageBase64"
                  :src="'data:image/png;base64,' + captchaImageBase64"
                  class="captcha-image"
                  alt="验证码"
                  title="点击刷新"
                  @click="refreshCaptcha"
                />
                <el-button text :loading="captchaLoading" class="code-btn-refresh" @click="refreshCaptcha">
                  换一张
                </el-button>
              </div>
            </el-form-item>

            <div class="form-section-divider">
              <span class="section-divider-line" />
              <span class="section-divider-label">选填</span>
              <span class="section-divider-line" />
            </div>

            <div class="field-label">邀请码 <span class="field-optional">（选填）</span></div>
            <el-form-item prop="inviteCode">
              <el-input
                v-model="registerForm.inviteCode"
                placeholder="如果有邀请码，请输入"
                size="large"
                class="reg-input"
              />
            </el-form-item>

            <div class="agreement-section">
              <el-checkbox v-model="registerForm.agreedToTerms">
                <span class="agree-text">
                  我已阅读并同意
                  <router-link to="/terms-of-service" target="_blank">《用户服务协议》</router-link>
                  和
                  <router-link to="/privacy-policy" target="_blank">《隐私政策》</router-link>
                </span>
              </el-checkbox>
            </div>

            <el-form-item style="margin-bottom: 0">
              <el-button
                type="primary"
                :loading="loading"
                class="submit-btn"
                @click="handleRegister"
              >
                {{ loading ? '注册中...' : '创建账号' }}
              </el-button>
            </el-form-item>
          </el-form>

          <div class="login-link-row">
            <span class="login-primary">已有账号？<router-link to="/login" class="login-link">去登录</router-link></span>
          </div>
        </div>
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
import TypewriterHeader from '@/components/business/TypewriterHeader.vue'
import { Reading, Message } from '@element-plus/icons-vue'
import quillLogo from '@/assets/quill.png'
import { useAuthStore } from '@/stores/auth'

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
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  position: relative;
}


/* ═══════════════════════════════════════════════════════════════
   左侧面板
   ═══════════════════════════════════════════════════════════════ */

.left-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px;
  background: linear-gradient(to right, #0f172a 0%, #162d50 25%, #1a5a70 50%, #5a7a75 78%, #9aaca0 100%);
  overflow: hidden;
}

@media (max-width: 1024px) {
  .left-panel {
    display: none;
  }
}

.left-top {
  position: absolute;
  top: 48px;
  left: 48px;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.5px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  backdrop-filter: blur(8px);
}

.brand-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.brand-name {
  font-family: 'Cinzel', 'Georgia', serif;
  color: #ffffff;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 2.5px;
  text-transform: uppercase;
}

.typewriter-wrapper {
  position: absolute;
  left: 0;
  right: 0;
  top: 100px;
  z-index: 25;
  display: flex;
  justify-content: center;
  pointer-events: none;
}

.left-center {
  position: relative;
  z-index: 20;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.value-props {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.value-item {
  display: flex;
  align-items: center;
  gap: 14px;
}

.value-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.value-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.value-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.value-title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.value-desc {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.left-footer {
  position: relative;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 24px;
}

.left-footer a {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
  text-decoration: none;
  transition: color 0.2s;
}

.left-footer a:hover {
  color: rgba(255, 255, 255, 0.85);
}

.decor-blur-1 {
  position: absolute;
  top: 15%;
  right: 10%;
  width: 300px;
  height: 300px;
  background: rgba(56, 189, 248, 0.2);
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  z-index: 0;
}

.decor-blur-2 {
  position: absolute;
  bottom: 10%;
  left: 5%;
  width: 400px;
  height: 400px;
  background: rgba(2, 132, 199, 0.25);
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
  z-index: 0;
}

.decor-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 1;
}

/* ═══════════════════════════════════════════════════════════════
   右侧面板
   ═══════════════════════════════════════════════════════════════ */

.right-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
  background: linear-gradient(to right, #9aaca0 0%, #b8bdb2 18%, #d5cec2 38%, #ede8df 65%, #f5f1eb 100%);
  position: relative;
  overflow: hidden;
}

.right-decor-blur-1 {
  position: absolute;
  top: 8%;
  left: -8%;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(90,117,112,0.1) 0%, rgba(2,132,199,0.04) 40%, transparent 70%);
  border-radius: 50%;
  filter: blur(70px);
  pointer-events: none;
  z-index: 0;
}

.right-decor-blur-2 {
  position: absolute;
  bottom: 5%;
  right: 8%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(16,185,129,0.06) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  z-index: 0;
}

.right-decor-blur-3 {
  position: absolute;
  top: 40%;
  right: 15%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(245,158,11,0.05) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(50px);
  pointer-events: none;
  z-index: 0;
}

.right-decor-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(42,35,30,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(42,35,30,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
  z-index: 0;
}

.form-wrapper {
  width: 100%;
  max-width: 460px;
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-bottom: 20px;
}

.mobile-logo {
  display: none;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 36px;
}

@media (max-width: 1024px) {
  .mobile-logo {
    display: flex;
  }
}

.mobile-logo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(2,132,199,0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ─── Form Card ─── */

.form-card {
  width: 100%;
  background: rgba(255,255,255,0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(221,214,200,0.25);
  border-radius: 16px;
  padding: 22px 28px 18px;
  box-shadow:
    0 1px 3px rgba(42,35,30,0.04),
    0 8px 32px rgba(42,35,30,0.06);
}

.form-header {
  text-align: center;
  margin-bottom: 18px;
}

.form-greeting {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.15em;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.form-title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 0 0 4px;
  line-height: 1.3;
}

.form-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.5;
}

/* ─── Form Layout ─── */

.register-form {
  width: 100%;
}

.form-row {
  display: flex;
  gap: 16px;
  width: 100%;
}

.form-col {
  flex: 1;
  min-width: 0;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 4px;
  letter-spacing: 0.2px;
}

.field-required {
  color: var(--rose-500);
}

.field-optional {
  color: var(--text-muted);
  font-weight: 400;
}

/* ─── Section Divider ─── */

.form-section-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0 10px;
}

.section-divider-line {
  flex: 1;
  height: 1px;
  background: rgba(221,214,200,0.35);
}

.section-divider-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  white-space: nowrap;
}

/* ─── Form Fields ─── */

.register-form :deep(.el-form-item) {
  margin-bottom: 10px;
}

.reg-input :deep(.el-input__wrapper) {
  height: 40px;
  background: rgba(255,255,255,0.7) !important;
  border: 1px solid rgba(221,214,200,0.3) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
  padding-left: 12px;
}

.reg-input :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary) !important;
}

.reg-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary) !important;
  box-shadow: 0 0 0 3px rgba(2,132,199,0.08) !important;
  background: rgba(255,255,255,0.9) !important;
}

.reg-input :deep(.el-input__inner) {
  background: transparent !important;
  font-size: 14px !important;
  color: var(--text-primary) !important;
}

.reg-input :deep(.el-input__inner::placeholder) {
  color: #c0c4cc !important;
}

.reg-input :deep(.el-input__prefix-inner) {
  color: #b0b7c3;
  font-size: 15px;
  margin-right: 6px;
}

/* ─── Code Input Row ─── */

.code-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.code-input {
  flex: 1;
}

.code-input :deep(.el-input__wrapper) {
  height: 40px;
  background: rgba(255,255,255,0.7) !important;
  border: 1px solid rgba(221,214,200,0.3) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
  padding-left: 12px;
}

.code-input :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary) !important;
}

.code-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary) !important;
  box-shadow: 0 0 0 3px rgba(2,132,199,0.08) !important;
  background: rgba(255,255,255,0.9) !important;
}

.code-input :deep(.el-input__inner) {
  background: transparent !important;
  font-size: 14px !important;
  color: var(--text-primary) !important;
}

.code-input :deep(.el-input__inner::placeholder) {
  color: #c0c4cc !important;
}

.code-btn {
  flex-shrink: 0;
  white-space: nowrap;
  height: 40px;
}

.code-btn-refresh {
  flex-shrink: 0;
  white-space: nowrap;
  padding: 0 8px;
}

.captcha-image {
  height: 40px;
  width: 110px;
  border: 1px solid rgba(221,214,200,0.3);
  border-radius: 8px;
  cursor: pointer;
  flex-shrink: 0;
  object-fit: contain;
  background: rgba(255,255,255,0.5);
}

.captcha-image:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(2,132,199,0.1);
}

/* ─── Agreement ─── */

.agreement-section {
  margin: 4px 0 2px;
}

.agreement-section :deep(.el-checkbox__label) {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.agree-text a {
  color: var(--accent-primary);
  text-decoration: none;
}

.agree-text a:hover {
  text-decoration: underline;
}

/* ─── Submit Button ─── */

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 10px;
  background: var(--accent-primary) !important;
  border-color: var(--accent-primary) !important;
  letter-spacing: 0.5px;
  margin-top: 0;
}

.submit-btn:hover {
  background: var(--accent-hover) !important;
  border-color: var(--accent-hover) !important;
  transform: translateY(-1px);
}

.submit-btn:active {
  opacity: 0.85;
  transform: scale(0.98);
}

/* ─── Divider ─── */

.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0 0;
  font-size: 13px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(221,214,200,0.4);
}

.divider span {
  color: var(--text-muted);
  white-space: nowrap;
}

/* ─── Login Link ─── */

.login-link-row {
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 16px;
}

.login-primary {
  display: block;
  line-height: 1.6;
}

.login-link {
  color: var(--accent-primary);
  font-weight: 500;
  text-decoration: none;
}

.login-link:hover {
  text-decoration: underline;
  color: var(--accent-hover);
}

.forgot-link {
  display: inline-block;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
  text-decoration: none;
  opacity: 0.55;
  transition: opacity 0.2s, color 0.2s;
}

.forgot-link:hover {
  opacity: 1;
  color: var(--accent-primary);
}

/* ─── ICP footer ─── */

.icp-footer {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  text-align: center;
  white-space: nowrap;
  z-index: 10;
  pointer-events: none;
}

.icp-footer a {
  pointer-events: auto;
  display: inline-block;
  font-size: 12px;
  color: rgba(42, 35, 30, 0.3);
  text-decoration: none;
  transition: color 0.2s ease;
}

.icp-footer a:hover {
  color: rgba(42, 35, 30, 0.6);
  text-decoration: underline;
}

/* ═══════════════════════════════════════════════════════════════
   移动端响应
   ═══════════════════════════════════════════════════════════════ */

@media (max-width: 1024px) {
  .register-page {
    grid-template-columns: 1fr;
  }

  .right-panel {
    min-height: 100vh;
  }

  .form-title {
    font-size: 22px;
  }

  .form-card {
    padding: 28px 24px 24px;
  }

  .form-row {
    flex-direction: column;
    gap: 0;
  }

  .icp-footer {
    bottom: 16px;
  }
}

@media (max-width: 480px) {
  .right-panel {
    padding: 24px 16px;
  }

  .form-wrapper {
    max-width: 100%;
  }

  .form-card {
    padding: 24px 18px 20px;
    border-radius: 12px;
  }

  .form-header {
    margin-bottom: 24px;
  }

  .form-title {
    font-size: 20px;
  }

  .submit-btn {
    height: 44px;
    font-size: 14px;
  }

  .code-btn {
    font-size: 12px;
    padding: 0 10px;
  }

  .captcha-image {
    width: 90px;
    height: 40px;
  }
}
</style>
